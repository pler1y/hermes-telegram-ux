import asyncio
import time
import sys
from pathlib import Path
from types import SimpleNamespace
import unittest

sys.path.insert(0, str(Path(__file__).parent))

from plugin.actions import ActionStore, normalize_actions
from plugin.status import ANALYZE, TurnRegistry, TurnState, phase_for_tool
from plugin.runtime import InteractionRuntime


class StatusTests(unittest.TestCase):
    def test_classifies_real_tool_phases_without_exposing_arguments(self):
        self.assertIn("查找", phase_for_tool("web_search", {"query": "private"}))
        self.assertIn("验证", phase_for_tool("terminal", {"command": "pytest -q"}))
        self.assertIn("部署", phase_for_tool("terminal", {"command": "systemctl restart app"}))
        self.assertNotIn("private", phase_for_tool("web_search", {"query": "private"}))

    def test_registry_moves_from_tool_to_analysis(self):
        registry = TurnRegistry()
        state = TurnState("s", "k", None, None, 1, [None], [], None, None)
        registry.bind(state)
        registry.update("s", phase_for_tool("read_file"), tool_started=True)
        self.assertEqual(state.tool_count, 1)
        registry.update("s", ANALYZE)
        self.assertEqual(state.phase, ANALYZE)


class ActionTests(unittest.TestCase):
    def test_actions_are_bounded_deduplicated_and_one_shot(self):
        actions = normalize_actions([
            {"label": "  查看  状态 ", "prompt": "status"},
            {"label": "查看 状态", "prompt": "status"},
            {"label": "继续优化", "prompt": "continue"},
            {"label": "多余选项", "prompt": "ignored"},
        ])
        self.assertEqual(len(actions), 3)
        clock = [100.0]
        store = ActionStore(clock=lambda: clock[0])
        menu = store.create_menu(session_key="k", user_id="u", chat_id="c",
                                 thread_id=None, message_id="m", actions=actions)
        self.assertIsNotNone(store.claim(menu.token, 0))
        self.assertIsNone(store.claim(menu.token, 0))

    def test_expired_menu_cannot_execute(self):
        clock = [100.0]
        store = ActionStore(clock=lambda: clock[0])
        menu = store.create_menu(session_key="k", user_id="u", chat_id="c",
                                 thread_id=None, message_id="m",
                                 actions=[{"label": "查看", "prompt": "go"}])
        clock[0] += 1801
        self.assertIsNone(store.peek(menu.token))


class _FakeContext:
    def get_config(self, _key, default=None):
        return default


class LifecycleTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.runtime = InteractionRuntime(_FakeContext())
        self.runtime.delay = 0.02
        self.runtime.min_edit = 0.01
        self.events = []

        async def record(state, text):
            if state.status_message_id is None:
                state.status_message_id = "17"
                state.cleanup_ids.append("17")
                self.events.append(("send", text))
            else:
                self.events.append(("edit", text))
            state.last_shown_text = text
            state.status_sent_at = time.monotonic()

        self.runtime._send_status = record

    def _turn(self):
        adapter = SimpleNamespace(register_post_delivery_callback=lambda *a, **k: None)
        source = SimpleNamespace(chat_id="1", user_id="2", thread_id=None, platform="telegram")
        turn = SimpleNamespace(
            source=source, session_id="session", session_key="key", run_generation=1,
            stream_consumer_holder=[None], _cleanup_msg_ids=[], _status_thread_metadata=None,
            agent_holder=[None],
        )
        runner = SimpleNamespace(_adapter_for_source=lambda _source: adapter)
        return runner, turn

    async def test_fast_turn_creates_no_status_bubble(self):
        runner, turn = self._turn()
        done = asyncio.get_running_loop().create_future()
        done.set_result(None)
        await self.runtime.status_lifecycle(runner, turn, [done])
        self.assertEqual(self.events, [])

    async def test_long_turn_sends_once_then_edits_same_bubble(self):
        runner, turn = self._turn()
        worker = asyncio.get_running_loop().create_future()
        task = asyncio.create_task(self.runtime.prepare_status_lifecycle(runner, turn, [worker]))
        await asyncio.sleep(0.06)
        self.runtime.pre_tool("read_file", {}, "session", tool_call_id="read")
        await asyncio.sleep(0.30)
        worker.set_result(None)
        await task
        self.assertEqual(self.events[0][0], "send")
        self.assertEqual(self.events[1][0], "edit")
        self.assertEqual(turn._cleanup_msg_ids, ["17"])

    async def test_external_receipt_is_not_immediately_overwritten_by_poll_loop(self):
        runner, turn = self._turn()
        turn.agent_holder[0] = SimpleNamespace(_pending_steer='supplement')
        worker = asyncio.get_running_loop().create_future()
        task = asyncio.create_task(self.runtime.prepare_status_lifecycle(runner, turn, [worker]))
        await asyncio.sleep(.06)
        state = self.runtime.registry.get('session')
        self.runtime.registry.receipt('session')
        await self.runtime._send_status(state,state.render(time.monotonic()))
        self.runtime.min_edit = .8
        count = len(self.events)
        self.runtime.pre_tool('read_file',{},'session',tool_call_id='a')
        await asyncio.sleep(.3)
        self.assertEqual(len(self.events),count)
        self.assertIn('补充已记下',state.last_shown_text)
        worker.set_result(None)
        await task


class PluginRegistrationTests(unittest.TestCase):
    def test_registers_and_restores_runtime_seam(self):
        try:
            from gateway.run import GatewayRunner
        except ModuleNotFoundError:
            self.skipTest("Hermes source tree is not on sys.path")

        class Context(_FakeContext):
            def __init__(self):
                self.tools = []
                self.hooks = []
                self.sections = []
                self.platforms = []
                self.unload = None

            def register_tool(self, **kwargs):
                self.tools.append(kwargs["name"])

            def register_hook(self, name, callback):
                self.hooks.append(name)

            def register_middleware(self, name, callback):
                self.hooks.append(name)

            def register_system_prompt_section(self, name, content, **kwargs):
                self.sections.append(name)

            def register_platform_handler(self, name, callback):
                self.platforms.append(name)

            def on_unload(self, callback):
                self.unload = callback

        ctx = Context()
        original = GatewayRunner._run_agent_notify_long_running
        runtime = InteractionRuntime(ctx)
        runtime.install()
        try:
            self.assertIs(GatewayRunner._run_agent_notify_long_running, original)
            runtime._patch_runner()
            self.assertTrue(getattr(GatewayRunner._run_agent_notify_long_running,
                                    "_hermes_interaction", False))
            self.assertIn("interaction_actions", ctx.tools)
            self.assertIn("pre_tool_call", ctx.hooks)
            self.assertIn("telegram", ctx.platforms)
        finally:
            runtime.uninstall()
        self.assertIs(GatewayRunner._run_agent_notify_long_running, original)


if __name__ == "__main__":
    unittest.main()
