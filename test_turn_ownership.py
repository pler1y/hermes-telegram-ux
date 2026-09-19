"""A displaced turn must not deliver or clean up its successor's UI."""
import asyncio
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock

from plugin.runtime import InteractionRuntime
from plugin.status import TurnState


class Adapter:
    pass


class TurnOwnershipTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.runtime = InteractionRuntime(SimpleNamespace(get_config=lambda key, default=None: default))
        self.runtime.delay = 0
        self.source = SimpleNamespace(platform="telegram", chat_id="1", user_id="2", thread_id=None)
        self.callbacks = []
        self.adapter = Adapter()
        self.adapter.register_post_delivery_callback = lambda *args, **kwargs: self.callbacks.append((args, kwargs))
        self.adapter.delete_message = AsyncMock()
        self.adapter.send_typing = AsyncMock()
        self.runner = SimpleNamespace(_adapter_for_source=lambda source: self.adapter)

    async def asyncTearDown(self):
        self.runtime.uninstall()

    def state(self, generation):
        return TurnState("session", "key", self.source, self.adapter, generation,
                         [None], [], None, asyncio.get_running_loop())

    def turn(self, generation):
        return SimpleNamespace(source=self.source, session_id="session", session_key="key",
                               run_generation=generation, stream_consumer_holder=[None],
                               _cleanup_msg_ids=[], _status_thread_metadata=None, agent_holder=[None])

    async def test_displaced_finalizer_preserves_successor_actions(self):
        old, new = self.state(1), self.state(2)
        self.runtime.registry.bind(new)
        actions = self.runtime.actions.remember("session", [{"label": "继续", "prompt": "继续处理"}])
        worker = asyncio.get_running_loop().create_future()
        worker.set_result(None)
        await self.runtime._run_status_lifecycle(self.turn(1), [worker], old)
        self.assertIs(self.runtime.registry.get("session"), new)
        self.assertEqual(self.runtime.actions.take_pending("session"), actions)
        self.assertEqual(self.callbacks, [])

    async def test_displaced_poll_stops_before_sending(self):
        old, new = self.state(1), self.state(2)
        self.runtime.registry.bind(new)
        self.runtime._send_status = AsyncMock()
        worker = asyncio.get_running_loop().create_future()
        task = asyncio.create_task(self.runtime._run_status_lifecycle(self.turn(1), [worker], old))
        try:
            await asyncio.sleep(.03)
            self.runtime._send_status.assert_not_awaited()
            self.assertTrue(task.done(), "displaced progress loop must exit even if its worker is hung")
        finally:
            worker.set_result(None)
            await task

    async def test_successor_does_not_adopt_foreground_message_scheduled_for_old_cleanup(self):
        old = self.state(1)
        old.status_message_id = "old-message"
        old.cleanup_ids.append("old-message")
        self.runtime.registry.bind(old)
        lifecycle = self.runtime.prepare_status_lifecycle(self.runner, self.turn(2), [None])
        try:
            new = self.runtime.registry.get("session")
            self.assertIsNone(new.status_message_id)
            self.assertEqual(new.cleanup_ids, [])
            self.assertEqual(old.cleanup_ids, ["old-message"])
        finally:
            lifecycle.close()

    async def test_stop_tail_does_not_interrupt_successor(self):
        from gateway.run import GatewayRunner
        self.runtime._patch_runner()
        old = self.state(1)
        old.status_message_id = "old-message"
        self.runtime.registry.bind(old)
        new = None

        async def interrupt_and_replace(*args, **kwargs):
            # Exercise the real native /stop entry point, with a new turn admitted
            # while its asynchronous platform interrupt is still draining.
            nonlocal new
            lifecycle = self.runtime.prepare_status_lifecycle(self.runner, self.turn(2), [None])
            new = self.runtime.registry.get("session")
            lifecycle.close()
            await asyncio.sleep(0)

        runner = SimpleNamespace(_interrupt_and_clear_session=interrupt_and_replace)
        await GatewayRunner._busy_stop_command(runner, SimpleNamespace(source=self.source), "key", self.source)
        self.assertIs(self.runtime.registry.get("session"), new)
        self.assertFalse(new.ended)
        self.assertFalse(new.interrupted)
        self.assertIsNone(new.status_message_id)
        self.adapter.delete_message.assert_awaited_once_with("1", "old-message")

    async def test_background_stop_tail_keeps_new_turn_alive(self):
        from gateway.run import GatewayRunner
        self.runtime._patch_runner()
        old = self.state(1)
        old.foreground_active = False
        old.status_message_id = "background-message"
        self.runtime.registry.bind(old)
        self.runtime._stop_owned_children = lambda session_id: 1
        new = self.state(2)

        async def native_stop(runner, event):
            self.runtime.registry.bind(new)
            await asyncio.sleep(0)
            return "Stopped"

        self.runtime._original_idle_stop = native_stop
        runner = SimpleNamespace(async_session_store=SimpleNamespace(
            get_or_create_session=AsyncMock(return_value=SimpleNamespace(session_id="session", session_key="key"))))
        await GatewayRunner._handle_stop_command(runner, SimpleNamespace(source=self.source))
        self.assertIs(self.runtime.registry.get("session"), new)
        self.assertFalse(new.interrupted)
        self.assertFalse(new.status_closed)
        self.adapter.delete_message.assert_awaited_once_with("1", "background-message")

    async def test_old_native_executor_hooks_cannot_claim_or_finish_successor(self):
        """Exercise the actual gateway's notify → copied executor context seam."""
        import threading
        from gateway.run import GatewayRunner
        from plugin.full_adapter import current_turn

        self.runtime._patch_runner()
        self.runner._get_executor = lambda: None
        old_lifecycle = GatewayRunner._run_agent_notify_long_running(self.runner, None, self.turn(10), [None])
        old_lifecycle.close()
        old = self.runtime.registry.get("session")
        ready, release = asyncio.Event(), threading.Event()
        loop = asyncio.get_running_loop()

        def old_worker():
            self.assertIs(current_turn.get(), old)
            self.runtime.pre_api("session", turn_id="session:task:old-uuid", api_request_id="session:task:old-uuid:api:1")
            loop.call_soon_threadsafe(ready.set)
            if not release.wait(3):
                raise AssertionError("test did not release old worker")
            event = dict(session_id="session", turn_id="session:task:old-uuid")
            self.runtime.pre_api(**event, api_request_id="session:task:old-uuid:api:2")
            self.runtime.api_error(**event)
            self.runtime.pre_tool("terminal", {"command": "false"}, **event, tool_call_id="late")
            self.runtime.post_tool("terminal", result={"exit_code": 1}, **event, tool_call_id="late")
            self.runtime.approval_wait("key", session_id="session")
            self.runtime.child_start(parent_session_id="session", child_session_id="late-child")
            self.runtime.session_end(**event, interrupted=True)

        worker = asyncio.create_task(GatewayRunner._run_in_executor_with_context(self.runner, old_worker))
        try:
            await asyncio.wait_for(ready.wait(), 2)
            new_lifecycle = GatewayRunner._run_agent_notify_long_running(self.runner, None, self.turn(12), [None])
            new_lifecycle.close()
            new = self.runtime.registry.get("session")
            self.runtime.pre_api("session", turn_id="session:task:new-uuid", api_request_id="session:task:new-uuid:api:1")
            self.runtime.pre_tool("read_file", {}, "session", tool_call_id="new-read", turn_id="session:task:new-uuid")
            expected_phase = new.phase
            actions = self.runtime.actions.remember("session", [{"label": "继续", "prompt": "继续处理"}])
            release.set()
            await asyncio.wait_for(worker, 2)
            self.assertEqual(new.hook_turn_id, "session:task:new-uuid")
            self.assertEqual(new.phase, expected_phase)
            self.assertEqual(new.tool_count, 1)
            self.assertEqual(new.tool_errors, 0)
            self.assertFalse(new.ended)
            self.assertFalse(new.interrupted)
            self.assertIsNone(new.approval_phase)
            self.assertNotIn("late-child", self.runtime._child_roots)
            self.assertEqual(self.runtime.actions.take_pending("session"), actions)

            # A hook dispatched without inherited context must already know the
            # current agent turn ID; unknown/old IDs cannot adopt a generation.
            token = current_turn.set(None)
            try:
                self.runtime.session_end("session", interrupted=True, turn_id="session:task:old-uuid")
                self.assertFalse(new.ended)
                self.runtime.session_end("session", completed=True, turn_id="session:task:new-uuid")
                self.assertTrue(new.completed)
            finally:
                current_turn.reset(token)
        finally:
            release.set()
            await worker

    async def test_child_owner_survives_background_handoff_but_not_stop(self):
        from plugin.full_adapter import current_turn
        from unittest.mock import patch
        first = self.runtime.prepare_status_lifecycle(self.runner, self.turn(1), [None])
        first.close()
        old = self.runtime.registry.get("session")
        self.runtime.child_start(parent_session_id="session", child_session_id="child")
        old.foreground_active = False
        second = self.runtime.prepare_status_lifecycle(self.runner, self.turn(2), [None])
        second.close()
        new = self.runtime.registry.get("session")
        token = current_turn.set(old)  # an existing background worker retains its original context
        try:
            self.runtime.pre_tool("read_file", {}, "child", tool_call_id="background-read")
            self.assertEqual(new.tool_count, 1)
            self.runtime.child_stop(parent_session_id="session", child_session_id="child")
            self.assertEqual(new.active_tools, 0)
            before = new.last_event_at
            self.runtime.post_tool("read_file", "late", "child", tool_call_id="background-read")
            self.assertEqual(new.last_event_at, before)
        finally:
            current_turn.reset(token)
        self.runtime.child_start(parent_session_id="session", child_session_id="stopped-child")
        record = {"subagent_id": "stopped-child", "owner_agent_session_id": "session"}
        with patch("tools.delegate_tool_registry.list_active_subagents", return_value=[record]), \
                patch("tools.delegate_tool_registry.interrupt_subagent", return_value=True):
            self.runtime._stop_owned_children("session")
        self.runtime.pre_tool("read_file", {}, "stopped-child", tool_call_id="too-late")
        self.assertEqual(new.tool_count, 1)

    async def test_busy_stop_still_calls_native_when_child_lookup_or_persistence_fails(self):
        from gateway.run import GatewayRunner
        from unittest.mock import Mock, patch
        self.runtime._patch_runner()
        self.runtime._original_stop = AsyncMock(return_value="Stopped")
        state = self.state(1)
        self.runtime.registry.bind(state)
        event = SimpleNamespace(source=self.source)
        with patch("tools.delegate_tool_registry.list_active_subagents", side_effect=RuntimeError("unavailable")):
            await GatewayRunner._busy_stop_command(self.runner, event, "key", self.source)
        self.runtime._original_stop.assert_awaited_once()

        self.runtime._original_stop.reset_mock()
        self.runtime.registry.bind(self.state(2))
        self.runtime._state_store = SimpleNamespace(set=Mock(side_effect=OSError("disk full")))
        records = [dict(subagent_id="bad", owner_agent_session_id="session"),
                   dict(subagent_id="good", owner_agent_session_id="session", delegation_id="cancelled")]
        with patch("tools.delegate_tool_registry.list_active_subagents", return_value=records), \
                patch("tools.delegate_tool_registry.interrupt_subagent", side_effect=[RuntimeError("child failed"), True]) as interrupt:
            await GatewayRunner._busy_stop_command(self.runner, event, "key", self.source)
        self.assertEqual(interrupt.call_count, 2)
        self.runtime._original_stop.assert_awaited_once()
        self.assertEqual(self.runtime._cancelled_delegations["cancelled"]["owner"], "session")

    async def test_idle_stop_still_calls_native_when_background_lookup_fails(self):
        from gateway.run import GatewayRunner
        self.runtime._patch_runner()
        self.runtime._original_idle_stop = AsyncMock(return_value="Stopped")
        runner = SimpleNamespace(async_session_store=SimpleNamespace(
            get_or_create_session=AsyncMock(side_effect=OSError("store unavailable"))))
        result = await GatewayRunner._handle_stop_command(runner, SimpleNamespace(source=self.source))
        self.assertEqual(result, "Stopped")
        self.runtime._original_idle_stop.assert_awaited_once()
