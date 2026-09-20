"""Small bilingual status vocabulary and lossless, optional final annotations."""
import re
import time

TOOL_ACTIONS = {
    "web_search": ("正在检索资料", "Searching for information"),
    "web_extract": ("正在阅读网页", "Reading web pages"),
    "browse": ("正在浏览网页", "Browsing web pages"),
    "read_file": ("正在阅读文件", "Reading files"),
    "write_file": ("正在写入文件", "Writing files"),
    "patch": ("正在修改文件", "Editing files"),
    "terminal": ("正在运行任务", "Running the task"),
    "delegate_task": ("正在处理子任务", "Working with subagents"),
    "search_files": ("正在查找文件", "Searching files"),
    "image_generate": ("正在生成图片", "Generating an image"),
}

LABELS = {
    "zh": {
        "working": "⏳ 正在处理", "tool": "🛠 正在调用工具：{detail}",
        "api": "🤔 正在请求模型", "approval": "🔐 等待审批，请使用 Hermes 的审批消息",
        "smart": "🔐 正在评估审批", "interim": "📝 已收到阶段说明，任务继续处理中",
        "tool_error": "⚠️ 工具返回异常，等待后续处理", "api_error": "⚠️ 模型请求失败，等待 Hermes 后续处理",
        "approval_timeout": "⌛ 审批已超时", "approval_failed": "⚠️ 审批通知发送失败",
        "approval_cancelled": "↩️ 审批请求已撤回", "approval_denied": "🚫 审批未通过",
        "ended": "✓ 本轮处理已结束", "failed": "⚠️ 本轮运行异常结束",
        "interrupted": "⏹ 本轮运行已中断", "unknown_end": "本轮运行已结束，结果以 Hermes 回复为准",
        "expired": "⌛ 状态更新已超时，请以 Hermes 后续回复为准",
        "stats": "工具 {tools} 次 · 模型请求 {apis} 次", "errors": " · 工具异常 {errors} 次",
        "partial": "（仅统计已收到的事件）", "footer": "本轮记录：",
        "help": "Hermes Telegram UX · Catalog-safe\n显示可关联的工具、模型和审批状态，最终回复可附执行统计。\n/new、/stop、审批按钮和后台结果由 Hermes 处理。\n配置位于 plugins.entries.hermes-telegram-ux-catalog.settings；修改后重启 Gateway。",
    },
    "en": {
        "working": "⏳ Working", "tool": "🛠 Running tool: {detail}",
        "api": "🤔 Requesting the model", "approval": "🔐 Awaiting approval — use the Hermes approval message",
        "smart": "🔐 Evaluating approval", "interim": "📝 Interim update received; work continues",
        "tool_error": "⚠️ Tool reported a problem; awaiting further handling", "api_error": "⚠️ Model request failed; awaiting Hermes handling",
        "approval_timeout": "⌛ Approval timed out", "approval_failed": "⚠️ Approval notification failed",
        "approval_cancelled": "↩️ Approval request withdrawn", "approval_denied": "🚫 Approval denied",
        "ended": "✓ Turn processing ended", "failed": "⚠️ Turn ended with an error",
        "interrupted": "⏹ Turn interrupted", "unknown_end": "Turn ended; see Hermes for the result",
        "expired": "⌛ Status updates expired; see subsequent Hermes replies",
        "stats": "Tools: {tools} · Model requests: {apis}", "errors": " · Tool issues: {errors}",
        "partial": " (observed events only)", "footer": "Turn record: ",
        "help": "Hermes Telegram UX · Catalog-safe\nShows correlated tool, model and approval events, plus optional reply statistics.\nHermes handles /new, /stop, approval buttons and background results.\nSettings: plugins.entries.hermes-telegram-ux-catalog.settings. Restart the Gateway after changes.",
    },
}


def statistics(turn, language):
    labels = LABELS[language]
    tools, apis, errors = turn.counts()
    result = labels["stats"].format(tools=tools, apis=apis)
    if errors:
        result += labels["errors"].format(errors=errors)
    if turn.capped:
        result += labels["partial"]
    return result


def status_text(turn, language, ending=None, now=None, detailed=None):
    phase, detail = (ending, "") if ending else turn.phase()
    prefs = turn.preferences
    detailed = prefs.get("display", "brief") == "detail" if detailed is None else detailed
    text = LABELS[language][phase].format(detail=detail)
    if phase == "tool":
        name = detail.split(", ")[0]
        action = TOOL_ACTIONS.get(name, ("正在使用工具处理任务", "Working with a tool"))[language == "en"]
        text = "🛠 " + action + (f" · {detail}" if detailed else "")
    elif phase == "api":
        text = "🤔 正在整理信息并生成回复" if language == "zh" else "🤔 Preparing the response"
    lines = [text]
    if not ending:
        labels = {"goal": "任务", "action": "当前", "finding": "发现", "next": "接下来"} if language == "zh" else {"goal": "Task", "action": "Now", "finding": "Found", "next": "Next"}
        for key in ("goal", "action", "finding", "next"):
            value = turn.note.get(key)
            if value:
                lines.append(f"{labels[key]}：{value}" if language == "zh" else f"{labels[key]}: {value}")
    elapsed = max(0, int((time.monotonic() if now is None else now) - turn.started))
    if prefs.get("wait_hint", True) and elapsed >= 20:
        lines.append(f"已用时 {elapsed // 60} 分 {elapsed % 60} 秒" if language == "zh" else f"Elapsed {elapsed // 60}m {elapsed % 60}s")
    if turn.retries:
        lines.append(f"本次模型请求重试 {turn.retries} 次" if language == "zh" else f"Retries for this model request: {turn.retries}")
    if turn.children:
        counts = {state: list(turn.children.values()).count(state) for state in set(turn.children.values())}
        running, completed = counts.get("running", 0), counts.get("completed", 0)
        issues = sum(counts.get(state, 0) for state in ("failed", "error", "interrupted"))
        lines.append(f"子任务：进行中 {running} · 完成 {completed} · 异常/中断 {issues}" if language == "zh" else f"Subtasks: {running} running · {completed} completed · {issues} failed/interrupted")
    if detailed:
        lines.append(statistics(turn, language))
    if not prefs.get("emoji", True):
        lines[0] = re.sub(r"^[⏳🛠🤔🔐📝⚠⌛↩🚫✓⏹]\ufe0f?\s*", "", lines[0])
    return "\n".join(lines)


def annotate_reply(response, turn, language):
    if not isinstance(response, str) or not response.strip() or not turn.tools:
        return None
    # Delivery directives, media-only replies, and code fences remain completely native.
    if re.search(r"(?im)^\s*(?:MEDIA:|NO_REPLY\b|HEARTBEAT_OK\b|\[(?:SILENT|NO_REPLY)\])", response):
        return None
    if response.count("```") % 2 or response.count("~~~") % 2:
        return None
    footer = "\n\n" + LABELS[language]["footer"] + statistics(turn, language)
    return None if response.endswith(footer) else response + footer
