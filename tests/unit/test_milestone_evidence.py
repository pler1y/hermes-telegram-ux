"""Facts and freshness are independent of model activity and tool acknowledgements."""
import unittest

from catalog.model import Turn
from catalog.presentation import status_text


class MilestoneEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.turn = Turn("s", "t", 1, user_task="Grok 4.6 什么时候发布？")

    def tool(self, call="search", name="web_search", result=None, status="ok"):
        data = {"tool_call_id": call, "tool_name": name,
                "args": {"query": "Grok 4.6 official release date"}}
        self.turn.observe("pre_tool_call", data, 2)
        self.turn.observe("post_tool_call", dict(data, result=result, status=status), 3)

    def note(self, call="note", **fields):
        data = {"tool_call_id": call, "tool_name": "telegram_ux_update", "args": fields}
        self.turn.observe("pre_tool_call", data, 4)
        self.turn.observe("post_tool_call", dict(data, status="ok"), 5)

    def test_a_successful_tool_exit_is_not_evidence_for_arbitrary_finding(self):
        self.tool(result={"results": [{"title": "Announcement", "url": "https://example.test"}]})
        previous = status_text(self.turn, "zh")
        for index, finding in enumerate(("发布时间已经确认", "不同来源给出的日期存在差异", "找到 8 条结果")):
            self.note(call=str(index), finding=finding)
            self.assertEqual(status_text(self.turn, "zh"), previous)
            self.assertFalse(self.turn.note)

    def test_matching_result_fact_is_allowed_without_keeping_source_prose(self):
        self.tool(result={"results": [{"title": "private source text", "url": "https://example.test"}]})
        self.note(finding="找到 1 条结果", action="核对来源中的发布日期")
        self.assertEqual(self.turn.note.get("finding"), "找到 1 条结果")
        self.assertNotIn("private source text", repr(self.turn))

    def test_failed_host_status_cannot_support_positive_finding(self):
        self.tool(result={"results": [{"title": "Announcement", "url": "https://example.test"}]}, status="error")
        self.note(finding="找到 1 条结果")
        self.assertNotIn("找到", status_text(self.turn, "zh"))
        self.assertIn("没有成功", status_text(self.turn, "zh"))

    def test_supported_read_fact_and_missing_file_fact(self):
        for result, status, finding in (({"content": "actual file"}, "ok", "已读取文件"),
                                         ({"error": "File not found"}, "error", "未找到指定文件")):
            with self.subTest(finding=finding):
                self.turn = Turn("s", "t", 1)
                self.tool(name="read_file", result=result, status=status)
                self.note(finding=finding, next="核对文件位置与相关说明")
                self.assertEqual(self.turn.note.get("finding"), finding)

    def test_finding_is_matched_to_current_result_not_old_success(self):
        self.tool(result={"results": [{"title": "Announcement", "url": "https://example.test"}]})
        self.tool(call="new", name="read_file", result={"error": "File not found"}, status="error")
        self.note(finding="找到 1 条结果", action="检查文件位置后补充核对")
        self.assertNotIn("finding", self.turn.note)
        self.assertIn("检查文件位置", status_text(self.turn, "zh"))

    def test_repeating_a_visible_fact_alone_does_not_create_a_milestone(self):
        self.tool(result={"results": [{"title": "Announcement", "url": "https://example.test"}]})
        before = status_text(self.turn, "zh")
        self.note(finding="找到 1 条结果")
        self.assertEqual(status_text(self.turn, "zh"), before)
        self.assertEqual(self.turn.display_kind, "result")

    def test_note_crossing_an_api_event_is_not_stale(self):
        data = {"tool_call_id": "note", "tool_name": "telegram_ux_update", "args": {"action": "比较不同来源中的日期"}}
        self.turn.observe("pre_tool_call", data, 2)
        self.turn.observe("pre_api_request", {"api_request_id": "next"}, 3)
        self.turn.observe("post_tool_call", dict(data, status="ok"), 4)
        self.assertIn("比较不同来源", status_text(self.turn, "zh"))
        self.turn.observe("post_api_request", {"api_request_id": "next", "assistant_tool_call_count": 1}, 5)
        self.assertEqual(self.turn.display_kind, "note")
        self.assertIn("比较不同来源", status_text(self.turn, "zh", now=300))

    def test_current_running_action_survives_api_and_rejects_concurrent_note(self):
        self.turn.observe("pre_tool_call", {"tool_call_id": "search", "tool_name": "web_search", "args": {"query": "model release date"}}, 2)
        self.turn.observe("pre_api_request", {"api_request_id": "next"}, 3)
        self.note(action="比较不同来源中的日期")
        self.assertFalse(self.turn.note)
        self.assertEqual(self.turn.display_kind, "tool")
        self.turn.observe("post_tool_call", {"tool_call_id": "search", "tool_name": "web_search", "status": "ok", "result": {"results": []}}, 6)
        self.assertEqual(self.turn.display_kind, "result")
        self.assertIn("没有返回结果", status_text(self.turn, "zh"))

    def test_new_result_invalidates_pending_note(self):
        self.turn.observe("pre_tool_call", {"tool_call_id": "search", "tool_name": "web_search", "args": {}}, 2)
        note = {"tool_call_id": "note", "tool_name": "telegram_ux_update", "args": {"action": "比较不同来源中的日期"}}
        self.turn.observe("pre_tool_call", note, 3)
        self.turn.observe("post_tool_call", {"tool_call_id": "search", "tool_name": "web_search", "status": "ok", "result": {"results": []}}, 4)
        self.turn.observe("post_tool_call", dict(note, status="ok"), 5)
        self.assertEqual(self.turn.display_kind, "result")

    def test_missing_pre_hook_does_not_claim_a_note_was_executed_in_order(self):
        self.turn.observe("post_tool_call", {"tool_call_id": "note", "tool_name": "telegram_ux_update", "args": {"action": "比较不同来源中的日期"}, "status": "ok"}, 2)
        self.assertFalse(self.turn.note)

    def test_blocked_note_cannot_be_relabelled_success_by_a_duplicate_post(self):
        data = {"tool_call_id": "note", "tool_name": "telegram_ux_update", "args": {"action": "比较不同来源中的日期"}}
        self.turn.observe("pre_tool_call", data, 2)
        self.turn.observe("post_tool_call", dict(data, status="blocked"), 3)
        self.turn.observe("post_tool_call", dict(data, status="ok"), 4)
        self.assertFalse(self.turn.note)

    def test_opaque_helper_does_not_erase_specific_milestone(self):
        self.note(action="比较不同来源中的日期")
        before = status_text(self.turn, "zh")
        for number, result in enumerate(("unstructured output", {"success": True}, {"exit_code": 0})):
            self.tool(call=str(number), name="opaque_helper", result=result)
            self.assertEqual(status_text(self.turn, "zh"), before)
            self.assertEqual(self.turn.display_kind, "note")
        self.tool(call="failed", name="opaque_helper", result={"exit_code": 1}, status="error")
        self.assertIn("没有成功", status_text(self.turn, "zh"))

    def test_opaque_success_does_not_erase_a_concrete_result(self):
        self.tool(result={"results": [{"title": "Announcement", "url": "https://example.test"}]})
        before = status_text(self.turn, "zh")
        self.tool(call="opaque", name="opaque_helper", result={"exit_code": 0})
        self.assertEqual(status_text(self.turn, "zh"), before)


if __name__ == "__main__":
    unittest.main()
