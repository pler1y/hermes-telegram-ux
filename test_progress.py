"""Progress acceptance through the same event hooks used by the live gateway."""
import json
import time
import unittest
from types import SimpleNamespace

from plugin.progress import TaskProgress, shell_stage
from plugin.runtime import InteractionRuntime
from plugin.status import TurnState


class Context:
    def get_config(self, key, default=None):
        return default


class TaskProgressTests(unittest.TestCase):
    def setUp(self):
        self.runtime = InteractionRuntime(Context())
        self.state = TurnState("root", "key", None, None, 1, [None], [], None, None, progress=TaskProgress())
        self.runtime.registry.bind(self.state)

    def text(self, elapsed=0):
        return self.state.render(time.monotonic()+elapsed, 45)

    def start(self, name, args=None, call="a", owner="root"):
        self.runtime.pre_tool(name, args or {}, owner, tool_call_id=call)

    def finish(self, name, result, call="a", owner="root", **kwargs):
        self.runtime.post_tool(name, owner, result, tool_call_id=call, **kwargs)

    def test_opening_does_not_pretend_to_understand_a_category(self):
        for text in ["随便聊聊", "整理订货资料", "帮我重新安排练习计划", "部署服务"]:
            progress = TaskProgress()
            progress.initialize(text)
            self.assertEqual(progress.request, text)
            self.assertEqual(progress.render(time.monotonic(), 45), "我看一下…")
            self.assertNotIn("深度思考", progress.render(time.monotonic()+90, 45))

    def test_search_transitions_follow_native_structured_result(self):
        self.runtime.pre_api("root", user_message="查一下最新消息")
        self.start("web_search", {"query": "secret query"})
        self.assertIn("正在搜索", self.text())
        self.assertNotIn("secret", self.text())
        self.finish("web_search", json.dumps({"success": True, "data": {"web": [{"title": "a"}, {"title": "b"}]}}))
        self.assertIn("已找到 2 条候选资料", self.text())
        self.assertIn("核对资料", self.text())
        self.start("web_extract", call="b")
        self.assertIn("核对具体内容", self.text())
        self.assertIn("2 条候选资料", self.text())

    def test_empty_and_unknown_results_do_not_invent_found_count(self):
        self.start("web_search")
        self.finish("web_search", {"data": {"web": []}})
        self.assertIn("没有找到", self.text())
        self.start("web_search", call="b")
        self.finish("web_search", "a page claims 10 results", call="b")
        self.assertIn("搜索已返回", self.text())
        self.assertNotIn("10", self.text())

    def test_deploy_has_precheck_test_execution_and_postcheck(self):
        self.runtime.pre_api("root", user_message="部署这个项目")
        self.start("terminal", {"command": "systemctl status example"})
        self.assertIn("现有内容", self.text())
        self.finish("terminal", {"exit_code": 0})
        self.start("terminal", {"command": "python -m unittest discover"}, call="b")
        self.assertIn("运行测试", self.text())
        self.finish("terminal", {"exit_code": 0}, call="b")
        self.assertIn("测试通过", self.text())
        self.assertNotIn("部署成功", self.text())
        self.start("terminal", {"command": "systemctl restart example"}, call="c")
        self.assertIn("执行部署", self.text())
        self.finish("terminal", {"exit_code": 0}, call="c")
        self.assertIn("还需要确认实际运行", self.text())
        self.start("terminal", {"command": "curl --fail http://localhost:9876/health"}, call="d")
        self.assertIn("部署后的运行", self.text())

    def test_failed_test_clears_conditional_next_step_without_claiming_deploy(self):
        self.start("interaction_update", {"activity": "先检查改动能否正常工作", "next_step": "通过后再上线", "task_type": "build"})
        self.assertIn("接下来：通过后再上线", self.text())
        self.start("terminal", {"command": "pytest"})
        self.finish("terminal", {"exit_code": 1})
        self.assertIn("测试没通过", self.text())
        self.assertNotIn("上线", self.text())
        self.assertFalse(self.state.failed)

    def test_success_requires_evidence_not_just_tool_return(self):
        self.start("terminal", {"command": "pytest"})
        self.finish("terminal", {"output": "work queued"})
        self.assertNotIn("测试通过", self.text())
        self.assertIn("核对结果", self.text())

    def test_running_test_and_poll_are_not_treated_as_finished(self):
        self.start("terminal", {"command": "pytest"})
        self.finish("terminal", {"session_id": "p1", "status": "running"})
        self.assertIn("运行测试", self.text())
        self.assertNotIn("通过", self.text())
        self.start("process", {"action": "poll", "session_id": "p1"}, call="b")
        self.finish("process", {"status": "running", "output": "..."}, call="b")
        self.assertIn("运行测试", self.text())
        self.start("process", {"action": "poll", "session_id": "p1"}, call="c")
        self.finish("process", {"exit_code": 0, "status": "exited"}, call="c")
        self.assertIn("测试通过", self.text())
        self.assertFalse(self.state.progress.processes)

    def test_parallel_results_are_paired_by_call_and_child_owner(self):
        self.runtime.child_start(parent_session_id="root", child_session_id="child")
        self.runtime.pre_api("root", user_message="部署项目")
        self.runtime.pre_api("child", user_message="搜索消息")
        self.assertEqual(self.state.progress.request, "部署项目")
        self.start("web_search", call="same", owner="root")
        self.start("terminal", {"command": "pytest"}, call="same", owner="child")
        self.finish("web_search", {"results": [{}, {}]}, call="same")
        self.assertIn("运行测试", self.text())
        self.assertIn("2 条候选资料", self.text())
        before = self.text()
        self.finish("web_search", {"results": []}, call="same")
        self.assertEqual(before, self.text())

    def test_duplicate_and_late_hooks_do_not_overwrite_completed_status(self):
        self.start("web_search")
        self.start("web_search")
        self.assertEqual(self.state.active_tools, 1)
        self.runtime.session_end("root", completed=True)
        final = self.text()
        self.finish("web_search", {"results": [{}, {}]})
        self.start("interaction_update", {"activity": "not now"})
        self.assertEqual(final, self.text())

    def test_setup_tools_do_not_claim_to_read_or_search_user_data(self):
        self.runtime.pre_api("root", user_message="部署项目")
        before = self.text()
        for tool in ["skill_view", "tool_search", "tool_describe"]:
            self.start(tool)
            self.finish(tool, {"success": True})
        self.assertEqual(before, self.text())
        self.assertEqual(self.state.tool_count, 0)

    def test_running_polls_do_not_reset_the_slow_stage_clock(self):
        from unittest.mock import patch
        self.start("terminal", {"command": "pytest"})
        began = self.state.progress.changed_at
        with patch("plugin.progress.time.monotonic", return_value=began+60):
            self.finish("terminal", {"status": "running", "session_id": "p"})
            self.start("process", {"session_id": "p"}, call="b")
            self.finish("process", {"status": "running"}, call="b")
        self.assertEqual(self.state.progress.changed_at, began)
        self.assertIn("还没返回新结果", self.text(90))

    def test_blocked_tool_has_no_success_and_approval_has_no_stall_notice(self):
        self.start("terminal", {"command": "pytest"})
        self.runtime.approval_wait("key")
        self.assertIn("等待你确认", self.text(90))
        self.assertNotIn("还没返回", self.text(90))
        self.runtime.approval_done("key")
        self.finish("terminal", {}, status="blocked")
        self.assertIn("没通过", self.text())

    def test_commands_are_classified_by_executable_not_printed_text(self):
        for command in ["echo 'pytest && systemctl restart x'", "cat deploy.py", "systemctl status app", "python -c 'print(\"pytest\")'"]:
            self.assertNotIn(shell_stage(command), {"test", "deploy", "test_deploy"})
        self.assertEqual(shell_stage("cd app && python3 -m pytest -q"), "test")
        self.assertEqual(shell_stage("pytest && systemctl restart app"), "test_deploy")
        self.assertEqual(shell_stage("systemctl start app; curl --fail http://localhost/health; systemctl stop app"), "deploy_verify")

    def test_status_copy_is_stable_between_events_and_survives_slow_step(self):
        self.runtime.pre_api("root", user_message="帮我查一下")
        first = self.text()
        self.runtime.pre_api("root", user_message="部署")
        self.assertEqual(first, self.text())
        self.start("web_search")
        self.assertIn("这一步还没返回新结果", self.text(90))
        self.assertIn("正在搜索", self.text(90))


if __name__ == "__main__":
    unittest.main()
