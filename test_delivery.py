"""Status delivery through the real runtime, with Telegram and time controlled locally."""
import asyncio
from types import SimpleNamespace as NS
import unittest
from unittest.mock import AsyncMock, patch

from gateway.platforms.base import SendResult
from plugin.runtime import InteractionRuntime
from plugin.progress import TaskProgress
from plugin.status import TurnState


class Adapter:
    def __init__(self):
        self.send = AsyncMock(return_value=SendResult(success=True, message_id="18"))
        self.edit_message = AsyncMock(return_value=SendResult(success=True, message_id="17"))
        self.send_typing = AsyncMock()


class DeliveryRetryTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        # Import native metadata helpers before controlling the clock.
        import gateway.run
        self.runtime = InteractionRuntime(NS(get_config=lambda key, default=None: default))
        self.adapter = Adapter()
        self.now = 100.0
        self.clock = patch("plugin.runtime.time.monotonic", side_effect=lambda: self.now)
        self.clock.start()
        self.addCleanup(self.clock.stop)
        self.state = self.make_state("s")

    def make_state(self, sid, *, sent=True):
        source = NS(chat_id="123", thread_id=None, user_id="u", platform="telegram")
        state = TurnState(sid, sid, source, self.adapter, 1, [None], [], None, None,
                          progress=TaskProgress())
        if sent:
            state.status_message_id = "17"
            state.status_sent_at = 90.0
            state.last_shown_text = "Previous step"
        return state

    async def test_server_wait_blocks_edits_and_then_delivers_latest_status(self):
        self.adapter.edit_message.side_effect = [
            SendResult(success=False, error="flood_control:60.0", retry_after=60),
            SendResult(success=True, message_id="17"),
        ]
        await self.runtime._send_status(self.state, "Reading")
        for at in (100.25, 101, 110, 159.99):
            self.now = at
            await self.runtime._send_status(self.state, "Checking")
        self.assertEqual(self.adapter.edit_message.await_count, 1)
        self.now = 160
        await self.runtime._send_status(self.state, "Latest result")
        self.assertEqual(self.adapter.edit_message.await_count, 2)
        self.assertEqual(self.state.last_shown_text, "Latest result")

    async def test_flood_wait_also_protects_other_turns_and_typing_on_same_bot(self):
        self.adapter.edit_message.return_value = SendResult(success=False, retry_after=60)
        await self.runtime._send_status(self.state, "Reading")
        other = self.make_state("other", sent=False)
        self.now = 101
        await self.runtime._send_status(other, "New task")
        await self.runtime._typing(other)
        self.adapter.send.assert_not_awaited()
        self.adapter.send_typing.assert_not_awaited()
        # A different bot is unaffected.
        other.adapter = Adapter()
        await self.runtime._send_status(other, "New task")
        other.adapter.send.assert_awaited_once()

    async def test_transport_failures_back_off_and_success_resets_the_delay(self):
        self.adapter.edit_message.return_value = SendResult(success=False, retryable=True)
        for at, expected in ((100, 1), (101, 1), (102.5, 2), (105, 2), (107.5, 3)):
            self.now = at
            await self.runtime._send_status(self.state, "Reading")
            self.assertEqual(self.adapter.edit_message.await_count, expected)
        self.adapter.edit_message.return_value = SendResult(success=True, message_id="17")
        self.now = 117.5
        await self.runtime._send_status(self.state, "Recovered")
        self.adapter.edit_message.return_value = SendResult(success=False)
        self.now = 120
        await self.runtime._send_status(self.state, "Next step")
        self.now = 122.5
        await self.runtime._send_status(self.state, "Next step")
        self.assertEqual(self.adapter.edit_message.await_count, 6)

    async def test_failed_initial_send_and_raised_error_do_not_bypass_backoff(self):
        state = self.make_state("new", sent=False)
        self.adapter.send.side_effect = [TimeoutError(), SendResult(success=True, message_id="18")]
        await self.runtime._send_status(state, "Reading")
        self.now = 100.25
        await self.runtime._send_status(state, "Reading")
        self.adapter.send.assert_awaited_once()
        self.now = 102.5
        await self.runtime._send_status(state, "Reading")
        self.assertEqual(state.status_message_id, "18")
        self.assertEqual(state.cleanup_ids, ["18"])

    async def test_closed_status_cannot_be_retried_after_cooldown(self):
        self.adapter.edit_message.return_value = SendResult(success=False, retry_after=60)
        await self.runtime._send_status(self.state, "Reading")
        self.state.status_closed = True
        self.now = 160
        await self.runtime._send_status(self.state, "Late update")
        self.adapter.edit_message.assert_awaited_once()

    async def test_foreground_poll_loop_respects_retry_after(self):
        self.runtime.delay = 0
        self.adapter.edit_message.side_effect = [
            SendResult(success=False, retry_after=60), SendResult(success=True, message_id="17")]
        worker = asyncio.get_running_loop().create_future()
        self.runtime.registry.bind(self.state)
        self.state.progress.start("s", "read", "read_file", {})

        async def advance(seconds):
            self.now += seconds
            if self.now >= 161 and not worker.done():
                worker.set_result(None)

        with patch("plugin.runtime.asyncio.sleep", side_effect=advance):
            await self.runtime._run_status_lifecycle(NS(agent_holder=[None]), [worker], self.state)
        self.assertEqual(self.adapter.edit_message.await_count, 2)

    async def test_background_poll_loop_respects_retry_after(self):
        self.adapter.edit_message.side_effect = [
            SendResult(success=False, retry_after=60), SendResult(success=True, message_id="17")]
        self.state.foreground_active = False
        self.state.progress.start("s", "read", "read_file", {})
        self.runtime.registry.bind(self.state)

        async def advance(seconds):
            self.now += seconds
            if self.now >= 161:
                self.state.ended = True

        with patch("plugin.runtime.asyncio.sleep", side_effect=advance):
            await self.runtime._watch_background("s")
        self.assertEqual(self.adapter.edit_message.await_count, 2)

    async def test_turn_handoff_keeps_early_send_backoff(self):
        self.adapter.send.return_value = SendResult(success=False, retryable=True)
        await self.runtime.intake.begin(self.state.source, "Read a file", self.adapter)
        self.adapter.send.assert_awaited_once()
        turn = NS(source=self.state.source, session_id="s", session_key="k", run_generation=1,
                  stream_consumer_holder=[None], _cleanup_msg_ids=[], _status_thread_metadata=None,
                  agent_holder=[None])
        worker = asyncio.get_running_loop().create_future()
        worker.set_result(None)
        self.runtime.delay = 0
        lifecycle = self.runtime.prepare_status_lifecycle(
            NS(_adapter_for_source=lambda source: self.adapter), turn, [worker])
        try:
            state = self.runtime.registry.get("s")
            self.now = 100.25
            await self.runtime._send_status(state, "Reading")
            self.adapter.send.assert_awaited_once()
            self.now = 102.5
            self.adapter.send.return_value = SendResult(success=True, message_id="18")
            await self.runtime._send_status(state, "Reading")
            self.assertEqual(state.status_message_id, "18")
        finally:
            await lifecycle
            self.runtime.uninstall()


if __name__ == "__main__":
    unittest.main()
