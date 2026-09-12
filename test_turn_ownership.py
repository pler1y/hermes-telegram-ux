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
