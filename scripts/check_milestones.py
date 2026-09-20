#!/usr/bin/env python3
"""Replay authored public events through the plugin and its synthetic transport.

This does not run Hermes, a model, Telegram, web searches, or shell commands.
Tool arguments/results below are fixtures, not external facts. Every recorded
status is produced by the actual registered hook -> adapter -> transport path.
"""
import argparse
import asyncio
import json
from pathlib import Path
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from catalog.adapter import HermesCatalogAdapter


class ReplayContext:
    profile_name = "default"

    def __init__(self, language="zh"):
        self.settings = {"language": language, "cleanup_delay": 0}
        self.hooks, self.tasks, self.tools = {}, [], []

    def get_config(self, key, default=None):
        return self.settings.get(key, default)

    def register_hook(self, name, callback):
        self.hooks[name] = callback

    def register_platform_handler(self, platform, factory):
        if platform != "telegram":
            raise AssertionError("Replay must use the Telegram platform")
        self.factory = factory

    def register_tool(self, **kwargs):
        self.tools.append(kwargs)

    def on_unload(self, callback):
        self.unload = callback

    def spawn_task(self, coro, **kwargs):
        task = asyncio.create_task(coro)
        self.tasks.append(task)
        return task


class RecordingTelegram:
    """Record only public send/edit/delete calls made by TelegramPanels."""

    def __init__(self):
        self.calls = []

    async def send(self, **kwargs):
        self.calls.append({"operation": "send", **kwargs})
        return SimpleNamespace(success=True, message_id="owned-status")

    async def edit_message(self, **kwargs):
        self.calls.append({"operation": "edit", **kwargs})
        return SimpleNamespace(success=True)

    async def delete_message(self, **kwargs):
        self.calls.append({"operation": "delete", **kwargs})
        return True


class PublicReplay:
    """A local callback host; it deliberately does not simulate model choices."""

    def __init__(self, task, language="zh"):
        self.task, self.language = task, language
        self.now = 100.0
        self.ctx, self.telegram = ReplayContext(language), RecordingTelegram()
        self.adapter = HermesCatalogAdapter(self.ctx, clock=lambda: self.now)
        self.adapter.register()
        self.ctx.factory(None, self.telegram)
        # Accelerate the plugin-owned display throttle for deterministic replay.
        self.adapter.transport.interval = 0.001
        self.key = ("replay-session", "replay-turn")
        self.rows, self.sequence, self.cursor = [], 0, 0

    @property
    def ids(self):
        return {"session_id": self.key[0], "turn_id": self.key[1]}

    @property
    def visible(self):
        return next((call["content"] for call in reversed(self.telegram.calls)
                     if "content" in call), "")

    async def settle(self):
        await asyncio.sleep(0.015)

    def capture(self, label):
        calls = self.telegram.calls[self.cursor:]
        self.rows.append({"event": label, "calls": [dict(call) for call in calls]})
        self.cursor = len(self.telegram.calls)

    async def begin(self):
        incoming = SimpleNamespace(internal=False, message_id="10", source=SimpleNamespace(
            platform="telegram", chat_id="-10042", user_id="101", thread_id="7"))
        self.ctx.hooks["pre_gateway_dispatch"](event=incoming)
        self.guidance = await asyncio.to_thread(self.ctx.hooks["pre_llm_call"],
            **self.ids, sender_id="101", platform="telegram", user_message=self.task)
        await self.settle()
        self.capture("已授权的 pre_llm_call：建立本轮临时气泡")

    async def event(self, label, hook, **kwargs):
        self.now += 1
        value = self.ctx.hooks[hook](**self.ids, **kwargs)
        if value is not None:
            raise AssertionError(f"Observer {hook} must not return task directives")
        await self.settle()
        self.capture(label)

    async def api(self, label="普通模型请求及返回", count=1):
        self.sequence += 1
        request = "api-" + str(self.sequence)
        await self.event(label + " / pre", "pre_api_request", api_request_id=request)
        await self.event(label + " / post", "post_api_request", api_request_id=request,
                         assistant_tool_call_count=count)

    async def note(self, label, **args):
        self.sequence += 1
        call = "milestone-" + str(self.sequence)
        tool = self.ctx.tools[0]
        await self.event(label + " / pre", "pre_tool_call", tool_call_id=call,
                         tool_name=tool["name"], args=args)
        result = tool["handler"](args)
        await self.event(label + " / post", "post_tool_call", tool_call_id=call,
                         tool_name=tool["name"], args=args, result=result, status="ok")

    async def tool(self, label, name, args, result, status="ok"):
        self.sequence += 1
        call = "tool-" + str(self.sequence)
        await self.event(label + " / pre", "pre_tool_call", tool_call_id=call,
                         tool_name=name, args=args)
        await self.event(label + " / post", "post_tool_call", tool_call_id=call,
                         tool_name=name, args=args, result=result, status=status)

    async def quiet(self, seconds=45):
        """Advance the display clock without adding a public task event."""
        before, touched = self.visible, self.adapter.turns[self.key].touched
        self.now += seconds
        refreshed = self.adapter.refresh(self.key)
        if refreshed != before:
            raise AssertionError("Elapsed time alone changed the public status")
        if self.adapter.turns[self.key].touched != touched:
            raise AssertionError("A display refresh extended the activity TTL")
        await self.settle()
        self.capture(f"静默 {seconds} 秒（推进测试时钟并调用显示刷新）")

    async def finish(self):
        await self.event("post_llm_call：模拟原生回答已生成（内容不复制）", "post_llm_call",
                         assistant_response="NATIVE_FINAL_PAYLOAD_NOT_FOR_STATUS")
        await self.event("on_session_end(completed=True)：清理临时气泡", "on_session_end",
                         completed=True)
        await asyncio.wait_for(asyncio.gather(*self.ctx.tasks), 1)
        self.capture("等待本轮 transport 工作任务结束")
        before = len(self.telegram.calls)
        await self.event("迟到的工具事件（已结束的轮次）", "pre_tool_call",
                         tool_call_id="late", tool_name="web_search", args={"query": "late"})
        if len(self.telegram.calls) != before:
            raise AssertionError("A late event resurrected a completed status")

    async def close(self):
        self.adapter.close()
        await asyncio.sleep(0)
        await asyncio.wait_for(asyncio.gather(*self.ctx.tasks, return_exceptions=True), 1)


