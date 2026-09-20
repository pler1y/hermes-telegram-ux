import asyncio
from contextvars import Context
from types import SimpleNamespace
import unittest

from catalog.adapter import HermesCatalogAdapter, HOOKS
from catalog.presentation import status_text


class ContextStub:
    profile_name = "default"

    def __init__(self, **settings):
        self.settings, self.hooks, self.tasks = settings, {}, []
        self.commands = {}

    def get_config(self, key, default=None):
        return self.settings.get(key, default)

    def register_hook(self, name, cb):
        self.hooks[name] = cb

    def register_platform_handler(self, platform, factory):
        self.factory = factory

    def register_command(self, name, cb, **kwargs):
        self.commands[name] = cb

    def register_tool(self, **kwargs):
        self.tool = kwargs

    def on_unload(self, cb):
        self.unload = cb

    def spawn_task(self, coro, **kwargs):
        task = asyncio.create_task(coro)
        self.tasks.append(task)
        return task


class TelegramStub:
    def __init__(self):
        self.sent, self.edits, self.deleted = [], [], []
        self.failure, self.edit_failure = None, None
        self.send_gate = None
        self.edit_gate = None

    async def send(self, **kwargs):
        self.sent.append(kwargs)
        if self.send_gate:
            await self.send_gate.wait()
        if self.failure:
            raise self.failure
        return SimpleNamespace(success=True, message_id=str(len(self.sent)))

    async def edit_message(self, **kwargs):
        self.edits.append(kwargs)
        if self.edit_gate:
            await self.edit_gate.wait()
        if self.edit_failure:
            return SimpleNamespace(success=False, retry_after=None)
        return SimpleNamespace(success=True)

    async def delete_message(self, **kwargs):
        self.deleted.append(kwargs)
        return True


def event(chat="101", user="101", thread=None, message="10", **source):
    return SimpleNamespace(internal=False, message_id=message,
        source=SimpleNamespace(platform="telegram", chat_id=chat, user_id=user,
                               thread_id=thread, **source))


def start(adapter, sid="s1", tid="t1", sender="101", **kwargs):
    return adapter.pre_llm_call(session_id=sid, turn_id=tid, sender_id=sender, platform="telegram", **kwargs)


