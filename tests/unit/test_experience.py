import asyncio
from copy import deepcopy
import time
from types import SimpleNamespace
import unittest

from catalog.adapter import HermesCatalogAdapter
from catalog.experience import TOOL, normalize_note
from catalog.model import Turn
from catalog.preferences import Preferences
from catalog.presentation import status_text
from catalog.telegram import Route
from test_catalog import ContextStub, TelegramStub, event, start


class MemoryState:
    def __init__(self):
        self.data = {}
        self.fail = False

    def get(self, key, default=None):
        return deepcopy(self.data.get(key, default))

    def set(self, key, value):
        if self.fail:
            raise ValueError("quota")
        self.data[key] = deepcopy(value)


class Native:
    def __init__(self):
        self.bot = self
        self.handlers, self.messages, self.markups, self.edits = [], [], [], []

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


class Query:
    def __init__(self, card, action, owner=None, chat=None, topic=None, message=None):
        self.data = "tgux2:" + card.token + ":" + action
        self.from_user = SimpleNamespace(id=owner or card.route.owner_id)
        self.message = SimpleNamespace(chat=SimpleNamespace(id=chat or card.route.chat_id),
            message_id=message or card.message_id, message_thread_id=topic or card.route.thread_id)
        self.answers, self.edits, self.deleted = [], [], False

    async def answer(self, *args, **kwargs):
        self.answers.append((args, kwargs))

    async def edit_message_text(self, **kwargs):
        self.edits.append(kwargs)

    async def delete_message(self):
        self.deleted = True


class PreferenceTests(unittest.TestCase):
    def setUp(self):
        self.ctx = ContextStub()
        self.ctx.state = MemoryState()

    def test_preferences_survive_reload_and_do_not_change_other_users_or_topics(self):
        prefs = Preferences(self.ctx)
        a, b, c = Route("-10", "1", "2", "10"), Route("-10", "2", "2", "11"), Route("-10", "3", "3", "10")
        prefs.toggle(a, "language")
        self.assertEqual(Preferences(self.ctx).read(a)["language"], "en")
        self.assertEqual(prefs.read(b)["language"], "zh")
        self.assertEqual(prefs.read(c)["language"], "zh")
        self.assertEqual(self.ctx.settings, {})

    def test_invalid_saved_types_do_not_enable_behavior(self):
        route = Route("10", "1", None, "10")
        prefs = Preferences(self.ctx)
        self.ctx.state.set(prefs.key(route), {"progress": 1, "language": "xx", "surprise": True})
        self.assertIs(prefs.read(route)["progress"], True)
        self.assertEqual(prefs.read(route)["language"], "zh")
        self.assertNotIn("surprise", prefs.read(route))

    def test_failed_save_does_not_claim_or_apply_success(self):
        prefs, route = Preferences(self.ctx), Route("10", "1", None, "10")
        self.ctx.state.fail = True
        with self.assertRaises(ValueError):
            prefs.toggle(route, "language")
        self.assertEqual(prefs.read(route)["language"], "zh")

    def test_public_notes_are_bounded_and_cannot_be_commands_or_delivery_directives(self):
        note = normalize_note({"goal": "x" * 1000, "finding": "MEDIA:/secret", "next": "a\n\u202eb",
                               "followups": ["/stop", "Continue", "Continue"], "hidden": "secret"})
        self.assertEqual(len(note["goal"]), 180)
        self.assertNotIn("finding", note)
        self.assertNotIn("hidden", note)
        self.assertEqual(note["followups"], ["Continue"])
        self.assertNotIn("\u202e", note["next"])

    def test_elapsed_and_retry_feedback_does_not_invent_completion(self):
        turn = Turn("s", "t", 10)
        turn.observe("pre_api_request", {"api_request_id": "a", "retry_count": 2}, 20)
        text = status_text(turn, "zh", now=80)
        self.assertIn("1 分 10 秒", text)
        self.assertIn("重试 2 次", text)
        self.assertNotIn("%", text)
        self.assertNotIn("完成", text)

    def test_no_emoji_does_not_remove_words_from_plain_status(self):
        turn = Turn("s", "t", time.monotonic(), preferences={"emoji": False})
        self.assertTrue(status_text(turn, "en", "unknown_end").startswith("Turn ended"))
        self.assertFalse(status_text(turn, "zh").startswith("⏳"))


class ExperienceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.ctx = ContextStub()
        self.ctx.state = MemoryState()
        self.adapter = HermesCatalogAdapter(self.ctx)
        self.adapter.register()
        self.native, self.telegram = Native(), TelegramStub()
        self.ctx.factory(self.native, self.telegram)
        self.adapter.transport.interval = .001

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

    async def menu(self):
        incoming = event()
        incoming.text = "/tgux"
        self.adapter.pre_gateway_dispatch(event=incoming)
        self.adapter.pre_command(surface="gateway", command="tgux", platform="telegram")
        self.assertIsNone(self.adapter.help_command())
        await self.settle()
        return list(self.adapter.interface.cards.values())[-1]

    async def click(self, card, action, **kwargs):
        query = Query(card, action, **kwargs)
        await self.adapter.interface.callback(SimpleNamespace(callback_query=query), None)
        return query

    async def test_menu_requires_authorized_command_not_just_incoming_text(self):
        incoming = event()
        incoming.text = "/tgux"
        self.adapter.pre_gateway_dispatch(event=incoming)
        self.assertIsInstance(self.adapter.help_command(), str)
        await self.settle()
        self.assertFalse(self.native.messages)
        card = await self.menu()
        self.assertEqual(card.route.owner_id, "101")
        self.assertIn("任务助手", self.native.messages[-1]["text"])
        # Consumed ticket cannot create another card.
        self.assertIsInstance(self.adapter.help_command(), str)

    async def test_sdk_callback_scope_leaves_native_buttons_alone(self):
        import re
        handler = self.native.handlers[0]
        self.assertIsNone(re.match(handler.pattern, "approve:123"))
        self.assertIsNotNone(re.match(handler.pattern, "tgux2:abc:close"))

    async def test_card_owner_chat_topic_message_and_expiry_checked(self):
        card = await self.menu()
        for mismatch in ({"owner": "999"}, {"chat": "999"}, {"topic": "999"}, {"message": "999"}):
            query = await self.click(card, "set_language", **mismatch)
            self.assertTrue(query.answers[0][1]["show_alert"])
        self.assertFalse(self.ctx.state.data)
        card.expires = 0
        query = await self.click(card, "close")
        self.assertFalse(query.deleted)

    async def test_settings_save_and_take_effect_next_turn(self):
        card = await self.menu()
        await self.click(card, "set_language")
        result = await self.begin()
        self.assertIn("telegram_ux_update", result["context"])
        self.assertIn("Working", self.telegram.sent[-1]["content"])
        self.assertEqual(self.ctx.settings, {})

    async def test_save_failure_is_visible_and_leaves_setting_unchanged(self):
        card = await self.menu()
        self.ctx.state.fail = True
        query = await self.click(card, "set_language")
        self.assertIn("Action failed", query.answers[-1][0][0])
        self.assertFalse(query.edits)

    async def test_hide_only_stops_plugin_display_not_turn(self):
        await self.begin()
        card = list(self.adapter.interface.cards.values())[0]
        query = await self.click(card, "close")
        await self.settle()
        self.assertTrue(query.deleted)
        self.assertIn(("s1", "t1"), self.adapter.turns)
        self.adapter.observe("pre_tool_call", session_id="s1", turn_id="t1", tool_call_id="a", tool_name="read_file")
        await self.settle()
        self.assertEqual(len(self.telegram.sent), 1)
        self.assertNotIn(("s1", "t1"), self.adapter.routes)

    async def test_status_details_menu_does_not_replace_live_card(self):
        await self.begin()
        card = list(self.adapter.interface.cards.values())[0]
        query = await self.click(card, "details")
        self.assertFalse(query.edits)
        self.assertIn("工具", self.native.messages[-1]["text"])
        self.assertEqual(len(self.adapter.interface.cards), 2)

    async def test_public_progress_tool_and_correlated_children_update_card(self):
        await self.begin()
        data = dict(session_id="s1", turn_id="t1", tool_name=TOOL, tool_call_id="p",
                    args={"goal": "整理报告", "finding": "确认两项结果", "followups": ["请展开第一项"]})
        self.adapter.observe("post_tool_call", **data, status="ok")
        self.adapter.observe("subagent_start", parent_session_id="s1", parent_turn_id="t1", child_session_id="child")
        self.adapter.observe("subagent_stop", parent_session_id="s1", parent_turn_id="t1", child_session_id="child", child_status="completed", child_summary="not copied")
        self.adapter.observe("subagent_start", parent_session_id="other", parent_turn_id="t1", child_session_id="wrong")
        await self.settle()
        text = self.native.edits[-1]["text"]
        self.assertIn("整理报告", text)
        self.assertIn("确认两项结果", text)
        self.assertIn("完成 1", text)
        self.assertNotIn("not copied", text)
        self.assertEqual(self.adapter.turns[("s1", "t1")].counts()[0], 0)
        self.adapter.on_session_end(session_id="s1", turn_id="t1", completed=True)
        await self.settle()
        card = list(self.adapter.interface.cards.values())[0]
        self.assertTrue(card.view["terminal"])
        await self.click(card, "followups")
        keyboard = self.native.messages[-1]["reply_markup"]
        self.assertEqual(keyboard.keyboard[0][0].text, "请展开第一项")
        self.assertTrue(keyboard.one_time_keyboard)
        self.assertTrue(keyboard.selective)

    async def test_blocked_progress_tool_never_claims_its_note(self):
        await self.begin()
        self.adapter.observe("post_tool_call", session_id="s1", turn_id="t1", tool_name=TOOL,
                             tool_call_id="p", args={"finding": "should not appear"}, status="blocked")
        self.assertFalse(self.adapter.turns[("s1", "t1")].note)

    async def test_progress_edits_keep_buttons_and_terminal_controls_atomically(self):
        await self.begin()
        self.adapter.observe("pre_tool_call", session_id="s1", turn_id="t1", tool_call_id="a", tool_name="read_file")
        await self.settle()
        edit = self.native.edits[-1]
        self.assertIn("正在阅读文件", edit["text"])
        self.assertIn("关闭提示", [b.text for row in edit["reply_markup"].inline_keyboard for b in row])
        self.assertFalse(self.telegram.edits)
        self.adapter.on_session_end(session_id="s1", turn_id="t1", completed=True)
        await self.settle()
        edit = self.native.edits[-1]
        self.assertIn("继续处理", [b.text for row in edit["reply_markup"].inline_keyboard for b in row])

    async def test_final_reply_default_is_unchanged(self):
        await self.begin()
        self.adapter.observe("pre_tool_call", session_id="s1", turn_id="t1", tool_name="read_file", tool_call_id="c")
        self.assertIsNone(self.adapter.transform_llm_output(response_text="Answer", platform="telegram", session_id="s1", turn_id="t1"))

    async def test_progress_off_still_allows_menu_and_native_answer(self):
        card = await self.menu()
        await self.click(card, "set_progress")
        await self.begin()
        self.assertFalse(self.telegram.sent)
        self.assertIn(("s1", "t1"), self.adapter.turns)
        self.assertIsNone(self.adapter.transform_llm_output(response_text="Answer", platform="telegram", session_id="s1", turn_id="t1"))

    async def test_native_commands_are_user_sent_and_not_injected(self):
        card = await self.menu()
        await self.click(card, "commands")
        keyboard = self.native.messages[-1]["reply_markup"]
        self.assertIn("/stop", [row[0].text for row in keyboard.keyboard])
        self.assertFalse(self.adapter.turns)

    async def test_unload_removes_scoped_sdk_handler(self):
        self.adapter.close()
        await self.settle()
        self.assertFalse(self.native.handlers)


if __name__ == "__main__":
    unittest.main()
