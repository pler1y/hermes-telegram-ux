"""Fixed editions must never guess a user's language or change operational tool arguments."""
import re
import unittest
from plugin.i18n import EN, decorate, greeting, localize, tr
from plugin.narration import with_progress_schema
from plugin.experience import prompt_for
from plugin.progress import TaskProgress
from plugin.status import TurnState
from plugin.welcome import WelcomeMenu


class LanguageTests(unittest.TestCase):
    def test_fixed_edition_does_not_follow_input_language(self):
        self.assertEqual(greeting("你好", "en"), "Hey! 👋")
        self.assertEqual(greeting("hello", "zh"), "在呢 👋")
        self.assertEqual(greeting("Read this file", "zh"), "🤔 思考中…")
        self.assertEqual(greeting("谢谢", "en"), "You're welcome 😊")

    def test_english_progress_preserves_counts_and_model_text(self):
        self.assertEqual(localize("已找到 12 条候选资料。", "en"), "Found 12 potential sources.")
        self.assertEqual(localize("Reading {customer} data", "en"), "Reading {customer} data")
        progress = TaskProgress()
        progress.initialize("Check a file")
        progress.start("owner", "read", "read_file", {})
        state = TurnState("s", "k", None, None, 1, [None], [], None, None,
                          progress=progress, language="en", emoji=True)
        for at in (progress.changed_at, progress.changed_at + 60):
            text = state.render(at)
            self.assertFalse(re.search(r"[\u4e00-\u9fff]", text), text)
        progress.finish("owner", "read", "read_file", {"error": "no file"}, True)
        self.assertNotRegex(state.render(progress.changed_at), r"[\u4e00-\u9fff]")

    def test_english_model_request_has_no_chinese_requirement(self):
        request = {"instructions": "original", "tools": [{"type": "function", "name": "read_file",
                    "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}}]}
        updated = with_progress_schema(request, language="en", require_note=True)
        self.assertIn("English", updated["instructions"])
        self.assertNotIn("Chinese", updated["instructions"])
        self.assertNotRegex(str(updated), r"[\u4e00-\u9fff]")
        self.assertEqual(request["instructions"], "original")
        self.assertNotIn("_hermes_progress", request["tools"][0]["parameters"]["properties"])
        self.assertNotRegex(prompt_for("en"), r"[\u4e00-\u9fff]")

    def test_emoji_does_not_rotate_or_double_decorate(self):
        text = decorate("Checking prices", "search")
        self.assertEqual(text, "🔎 Checking prices")
        self.assertEqual(decorate(text, "search"), text)
        self.assertEqual(decorate("Let me look 👀", "search"), "Let me look 👀")
        self.assertEqual(decorate("Checking prices", "search", False), "Checking prices")

    def test_every_english_menu_page_and_action_is_translated(self):
        from plugin.welcome import PAGES, COMMANDS
        menu = WelcomeMenu(None, language="en")
        owner = {"user": 1, "chat": 1, "thread": None, "message": 2}
        for page in PAGES:
            _, text, markup, state = menu._view(owner, page)
            self.assertNotRegex(text + str(markup.to_dict()), r"[\u4e00-\u9fff]")
            for kind, value, label in state["actions"].values():
                if kind == "request":
                    self.assertIn(value, COMMANDS)
                    self.assertNotRegex(value, r"[\u4e00-\u9fff]")

    def test_translation_templates_have_matching_fields(self):
        for original, translated in EN.items():
            self.assertEqual(re.findall(r"\{\w+\}", original), re.findall(r"\{\w+\}", translated), original)
        self.assertEqual(tr("已选择：{label}，正在提交。", "en", label="{not a template}"),
                         "Selected: {not a template}. Sending it now.")

    def test_internal_status_cannot_hide_terminal_or_permission_state(self):
        state = TurnState("s", "k", None, None, 1, [None], [], None, None, language="en")
        state.internal_status = "🧠 正在整理前面的聊天，稍等一下。"
        state.ended = True
        state.phase = "⏹️ 当前任务已中断；已执行的操作不会自动撤销。"
        self.assertIn("interrupted", state.render(0))
        state.ended = False
        state.approval_phase = "pending"
        state.phase = "等待你确认：请先处理聊天中的操作确认请求。"
        self.assertIn("approval", state.render(0))

    def test_english_receipt_and_final_answer_are_not_mistaken_for_progress(self):
        from plugin.background import acknowledgement_only
        from plugin.narration import public_text
        self.assertTrue(acknowledgement_only("Got it — I'll use your updated request."))
        self.assertFalse(acknowledgement_only("Got it. The answer is 42."))
        self.assertEqual(public_text("Final answer: use option 2"), "")
        self.assertEqual(public_text("Checking the delivery dates"), "Checking the delivery dates")
