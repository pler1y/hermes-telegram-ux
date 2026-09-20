"""Task-aware statuses must describe observed work, not an invented work plan."""
import json
import unittest

from catalog.model import Turn, safe_text, shell_stage, task_subject
from catalog.presentation import status_text


class TaskProgressTests(unittest.TestCase):
    def turn(self, text=""):
        return Turn("s", "t", 10, user_task=text)

    def pre(self, turn, call, name, args=None):
        turn.observe("pre_tool_call", {"tool_call_id": call, "tool_name": name, "args": args or {}}, 11)

    def post(self, turn, call, name, result=None, status="ok", args=None):
        turn.observe("post_tool_call", {"tool_call_id": call, "tool_name": name, "status": status, "result": result, "args": args or {}}, 12)

    def search(self, turn, call="a", query="上海未来7天天气"):
        self.pre(turn, call, "web_search", {"query": query})

    def results(self, count=3):
        return json.dumps({"success": True, "data": {"web": [{"title": "Forecast", "url": "https://example.test/weather"} for _ in range(count)]}})

    def test_a_simple_question_starts_with_short_generic_feedback(self):
        turn = self.turn("1+1等于多少")
        self.assertEqual(status_text(turn, "zh"), "🤔 思考中…")
        turn.observe("pre_api_request", {"api_request_id": "r", "api_call_count": 1}, 10)
        self.assertEqual(status_text(turn, "zh"), "🤔 思考中…")

    def test_b_weather_query_upgrades_same_turn_to_concrete_task(self):
        turn = self.turn("你帮我找一下上海未来一周天气怎么样，尤其帮我看看是不是会降温，我出门要穿什么")
        self.assertEqual(turn.user_task, "上海未来一周天气")
        self.search(turn)
        text = status_text(turn, "zh")
        self.assertIn("搜索上海未来7天天气", text)
        self.assertNotIn("上海未来一周天气", text)
        self.assertNotIn("web_search", text)
        self.assertNotIn("帮我", text)

    def test_initial_feedback_waits_for_observed_search_without_question_echo(self):
        turn = self.turn("帮我查一下上海未来7天天气")
        self.assertEqual(status_text(turn, "zh"), "🤔 思考中…")
        turn.observe("pre_api_request", {"api_request_id": "r"}, 11)
        self.assertEqual(status_text(turn, "zh"), "🤔 思考中…")
        self.assertNotIn("搜索", status_text(turn, "zh"))
        self.search(turn)
        self.assertIn("搜索上海未来7天天气", status_text(turn, "zh"))

    def test_real_hermes_search_json_counts_search_results_not_weather_days(self):
        turn = self.turn("上海未来7天天气，温度湿度风速")
        self.search(turn)
        self.post(turn, "a", "web_search", self.results(7))
        text = status_text(turn, "zh")
        self.assertIn("7 条结果", text)
        self.assertNotIn("7 条天气数据", text)
        self.assertNotIn("湿度", text)
        self.assertNotIn("风速数据", text)

    def test_structured_weather_fields_require_nonempty_numeric_data(self):
        turn = self.turn("上海未来7天天气，温度湿度风速")
        self.pre(turn, "a", "weather", {})
        self.post(turn, "a", "weather", {"daily": {"temperature_2m_max": [25, 26], "wind_speed_10m_max": [4, 5]}, "daily_units": {"relative_humidity_2m": "%"}})
        text = status_text(turn, "zh")
        self.assertIn("温度、风速数据", text)
        self.assertNotIn("湿度", text)
        self.assertNotIn("已经整理完成", text)

    def test_requested_fields_snippets_and_units_are_not_evidence(self):
        for result in ({"temperature": "unknown", "humidity": [], "wind": None},
                       {"description": "temperature humidity wind", "daily_units": {"temperature": "C"}},
                       "Found 7 days with temperature humidity wind"):
            with self.subTest(result=result):
                turn = self.turn("上海天气，温度湿度风速")
                self.pre(turn, "a", "weather")
                self.post(turn, "a", "weather", result)
                text = status_text(turn, "zh")
                self.assertNotIn("已获取", text)
                self.assertNotIn("湿度", text)

    def test_credential_url_uses_generic_read_without_task_query_or_fragment(self):
        turn = self.turn("查一下 Hermes 插件 API 文档")
        self.pre(turn, "a", "web_extract", {"urls": ["https://user:secret@docs.test/api?token=SECRET#private"]})
        self.assertEqual(status_text(turn, "zh"), "📖 阅读…")
        self.assertNotIn("Hermes 插件 API 文档", status_text(turn, "zh"))
        self.assertNotIn("SECRET", repr(turn))
        self.assertNotIn("private", repr(turn))

    def test_c_news_query_and_human_task_summary(self):
        turn = self.turn("调查最近一周 OpenAI 有什么重要新闻")
        self.search(turn, query="最近一周 OpenAI 重要新闻")
        self.assertIn("最近一周 OpenAI 重要新闻", status_text(turn, "zh"))
        self.assertNotIn("正在使用工具", status_text(turn, "zh"))

    def test_d_code_read_search_and_real_test_events(self):
        turn = self.turn("检查这个项目为什么 Telegram 状态消息没有删除")
        self.pre(turn, "read", "read_file", {"path": "/Users/private/company/catalog/telegram.py"})
        self.assertIn("检查 telegram.py", status_text(turn, "zh"))
        self.assertNotIn("/Users", repr(turn))
        self.pre(turn, "search", "search_files", {"pattern": "delete_message|cleanup", "path": "/secret/project"})
        self.assertEqual(status_text(turn, "zh"), "🔍 定位…")
        self.pre(turn, "test", "terminal", {"command": "python3 -m unittest discover -s tests"})
        self.assertIn("运行相关测试", status_text(turn, "zh"))
        self.post(turn, "test", "terminal", {"exit_code": 0, "output": "arbitrary output"})
        self.assertIn("测试命令已执行完", status_text(turn, "zh"))
        self.assertNotIn("全部测试通过", status_text(turn, "zh"))
        self.assertNotIn("arbitrary output", repr(turn))

    def test_only_real_command_executables_claim_test_stage(self):
        for command in ("echo pytest", "printf 'python -m pytest'", "python -c 'print(\"pytest\")'", "cat pytest.log", "pytest && deploy"):
            with self.subTest(command=command):
                self.assertNotEqual(shell_stage(command), "test")
        for command in ("pytest -q", "python3 -m unittest discover", "cd /project && pytest", "bash -lc 'python -m pytest'", "uv run pytest"):
            with self.subTest(command=command):
                self.assertEqual(shell_stage(command), "test")

    def test_e_failed_tool_does_not_invent_success_or_retry(self):
        for status, result in (("error", self.results()), ("ok", {"success": False, "error": "secret failure"}), ("ok", {"exit_code": 1, "output": "secret"})):
            with self.subTest(status=status, result=result):
                turn = self.turn("上海天气")
                self.search(turn)
                self.post(turn, "a", "web_search", result, status)
                text = status_text(turn, "zh")
                self.assertIn("没有成功", text)
                self.assertNotIn("已找到", text)
                self.assertNotIn("重试", text)
                self.assertNotIn("其他方式", text)
                self.assertNotIn("secret", repr(turn))

    def test_empty_search_results_do_not_claim_a_finding(self):
        turn = self.turn("上海天气")
        self.search(turn)
        self.post(turn, "a", "web_search", self.results(0))
        self.assertIn("没有返回结果", status_text(turn, "zh"))

    def test_failed_read_then_model_request_does_not_claim_file_information(self):
        turn = self.turn("检查 Telegram 消息清理")
        self.pre(turn, "a", "read_file", {"path": "/private/telegram.py"})
        self.post(turn, "a", "read_file", {"error": "not found"}, "error")
        self.assertIn("没有成功", status_text(turn, "zh"))
        turn.observe("pre_api_request", {"api_request_id": "next"}, 13)
        text = status_text(turn, "zh")
        self.assertNotIn("中的信息", text)
        self.assertNotIn("整理", text)
        self.assertNotIn("已获取", text)

    def test_cancelled_and_unknown_tool_status_never_claim_returned_data(self):
        for status in ("cancelled", "unexpected"):
            with self.subTest(status=status):
                turn = self.turn("上海天气")
                self.pre(turn, "a", "read_file", {"path": "weather.json"})
                self.post(turn, "a", "read_file", {"temperature": [20], "humidity": [80], "wind": [2]}, status)
                text = status_text(turn, "zh")
                self.assertNotIn("已获取", text)
                self.assertNotIn("整理", text)
                self.assertNotIn("数据", text)

    def test_late_tool_completion_cannot_replace_newer_work(self):
        turn = self.turn("调查 OpenAI 新闻")
        self.search(turn, "old", "OpenAI 新闻")
        self.pre(turn, "new", "read_file", {"path": "/tmp/notes.md"})
        latest = status_text(turn, "zh")
        self.post(turn, "old", "web_search", self.results(7))
        self.assertEqual(status_text(turn, "zh"), latest)
        self.pre(turn, "old", "web_search", {"query": "stale"})
        self.assertEqual(status_text(turn, "zh"), latest)

    def test_late_approval_cannot_resurrect_completed_tool_or_cover_new_tool(self):
        turn = self.turn("上海天气")
        self.pre(turn, "old", "read_file", {"path": "weather.json"})
        turn.observe("pre_approval_request", {"tool_call_id": "old"}, 11)
        turn.observe("post_approval_response", {"tool_call_id": "old", "choice": "once"}, 12)
        self.post(turn, "old", "read_file", {"content": "{}"})
        self.search(turn, "new")
        current = status_text(turn, "zh")
        turn.observe("post_approval_response", {"tool_call_id": "old", "choice": "cancelled"}, 13)
        turn.observe("pre_approval_request", {"tool_call_id": "old"}, 14)
        self.assertEqual(status_text(turn, "zh"), current)
        self.assertEqual(turn.approvals["old"], "once")

    def test_approval_before_tool_start_is_supported_but_terminal_response_is_stable(self):
        turn = self.turn()
        turn.observe("pre_approval_request", {"tool_call_id": "a"}, 10)
        self.assertIn("等待审批", status_text(turn, "zh"))
        turn.observe("post_approval_response", {"tool_call_id": "a", "choice": "once"}, 11)
        turn.observe("post_approval_response", {"tool_call_id": "a", "choice": "timeout"}, 12)
        turn.observe("pre_approval_request", {"tool_call_id": "a"}, 13)
        self.assertEqual(turn.approvals["a"], "once")
        self.pre(turn, "a", "read_file", {"path": "file.md"})
        self.assertIn("读取 file.md", status_text(turn, "zh"))

    def test_parallel_approval_resolution_does_not_replace_another_active_tool(self):
        turn = self.turn("上海天气")
        self.pre(turn, "old", "terminal")
        turn.observe("pre_approval_request", {"tool_call_id": "old"}, 11)
        self.search(turn, "new")
        turn.observe("post_approval_response", {"tool_call_id": "old", "choice": "cancelled"}, 12)
        self.assertIn("搜索", status_text(turn, "zh"))

    def test_completion_before_approval_response_does_not_leave_pending_wait(self):
        turn = self.turn("上海天气")
        self.pre(turn, "old", "read_file", {"path": "notes.md"})
        turn.observe("pre_approval_request", {"tool_call_id": "old"}, 11)
        self.post(turn, "old", "read_file", {"content": "notes"})
        self.search(turn, "new")
        turn.observe("post_approval_response", {"tool_call_id": "old", "choice": "cancelled"}, 13)
        self.assertIn("搜索", status_text(turn, "zh"))

    def test_current_tool_result_can_upgrade_status_after_generic_model_request(self):
        turn = self.turn("调查 OpenAI 新闻")
        self.search(turn)
        turn.observe("pre_api_request", {"api_request_id": "new"}, 12)
        current = status_text(turn, "zh")
        self.post(turn, "a", "web_search", self.results(7))
        self.assertNotEqual(status_text(turn, "zh"), current)
        self.assertIn("7 条结果", status_text(turn, "zh"))
        self.assertEqual(turn.display_kind, "result")

    def test_duplicate_posts_do_not_replace_original_outcome(self):
        turn = self.turn("上海天气")
        self.search(turn)
        self.post(turn, "a", "web_search", self.results(2))
        first = status_text(turn, "zh")
        self.post(turn, "a", "web_search", status="error")
        self.assertEqual(status_text(turn, "zh"), first)

    def test_tool_object_source_hostname_and_generic_fallback(self):
        turn = self.turn("Shanghai weather")
        self.search(turn, query="Shanghai seven day weather")
        self.assertIn("Shanghai seven day weather", status_text(turn, "en"))
        self.pre(turn, "partial", "web_extract", {"url": "https://example.test/private?q=secret"})
        self.assertIn("example.test", status_text(turn, "en"))
        self.assertNotIn("private", status_text(turn, "en"))
        self.assertNotIn("secret", status_text(turn, "en"))
        other = self.turn()
        self.pre(other, "unknown", "unknown_tool", {"prompt": "a secret"})
        self.assertEqual(status_text(other, "en"), "⚙️ Executing the current step…")

    def test_public_model_update_one_action_not_four_field_log(self):
        turn = self.turn("上海天气")
        self.pre(turn, "note", "telegram_ux_update")
        self.post(turn, "note", "telegram_ux_update", args={"goal": "上海未来一周天气", "action": "正在比较每天的天气变化", "finding": "已获得七天天气", "next": "给出建议"})
        text = status_text(turn, "zh")
        self.assertEqual(text, "📝 比较每天的天气变化…")
        self.assertNotIn("已获得", text)
        self.assertEqual(len(text.splitlines()), 1)
        self.search(turn)
        self.assertIn("搜索", status_text(turn, "zh"))

    def test_late_public_note_cannot_replace_a_newer_stage(self):
        turn = self.turn("上海天气")
        self.pre(turn, "note", "telegram_ux_update")
        self.search(turn)
        self.post(turn, "note", "telegram_ux_update", args={"action": "正在处理过时的任务"})
        self.assertFalse(turn.note)
        self.assertIn("搜索", status_text(turn, "zh"))

    def test_new_public_action_after_result_is_visible(self):
        turn = self.turn("上海天气")
        self.search(turn)
        self.post(turn, "a", "web_search", self.results(3))
        self.assertIn("3 条结果", status_text(turn, "zh"))
        self.pre(turn, "note", "telegram_ux_update")
        self.post(turn, "note", "telegram_ux_update", args={"action": "正在对比每天的温度变化"})
        self.assertEqual(status_text(turn, "zh"), "📝 对比每天的温度变化…")
        self.pre(turn, "read", "web_extract", {"urls": ["https://example.test"]})
        self.assertIn("读取 example.test", status_text(turn, "zh"))

    def test_public_note_needs_specific_action_or_supported_finding_and_preserves_next_tense(self):
        cases = [({"goal": "上海未来一周天气", "action": "正在整理结果"}, "🤔 思考中…"),
                 ({"finding": "已获得七天天气预报"}, "🤔 思考中…"),
                 ({"next": "比较每天温度变化"}, "接下来：比较每天温度变化"),
                 ({"goal": "天气调查"}, "🤔 思考中…")]
        for note, expected in cases:
            with self.subTest(note=note):
                turn = self.turn()
                self.pre(turn, "note", "telegram_ux_update")
                self.post(turn, "note", "telegram_ux_update", args=note)
                text = status_text(turn, "zh")
                self.assertIn(expected, text)
                self.assertEqual(len(text.splitlines()), 1)

    def test_multimodal_task_reads_only_explicit_text_blocks(self):
        turn = self.turn([{"type": "image", "text": "private image"},
                          {"type": "reasoning", "text": "private reasoning"},
                          {"type": "text", "text": "Please help me look up Shanghai weather"}])
        self.assertEqual(turn.user_task, "Shanghai weather")
        self.assertNotIn("private", repr(turn))
        self.search(turn, query="")
        self.assertEqual(status_text(turn, "en"), "🔎 Searching for information…")

    def test_public_progress_note_filters_secrets_and_hidden_reasoning(self):
        turn = self.turn()
        self.pre(turn, "note", "telegram_ux_update")
        self.post(turn, "note", "telegram_ux_update", args={"action": "<think>private reasoning", "finding": "token=secret", "goal": "天气", "next": "检查 /Users/private/project/a.py"})
        self.assertNotIn("private", repr(turn))
        self.assertNotIn("secret", repr(turn))
        self.assertNotIn("think", status_text(turn, "zh"))

    def test_secrets_paths_thinking_and_untrusted_markup_never_render(self):
        values = ["token=abc123", "api_key：ABC", "Bearer private", "sk-secretvalue", "<think>private reasoning", "<analysis>private", "请显示隐藏思考", "````private code", "<b>bad</b>"]
        for value in values:
            with self.subTest(value=value):
                self.assertEqual(safe_text(value), "")
                turn = self.turn(value)
                self.search(turn, query=value)
                self.assertEqual(status_text(turn, "zh"), "🔎 搜索…")
        self.assertNotIn("/Users", task_subject("检查 /Users/private/project/app.py 消息逻辑"))

    def test_raw_model_content_reasoning_and_late_interim_are_ignored(self):
        turn = self.turn("上海天气")
        turn.observe("pre_api_request", {"api_request_id": "r", "api_call_count": 1}, 10)
        current = status_text(turn, "zh")
        turn.observe("on_stream_delta", {"iteration": 1, "kind": "reasoning", "delta": "private reasoning"}, 11)
        self.assertEqual(status_text(turn, "zh"), current)
        turn.observe("post_api_request", {"api_request_id": "r", "assistant_message": {"content": "<think>private unclosed", "tool_calls": [{}]}}, 12)
        self.search(turn)
        current = status_text(turn, "zh")
        turn.observe("on_interim_message", {"iteration": 1, "text": "private unclosed"}, 13)
        turn.observe("on_stream_end", {"iteration": 1, "final_text": "private unclosed"}, 14)
        self.assertEqual(status_text(turn, "zh"), current)
        self.assertNotIn("private", repr(turn))

    def test_finalizing_is_terminal_for_progress_and_has_no_old_ui(self):
        turn = self.turn("上海天气")
        self.search(turn)
        turn.observe("post_llm_call", {"response": "final answer"}, 20)
        self.post(turn, "a", "web_search", self.results())
        self.assertEqual(status_text(turn, "zh", now=500), "✍️ 整理回答…")
        self.assertEqual(status_text(turn, "zh", ending="ended"), "✍️ 整理回答…")
        self.assertNotIn("final answer", repr(turn))
        for old_ui in ("已结束", "已用时", "工具", "继续处理", "详情", "设置", "关闭提示"):
            self.assertNotIn(old_ui, status_text(turn, "zh"))

    def test_progress_memory_is_bounded(self):
        turn = self.turn()
        for index in range(600):
            self.pre(turn, str(index), "read_file", {"path": "/private/app.py"})
        self.assertEqual(len(turn.tools), 512)
        self.assertEqual(len(turn.observations), 512)
        self.assertNotIn("512", turn.tools)
        self.assertNotIn("512", turn.observations)
        self.assertIn("检查 app.py", status_text(turn, "zh"))

    def test_long_query_and_public_action_keep_the_bubble_short(self):
        for language, limit, content in (("zh", 60, "上海未来一周天气和温度变化" * 12),
                                         ("en", 110, "Shanghai weather and temperature changes " * 12)):
            with self.subTest(language=language):
                turn = self.turn()
                self.search(turn, query=content)
                self.assertLessEqual(len(status_text(turn, language)), limit)
                other = self.turn()
                self.pre(other, "note", "telegram_ux_update")
                self.post(other, "note", "telegram_ux_update", args={"action": content})
                self.assertLessEqual(len(status_text(other, language)), limit)
                self.assertEqual(len(status_text(other, language).splitlines()), 1)


if __name__ == "__main__":
    unittest.main()
