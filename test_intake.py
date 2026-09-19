"""Early Telegram feedback, preflight handoff, authorization and cleanup boundaries."""
import asyncio
from types import SimpleNamespace as NS
import unittest
from unittest.mock import AsyncMock
from gateway.config import Platform
from gateway.session import SessionSource
from plugin.runtime import InteractionRuntime
from plugin.intake import source_key


class Context:
    def get_config(self, key, default=None):
        return {"language": "en"}.get(key, default)


class Adapter:
    def __init__(self):
        self.events = []
    async def send(self, chat_id, content, **kwargs):
        self.events.append(("send", str(chat_id), content))
        return NS(success=True, message_id=str(len(self.events)))
    async def edit_message(self, chat_id, message_id, content, **kwargs):
        self.events.append(("edit", str(message_id), content))
        return NS(success=True)
    async def delete_message(self, chat_id, message_id):
        self.events.append(("delete", str(message_id)))


class IntakeTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.runtime = InteractionRuntime(Context())
        self.adapter = Adapter()
        self.source = SessionSource(Platform.TELEGRAM, "123", user_id="u")

    async def asyncTearDown(self):
        self.runtime.uninstall()
        await asyncio.sleep(0)

    async def test_acknowledgement_does_not_wait_for_model_or_status_delay(self):
        self.runtime.delay = 30
        await self.runtime.intake.begin(self.source, "hello", self.adapter)
        self.assertEqual(self.adapter.events, [("send", "123", "Hey! 👋")])
        self.assertEqual(self.runtime.registry._states, {})

    async def test_batched_messages_share_one_early_bubble(self):
        await self.runtime.intake.begin(self.source, "Check these prices", self.adapter)
        await self.runtime.intake.begin(self.source, "And shipping", self.adapter)
        self.assertEqual(len(self.adapter.events), 1)

    async def test_quiet_intake_waits_for_a_real_event_and_can_show_compression(self):
        self.runtime.soft_wait = True
        await self.runtime.intake.begin(self.source, 'hello', self.adapter)
        self.assertEqual(self.adapter.events, [])
        await self.runtime.intake.internal(self.source, '🧠 正在整理前面的聊天，稍等一下。')
        self.assertEqual(self.adapter.events[0][0], 'send')
        self.assertIn('Tidying up', self.adapter.events[0][2])

    async def test_busy_intake_only_claims_receipt_before_native_routing(self):
        from plugin.progress import TaskProgress
        from plugin.status import TurnState
        state = TurnState('s', 'k', self.source, self.adapter, 1, [None], [], None, None,
                          progress=TaskProgress(), language='en')
        self.runtime.registry.bind(state)
        await self.runtime.intake.begin(self.source, 'A separate task', self.adapter)
        self.assertIn('Got your message.', self.adapter.events[0][2])
        self.assertNotIn('added', self.adapter.events[0][2])

    async def test_normal_turn_adopts_early_bubble_and_native_cleanup_id(self):
        await self.runtime.intake.begin(self.source, "Check a file", self.adapter)
        turn = NS(source=self.source, session_id="s", session_key="k", run_generation=1,
                  stream_consumer_holder=[None], _cleanup_msg_ids=[], _status_thread_metadata=None,
                  agent_holder=[None])
        worker = asyncio.get_running_loop().create_future()
        worker.set_result(None)
        self.runtime.delay = 0
        task = self.runtime.prepare_status_lifecycle(NS(_adapter_for_source=lambda _: self.adapter), turn, [worker])
        state = self.runtime.registry.get("s")
        self.assertEqual(state.status_message_id, "1")
        self.assertEqual(turn._cleanup_msg_ids, ["1"])
        self.assertFalse(self.runtime.intake.pending)
        await task
        self.assertEqual(len(self.adapter.events), 1)

    async def test_internal_operation_edits_existing_bubble(self):
        await self.runtime.intake.begin(self.source, "Continue", self.adapter)
        await self.runtime.intake.internal(self.source, "🧠 正在整理前面的聊天，稍等一下。")
        self.assertEqual(self.adapter.events[-1], ("edit", "1", "🧠 Tidying up our earlier conversation. Hang on a moment."))

    async def test_late_cleanup_cannot_delete_replacement(self):
        await self.runtime.intake.begin(self.source, "one", self.adapter)
        old = self.runtime.intake.take(self.source)
        await self.runtime.intake.begin(self.source, "two", self.adapter)
        await self.runtime.intake.retire(source_key(self.source, self.adapter), old)
        self.assertTrue(self.runtime.intake.pending)
        self.assertEqual([e[0] for e in self.adapter.events], ["send", "send"])

    async def test_other_user_or_topic_gets_a_separate_receipt(self):
        await self.runtime.intake.begin(self.source, "one", self.adapter)
        other = SessionSource(Platform.TELEGRAM, "123", user_id="v", thread_id="9")
        await self.runtime.intake.begin(other, "two", self.adapter)
        await self.runtime.intake.retire(source_key(self.source, self.adapter), self.runtime.intake.pending[source_key(self.source, self.adapter)])
        self.assertIn(source_key(other, self.adapter), self.runtime.intake.pending)

    async def test_native_authorization_must_be_definite_before_early_feedback(self):
        app = NS(add_handler=lambda handler, group: setattr(app, "handler", handler))
        self.adapter._should_process_message = lambda *a, **k: True
        self.adapter._source_from_message_for_auth = lambda _: self.source
        self.adapter._is_sender_authorized = lambda *a, **k: None
        self.adapter._legacy_runner_auth_fn = lambda: None
        self.runtime.intake.wire(app, self.adapter)
        update = NS(effective_message=NS(text="hello", caption=None))
        await app.handler.callback(update, None)
        self.assertFalse(self.adapter.events)
        self.adapter._is_sender_authorized = lambda *a, **k: True
        await app.handler.callback(update, None)
        self.assertEqual(self.adapter.events[0][2], "Hey! 👋")

    async def test_hygiene_event_starts_before_work_and_cleanup_runs_on_failure(self):
        feedback = self.runtime.intake
        adapter = self.adapter
        observed = []
        class Gateway:
            async def _hmwa_hygiene_plan(self, *args): return NS(needs_compress=True)
            async def _hmwa_hygiene_notify(self, *args): pass
            async def _hmwa_run_session_hygiene(self, event, source):
                await self._hmwa_hygiene_plan()
                observed.append(feedback.pending[source_key(source, adapter)].internal_status)
                raise RuntimeError("fixture failed before model start")
            async def _handle_message_with_agent(self, event, source):
                return await self._hmwa_run_session_hygiene(event, source)
        feedback.patch_gateway(Gateway)
        await feedback.begin(self.source, "Continue", self.adapter)
        with self.assertRaisesRegex(RuntimeError, "fixture"):
            await Gateway()._handle_message_with_agent(None, self.source)
        self.assertEqual(observed, ["🧠 正在整理前面的聊天，稍等一下。"])
        self.assertEqual(self.adapter.events[-1][0], "delete")
        self.assertFalse(feedback.pending)

    async def test_native_hygiene_notices_distinguish_deferred_failed_and_recovered(self):
        class Gateway:
            _handle_message_with_agent = AsyncMock()
            _hmwa_hygiene_plan = AsyncMock()
            _hmwa_run_session_hygiene = AsyncMock()
            async def _hmwa_hygiene_notify(self, source, meta, message, what): return message
        self.runtime.intake.patch_gateway(Gateway)
        runner = Gateway()
        deferred = await runner._hmwa_hygiene_notify(self.source, None, "native", "compression-turnhold notice")
        self.assertIn("isn't ready yet", deferred)
        self.assertNotIn("failed", deferred)
        failed = await runner._hmwa_hygiene_notify(self.source, None, "native", "compression-failure warning")
        self.assertIn("original messages are still there", failed)
        self.assertIn("/compress", failed)
        recovered = await runner._hmwa_hygiene_notify(self.source, None, "native", "aux-model-fallback notice")
        self.assertIn("main model finished", recovered)
        unchanged = await runner._hmwa_hygiene_notify(self.source, None, "unknown native notice", "future-event")
        self.assertEqual(unchanged, "unknown native notice")

    async def test_native_in_turn_compression_edits_only_the_live_turn(self):
        from gateway.run_turn_runner import TurnRunner
        from agent.conversation_compression import COMPACTION_STATUS, COMPACTION_DONE_STATUS

        class Gateway:
            _handle_message_with_agent = AsyncMock()
            _hmwa_hygiene_plan = AsyncMock()
            _hmwa_run_session_hygiene = AsyncMock()
            _hmwa_hygiene_notify = AsyncMock()

        self.runtime.intake.patch_gateway(Gateway)
        await self.runtime.intake.begin(self.source, "Continue", self.adapter)
        state = self.runtime.intake.take(self.source)
        state.session_id = "s"
        self.runtime.registry.bind(state)
        scheduled = []
        runner = NS(_ctx=NS(session_id="s", source=self.source),
                    _status_live=lambda: True,
                    _schedule=lambda coro, label: scheduled.append(coro))

        TurnRunner._status_callback_sync(runner, "info", COMPACTION_STATUS)
        await scheduled.pop(0)
        self.assertEqual(self.adapter.events[-1],
                         ("edit", "1", "🧠 Tidying up our earlier conversation. Hang on a moment."))
        TurnRunner._status_callback_sync(runner, "compacted", COMPACTION_DONE_STATUS)
        await scheduled.pop(0)
        self.assertEqual(self.adapter.events[-1],
                         ("edit", "1", "🧐 Earlier conversation tidied up. Back to your request."))

        TurnRunner._status_callback_sync(runner, "info", COMPACTION_STATUS)
        state.ended = True
        previous = list(self.adapter.events)
        await scheduled.pop(0)
        self.assertEqual(self.adapter.events, previous)

    async def test_another_group_member_receives_own_bubble_when_one_member_is_running(self):
        from plugin.status import TurnState
        from plugin.progress import TaskProgress
        first = SessionSource(Platform.TELEGRAM, "-100", user_id="alice", chat_type="group")
        second = SessionSource(Platform.TELEGRAM, "-100", user_id="bob", chat_type="group")
        state = TurnState("alice-session", "alice-key", first, self.adapter, 1, [None], [], None, None,
                          progress=TaskProgress(), language="en")
        self.runtime.registry.bind(state)
        await self.runtime.intake.begin(second, "My own task", self.adapter)
        self.assertEqual(len(self.adapter.events), 1)
        self.assertEqual(self.adapter.events[0][:2], ("send", "-100"))
        self.assertIn(source_key(second, self.adapter), self.runtime.intake.pending)
        self.assertIsNone(state.status_message_id)

    async def test_same_source_on_two_bots_gets_separate_pending_receipts(self):
        other_bot = Adapter()
        await self.runtime.intake.begin(self.source, "hello", self.adapter)
        await self.runtime.intake.begin(self.source, "hello", other_bot)
        self.assertEqual(len(self.runtime.intake.pending), 2)
        self.assertEqual(len(self.adapter.events), 1)
        self.assertEqual(len(other_bot.events), 1)
        self.assertIsNone(self.runtime.intake.take(self.source), "an adapter-less lookup cannot choose a bot")
        first = self.runtime.intake.take(self.source, self.adapter)
        self.assertIs(first.adapter, self.adapter)
        self.assertIn(source_key(self.source, other_bot), self.runtime.intake.pending)

    async def test_gateway_wrapper_restores_worker_owner_even_when_native_turn_fails(self):
        from plugin.full_adapter import current_turn
        marker = object()
        class Gateway:
            _hmwa_hygiene_plan = AsyncMock()
            _hmwa_run_session_hygiene = AsyncMock()
            _hmwa_hygiene_notify = AsyncMock()
            async def _handle_message_with_agent(self, event, source):
                current_turn.set(marker)
                raise RuntimeError("native failed")
        self.runtime.intake.patch_gateway(Gateway)
        before = current_turn.get()
        with self.assertRaisesRegex(RuntimeError, "native failed"):
            await Gateway()._handle_message_with_agent(None, self.source)
        self.assertIs(current_turn.get(), before)