def search_results(count):
    return {"results": [{"title": f"Fixture source {index + 1}",
                         "url": f"https://example.org/source-{index + 1}"}
                        for index in range(count)]}


async def stable_api(replay):
    before = len(replay.telegram.calls)
    await replay.api()
    await replay.quiet()
    if len(replay.telegram.calls) != before:
        raise AssertionError("Generic API activity replaced meaningful progress")


async def release_research(replay):
    await replay.tool("搜索官方发布信息", "web_search",
        {"query": "Grok 4.6 官方发布信息"}, search_results(8))
    await stable_api(replay)
    await replay.note("公开 milestone：跨来源比较", action="核对不同来源中的发布日期")
    await stable_api(replay)
    await replay.tool("读取公告来源", "web_extract", {"urls": ["https://x.ai/news/"]},
        {"results": [{"content": "Fixture announcement; no release-date claim is made."}]})
    await replay.note("公开 milestone：比较资料", action="比较官方资料与其他来源的日期")
    await replay.tool("补充查找来源", "web_search",
        {"query": "Grok 4.6 官方更新记录"}, search_results(1))
    await replay.note("公开 milestone：整理结果", action="整理发布时间线")


async def cleanup_investigation(replay):
    await replay.tool("定位清理入口", "terminal",
        {"command": "rg -n 'delete_owned|on_session_end' catalog"},
        {"output": "Fixture cleanup entry points", "exit_code": 0})
    await replay.note("公开 milestone：检查生命周期", action="检查状态气泡的清理入口")
    await replay.tool("读取消息清理代码", "read_file",
        {"path": "/private/fixture/catalog/telegram.py"},
        {"content": "Fixture public transport source", "total_lines": 40})
    await stable_api(replay)
    await replay.note("公开 milestone：检查触发条件", action="核对消息删除的触发条件")
    await replay.tool("运行清理测试", "terminal",
        {"command": "python -m unittest tests.test_cleanup"},
        {"output": "Fixture: 4 tests completed", "exit_code": 0})
    await replay.note("公开 milestone：整理原因", action="整理状态消息未删除的原因")


async def data_analysis(replay):
    await replay.tool("读取数据文件", "read_file", {"path": "/private/fixture/sales.csv"},
        {"content": "month,revenue\n1,10\n2,20\n3,0\n", "total_lines": 4, "file_size": 34})
    await replay.note("公开 milestone：检查字段", action="检查月份与收入字段")
    await stable_api(replay)
    await replay.tool("计算关键指标", "execute_code", {"code": "print(sum([10, 20, 0]))"},
        {"status": "success", "output": "30", "exit_code": 0})
    await replay.note("公开 milestone：核对数据", action="核对收入为零的记录")
    await replay.tool("补充读取数据", "read_file", {"path": "/private/fixture/adjustments.csv"},
        {"content": "month,note\n3,no sales\n", "total_lines": 2, "file_size": 23})
    await replay.note("公开 milestone：整理结果", action="整理关键指标与数据说明")


async def multiple_sources(replay):
    await replay.tool("搜索近期公开事件", "web_search",
        {"query": "Aurora 项目 最近一周 公开信息"}, search_results(5))
    await replay.note("公开 milestone：筛选来源", action="筛选最近一周的主要来源")
    await replay.tool("读取公告", "web_extract",
        {"urls": ["https://example.org/aurora/announcements"]},
        {"results": [{"content": "Fixture project announcement"}]})
    await replay.note("公开 milestone：对比事件", action="对比不同来源中的事件信息")
    await stable_api(replay)
    await replay.tool("补充核对事件", "web_search",
        {"query": "Aurora 项目 事件日期 官方记录"}, search_results(2))
    await replay.note("公开 milestone：整理时间线", action="整理最近一周的事件时间线")


