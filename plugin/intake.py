"""Own the early acknowledgement until the normal task lifecycle can adopt it."""
from __future__ import annotations

import asyncio
from collections import OrderedDict
from contextlib import suppress
from contextvars import ContextVar
from functools import wraps
import logging
import time

from .i18n import greeting, tr
from .status import TurnState
from .bindings import Overrides
from .full_adapter import source_key, current_turn

logger = logging.getLogger(__name__)
_preparing = ContextVar("hermes_ux_preparing", default=None)


class IntakeFeedback:
    def __init__(self, runtime):
        self.runtime = runtime
        self.pending = OrderedDict()
        self.expiry = {}
        self.patches = Overrides()

    async def begin(self, source, text, adapter):
        key = source_key(source, adapter)
        current = self.runtime._state_for_source(source, adapter)
        if current and not current.ended:
            # Native busy dispatch still decides steer/queue/redirect. This only acknowledges receipt.
            self.runtime.registry.receipt(current.session_id, text, message="收到这条消息了。")
            await self.runtime._send_status(current, current.render(time.monotonic(), self.runtime.slow_after))
            return
        state = self.pending.get(key)
        if state is None:
            if len(self.pending) >= 256:
                old_key, old = next(iter(self.pending.items()))
                await self.retire(old_key, old)
            state = TurnState("", "", source, adapter, None, [None], [], None,
                              asyncio.get_running_loop(), language=self.runtime.language)
            state.metadata = {"thread_id": source.thread_id} if getattr(source, "thread_id", None) else None
            self.pending[key] = state
            self.expiry[key] = asyncio.create_task(self._expire(key, state))
        # Consecutive Telegram chunks share one acknowledgement, even before native batching.
        async with state.send_lock:
            if not state.status_message_id and not self.runtime.soft_wait:
                await self.runtime._deliver_status(state, greeting(text, self.runtime.language))
                if state.status_message_id:
                    logger.info("Hermes Interaction: intake acknowledgement age=%.3fs", time.monotonic() - state.created_at)

    def _pending_key(self, source, adapter=None):
        if adapter is not None:
            return source_key(source, adapter)
        keys = [key for key, state in self.pending.items() if source_key(state.source) == source_key(source)]
        return keys[0] if len(keys) == 1 else None

    def take(self, source, adapter=None):
        key = self._pending_key(source, adapter)
        state = self.pending.pop(key, None)
        timer = self.expiry.pop(key, None)
        if timer:
            timer.cancel()
        return state

    async def retire(self, key, expected):
        if self.pending.get(key) is not expected:
            return
        self.pending.pop(key)
        timer = self.expiry.pop(key, None)
        if timer and timer is not asyncio.current_task():
            timer.cancel()
        async with expected.send_lock:
            expected.status_closed = True
            if expected.status_message_id:
                with suppress(Exception):
                    await expected.adapter.delete_message(expected.source.chat_id, expected.status_message_id)

    async def _expire(self, key, state):
        try:
            await asyncio.sleep(45)
            # Once admitted, the gateway wrapper owns cleanup, including long compression waits.
            if not getattr(state, "admitted", False):
                await self.retire(key, state)
        except asyncio.CancelledError:
            pass

    async def internal(self, source, message, adapter=None):
        state = self.pending.get(self._pending_key(source, adapter)) or self.runtime._state_for_source(source, adapter)
        if state is None or state.status_closed or state.ended:
            return
        state.internal_status = message
        await self.runtime._send_status(state, tr(message, self.runtime.language))

    def wire(self, application, adapter):
        from telegram.ext import MessageHandler, filters

        async def receive(update, context):
            message = update.effective_message
            if message is None:
                return
            if not adapter._should_process_message(message, is_command=False):
                return
            source = adapter._source_from_message_for_auth(message)
            # Unlike the intake prefilter, this must not treat "may need pairing" as authorized.
            decision = adapter._is_sender_authorized(
                source.user_id, chat_type=source.chat_type, chat_id=source.chat_id,
                is_bot=source.is_bot, thread_id=source.thread_id)
            if decision is None:
                check = adapter._legacy_runner_auth_fn()
                decision = check(source) if check else False
            if not decision:
                return
            try:
                await asyncio.wait_for(self.begin(source, message.text or message.caption or "", adapter), 2.0)
            except Exception:
                logger.debug("Early acknowledgement unavailable; native message processing continues")

        handler = MessageHandler((filters.TEXT | filters.PHOTO | filters.Document.ALL | filters.VOICE | filters.AUDIO) & ~filters.COMMAND, receive)
        application.add_handler(handler, group=-1)
        return lambda: application.remove_handler(handler, group=-1)

    def patch_gateway(self, cls):
        def patch(name, make):
            original = getattr(cls, name)
            replacement = make(original)
            self.patches.set(cls, name, replacement)

        def turn(original):
            @wraps(original)
            async def wrapped(runner, event, source, *args, **kwargs):
                if not self.runtime.is_telegram(source):
                    return await original(runner, event, source, *args, **kwargs)
                adapter = self.runtime.native.remember_runner(runner, source)
                key = self._pending_key(source, adapter)
                early = self.pending.get(key)
                if early:
                    early.admitted = True
                token = _preparing.set((source, adapter))
                turn_token = current_turn.set(None)
                try:
                    return await original(runner, event, source, *args, **kwargs)
                finally:
                    _preparing.reset(token)
                    current_turn.reset(turn_token)
                    if early:
                        await self.retire(key, early)
            return wrapped

        def plan(original):
            @wraps(original)
            async def wrapped(runner, *args, **kwargs):
                result = await original(runner, *args, **kwargs)
                preparing = _preparing.get()
                if preparing and getattr(result, "needs_compress", False):
                    await self.internal(preparing[0], "🧠 正在整理前面的聊天，稍等一下。", preparing[1])
                return result
            return wrapped

        def hygiene(original):
            @wraps(original)
            async def wrapped(runner, event, source, *args, **kwargs):
                try:
                    return await original(runner, event, source, *args, **kwargs)
                finally:
                    adapter = self.runtime.native.remember_runner(runner, source)
                    state = self.pending.get(self._pending_key(source, adapter))
                    if state and state.internal_status:
                        # Do not claim compression succeeded: Hermes can continue with old history.
                        state.internal_status = ""
                        await self.runtime._send_status(state, greeting("", self.runtime.language))
            return wrapped

        def notice(original):
            @wraps(original)
            async def wrapped(runner, source, meta, message, what):
                # These are distinct native outcomes. Deferral is not a failure, and a
                # successful main-model fallback must never be labelled as an abort.
                if self.runtime.is_telegram(source):
                    copy = {
                        "compression-turnhold notice": "🧠 聊天整理还没完成，这次先沿用原来的内容继续。",
                        "compression-timeout warning": "⚠️ 聊天整理等得太久，这次先沿用原来的内容继续。可用 /compress 重试。",
                        "compression-failure warning": "⚠️ 聊天整理没有成功，原来的消息仍然保留。可用 /compress 重试，或检查整理模型的设置。",
                        "aux-model-fallback notice": "🧠 专用整理模型没有成功，已用当前模型完成整理。可以稍后检查整理模型的设置。",
                    }.get(what)
                    if copy:
                        message = tr(copy, self.runtime.language)
                return await original(runner, source, meta, message, what)
            return wrapped

        patch("_handle_message_with_agent", turn)
        patch("_hmwa_hygiene_plan", plan)
        patch("_hmwa_run_session_hygiene", hygiene)
        patch("_hmwa_hygiene_notify", notice)

        from gateway.run_turn_runner import TurnRunner
        from agent.conversation_compression import (
            COMPACTION_STATUS, COMPACTION_HEARTBEAT_STATUS, COMPACTION_DONE_STATUS,
        )
        original_status = TurnRunner._status_callback_sync

        @wraps(original_status)
        def status(runner, kind, message):
            ctx = runner._ctx
            state = self.runtime.registry.get(getattr(ctx, "session_id", ""))
            if (state and state.generation == getattr(ctx, "run_generation", None)
                    and self.runtime.is_telegram(ctx.source) and runner._status_live()):
                if message in {COMPACTION_STATUS, COMPACTION_HEARTBEAT_STATUS}:
                    text = "🧠 正在整理前面的聊天，稍等一下。"
                elif kind == "compacted" and message == COMPACTION_DONE_STATUS:
                    text = "🧐 前面的聊天整理好了，继续看你的问题。"
                else:
                    return original_status(runner, kind, message)

                async def deliver():
                    if self.runtime.registry.get(state.session_id) is state and not state.ended:
                        await self.internal(state.source, text, state.adapter)
                runner._schedule(deliver(), "UX internal status delivery")
                return
            return original_status(runner, kind, message)

        self.patches.set(TurnRunner, "_status_callback_sync", status)

    def close(self):
        self.patches.rollback()
        for task in self.expiry.values():
            task.cancel()
        self.expiry.clear()
        self.pending.clear()