class StateTests(unittest.TestCase):
    def setUp(self):
        self.ctx = ContextStub(final_summary=True)
        self.adapter = HermesCatalogAdapter(self.ctx)
        self.adapter.register()
        start(self.adapter)

    def tearDown(self):
        self.adapter.close()

    def feed(self, name, **kwargs):
        return self.ctx.hooks[name](session_id="s1", turn_id="t1", **kwargs)

    def test_registration_is_exact_and_observers_never_direct(self):
        self.assertEqual(set(self.ctx.hooks), set(HOOKS))
        self.assertIsNone(self.feed("pre_tool_call", tool_call_id="a", tool_name="terminal", args={"secret": "abc"}))
        self.assertIsNone(self.feed("pre_approval_request", tool_call_id="a", command="secret", surface="gateway"))
        self.assertIn("等待审批", status_text(self.adapter.turns[("s1", "t1")], "zh"))
        self.assertNotIn("secret", repr(self.adapter.turns))

    def test_duplicate_and_out_of_order_tool_events(self):
        self.feed("post_tool_call", tool_call_id="a", tool_name="read_file", status="error")
        self.feed("post_tool_call", tool_call_id="a", tool_name="read_file", status="error")
        self.feed("pre_tool_call", tool_call_id="a", tool_name="read_file")
        turn = self.adapter.turns[("s1", "t1")]
        self.assertEqual(turn.tools, {"a": ("read_file", "error")})
        self.assertFalse(turn.apis)
        self.assertNotEqual(turn.phase()[0], "tool")

    def test_api_retries_count_distinct_attempts(self):
        for rid in ("r1", "r1", "r2"):
            self.feed("pre_api_request", api_request_id=rid)
        self.feed("api_request_error", api_request_id="r1", retryable=True)
        self.feed("post_api_request", api_request_id="r2")
        self.assertEqual(set(self.adapter.turns[("s1", "t1")].apis), {"r1", "r2"})
        self.assertFalse(self.adapter.turns[("s1", "t1")].tools)

    def test_activity_hooks_refresh_ttl_without_storing_text_or_changing_progress(self):
        now = [10.0]
        self.adapter.clock = lambda: now[0]
        for index in range(513):
            self.feed("pre_tool_call", tool_call_id=str(index), tool_name="read_file", args={"path": "/tmp/readme.md"})
        turn = self.adapter.turns[("s1", "t1")]
        progress = dict(turn.progress)
        containers = (len(turn.tools), len(turn.apis), len(turn.approvals), len(turn.note_calls))
        self.assertEqual(containers, (512, 0, 0, 0))
        self.assertNotIn("512", turn.tools)
        now[0] = 11.0
        self.feed("on_interim_message", iteration=1, text="native interim must not be copied")
        self.assertEqual(turn.touched, 11.0)
        now[0] = 12.0
        self.adapter.observe("subagent_stop", parent_session_id="s1", parent_turn_id="t1",
                             child_session_id="child", child_status="completed", child_summary="private child summary")
        self.assertEqual(turn.touched, 12.0)
        self.assertEqual(turn.progress, progress)
        self.assertEqual((len(turn.tools), len(turn.apis), len(turn.approvals), len(turn.note_calls)), containers)
        self.assertNotIn("native interim", repr(turn))
        self.assertNotIn("private child", repr(turn))
        self.adapter.observe("subagent_start", parent_session_id="wrong", parent_turn_id="t1", child_session_id="wrong")
        self.assertEqual(turn.touched, 12.0)

    def test_approvals_correlate_by_unique_turn_not_session_key(self):
        self.ctx.hooks["pre_approval_request"](turn_id="t1", tool_call_id="a", session_key="opaque:route", surface="gateway")
        turn = self.adapter.turns[("s1", "t1")]
        self.assertEqual(turn.phase()[0], "approval")
        self.ctx.hooks["post_approval_response"](turn_id="t1", tool_call_id="a", choice="cancelled")
        self.assertEqual(turn.phase()[0], "approval_cancelled")

    def test_smart_approval_is_not_human_wait(self):
        self.feed("pre_approval_request", tool_call_id="a", surface="smart")
        self.assertEqual(self.adapter.turns[("s1", "t1")].phase()[0], "smart")

    def test_concurrent_sessions_and_late_events(self):
        start(self.adapter, "s2", "t2", "102")
        self.feed("pre_tool_call", tool_call_id="a", tool_name="read_file")
        self.assertFalse(self.adapter.turns[("s2", "t2")].tools or self.adapter.turns[("s2", "t2")].apis)
        self.adapter.on_session_end(session_id="s1", turn_id="t1", completed=True)
        self.feed("post_tool_call", tool_call_id="a", tool_name="read_file", status="ok")
        self.assertNotIn(("s1", "t1"), self.adapter.turns)
        self.assertIn(("s2", "t2"), self.adapter.turns)

    def test_ambiguous_approval_is_ignored(self):
        start(self.adapter, "s2", "t1", "102")
        self.ctx.hooks["pre_approval_request"](turn_id="t1", tool_call_id="a")
        self.assertTrue(all(not turn.approvals for turn in self.adapter.turns.values()))

    def test_legacy_summary_setting_cannot_register_final_answer_transform(self):
        self.feed("post_tool_call", tool_call_id="a", tool_name="read_file", status="ok")
        self.assertNotIn("transform_llm_output", self.ctx.hooks)
        self.assertIn("post_llm_call", self.ctx.hooks)
        self.assertNotIn("本轮记录", status_text(self.adapter.turns[("s1", "t1")], "zh"))

    def test_post_llm_observation_never_copies_or_rewrites_final_payload(self):
        for value in ("中文🙂\n```python\nprint(1)\n```", "", " ", "[SILENT]", "NO_REPLY", "HEARTBEAT_OK", "MEDIA:/tmp/file.png", "Files\nMEDIA:/tmp/file.csv", "```python\nx"):
            with self.subTest(value=value):
                self.assertIsNone(self.feed("post_llm_call", assistant_response=value, conversation_history=[{"content": "hidden narrative"}]))
                self.assertNotIn("hidden narrative", repr(self.adapter.turns))
                self.assertEqual(status_text(self.adapter.turns[("s1", "t1")], "zh"), "✍️ 正在整理最终回答…")
        self.assertNotIn("transform_llm_output", self.ctx.hooks)

    def test_other_platform_cannot_start_a_telegram_status(self):
        result = self.adapter.pre_llm_call(session_id="cli", turn_id="t2", platform="cli", sender_id="101", user_message="hello")
        self.assertIsNone(result)
        self.assertNotIn(("cli", "t2"), self.adapter.turns)

    def test_reset_only_discards_outgoing_session(self):
        start(self.adapter, "s2", "t2", "102")
        self.adapter.on_session_reset(old_session_id="s1", session_id="s2")
        self.assertEqual(set(self.adapter.turns), {("s2", "t2")})

    def test_missing_identifiers_and_subagents_do_not_create_states(self):
        start(self.adapter, "", "", "")
        start(self.adapter, "child", "ct", "101", parent_session_id="s1")
        self.assertEqual(len(self.adapter.turns), 1)

    def test_missing_and_malformed_events_never_block(self):
        for name in HOOKS:
            if name not in ("pre_llm_call", "pre_gateway_dispatch"):
                self.assertIsNone(self.ctx.hooks[name](future_field={"x": 1}))
        self.feed("post_tool_call", tool_call_id={}, tool_name="<b>bad</b>", status="ok")
        self.assertFalse(self.adapter.turns[("s1", "t1")].tools or self.adapter.turns[("s1", "t1")].apis)

    def test_event_storage_is_bounded(self):
        for i in range(900):
            self.feed("pre_tool_call", tool_call_id=str(i), tool_name="x")
        self.assertEqual(len(self.adapter.turns[("s1", "t1")].tools), 512)
        self.assertNotIn("512", self.adapter.turns[("s1", "t1")].tools)
        self.assertEqual(len(self.adapter.turns[("s1", "t1")].observations), 512)

    def test_ttl_is_status_expiry_not_a_task_timeout(self):
        now = [0.0]
        adapter = HermesCatalogAdapter(ContextStub(), clock=lambda: now[0])
        start(adapter)
        now[0] = 601
        adapter.observe("pre_tool_call", session_id="s1", turn_id="t1", tool_call_id="a")
        self.assertFalse(adapter.turns)

    def test_invalid_settings_fall_back_and_unload_clears(self):
        adapter = HermesCatalogAdapter(ContextStub(language="bad", status_ttl="nan", update_interval="oops", cleanup_delay="nan"))
        self.assertEqual((adapter.ttl, adapter.interval, adapter.cleanup_delay), (600, 1.5, 1))
        start(adapter, user_message="Please check the forecast")
        self.assertEqual(adapter.turns[("s1", "t1")].language, "en")
        adapter.close()
        self.ctx.unload()
        start(self.adapter, "s3", "t3")
        self.assertFalse(self.adapter.turns)


class TransportTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.ctx = ContextStub(cleanup_delay=0.005)
        self.adapter = HermesCatalogAdapter(self.ctx)
        self.adapter.register()
        self.telegram = TelegramStub()
        self.ctx.factory(None, self.telegram)
        self.adapter.transport.interval = 0.001

    async def asyncTearDown(self):
        self.adapter.close()
        await asyncio.sleep(0)
        await asyncio.gather(*self.ctx.tasks, return_exceptions=True)

    async def settle(self):
        await asyncio.sleep(0.02)

    async def begin(self, incoming=None, sid="s1", tid="t1", sender="101"):
        self.adapter.pre_gateway_dispatch(event=incoming or event())
        # This models the standard context propagation; actual manager tests cover its timeout workers.
        await asyncio.to_thread(start, self.adapter, sid, tid, sender)
        await self.settle()

    async def test_no_reply_before_authorized_execution(self):
        self.adapter.pre_gateway_dispatch(event=event())
        await self.settle()
        self.assertFalse(self.telegram.sent)

    async def test_topic_route_and_single_edited_panel(self):
        await self.begin(event(chat="-10042", thread="7"))
        self.adapter.observe("pre_tool_call", session_id="s1", turn_id="t1", tool_call_id="a", tool_name="read_file")
        await self.settle()
        self.assertEqual(len(self.telegram.sent), 1)
        self.assertEqual(self.telegram.sent[0]["metadata"], {"thread_id": "7"})
        self.assertEqual(self.telegram.sent[0]["reply_to"], "10")
        self.assertIn("正在检查指定文件", self.telegram.edits[-1]["content"])

    async def test_context_loss_falls_back_without_network(self):
        self.adapter.pre_gateway_dispatch(event=event())
        Context().run(start, self.adapter)
        await self.settle()
        self.assertFalse(self.telegram.sent)
        self.assertIn(("s1", "t1"), self.adapter.turns)

    async def test_ticket_cannot_be_reused_by_internal_or_later_turn(self):
        await self.begin()
        self.adapter.on_session_end(session_id="s1", turn_id="t1", completed=True)
        start(self.adapter, "s1", "t2")
        await self.settle()
        self.assertEqual(len(self.telegram.sent), 1)
        self.assertNotIn(("s1", "t2"), self.adapter.routes)

    async def test_sender_profile_and_expired_route_rejected(self):
        for incoming, sender in ((event(), "999"), (event(profile="other"), "101")):
            self.adapter.pre_gateway_dispatch(event=incoming)
            start(self.adapter, sid=str(sender) + str(incoming.source), tid="t", sender=sender)
        self.adapter.pre_gateway_dispatch(event=event())
        self.adapter.ingress.get().created -= 61
        start(self.adapter, "expired", "t3")
        await self.settle()
        self.assertFalse(self.telegram.sent)

    async def test_parallel_task_contexts_keep_routes_separate(self):
        await asyncio.gather(self.begin(event(chat="-10001", thread="1"), "a", "ta"),
                             self.begin(event(chat="-10001", thread="2"), "b", "tb"))
        self.assertEqual({item["metadata"]["thread_id"] for item in self.telegram.sent}, {"1", "2"})
        self.adapter.on_session_end(session_id="a", turn_id="ta", interrupted=True)
        await self.settle()
        self.assertEqual(set(self.adapter.turns), {("b", "tb")})
        self.assertIn("已中断", self.telegram.edits[-1]["content"])
        self.assertEqual(len(self.telegram.deleted), 1)
        self.assertEqual(set(self.adapter.transport.panels), {("b", "tb")})

    async def test_unknown_initial_send_is_never_retried(self):
        self.telegram.failure = TimeoutError("secret")
        await self.begin()
        for i in range(4):
            self.adapter.observe("pre_api_request", session_id="s1", turn_id="t1", api_request_id=str(i))
            await self.settle()
        self.assertEqual(len(self.telegram.sent), 1)
        self.adapter.on_session_end(session_id="s1", turn_id="t1", completed=True)
        await self.settle()
        self.assertIn(("s1", "t1"), self.adapter.transport.blocked)
        self.assertFalse(self.adapter.transport.panels)
        self.assertFalse(self.telegram.deleted)

    async def test_edit_failure_never_sends_replacement(self):
        await self.begin()
        self.telegram.edit_failure = True
        for i in range(3):
            self.adapter.observe("pre_tool_call", session_id="s1", turn_id="t1", tool_call_id=str(i), tool_name="read_file")
            await self.settle()
        self.assertEqual(len(self.telegram.sent), 1)
        self.assertEqual(len(self.telegram.deleted), 1)
        self.assertFalse(self.adapter.transport.panels)

    async def test_finish_during_send_updates_only_owned_message(self):
        self.telegram.send_gate = asyncio.Event()
        await self.begin()
        self.adapter.on_session_end(session_id="s1", turn_id="t1", completed=True)
        self.telegram.send_gate.set()
        await self.settle()
        self.assertEqual(len(self.telegram.sent), 1)
        self.assertIn("正在整理最终回答", self.telegram.edits[-1]["content"])
        self.assertFalse(self.adapter.turns)
        self.assertEqual(self.telegram.deleted, [{"chat_id": "101", "message_id": "1"}])

    async def test_finish_during_inflight_edit_flushes_terminal_status(self):
        await self.begin()
        self.telegram.edit_gate = asyncio.Event()
        self.adapter.observe("pre_tool_call", session_id="s1", turn_id="t1", tool_call_id="a", tool_name="web_search", args={"query": "上海未来7天天气"})
        await self.settle()
        self.assertIn("上海未来 7 天天气", self.telegram.edits[-1]["content"])
        self.adapter.on_session_end(session_id="s1", turn_id="t1", completed=True)
        await self.settle()
        self.telegram.edit_gate.set()
        await self.settle()
        self.assertEqual(len(self.telegram.sent), 1)
        self.assertIn("正在整理最终回答", self.telegram.edits[-1]["content"])
        self.assertFalse(self.adapter.transport.panels)
        self.assertEqual(len(self.telegram.deleted), 1)

    async def test_interim_text_is_not_resent(self):
        await self.begin()
        self.adapter.observe("pre_tool_call", session_id="s1", turn_id="t1", tool_call_id="a", tool_name="web_search", args={"query": "OpenAI 新闻"})
        await self.settle()
        before = list(self.telegram.edits)
        self.adapter.observe("on_interim_message", session_id="s1", turn_id="t1", iteration=1, text="private text", already_streamed=True)
        await self.settle()
        self.assertNotIn("private text", str(self.telegram.edits))
        self.assertEqual(self.telegram.edits, before)
        self.assertIn("OpenAI 新闻", self.telegram.edits[-1]["content"])

    async def test_expiry_cleans_state_without_claiming_task_failed(self):
        self.adapter.transport.ttl = 0.03
        await self.begin()
        await asyncio.sleep(0.05)
        self.assertFalse(self.adapter.turns)
        self.assertIn("状态更新已超时", self.telegram.edits[-1]["content"])
        self.assertEqual(len(self.telegram.deleted), 1)
        self.assertFalse(self.adapter.transport.panels)

    async def test_reset_and_unload_cancel_owned_panels(self):
        await self.begin()
        self.adapter.on_session_reset(old_session_id="s1")
        await self.settle()
        self.assertEqual(len(self.telegram.deleted), 1)
        self.assertFalse(self.adapter.transport.panels)

    async def test_reconnect_does_not_reuse_old_ticket(self):
        self.adapter.pre_gateway_dispatch(event=event())
        newer = TelegramStub()
        self.ctx.factory(None, newer)
        start(self.adapter)
        await self.settle()
        self.assertFalse(self.telegram.sent or newer.sent)


if __name__ == "__main__":
    unittest.main()
