"""Exercise shared-process lifecycle and bot ownership through production entry points."""
import asyncio
from functools import wraps
from types import SimpleNamespace as NS
import unittest
from unittest.mock import AsyncMock, Mock, patch

from plugin.actions import ActionStore, TelegramActions
from plugin.runtime import InteractionRuntime
from plugin.status import TurnState


class Application:
    def __init__(self, fail_at=None):
        self.handlers = []
        self.fail_at = fail_at

    def add_handler(self, handler, group=0):
        if len(self.handlers) == self.fail_at:
            raise RuntimeError("handler registration failed")
        self.handlers.append((handler, group))

    def remove_handler(self, handler, group=0):
        self.handlers.remove((handler, group))


class SharedRuntimeTests(unittest.IsolatedAsyncioTestCase):
    async def test_stream_override_does_not_retain_finished_consumers_or_replace_later_wrappers(self):
        import gc
        import weakref
        class Consumer:
            def _clean_for_display(self, text):
                return text
        runtime = InteractionRuntime(NS(get_config=lambda key, default=None: default))
        consumer = Consumer()
        runtime._wire_stream(NS(stream_holder=[consumer]))
        ux = consumer._clean_for_display
        later = lambda text: ux(text)
        consumer._clean_for_display = later
        runtime.uninstall()
        self.assertIs(consumer._clean_for_display, later)
        self.assertEqual(later("answer\nMEDIA: /tmp/fixture.txt"), "answer\nMEDIA: /tmp/fixture.txt")
        del ux, later, consumer
        consumer = Consumer()
        ref = weakref.ref(consumer)
        runtime._wire_stream(NS(stream_holder=[consumer]))
        del consumer
        gc.collect()
        self.assertIsNone(ref(), "finished stream must not be retained by the override registry")
        runtime.uninstall()

    async def test_unload_preserves_later_wrapper_and_makes_our_wrapped_layer_inert(self):
        from gateway.run import GatewayRunner
        from gateway.config import Platform
        runtime = InteractionRuntime(NS(get_config=lambda key, default=None: default))
        original = GatewayRunner._compose_busy_ack_message
        original_owned = vars(GatewayRunner).get("_compose_busy_ack_message")
        calls = []
        runtime._patch_runner()
        ux = GatewayRunner._compose_busy_ack_message

        @wraps(ux)
        def later(*args, **kwargs):
            calls.append("later")
            return ux(*args, **kwargs)

        GatewayRunner._compose_busy_ack_message = later
        try:
            runtime.uninstall()
            self.assertIs(GatewayRunner._compose_busy_ack_message, later)
            # The wrapper retained by another plugin must forward to native once unloaded.
            args = (object(), NS(source=NS(platform=Platform.TELEGRAM)), 0, None, None)
            flags = dict(is_steer_mode=False, is_queue_mode=False, is_redirect_mode=False,
                         demoted_for_subagents=False, demoted_for_compression=False)
            with patch("agent.onboarding.is_seen", return_value=True):
                self.assertEqual(GatewayRunner._compose_busy_ack_message(*args, **flags),
                                 original(*args, **flags))
            self.assertEqual(calls, ["later"])
            runtime._patch_runner()
            runtime.uninstall()
            self.assertIs(GatewayRunner._compose_busy_ack_message, later)

        finally:
            if original_owned is None:
                delattr(GatewayRunner, "_compose_busy_ack_message")
            else:
                GatewayRunner._compose_busy_ack_message = original_owned
            runtime.uninstall()

    async def test_partial_platform_wiring_rolls_back_and_can_retry(self):
        from gateway.run import GatewayRunner
        from gateway.config import PlatformConfig
        from plugins.platforms.telegram.adapter import TelegramAdapter
        runtime = InteractionRuntime(NS(get_config=lambda key, default=None: default))
        adapter = TelegramAdapter(PlatformConfig())
        original_send = adapter.send
        original_notify = GatewayRunner._run_agent_notify_long_running
        app = Application(fail_at=3)
        try:
            with self.assertRaisesRegex(RuntimeError, "registration failed"):
                runtime.wire_telegram(app, adapter)
            self.assertEqual(app.handlers, [])
            self.assertEqual(adapter.send, original_send)
            self.assertIs(GatewayRunner._run_agent_notify_long_running, original_notify)
            app.fail_at = None
            runtime.wire_telegram(app, adapter)
            count = len(app.handlers)
            runtime.wire_telegram(app, adapter)
            self.assertEqual(len(app.handlers), count, "repeat wiring must not duplicate handlers")
        finally:
            runtime.uninstall()


