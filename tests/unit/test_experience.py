import asyncio
from types import SimpleNamespace
import unittest

from catalog.adapter import HermesCatalogAdapter
from catalog.experience import TOOL, normalize_note, turn_guidance
from catalog.model import Turn
from catalog.presentation import status_text
from test_catalog import ContextStub, TelegramStub, event, start


class ForbiddenState:
    def __init__(self):
        self.accesses = []

    def get(self, *args, **kwargs):
        self.accesses.append("get")
        raise AssertionError("Runtime must not read old preferences")

    def set(self, *args, **kwargs):
        self.accesses.append("set")
        raise AssertionError("Runtime must not persist preferences")


class Native:
    def __init__(self):
        self.bot = self
        self.approval_handler = object()
        self.handlers = [self.approval_handler]
        self.messages, self.markups, self.edits = [], [], []

    def add_handler(self, handler):
        self.handlers.append(handler)

    def remove_handler(self, handler):
        self.handlers.remove(handler)

    async def send_message(self, **kwargs):
        self.messages.append(kwargs)
        return SimpleNamespace(message_id=100 + len(self.messages))

    async def edit_message_reply_markup(self, **kwargs):
        self.markups.append(kwargs)

    async def edit_message_text(self, **kwargs):
        self.edits.append(kwargs)


class PublicNoteTests(unittest.TestCase):
    def test_public_notes_are_bounded_and_cannot_be_commands_or_delivery_directives(self):
        note = normalize_note({"goal": "x" * 1000, "finding": "MEDIA:/secret", "next": "a\n\u202eb",
                               "followups": ["/stop", "Continue", "Continue"], "hidden": "secret"})
        self.assertEqual(len(note["goal"]), 180)
        self.assertNotIn("finding", note)
        self.assertNotIn("hidden", note)
        self.assertNotIn("followups", note)
        self.assertNotIn("\u202e", note["next"])

    def test_status_stays_brief_without_elapsed_time_or_statistics(self):
        turn = Turn("s", "t", 10)
        turn.observe("pre_api_request", {"api_request_id": "a", "retry_count": 2}, 20)
        text = status_text(turn, "zh", now=80)
        self.assertNotIn("分", text)
        self.assertLessEqual(len(text.splitlines()), 2)
        self.assertNotIn("%", text)
        self.assertNotIn("完成", text)

    def test_guidance_only_describes_public_progress(self):
        guidance = turn_guidance()
        self.assertEqual(set(guidance), {"context"})
        context = guidance["context"]
        self.assertIn("telegram_ux_update", context)
        self.assertIn("verified", context)
        self.assertIn("not reasoning", context)
        self.assertIn("interim", context)
        self.assertNotIn("attachments", context)
        self.assertNotIn("/tgux", context)


class ExperienceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.ctx = ContextStub()
        self.ctx.state = ForbiddenState()
        self.adapter = HermesCatalogAdapter(self.ctx)
        self.adapter.register()
        self.native, self.telegram = Native(), TelegramStub()
        self.ctx.factory(self.native, self.telegram)
        self.adapter.transport.interval = .001
        self.adapter.transport.cleanup_delay = .001

    async def asyncTearDown(self):
        self.adapter.close()
        await asyncio.sleep(0)
        await asyncio.gather(*self.ctx.tasks, return_exceptions=True)

    async def settle(self):
        await asyncio.sleep(.02)

    async def begin(self):
        self.adapter.pre_gateway_dispatch(event=event())
        result = start(self.adapter)
        await self.settle()
        return result

    async def test_no_commands_handlers_or_persistent_preferences(self):
        await self.begin()
        self.assertEqual(self.ctx.commands, {})
        self.assertNotIn("pre_command", self.ctx.hooks)
        self.assertEqual(self.native.handlers, [self.native.approval_handler])
        self.assertFalse(self.native.messages or self.native.markups or self.native.edits)
        self.assertFalse(self.ctx.state.accesses)
        self.adapter.close()
        await self.settle()
        self.assertEqual(self.native.handlers, [self.native.approval_handler])

    async def test_legacy_settings_do_not_disable_progress_or_restore_old_ui(self):
        self.adapter.close()
        self.ctx.settings.update(progress=False, emoji=False, final_summary=True,
                                 display="detail", wait_hint=True, followups=True)
        self.adapter = HermesCatalogAdapter(self.ctx)
        self.adapter.register()
        self.ctx.factory(self.native, self.telegram)
        self.adapter.transport.interval = .001
        self.adapter.transport.cleanup_delay = .001
        result = await self.begin()
        self.assertIn("telegram_ux_update", result["context"])
        self.assertEqual(self.telegram.sent[-1]["content"], "🤔 正在思考中…")
        self.adapter.on_session_end(session_id="s1", turn_id="t1", completed=True)
        await self.settle()
        self.assertEqual(len(self.telegram.deleted), 1)
        self.assertFalse(self.ctx.state.accesses)
        self.assertFalse(self.native.messages or self.native.markups or self.native.edits)
        for item in self.telegram.sent + self.telegram.edits:
            self.assertNotIn("reply_markup", item)
            for obsolete in ("已用时", "本轮记录", "继续处理", "关闭提示"):
                self.assertNotIn(obsolete, item["content"])

    async def test_native_commands_remain_unhandled_and_do_not_create_status(self):
        for name in ("/new", "/stop", "/usage", "/tgux"):
            incoming = event()
            incoming.text = name
            self.adapter.pre_gateway_dispatch(event=incoming)
        await self.settle()
        self.assertEqual(self.ctx.commands, {})
        self.assertNotIn("pre_command", self.ctx.hooks)
        self.assertFalse(self.telegram.sent or self.native.messages)
        self.assertEqual(self.native.handlers, [self.native.approval_handler])


    async def test_normal_status_never_creates_a_menu(self):
        await self.begin()
        self.assertFalse(self.native.messages or self.native.markups or self.native.edits)
        self.assertNotIn("reply_markup", self.telegram.sent[0])

    async def test_weather_task_lifecycle_edits_one_message_then_cleans(self):
        self.adapter.pre_gateway_dispatch(event=event())
        start(self.adapter, user_message="帮我查一下上海未来7天天气，看看温度、湿度和风速")
        await self.settle()
        self.assertEqual(self.telegram.sent[0]["content"], "🤔 正在思考中…")
        ids = {"session_id": "s1", "turn_id": "t1"}
        self.adapter.observe("pre_tool_call", **ids, tool_name="web_search", tool_call_id="search",
                             args={"query": "上海未来7天天气"})
        await self.settle()
        self.assertIn("搜索上海", self.telegram.edits[-1]["content"])
        self.adapter.observe("post_tool_call", **ids, tool_name="web_search", tool_call_id="search", status="ok",
                             result={"data": {"web": [{"title": "Forecast", "url": "https://example.test"}]}})
        await self.settle()
        self.assertIn("1 条搜索结果", self.telegram.edits[-1]["content"])
        self.adapter.observe("pre_tool_call", **ids, tool_name="web_extract", tool_call_id="read",
                             args={"urls": ["https://example.test/weather"]})
        await self.settle()
        self.assertIn("上海", self.telegram.edits[-1]["content"])
        self.adapter.observe("post_tool_call", **ids, tool_name="web_extract", tool_call_id="read", status="ok",
                             result={"daily": {"temperature_2m_max": [25, 26], "wind_speed_10m_max": [4, 5]}})
        await self.settle()
        self.assertIn("温度、风速", self.telegram.edits[-1]["content"])
        self.assertNotIn("湿度", self.telegram.edits[-1]["content"])
        self.adapter.observe("post_llm_call", **ids, assistant_response="The untouched native answer")
        self.adapter.on_session_end(**ids, completed=True)
        await self.settle()
        self.assertEqual(len(self.telegram.sent), 1)
        self.assertTrue(all(item["message_id"] == "1" for item in self.telegram.edits + self.telegram.deleted))
        self.assertEqual(len(self.telegram.deleted), 1)
        self.assertFalse(self.native.messages or self.native.markups or self.native.edits)
        self.assertFalse(self.adapter.turns or self.adapter.transport.panels)
        self.assertTrue(all("untouched native answer" not in item["content"] for item in self.telegram.edits))

    async def test_public_progress_note_is_brief_without_child_or_followup_cards(self):
        await self.begin()
        data = dict(session_id="s1", turn_id="t1", tool_name=TOOL, tool_call_id="p",
                    args={"goal": "整理报告", "action": "比较报告中的两项结果", "finding": "确认两项结果"})
        self.adapter.observe("pre_tool_call", **data)
        self.adapter.observe("post_tool_call", **data, status="ok")
        self.adapter.observe("subagent_start", parent_session_id="s1", parent_turn_id="t1", child_session_id="child")
        self.adapter.observe("subagent_stop", parent_session_id="s1", parent_turn_id="t1", child_session_id="child", child_status="completed", child_summary="not copied")
        self.adapter.observe("subagent_start", parent_session_id="other", parent_turn_id="t1", child_session_id="wrong")
        await self.settle()
        text = self.telegram.edits[-1]["content"]
        self.assertIn("结果", text)
        self.assertNotIn("not copied", text)
        self.assertLessEqual(len(text.splitlines()), 2)
        self.assertFalse(self.adapter.turns[("s1", "t1")].tools)
        self.assertNotIn("wrong", repr(self.adapter.turns[("s1", "t1")]))
        self.adapter.on_session_end(session_id="s1", turn_id="t1", completed=True)
        await self.settle()
        self.assertEqual(len(self.telegram.deleted), 1)

    async def test_blocked_progress_tool_never_claims_its_note(self):
        await self.begin()
        self.adapter.observe("post_tool_call", session_id="s1", turn_id="t1", tool_name=TOOL,
                             tool_call_id="p", args={"finding": "should not appear"}, status="blocked")
        self.assertFalse(self.adapter.turns[("s1", "t1")].note)

    async def test_progress_edits_have_no_buttons_and_completion_deletes(self):
        await self.begin()
        self.adapter.observe("pre_tool_call", session_id="s1", turn_id="t1", tool_call_id="a", tool_name="read_file", args={"path": "/project/catalog/telegram.py"})
        await self.settle()
        self.assertIn("telegram.py", self.telegram.edits[-1]["content"])
        self.assertFalse(self.native.markups or self.native.edits)
        self.assertTrue(all("reply_markup" not in call for call in self.telegram.sent + self.telegram.edits))
        self.adapter.on_session_end(session_id="s1", turn_id="t1", completed=True)
        await self.settle()
        self.assertEqual(len(self.telegram.sent), 1)
        self.assertEqual(len(self.telegram.deleted), 1)
        self.assertTrue(all("已结束" not in call["content"] for call in self.telegram.sent + self.telegram.edits))

    async def test_native_reply_is_never_transformed_even_with_old_preference(self):
        self.ctx.settings["final_summary"] = True
        await self.begin()
        self.assertNotIn("transform_llm_output", self.ctx.hooks)
        self.adapter.observe("post_llm_call", session_id="s1", turn_id="t1", assistant_response="native answer not copied")
        await self.settle()
        self.assertNotIn("native answer not copied", self.telegram.edits[-1]["content"])


if __name__ == "__main__":
    unittest.main()
