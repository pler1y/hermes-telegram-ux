"""Nonblocking, coalesced status messages through the supplied public adapter."""
import asyncio
from dataclasses import dataclass, field
import logging
import time

LOG = logging.getLogger("hermes-telegram-ux-catalog")


@dataclass(frozen=True)
class Route:
    chat_id: str
    message_id: str
    thread_id: str | None = None


@dataclass
class Panel:
    route: Route
    text: str
    touched: float
    terminal: bool = False
    message_id: str | None = None
    wake: asyncio.Event = field(default_factory=asyncio.Event)
    task: object = None


class TelegramPanels:
    def __init__(self, ctx, adapter, interval, ttl, expire):
        self.ctx = ctx
        self.adapter = adapter
        self.loop = asyncio.get_running_loop()
        self.interval = interval
        self.ttl = ttl
        self.expire = expire
        self.panels = {}
        self.blocked = set()
        self.closed = False

    def publish(self, key, route, text, terminal=False):
        if not self.closed and not self.loop.is_closed():
            self.loop.call_soon_threadsafe(self.accept, key, route, text, terminal)

    def accept(self, key, route, text, terminal):
        if self.closed:
            return
        if terminal:
            self.blocked.discard(key)
        elif key in self.blocked:
            return
        panel = self.panels.get(key)
        if panel is None:
            if terminal or len(self.panels) >= 128:
                return
            panel = Panel(route, text, time.monotonic())
            self.panels[key] = panel
            try:
                panel.task = self.ctx.spawn_task(self.run(key, panel), name="catalog-telegram-status")
            except Exception:
                self.panels.pop(key, None)
                raise
        if panel.terminal:
            return
        panel.text, panel.touched, panel.terminal = text, time.monotonic(), terminal
        panel.wake.set()

    async def run(self, key, panel):
        last_text, last_edit = "", 0.0
        try:
            while not self.closed:
                panel.wake.clear()
                if not panel.message_id:
                    # A short turn can finish before the first send; do not create a late bubble.
                    if panel.terminal:
                        return
                    text = panel.text
                    metadata = {"thread_id": panel.route.thread_id} if panel.route.thread_id else None
                    result = await asyncio.wait_for(self.adapter.send(
                        chat_id=panel.route.chat_id, content=text,
                        reply_to=panel.route.message_id, metadata=metadata,
                    ), timeout=5)
                    # Never retry an initial send: a timeout may already have delivered it.
                    if not result.success or not result.message_id:
                        return
                    panel.message_id = str(result.message_id)
                    last_text, last_edit = text, time.monotonic()
                if panel.text != last_text:
                    delay = self.interval - (time.monotonic() - last_edit)
                    if delay > 0 and not panel.terminal:
                        await asyncio.sleep(delay)
                        continue
                    text = panel.text
                    result = await asyncio.wait_for(self.adapter.edit_message(
                        chat_id=panel.route.chat_id, message_id=panel.message_id, content=text,
                    ), timeout=5)
                    if not result.success:
                        # An edit cannot duplicate a message. Honor bounded explicit rate limits.
                        retry = getattr(result, "retry_after", None)
                        if isinstance(retry, (int, float)) and 0 < retry <= 30 and not panel.terminal:
                            await asyncio.sleep(retry)
                            continue
                        return
                    last_text, last_edit = text, time.monotonic()
                if panel.terminal:
                    return
                idle = self.ttl - (time.monotonic() - panel.touched)
                if idle <= 0:
                    expired_text = self.expire(key)
                    if expired_text:
                        panel.text, panel.terminal = expired_text, True
                        continue
                    return
                if panel.wake.is_set():
                    continue
                try:
                    await asyncio.wait_for(panel.wake.wait(), timeout=idle)
                except asyncio.TimeoutError:
                    pass
        except asyncio.CancelledError:
            # Clean up only our own known message; never touch the final reply.
            if panel.message_id:
                try:
                    await asyncio.wait_for(self.adapter.delete_message(
                        chat_id=panel.route.chat_id, message_id=panel.message_id,
                    ), timeout=2)
                except Exception:
                    pass
            raise
        except Exception as exc:
            # Do not log adapter errors, which may contain Telegram IDs or payload text.
            LOG.warning("Catalog status delivery unavailable (%s); Hermes continues", type(exc).__name__)
        finally:
            if not panel.terminal and not self.closed:
                self.blocked.add(key)
            if self.panels.get(key) is panel:
                self.panels.pop(key, None)

    def discard(self, key):
        if not self.loop.is_closed():
            self.loop.call_soon_threadsafe(self.cancel, key)

    def cancel(self, key):
        self.blocked.discard(key)
        panel = self.panels.pop(key, None)
        if panel is not None and panel.task is not None:
            panel.terminal = True
            panel.task.cancel()

    def close(self):
        self.closed = True
        if not self.loop.is_closed():
            self.loop.call_soon_threadsafe(self.cancel_all)

    def cancel_all(self):
        self.blocked.clear()
        for key in list(self.panels):
            self.cancel(key)
