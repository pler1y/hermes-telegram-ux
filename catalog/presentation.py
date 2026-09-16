"""Small bilingual status vocabulary and lossless, optional final annotations."""
import re

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


def status_text(turn, language, ending=None):
    phase, detail = (ending, "") if ending else turn.phase()
    return LABELS[language][phase].format(detail=detail) + "\n" + statistics(turn, language)


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
