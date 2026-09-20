"""Concise task-aware rendering of public observations, with safe fallbacks."""
import re

LABELS = {
    "zh": {
        "working": "🤔 正在思考中…", "api": "🤔 正在处理你的问题…",
        "approval": "🔐 等待审批，请使用 Hermes 的审批消息",
        "smart": "🔐 正在评估审批", "interim": "🤔 正在处理你的问题…",
        "tool_error": "⚠️ 这一步没有成功，等待后续处理",
        "tool_cancelled": "↩️ 这一步已取消",
        "api_error": "⚠️ 模型请求失败，等待 Hermes 后续处理",
        "approval_timeout": "⌛ 审批已超时", "approval_failed": "⚠️ 审批通知发送失败",
        "approval_cancelled": "↩️ 审批请求已撤回", "approval_denied": "🚫 审批未通过",
        "finalizing": "✍️ 正在整理最终回答…", "failed": "⚠️ 本轮运行异常结束",
        "interrupted": "⏹ 本轮运行已中断", "unknown_end": "正在清理临时状态…",
        "expired": "⌛ 状态更新已超时，请以 Hermes 后续回复为准",
        "help": "Hermes Telegram UX · Catalog-safe\n用一条临时气泡显示当前任务进度，回合结束后自动清理。\n/new、/stop、审批、最终回答和附件由 Hermes 处理。",
    },
    "en": {
        "working": "🤔 Thinking…", "api": "🤔 Working on your request…",
        "approval": "🔐 Awaiting approval — use the Hermes approval message",
        "smart": "🔐 Evaluating approval", "interim": "🤔 Working on your request…",
        "tool_error": "⚠️ This step did not succeed; awaiting further handling",
        "tool_cancelled": "↩️ This step was cancelled",
        "api_error": "⚠️ Model request failed; awaiting Hermes handling",
        "approval_timeout": "⌛ Approval timed out", "approval_failed": "⚠️ Approval notification failed",
        "approval_cancelled": "↩️ Approval request withdrawn", "approval_denied": "🚫 Approval denied",
        "finalizing": "✍️ Preparing the final answer…", "failed": "⚠️ Turn ended with an error",
        "interrupted": "⏹ Turn interrupted", "unknown_end": "Clearing temporary status…",
        "expired": "⌛ Status updates expired; see subsequent Hermes replies",
        "help": "Hermes Telegram UX · Catalog-safe\nShows task progress in one temporary bubble, removed when the turn ends.\nHermes handles /new, /stop, approvals, final answers and attachments.",
    },
}


def action_text(info, task, language):
    stage, subject = info.get("stage"), info.get("subject", "")
    english = language == "en"
    if stage == "search":
        target = subject or task
        return ("🔎 Searching for " + target + "…" if target else "🔎 Searching for information…") if english else ("🔎 正在搜索" + target + "…" if target else "🔎 正在搜索相关资料…")
    if stage == "read_web":
        return ("📖 Reading " + subject + "…" if subject else "📖 Reading web pages…") if english else ("📖 正在阅读" + subject + "相关资料…" if subject else "📖 正在阅读网页…")
    if stage == "read":
        return ("📖 Reading " + subject + "…" if subject else "📖 Reading files…") if english else ("📖 正在检查" + subject + "…" if subject else "📖 正在阅读文件…")
    if stage == "write":
        return ("✏️ Updating " + subject + "…" if subject else "✏️ Updating files…") if english else ("✏️ 正在修改" + subject + "…" if subject else "✏️ 正在修改文件…")
    if stage == "locate":
        return ("🔍 Looking for " + subject + " in the project…" if subject else "🔍 Searching the project…") if english else ("🔍 正在定位" + subject + "…" if subject else "🔍 正在查找项目中的相关代码…")
    if stage == "test":
        return "🧪 Running project tests…" if english else "🧪 正在运行项目测试…"
    if stage == "calculate":
        return "🧮 Calculating…" if english else "🧮 正在进行计算…"
    if stage == "create":
        return "🎨 Generating an image…" if english else "🎨 正在生成图片…"
    if stage == "delegate":
        return ("⚙️ Working on " + subject + "…" if subject else "⚙️ Subtask in progress…") if english else ("⚙️ 正在处理" + subject + "…" if subject else "⚙️ 子任务正在处理中…")
    return "⚙️ Executing the current step…" if english else "⚙️ 正在执行当前步骤…"


