"""Acceptance of authored public events through adapter and real transport code.

The host, tool responses and Telegram endpoint are synthetic. These tests do
not claim that a live model chose the notes or that Telegram delivered them.
"""
import asyncio
import unittest

from scripts.check_milestones import PublicReplay, run_scenarios, search_results


class MilestoneFlowTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.replays = []

    async def asyncTearDown(self):
        for replay in self.replays:
            await replay.close()

    async def begin(self, task="Grok 4.6 什么时候发布？", language="zh"):
        replay = PublicReplay(task, language)
        self.replays.append(replay)
        await replay.begin()
        return replay

    async def search(self, replay, count=2):
        await replay.tool("搜索夹具", "web_search", {"query": "Grok 4.6 官方发布信息"},
                          search_results(count))

    async def test_four_complete_task_timelines_use_one_owned_message(self):
        reports = await run_scenarios()
        self.assertEqual(len(reports), 4)
        for report in reports:
            with self.subTest(scenario=report["name"]):
                self.assertEqual(report["scope"], "authored-public-event-replay")
                self.assertEqual(report["milestone_calls"], 3)
                texts = [call["content"] for call in report["calls"] if "content" in call]
                self.assertGreaterEqual(len(set(texts)), 7)
                milestone_rows = [row for row in report["rows"]
                                  if row["event"].startswith("公开 milestone")
                                  and row["event"].endswith(" / post")]
                self.assertTrue(all(any(call["operation"] == "edit" for call in row["calls"])
                                    for row in milestone_rows))

    async def test_no_progress_keeps_initial_status_across_api_and_quiet(self):
        replay = await self.begin()
        initial = list(replay.telegram.calls)
        await replay.api(count=0)
        await replay.quiet(180)
        self.assertEqual(replay.visible, "🤔 思考中…")
        self.assertEqual(replay.telegram.calls, initial)
        self.assertNotIn("Grok", replay.visible)

    async def test_meaningful_milestone_survives_generic_api_and_fresh_tool_replaces_it(self):
        replay = await self.begin()
        await self.search(replay)
        await replay.note("比较阶段", action="核对不同来源中的发布日期")
        milestone = replay.visible
        self.assertIn("不同来源中的发布日期", milestone)
        before = len(replay.telegram.calls)
        await replay.api()
        await replay.quiet(180)
        self.assertEqual(replay.visible, milestone)
        self.assertEqual(len(replay.telegram.calls), before)
        await replay.event("真正开始读取来源", "pre_tool_call", tool_call_id="fresh-read",
            tool_name="web_extract", args={"urls": ["https://x.ai/news/"]})
        self.assertNotEqual(replay.visible, milestone)
        self.assertTrue(replay.visible.startswith("📖"))
        await replay.event("来源真实返回", "post_tool_call", tool_call_id="fresh-read",
            tool_name="web_extract", status="ok", result={"results": [{"content": "Fixture source"}]})
        self.assertIn("已读取", replay.visible)
        await replay.note("重新比较", action="比较公告资料与其他来源的日期")
        self.assertIn("其他来源的日期", replay.visible)

    async def test_result_fact_survives_real_heartbeat_without_ttl_extension(self):
        replay = await self.begin()
        await self.search(replay, count=8)
        before = len(replay.telegram.calls)
        self.assertIn("8", replay.visible)
        await replay.api()
        touched = replay.adapter.turns[replay.key].touched
        replay.now += 180
        # The actual transport heartbeat waits at most two wall-clock seconds.
        await asyncio.sleep(2.1)
        self.assertEqual(len(replay.telegram.calls), before)
        self.assertEqual(replay.adapter.turns[replay.key].touched, touched)
        self.assertIn("8", replay.visible)

    async def test_duplicate_and_prefix_punctuation_variants_do_not_edit(self):
        replay = await self.begin()
        await self.search(replay)
        await replay.note("比较阶段", action="核对不同来源中的发布日期")
        before = len(replay.telegram.calls)
        for action in ("核对不同来源中的发布日期", "正在核对不同来源中的发布日期…",
                       "我正在核对不同来源中的发布日期。"):
            await replay.note("同一阶段改写", action=action)
        self.assertEqual(len(replay.telegram.calls), before)
        await replay.note("变化后的对象", action="核对不同来源中的版本编号")
        self.assertEqual(len(replay.telegram.calls), before + 1)
        self.assertIn("版本编号", replay.visible)

    async def test_new_numbers_in_otherwise_similar_milestones_are_not_suppressed(self):
        replay = await self.begin("比较四组数据")
        await replay.note("第一组", action="比较第 1 组数据中的差异")
        before = len(replay.telegram.calls)
        await replay.note("第二组", action="比较第 2 组数据中的差异")
        self.assertEqual(len(replay.telegram.calls), before + 1)
        self.assertIn("2", replay.visible)

    async def test_generic_goal_only_and_question_echo_notes_do_not_invent_progress(self):
        replay = await self.begin()
        before = len(replay.telegram.calls)
        for note in ({"goal": "Grok 4.6 发布时间"}, {"action": "我正在思考"},
                     {"action": "正在使用工具"}, {"action": "正在处理问题"},
                     {"action": "正在分析Grok 4.6 什么时候发布"}):
            await replay.note("无新增信息", **note)
        self.assertEqual(len(replay.telegram.calls), before)
        self.assertEqual(replay.visible, "🤔 思考中…")

    async def test_unverified_findings_are_ignored_but_valid_action_can_remain(self):
        replay = await self.begin()
        await replay.note("无事实支撑的日期", finding="发布日期已经确认")
        self.assertEqual(replay.visible, "🤔 思考中…")
        await self.search(replay)
        before = len(replay.telegram.calls)
        await replay.note("工具结果不支撑日期", finding="发布日期已经确认")
        self.assertEqual(len(replay.telegram.calls), before)
        await replay.note("保留公开工作阶段", finding="发布日期已经确认",
                          action="比较不同来源中的日期")
        self.assertIn("比较不同来源中的日期", replay.visible)
        self.assertNotIn("已经确认", replay.visible)

    async def test_intended_next_step_stays_an_intention_and_does_not_claim_recovery(self):
        replay = await self.begin()
        await replay.tool("读取失败", "web_extract", {"urls": ["https://example.org"]},
                          {"error": "Fixture fetch failed"}, status="error")
        before = replay.visible
        await replay.api()
        await replay.quiet()
        self.assertEqual(replay.visible, before)
        self.assertNotIn("换", replay.visible)
        await replay.note("公开下一步", next="补充核对官方来源")
        self.assertIn("接下来", replay.visible)
        self.assertIn("补充核对官方来源", replay.visible)
        self.assertNotIn("已恢复", replay.visible)

    async def test_status_omits_reasoning_queries_secrets_paths_and_commands(self):
        replay = await self.begin("检查状态清理代码")
        await replay.tool("带敏感查询的事件", "web_search",
            {"query": 'site:example.org "PRIVATE_QUERY_MARKER" after:2026-09-01'}, search_results(2))
        await replay.tool("完整路径输入", "read_file",
            {"path": "/Users/private/workspace/cleanup.py"},
            {"content": "PRIVATE_FILE_BODY", "total_lines": 1})
        for action in ("<think>PRIVATE_REASONING</think>", "api_key=sk-privatefixturevalue",
                       "运行 `cat /private/PRIVATE_COMMAND`", "核对 /Users/private/workspace/cleanup.py",
                       "site:example.org PRIVATE_QUERY_MARKER"):
            await replay.note("敏感输入过滤", action=action)
        await replay.event("原生 interim 忽略", "on_interim_message",
                           text="PRIVATE_INTERIM_REASONING", iteration=1)
        captured = repr(replay.telegram.calls) + repr(replay.adapter.turns)
        for forbidden in ("PRIVATE_QUERY_MARKER", "PRIVATE_REASONING", "sk-privatefixturevalue",
                          "PRIVATE_FILE_BODY", "PRIVATE_COMMAND", "PRIVATE_INTERIM_REASONING",
                          "/Users/", "/private/", "site:example.org", "<think>"):
            self.assertNotIn(forbidden, captured)

    async def test_running_tool_is_not_interrupted_by_a_late_milestone(self):
        replay = await self.begin()
        await replay.event("旧 milestone 开始", "pre_tool_call", tool_call_id="old-note",
            tool_name="telegram_ux_update", args={"action": "筛选主要来源"})
        await replay.event("新搜索开始", "pre_tool_call", tool_call_id="fresh",
            tool_name="web_search", args={"query": "Grok 4.6 官方更新记录"})
        before = len(replay.telegram.calls)
        await replay.event("旧 milestone 迟到返回", "post_tool_call", tool_call_id="old-note",
            tool_name="telegram_ux_update", args={"action": "筛选主要来源"}, status="ok")
        self.assertEqual(len(replay.telegram.calls), before)
        self.assertTrue(replay.visible.startswith("🔎"))

    async def test_english_statuses_keep_semantic_progress_and_clean_up(self):
        replay = await self.begin("When will Aurora version 3 be released?", "en")
        self.assertEqual(replay.visible, "🤔 Thinking…")
        await replay.api()
        self.assertEqual(replay.visible, "🤔 Thinking…")
        await replay.tool("Search", "web_search", {"query": "Aurora version 3 official announcements"},
                          search_results(3))
        self.assertIn("3", replay.visible)
        await replay.note("Compare", action="Comparing release dates across sources")
        before = len(replay.telegram.calls)
        await replay.api()
        await replay.note("Same comparison", action="Comparing release dates across sources.")
        await replay.quiet()
        self.assertEqual(len(replay.telegram.calls), before)
        self.assertIn("Comparing release dates", replay.visible)
        await replay.finish()
        self.assertEqual(replay.telegram.calls[-1]["operation"], "delete")
        texts = [call["content"] for call in replay.telegram.calls if "content" in call]
        self.assertTrue(all(len(text) <= 110 for text in texts))
        self.assertTrue(all(not any("\u3400" <= char <= "\u9fff" for char in text) for text in texts))


if __name__ == "__main__":
    unittest.main()