class MultiBotTests(unittest.IsolatedAsyncioTestCase):
    async def test_buttons_stay_on_the_turns_bot_after_another_bot_is_wired(self):
        ctx = NS(get_config=lambda key, default=None: default, inject_message=Mock(return_value=True))
        ui = TelegramActions(ctx, ActionStore())
        def adapter():
            return NS(_bot=NS(edit_message_reply_markup=AsyncMock(), send_message=AsyncMock()),
                      _is_callback_user_authorized=Mock(return_value=True))
        first, second = adapter(), adapter()
        app_a, app_b = Application(), Application()
        ui.wire(app_a, first)
        ui.wire(app_b, second)
        source = NS(user_id="7", chat_id="123", thread_id=None)
        state = TurnState("session", "key", source, first, 1,
                          [NS(message_id="42")], [], None, asyncio.get_running_loop())
        self.assertTrue(await ui.attach(state, [{"label": "继续", "prompt": "继续处理"}]))
        first._bot.edit_message_reply_markup.assert_awaited_once()
        second._bot.edit_message_reply_markup.assert_not_awaited()
        token = next(iter(ui.store.menus))
        query = NS(data=f"hi:{token}:0", from_user=NS(id=7),
                   message=NS(chat_id=123, message_id=42, message_thread_id=None,
                              chat=NS(type="private")), answer=AsyncMock(),
                   edit_message_reply_markup=AsyncMock())
        await app_b.handlers[0][0].callback(NS(callback_query=query), None)
        ctx.inject_message.assert_not_called()
        self.assertIsNotNone(ui.store.peek(token), "wrong bot must not consume the real menu")
        await app_a.handlers[0][0].callback(NS(callback_query=query), None)
        ctx.inject_message.assert_called_once_with("继续处理", session_key="key")

    async def test_native_session_policy_controls_group_thread_and_profile_matching(self):
        from gateway.config import Platform
        from gateway.run import GatewayRunner
        from gateway.session import SessionSource
        runtime = InteractionRuntime(NS(get_config=lambda key, default=None: default))
        class Bot:
            pass
        first_bot, second_bot = Bot(), Bot()
        runner = NS(config=NS(group_sessions_per_user=True, thread_sessions_per_user=False, multiplex_profiles=True),
                    _adapter_for_source=lambda source: first_bot)
        runner._session_key_for_source = GatewayRunner._session_key_for_source.__get__(runner)

        def source(user, thread=None, profile="one"):
            return SessionSource(Platform.TELEGRAM, "-100", chat_type="group", user_id=user,
                                 thread_id=thread, profile=profile)
        def bind(sid, src, bot):
            state = TurnState(sid, runner._session_key_for_source(src), src, bot, 1, [None], [], None, None)
            runtime.registry.bind(state)
            return state
        try:
            runtime.native.remember_runner(runner, source("alice"))
            alice = bind("a", source("alice"), first_bot)
            self.assertIs(runtime._state_for_source(source("alice"), first_bot), alice)
            self.assertIsNone(runtime._state_for_source(source("bob"), first_bot))
            bob = bind("b", source("bob"), first_bot)
            self.assertIs(runtime._state_for_source(source("bob"), first_bot), bob)
            self.assertIsNone(runtime._state_for_source(source("alice", profile="two"), first_bot))
            runtime.registry.pop("a")
            runtime.registry.pop("b")

            shared = bind("shared", source("alice", thread="7"), first_bot)
            self.assertIs(runtime._state_for_source(source("bob", thread="7"), first_bot), shared)
            runtime.registry.pop("shared")
            runner.config.thread_sessions_per_user = True
            private_thread = bind("private-thread", source("alice", thread="7"), first_bot)
            self.assertIsNone(runtime._state_for_source(source("bob", thread="7"), first_bot))
            self.assertIs(runtime._state_for_source(source("alice", thread="7"), first_bot), private_thread)
            runtime.registry.pop("private-thread")

            runner.config.group_sessions_per_user = False
            shared_group = bind("shared-group", source("alice"), first_bot)
            self.assertIs(runtime._state_for_source(source("bob"), first_bot), shared_group)
            runner_b = NS(_adapter_for_source=lambda source: second_bot,
                          _session_key_for_source=runner._session_key_for_source)
            runtime.native.remember_runner(runner_b, source("alice"))
            other_bot_state = bind("other-bot", source("alice"), second_bot)
            self.assertIs(runtime._state_for_source(source("alice"), second_bot), other_bot_state)
            self.assertIs(runtime._state_for_source(source("alice"), first_bot), shared_group)
            self.assertIsNone(runtime._state_for_source(source("alice")), "ambiguous bot lookup must not pick a task")
        finally:
            runtime.uninstall()

    async def test_group_send_without_sender_identity_cannot_edit_another_members_status(self):
        from gateway.config import Platform
        from gateway.session import SessionSource
        runtime = InteractionRuntime(NS(get_config=lambda key, default=None: default))
        class Bot:
            async def send(self, chat_id, content, **kwargs):
                return NS(success=True, message_id="ordinary-message")
        bot = Bot()
        src = SessionSource(Platform.TELEGRAM, "-100", chat_type="group", user_id="alice")
        state = TurnState("a", "a-key", src, bot, 1, [None], [], None, None)
        runtime.registry.bind(state)
        runtime._children["a"] = {"child"}
        runtime._send_status = AsyncMock()
        try:
            runtime._wire_send(bot)
            result = await bot.send("-100", "Got it!")
            self.assertEqual(result.message_id, "ordinary-message")
            runtime._send_status.assert_not_awaited()
        finally:
            runtime.uninstall()