def result_text(info, task, language):
    if info.get("status") != "ok":
        return ""
    facts, subject = info.get("facts", {}), info.get("subject") or task
    english = language == "en"
    fields = facts.get("weather_fields", ())
    if fields and re.search(r"天气|气温|预报|weather|forecast", task + " " + subject, re.I):
        names = {"temperature": ("温度", "temperature"), "humidity": ("湿度", "humidity"), "wind": ("风速", "wind speed")}
        observed = (", " if english else "、").join(names[name][english] for name in fields)
        return f"📊 Received {observed} data; organizing the weather information…" if english else f"📊 已获取{observed}数据，正在整理天气信息…"
    if "search_count" in facts:
        count = facts["search_count"]
        if count == 0:
            return "🔎 This search returned no results" if english else "🔎 这次搜索没有返回结果"
        suffix = (" for " + subject) if subject else ""
        return f"📊 Found {count} search results; reviewing information{suffix}…" if english else f"📊 已找到 {count} 条搜索结果，正在整理{subject or '相关资料'}…"
    if facts.get("test_completed"):
        return "🧪 Test command completed; reviewing the result…" if english else "🧪 测试命令已执行完，正在整理执行结果…"
    return ""


def note_text(turn, language):
    """An explicitly public model report, never treated as verified tool evidence."""
    action = turn.note.get("action")
    goal = turn.note.get("goal")
    if action:
        # Supply a missing object, not an entire original user question. A public
        # note remains a model report, distinct from structured tool evidence.
        if goal and language == "zh":
            match = re.fullmatch(r"(?:正在)?(整理|分析|搜索|查询|阅读|处理)(?:信息|结果|资料|任务)?[。.!…]*", action)
            if match:
                return f"📝 正在{match.group(1)}{goal.rstrip('。.!…')}…"
        if goal and language == "en":
            match = re.fullmatch(r"(?i)(reviewing|analyzing|searching|reading|processing)(?: information| results| the task)?[.!…]*", action)
            if match:
                return f"📝 {match.group(1).capitalize()} {goal.rstrip('.!…')}…"
        return "📝 " + action.rstrip("。.!…") + "…"
    if turn.note.get("finding"):
        return ("📝 Progress note: " if language == "en" else "📝 进度说明：") + turn.note["finding"]
    if turn.note.get("next"):
        return ("📝 Next: " if language == "en" else "📝 接下来：") + turn.note["next"]
    if goal:
        return ("📝 Task: " if language == "en" else "📝 当前任务：") + goal
    return ""


def status_text(turn, language, ending=None, now=None, detailed=None):
    """One line, no elapsed time, log counters, completion card or action controls.

    ``now``/``detailed`` remain accepted for existing command callers; ordinary
    progress has the same compact presentation for every display preference.
    """
    language = language if language in LABELS else "zh"
    phase, detail = turn.phase()
    if ending:
        phase = "finalizing" if ending == "ended" else ending
    text = LABELS[language].get(phase, LABELS[language]["working"])
    if not ending and phase in {"tool", "working", "api"}:
        info = turn.progress
        if turn.current_kind == "tool":
            text = action_text(info, turn.user_task, language)
        elif turn.current_kind in {"result", "api", "stream", "generating", "note"}:
            text = note_text(turn, language) if turn.current_kind == "note" else ""
            if not text:
                text = result_text(info, turn.user_task, language)
            if not text:
                text = note_text(turn, language)
            if not text and turn.current_kind == "result" and info.get("status") == "ok":
                text = "📊 Reviewing the current step's result…" if language == "en" else "📊 正在整理这一步的结果…"
            if not text and turn.current_kind in {"stream", "generating"}:
                # A stream can still lead to tools; this is deliberately not FINALIZING.
                text = "🤔 The model is preparing its response…" if language == "en" else "🤔 正在组织回复内容…"
            if not text and turn.current_kind == "api" and re.search(r"天气|新闻|文档|代码|项目|报告|数据|文件|weather|forecast|news|documentation|\bdocs\b|code|project|report|data|file", turn.user_task, re.I):
                # A known task is safe context, not proof that searching/reading has begun.
                text = f"🤔 Working on {turn.user_task}…" if language == "en" else f"🤔 正在处理{turn.user_task}…"
            if not text:
                text = LABELS[language]["working"]
    if not turn.preferences.get("emoji", True):
        text = re.sub(r"^[^\w\u3400-\u9fff]+\s*", "", text)
    limit = 110 if language == "en" else 60
    if len(text) > limit:
        shortened = text[:limit - 1].rstrip(" ，,。.!…")
        if language == "en" and " " in shortened[int(limit * .65):]:
            shortened = shortened.rsplit(" ", 1)[0]
        text = shortened + "…"
    return text
