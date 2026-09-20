"""One temporary message per turn, using only the supplied public adapter.

Agent completion is not a Telegram delivery receipt. A short cleanup window is
therefore best effort presentation timing; native answer delivery stays native.
"""
import asyncio
from collections import OrderedDict
from dataclasses import dataclass, field
import logging
import math
import time

LOG = logging.getLogger("hermes-telegram-ux-catalog")


@dataclass(frozen=True)
class Route:
    chat_id: str
    message_id: str
    thread_id: str | None = None
    owner_id: str = ""


@dataclass
class Panel:
    route: Route
    text: str
    touched: float
    initial_text: str = ""
    terminal: bool = False
    message_id: str | None = None
    wake: asyncio.Event = field(default_factory=asyncio.Event)
    task: object = None
    stopping: bool = False
    cleaning: bool = False


class TelegramPanels:
    def __init__(self, ctx, adapter, interval, ttl, expire,
                 heartbeat=None, cleanup_delay=1.0):
        self.ctx = ctx
        self.adapter = adapter
        self.loop = asyncio.get_running_loop()
        self.interval = interval
        self.ttl = ttl
        self.expire = expire
        self.heartbeat = heartbeat
        try:
            delay = float(cleanup_delay)
            self.cleanup_delay = min(5.0, max(0.0, delay)) if math.isfinite(delay) else 1.0
        except (TypeError, ValueError):
            self.cleanup_delay = 1.0
        self.panels = {}
        self.blocked = OrderedDict()
        self.closed = False

    def retire(self, key):
        # Bounded tombstones prevent queued or late events from resurrecting a
        # finished turn. The owning hook adapter also removes finished turns.
        self.blocked[key] = None
        self.blocked.move_to_end(key)
        while len(self.blocked) > 2048:
            self.blocked.popitem(last=False)

    def publish(self, key, route, text, terminal=False):
        if not self.closed and not self.loop.is_closed():
            self.loop.call_soon_threadsafe(self.accept, key, route, text, terminal)

    def accept(self, key, route, text, terminal):
        if self.closed or key in self.blocked or not isinstance(text, str):
            return
        panel = self.panels.get(key)
        if panel is None:
            if terminal:
                self.retire(key)
                return
            if len(self.panels) >= 128:
                return
            panel = Panel(route, text, time.monotonic(), initial_text=text)
            self.panels[key] = panel
            coro = self.run(key, panel)
            try:
                panel.task = self.ctx.spawn_task(coro, name="catalog-telegram-status")
            except Exception as exc:
                coro.close()
                self.panels.pop(key, None)
                self.retire(key)
                LOG.warning("Catalog status unavailable (%s); Hermes continues", type(exc).__name__)
                return
        if panel.terminal or panel.stopping or panel.cleaning or panel.route != route:
            return
        changed = panel.text != text or terminal
        panel.text, panel.touched, panel.terminal = text, time.monotonic(), terminal
        if terminal:
            self.retire(key)
        if changed:
            panel.wake.set()

    async def send_once(self, panel, text):
        metadata = {"thread_id": panel.route.thread_id} if panel.route.thread_id else None
        operation = asyncio.create_task(self.adapter.send(
            chat_id=panel.route.chat_id, content=text,
            reply_to=panel.route.message_id, metadata=metadata,
        ))
        started = time.monotonic()
        try:
            result = await asyncio.wait_for(asyncio.shield(operation), timeout=5)
        except asyncio.CancelledError:
            # Unload can cancel the supervised worker while send is in flight.
            # Briefly await its existing acknowledgement so a known delivered
            # message can still be removed; never issue a replacement send.
            panel.stopping = True
            try:
                result = await asyncio.wait_for(asyncio.shield(operation),
                    timeout=max(0.01, 5 - (time.monotonic() - started)))
                if result.success and result.message_id:
                    panel.message_id = str(result.message_id)
            except Exception:
                pass
            raise
        finally:
            if not operation.done():
                operation.cancel()
                await asyncio.gather(operation, return_exceptions=True)
        if result.success and result.message_id:
            panel.message_id = str(result.message_id)
            return True
        return False

    async def delete_owned(self, panel):
        if not panel.message_id:
            return
        # A failed deletion must never escape into Hermes. Two bounded attempts
        # cover a transient transport failure without keeping a permanent worker.
        for attempt in range(2):
            try:
                deleted = await asyncio.wait_for(self.adapter.delete_message(
                    chat_id=panel.route.chat_id, message_id=panel.message_id,
                ), timeout=2)
                if deleted:
                    return
            except Exception:
                pass
            if attempt == 0:
                await asyncio.sleep(0.15)
        LOG.warning("Catalog temporary status could not be deleted; Hermes continues")

    async def run(self, key, panel):
        last_text, last_edit = "", 0.0
        try:
            # Fast completion before this worker runs must not create a late
            # message. Completion during send instead waits for its message ID.
            if panel.terminal or panel.stopping or self.closed:
                return
            text = panel.initial_text
            if not await self.send_once(panel, text):
                return
            last_text, last_edit = text, time.monotonic()
            while not self.closed and not panel.stopping:
                panel.wake.clear()
                if panel.text != last_text:
                    delay = self.interval - (time.monotonic() - last_edit)
                    if delay > 0 and not panel.terminal:
                        try:
                            await asyncio.wait_for(panel.wake.wait(), timeout=delay)
                        except asyncio.TimeoutError:
                            pass
                        continue
                    text = panel.text
                    result = await asyncio.wait_for(self.adapter.edit_message(
                        chat_id=panel.route.chat_id, message_id=panel.message_id,
                        content=text, finalize=panel.terminal,
                    ), timeout=5)
                    if not result.success:
                        # The known message is still ours to clean up. Never
                        # replace a failed edit with a second status message.
                        return
                    last_text, last_edit = text, time.monotonic()
                if panel.terminal:
                    # A finalizing event can arrive during an earlier edit.
                    if panel.text != last_text:
                        continue
                    panel.cleaning = True
                    if self.cleanup_delay and not panel.stopping and not self.closed:
                        panel.wake.clear()
                        try:
                            await asyncio.wait_for(panel.wake.wait(), timeout=self.cleanup_delay)
                        except asyncio.TimeoutError:
                            pass
                    return
                idle = self.ttl - (time.monotonic() - panel.touched)
                if idle <= 0:
                    expired_text = self.expire(key)
                    panel.terminal = True
                    self.retire(key)
                    if isinstance(expired_text, str) and expired_text:
                        panel.text = expired_text
                        continue
                    return
                if panel.wake.is_set():
                    continue
                try:
                    await asyncio.wait_for(panel.wake.wait(), timeout=min(idle, 2 if self.heartbeat else 10))
                except asyncio.TimeoutError:
                    # A display tick never refreshes execution TTL or invents
                    # activity. Current callers may omit this entirely.
                    if self.heartbeat and not panel.terminal and time.monotonic() - panel.touched < self.ttl:
                        refreshed = self.heartbeat(key)
                        if refreshed:
                            panel.text = refreshed
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            # Adapter errors may contain IDs or payload text; log type only.
            LOG.warning("Catalog status delivery unavailable (%s); Hermes continues", type(exc).__name__)
        finally:
            panel.cleaning = True
            self.retire(key)
            try:
                await self.delete_owned(panel)
            finally:
                if self.panels.get(key) is panel:
                    self.panels.pop(key, None)

    def discard(self, key):
        if not self.loop.is_closed():
            self.loop.call_soon_threadsafe(self.cancel, key)

    def cancel(self, key):
        self.retire(key)
        panel = self.panels.get(key)
        if panel is not None:
            # Cooperative cancellation preserves an in-flight send's ID. All
            # I/O already has a short timeout, so no abandoned worker remains.
            panel.stopping = True
            panel.terminal = True
            panel.wake.set()

    def close(self):
        self.closed = True
        if not self.loop.is_closed():
            self.loop.call_soon_threadsafe(self.cancel_all)

    def cancel_all(self):
        for key in list(self.panels):
            self.cancel(key)