SCENARIOS = (
    ("发布信息调查", "Grok 4.6 什么时候发布？", release_research),
    ("代码清理问题检查", "检查这个项目为什么状态消息没有被删除", cleanup_investigation),
    ("文件与数据分析", "分析销售数据文件中的关键指标与异常记录", data_analysis),
    ("多来源调查", "调查最近一周 Aurora 项目发生了什么", multiple_sources),
)


def assert_lifecycle(replay):
    calls = replay.telegram.calls
    assert len([call for call in calls if call["operation"] == "send"]) == 1
    assert len([call for call in calls if call["operation"] == "delete"]) == 1
    assert calls[0]["content"] == "🤔 思考中…"
    assert calls[-1]["operation"] == "delete"
    assert all(call["chat_id"] == "-10042" for call in calls)
    assert all(call["message_id"] == "owned-status" for call in calls if call["operation"] != "send")
    assert calls[0]["metadata"] == {"thread_id": "7"}
    assert calls[0]["reply_to"] == "10"
    assert not replay.adapter.turns and not replay.adapter.transport.panels
    texts = [call["content"] for call in calls if "content" in call]
    assert all(len(text) <= 60 and len(text.splitlines()) == 1 for text in texts)
    assert all(left != right for left, right in zip(texts, texts[1:]))
    assert all(replay.task not in text for text in texts)
    assert not any("正在分析" in text or "正在处理你的问题" in text for text in texts)
    assert not any("NATIVE_FINAL_PAYLOAD" in text or "/private/" in text for text in texts)


async def run_scenarios():
    reports = []
    for name, task, scenario in SCENARIOS:
        replay = PublicReplay(task)
        try:
            await replay.begin()
            await stable_api(replay)
            await scenario(replay)
            await replay.finish()
            assert_lifecycle(replay)
            reports.append({"name": name, "task": task, "scope": "authored-public-event-replay",
                            "milestone_calls": sum(row["event"].startswith("公开 milestone") and row["event"].endswith(" / post") for row in replay.rows),
                            "rows": replay.rows, "calls": replay.telegram.calls})
        finally:
            await replay.close()
    return reports


def markdown_report(reports):
    lines = ["# 动态任务进度：四类公开事件回放", "",
        "由 `python scripts/check_milestones.py --write-doc` 生成。以下输入均为人工编写的公开事件、工具参数和结果夹具；没有运行模型、访问 Telegram、执行所列命令或查询真实网站。Grok 与 Aurora 的输入用于检验通用状态机制，不构成产品发布或项目动态事实。", "",
        "状态文本直接记录自已注册的公开 hook → `HermesCatalogAdapter` → `TelegramPanels` → 测试 transport 的 send/edit/delete 调用，未手写预期时间线。每步留出显示窗口，因此展示的是可见阶段回放；真实运行中的快速事件可能按现有节流规则合并。静默步骤只推进测试时钟并调用显示刷新，不冒充经过等量墙钟时间。", "",
        "本回放验证状态协同与消息生命周期，不能验证 Hermes 是否主动选择调用该工具、真实调用频率、模型是否忠实理解来源、真实 Telegram 延迟或原生最终回答送达。Milestone 均由脚本明确调用已注册的工具 handler；finding 的事实支持另由专项回归检查。", ""]
    for report in reports:
        lines.extend(["## " + report["name"], "", "模拟用户请求：" + report["task"], "",
                      f"主动 milestone：{report['milestone_calls']} 次。1 次 send，{sum(call['operation'] == 'edit' for call in report['calls'])} 次 edit，1 次 delete。", "",
                      "| 顺序 | 公开事件 / 测试步骤 | transport 可见变化 |", "| --- | --- | --- |"])
        for number, row in enumerate(report["rows"], 1):
            changes = "<br>".join("delete：删除 owned-status" if call["operation"] == "delete"
                else call["operation"] + "：" + call["content"] for call in row["calls"])
            lines.append(f"| {number} | {row['event']} | {changes or '无 send/edit/delete'} |")
        lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-doc", action="store_true",
                        help="Write the observed timelines to docs/MILESTONE-TIMELINES.md")
    args = parser.parse_args()
    reports = asyncio.run(run_scenarios())
    if args.write_doc:
        target = ROOT / "docs" / "MILESTONE-TIMELINES.md"
        target.write_text(markdown_report(reports), encoding="utf-8")
        print(f"PASS: {len(reports)} synthetic public-event scenarios; wrote {target.relative_to(ROOT)}")
    else:
        print(json.dumps({"scope": "synthetic transport; authored public events; no live model or Telegram",
                          "scenarios": reports}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
