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
            self.assertEqual(progress.render(time.monotonic(), 45), "思考中…")
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

    def test_failed_test_invalidates_prior_pass_but_keeps_found_sources(self):
        self.start("web_search", call="search")
        self.finish("web_search", {"results": [{}, {}]}, call="search")
        self.start("terminal", {"command": "pytest test_a.py"}, call="pass")
        self.finish("terminal", {"exit_code": 0}, call="pass")
        self.start("terminal", {"command": "pytest test_b.py"}, call="fail")
        self.finish("terminal", {"exit_code": 1}, call="fail")
        self.assertIn("测试没通过", self.text())
        self.assertNotIn("测试通过了", self.text())
        self.assertIn("2 条候选资料", self.text())
        self.assertNotIn("测试通过了", self.state.progress.snapshot()["finding"])

    def test_unrelated_parallel_success_does_not_clear_test_failure(self):
        self.start("terminal", {"command": "pytest"}, call="test")
        self.start("web_search", call="search")
        self.finish("terminal", {"exit_code": 1}, call="test")
        self.finish("web_search", {"results": [{}, {}]}, call="search")
        self.assertIn("测试没通过", self.text())
        self.assertIn("2 条候选资料", self.text())

    def test_sibling_owner_and_different_test_cannot_resolve_failed_step(self):
        self.runtime.child_start(parent_session_id="root", child_session_id="child")
        self.start("terminal", {"command": "pytest test_a.py"}, call="failed")
        self.finish("terminal", {"exit_code": 1}, call="failed")
        for call, owner, command in [("child", "child", "pytest test_a.py"),
                                      ("other", "root", "pytest test_b.py")]:
            with self.subTest(owner=owner, command=command):
                self.start("terminal", {"command": command}, call=call, owner=owner)
                self.finish("terminal", {"exit_code": 0}, call=call, owner=owner)
                self.assertIn("测试没通过", self.text())
                self.assertNotIn("测试通过了", self.text())
        self.start("terminal", {"command": "pytest test_a.py", "timeout": 120}, call="retry")
        self.finish("terminal", {"exit_code": 0}, call="retry")
        self.assertNotIn("测试没通过", self.text())
        self.assertIn("测试通过了", self.text())

    def test_retry_without_exit_result_does_not_resolve_failed_test(self):
        self.start("terminal", {"command": "pytest"})
        self.finish("terminal", {"exit_code": 1})
        self.start("terminal", {"command": "pytest"}, call="retry")
        self.finish("terminal", {"output": "work queued"}, call="retry")
        self.assertIn("测试没通过", self.text())
        self.assertNotIn("测试通过了", self.text())

    def test_background_retry_uses_original_step_identity(self):
        self.start("terminal", {"command": "pytest"})
        self.finish("terminal", {"session_id": "p1", "status": "running"})
        self.start("process", {"session_id": "p1"}, call="poll1")
        self.finish("process", {"exit_code": 1}, call="poll1")
        self.assertIn("测试没通过", self.text())
        self.start("terminal", {"command": "pytest"}, call="retry")
        self.finish("terminal", {"session_id": "p2", "status": "running"}, call="retry")
        self.start("write_stdin", {"session_id": "p2"}, call="poll2")
        self.finish("write_stdin", {"exit_code": 0}, call="poll2")
        self.assertNotIn("测试没通过", self.text())
        self.assertIn("测试通过了", self.text())

    def test_background_execution_options_do_not_change_retry_identity(self):
        self.start("terminal", {"command": "pytest"}, call="first")
        self.finish("terminal", {"exit_code": 1}, call="first")
        self.start("terminal", {"command": "pytest", "background": True, "notify": True}, call="retry")
        self.finish("terminal", {"session_id": "background-retry", "status": "running"}, call="retry")
        self.start("process", {"session_id": "background-retry"}, call="poll")
        self.finish("process", {"exit_code": 0}, call="poll")
        self.assertNotIn("测试没通过", self.text())
        self.assertIn("测试通过了", self.text())

    def test_health_check_retry_recovers_after_display_stage_changes(self):
        command = "curl --fail http://localhost:9876/health"
        self.start("terminal", {"command": command}, call="before")
        self.finish("terminal", {"exit_code": 7}, call="before")
        self.assertIn("没成功", self.text())
        self.start("terminal", {"command": "systemctl restart demo"}, call="deploy")
        self.finish("terminal", {"exit_code": 0}, call="deploy")
        self.assertIn("没成功", self.text())
        self.start("terminal", {"command": command}, call="after")
        self.assertIn("部署后的运行", self.text())
        self.finish("terminal", {"exit_code": 0}, call="after")
        self.assertNotIn("没成功", self.text())

    def test_older_parallel_attempt_cannot_replace_newer_result(self):
        for newer_exit, older_exit in [(1, 0), (0, 1)]:
            with self.subTest(newer_exit=newer_exit, older_exit=older_exit):
                self.setUp()
                self.start("terminal", {"command": "pytest"}, call="old")
                self.start("terminal", {"command": "pytest"}, call="new")
                self.finish("terminal", {"exit_code": newer_exit}, call="new")
                self.finish("terminal", {"exit_code": older_exit}, call="old")
                self.assertEqual("测试没通过" in self.text(), newer_exit != 0)
                self.assertEqual("测试通过了" in self.text(), newer_exit == 0)
                self.assertFalse(self.state.progress._attempts)

    def test_process_poll_inherits_attempt_order_across_retries(self):
        for newer_exit, older_exit in [(1, 0), (0, 1)]:
            with self.subTest(newer_exit=newer_exit, older_exit=older_exit):
                self.setUp()
                for attempt in ("old", "new"):
                    self.start("terminal", {"command": "pytest", "background": True}, call=attempt)
                    self.finish("terminal", {"session_id": attempt, "status": "running"}, call=attempt)
                self.start("process", {"session_id": "new"}, call="new-poll")
                self.finish("process", {"exit_code": newer_exit}, call="new-poll")
                # This poll starts later but belongs to the older execution.
                self.start("process", {"session_id": "old"}, call="old-poll")
                self.finish("process", {"exit_code": older_exit}, call="old-poll")
                self.assertEqual("测试没通过" in self.text(), newer_exit != 0)
                self.assertEqual("测试通过了" in self.text(), newer_exit == 0)
                self.assertFalse(self.state.progress.processes)
                self.assertFalse(self.state.progress._attempts)

    def test_retry_resolves_only_its_own_failure(self):
        for call in ("a", "b"):
            self.start("terminal", {"command": f"pytest test_{call}.py"}, call=call)
            self.finish("terminal", {"exit_code": 1}, call=call)
        self.start("terminal", {"command": "pytest test_b.py"}, call="retry_b")
        self.finish("terminal", {"exit_code": 0}, call="retry_b")
        self.assertIn("测试没通过", self.text())
        self.assertNotIn("测试通过了", self.text())
        self.start("terminal", {"command": "pytest test_a.py"}, call="retry_a")
        self.finish("terminal", {"exit_code": 0}, call="retry_a")
        self.assertNotIn("测试没通过", self.text())
        self.assertIn("测试通过了", self.text())

    def test_bundled_failure_invalidates_component_success(self):
        self.start("terminal", {"command": "pytest"})
        self.finish("terminal", {"exit_code": 0})
        self.start("terminal", {"command": "pytest && systemctl restart demo"}, call="bundle")
        self.finish("terminal", {"exit_code": 1}, call="bundle")
        self.assertIn("没成功", self.text())
        self.assertNotIn("测试通过了", self.text())

    def test_result_history_is_bounded_without_hiding_forgotten_failures(self):
        progress = TaskProgress()
        for i in range(140):
            progress.start("root", str(i), "web_search", {"query": str(i)})
            progress.finish("root", str(i), "web_search", {"results": [{}]})
            progress.start("root", f"test-{i}", "terminal", {"command": f"pytest test_{i}.py"})
            progress.finish("root", f"test-{i}", "terminal", {"exit_code": 1}, failed=True)
        self.assertLessEqual(len(progress._evidence), 64)
        self.assertLessEqual(len(progress._problems), 128)
        self.assertEqual(len(progress._overflow_problems), 1)
        self.assertFalse(progress._attempts)
        self.assertIn("测试没通过", progress.render(time.monotonic(), 45))
        self.assertIn("1 条候选资料", progress.render(time.monotonic(), 45))

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
