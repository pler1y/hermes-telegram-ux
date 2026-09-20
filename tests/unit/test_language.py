"""Installation language selection and its visible per-turn behavior."""
import asyncio
import unittest

from catalog.adapter import HermesCatalogAdapter
from catalog.language import resolve_language
from test_catalog import ContextStub, TelegramStub, event, start


class LanguageTests(unittest.TestCase):
    def test_auto_uses_current_public_prose(self):
        for message, expected in (("请查上海天气", "zh"), ("Please check Shanghai weather", "en"),
                                  ("请检查 OpenAI news", "zh"), ("1+1?", "zh"),
                                  ("🙂 123", "zh"), ("", "zh"), (None, "zh")):
            with self.subTest(message=message):
                self.assertEqual(resolve_language(message), expected)

    def test_installation_choice_overrides_message_language(self):
        self.assertEqual(resolve_language("Please check the forecast", "zh"), "zh")
        self.assertEqual(resolve_language("请检查天气", "en"), "en")
        self.assertEqual(resolve_language("123", "en"), "en")
        self.assertEqual(resolve_language("Please check the forecast", "invalid"), "en")

    def test_code_urls_and_paths_do_not_decide_language(self):
        for message, expected in (
            ("```python\nprint('Hello world')\n```", "zh"),
            ("https://example.com/english-weather", "zh"),
            ("/tmp/english-report.py", "zh"),
            ("Please inspect `中文变量`", "en"),
            ("Please inspect https://example.com/中文内容", "en"),
            ("Please inspect /tmp/中文报告.txt", "en"),
            ("Please inspect\n```python\nprint('中文内容')\n```", "en"),
        ):
            with self.subTest(message=message):
                self.assertEqual(resolve_language(message), expected)

    def test_only_public_text_blocks_are_language_evidence(self):
        message = [
            {"type": "image_url", "image_url": {"url": "https://example.com/中文.jpg"}, "text": "中文图片说明"},
            {"type": "reasoning", "text": "不可用于语言判断"},
            {"type": "input_text", "text": "另一个协议的内容"},
            {"type": "text", "text": "Please inspect this picture"},
        ]
        self.assertEqual(resolve_language(message), "en")
        self.assertEqual(resolve_language(message[:3]), "zh")
        self.assertEqual(resolve_language([{"type": "text", "text": "请检查图片"}]), "zh")
        self.assertEqual(resolve_language([{"type": "text", "text": 123}, None, "English raw item"]), "zh")
        self.assertEqual(resolve_language({"text": "English untyped dictionary"}), "zh")


class LanguageIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.ctx = ContextStub(language="auto", cleanup_delay=.001)
        self.adapter = HermesCatalogAdapter(self.ctx)
        self.adapter.register()
        self.telegram = TelegramStub()
        self.ctx.factory(None, self.telegram)
        self.adapter.transport.interval = .001

    async def asyncTearDown(self):
        self.adapter.close()
        await asyncio.sleep(0)
        await asyncio.gather(*self.ctx.tasks, return_exceptions=True)

    async def begin(self, text, turn_id, message_id):
        self.adapter.pre_gateway_dispatch(event=event(message=message_id))
        start(self.adapter, tid=turn_id, user_message=text)
        await asyncio.sleep(.02)

    async def test_auto_changes_each_turn_in_same_chat_without_remembering_last_language(self):
        for number, (text, language, initial) in enumerate((
                ("Please check the weather", "en", "🤔 Thinking…"),
                ("请查看天气", "zh", "🤔 思考中…"),
                ("1+1", "zh", "🤔 思考中…"),
                ("Please read the report", "en", "🤔 Thinking…"))):
            turn_id = str(number)
            await self.begin(text, turn_id, str(100 + number))
            self.assertEqual(self.telegram.sent[-1]["content"], initial)
            self.assertEqual(self.adapter.turns[("s1", turn_id)].language, language)
            self.adapter.on_session_end(session_id="s1", turn_id=turn_id, completed=True)
            await asyncio.sleep(.02)
        self.assertEqual(len(self.telegram.sent), 4)
        self.assertEqual(len(self.telegram.deleted), 4)
        self.assertFalse(self.ctx.commands)

    async def test_concurrent_turns_keep_their_language_through_error_and_cleanup(self):
        await self.begin("Please read this file", "english", "201")
        await self.begin("请读取这个文件", "chinese", "202")
        for turn_id, word in (("english", "not found"), ("chinese", "未找到指定文件")):
            data = dict(session_id="s1", turn_id=turn_id, tool_call_id=turn_id, tool_name="read_file")
            self.adapter.observe("pre_tool_call", **data, args={"path": "/tmp/missing.txt"})
            self.adapter.observe("post_tool_call", **data, status="error", result={"error": "File not found"})
            await asyncio.sleep(.02)
            self.assertIn(word, self.telegram.edits[-1]["content"])
            self.adapter.on_session_end(session_id="s1", turn_id=turn_id, completed=True)
            await asyncio.sleep(.02)
        self.assertEqual({item["message_id"] for item in self.telegram.deleted}, {"1", "2"})

    async def test_config_override_applies_before_initial_bubble_and_expiry(self):
        self.adapter.close()
        self.ctx.settings["language"] = "en"
        self.adapter = HermesCatalogAdapter(self.ctx)
        self.adapter.register()
        self.ctx.factory(None, self.telegram)
        self.adapter.transport.interval = .001
        await self.begin("请检查天气", "forced", "301")
        self.assertEqual(self.telegram.sent[-1]["content"], "🤔 Thinking…")
        self.assertIn("expired", self.adapter.expire(("s1", "forced")))
        self.assertNotIn(("s1", "forced"), self.adapter.turns)

    async def test_multimodal_first_status_uses_text_and_not_image_metadata(self):
        await self.begin([{"type": "image_url", "text": "中文图片元数据"},
                          {"type": "text", "text": "Please describe this picture"}], "image", "401")
        self.assertEqual(self.telegram.sent[-1]["content"], "🤔 Thinking…")
        self.assertEqual(self.adapter.turns[("s1", "image")].language, "en")
        self.assertNotIn("图片元数据", repr(self.adapter.turns))


if __name__ == "__main__":
    unittest.main()
