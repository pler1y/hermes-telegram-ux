"""Concise task-aware rendering of public observations, with safe fallbacks."""
import re

from .intelligence import summary_subject

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
    stage, subject = info.get("stage"), info.get("subject") or task
    english = language == "en"
    if stage == "search":
        text = (f"🔎 Searching for {subject}…" if subject else "🔎 Searching for information…") if english else (f"🔎 正在搜索{subject}…" if subject else "🔎 正在搜索相关资料…")
    elif stage == "read_web":
        text = (f"📖 Reading sources about {subject}…" if subject else "📖 Reading web pages…") if english else (f"📖 正在阅读{subject}相关资料…" if subject else "📖 正在阅读网页…")
    elif stage == "read_data":
        text = (f"📖 Reading data for {subject}…" if subject else "📖 Reading the requested data…") if english else (f"📖 正在读取{subject}数据…" if subject else "📖 正在读取所需数据…")
    elif stage in {"read", "inspect"}:
        text = (f"📖 Inspecting {subject}…" if subject else "📖 Reading files…") if english else (f"📖 正在检查{subject}…" if subject else "📖 正在阅读文件…")
    elif stage == "read_guide":
        text = (f"📖 Reading the guide for {subject}…" if subject else "📖 Reading the relevant guide…") if english else (f"📖 正在查阅{subject}…" if subject else "📖 正在查阅相关操作说明…")
    elif stage == "write":
        text = (f"✏️ Updating {subject}…" if subject else "✏️ Updating files…") if english else (f"✏️ 正在修改{subject}…" if subject else "✏️ 正在修改文件…")
    elif stage == "locate":
        text = (f"🔍 Locating {subject}…" if subject else "🔍 Searching the project…") if english else (f"🔍 正在定位{subject}…" if subject else "🔍 正在查找项目中的相关代码…")
    elif stage == "test":
        text = "🧪 Running project tests…" if english else "🧪 正在运行项目测试…"
    elif stage == "calculate":
        text = (f"🧮 Calculating {subject}…" if subject else "🧮 Calculating…") if english else (f"🧮 正在计算{subject}…" if subject else "🧮 正在进行计算…")
    elif stage == "check_time":
        text = (f"🕒 Checking the current date for {subject}…" if subject else "🕒 Checking the current date…") if english else (f"🕒 正在核对{subject}所用的日期…" if subject else "🕒 正在核对当前日期…")
    elif stage == "create":
        text = (f"🎨 Generating {subject}…" if subject else "🎨 Generating an image…") if english else (f"🎨 正在生成{subject}…" if subject else "🎨 正在生成图片…")
    elif stage == "delegate":
        text = (f"⚙️ Working on {subject}…" if subject else "⚙️ Subtask in progress…") if english else (f"⚙️ 正在协作完成{subject}…" if subject else "⚙️ 子任务正在处理中…")
    else:
        text = (f"⚙️ Executing a step for {subject}…" if subject else "⚙️ Executing the current step…") if english else (f"⚙️ 正在执行{subject}的相关步骤…" if subject else "⚙️ 正在执行当前步骤…")
    recovery = info.get("recovery")
    if recovery:
        # This label is set only by a real later pre_tool_call on the same task.
        body = re.sub(r"^[^\w\u3400-\u9fff]+\s*", "", text)
        if english:
            text = "↪️ " + ("Trying another method: " if recovery == "alternative" else "Trying again: ") + body
        else:
            text = "↪️ " + ("换一种方式，" if recovery == "alternative" else "再次尝试，") + body
    return text


def failure_text(info, task, language):
    english = language == "en"
    subject = info.get("subject") or task
    if info.get("facts", {}).get("missing_file"):
        return "⚠️ The requested file was not found; preparing an explanation…" if english else "⚠️ 未找到指定文件，正在整理说明…"
    if info.get("status") == "cancelled":
        return LABELS[language]["tool_cancelled"]
    if not subject:
        return LABELS[language]["tool_error"]
    action = {"search": ("搜索", "search"), "read_web": ("读取", "read"),
              "read_data": ("读取", "read"), "read": ("读取", "read"),
              "inspect": ("检查", "inspect"), "test": ("测试", "test"),
              "calculate": ("计算", "calculate")}.get(info.get("stage"), ("执行", "process"))
    return f"⚠️ This attempt to {action[1]} {subject} did not succeed" if english else f"⚠️ 这次{action[0]}{subject}没有成功"


def result_text(info, task, language):
    status, facts = info.get("status"), info.get("facts", {})
    if status in {"error", "blocked", "cancelled"}:
        return failure_text(info, task, language)
    if status not in {"ok", "mixed"}:
        return ""
    subject = info.get("subject") or task
    english = language == "en"
    if facts.get("partial_failure"):
        return (f"⚠️ Some sources for {subject or 'this task'} failed; reviewing available results…" if english else f"⚠️ 部分{subject or '相关'}资料读取失败，正在整理已有结果…")
    fields = facts.get("weather_fields", ())
    if fields and re.search(r"天气|气温|预报|weather|forecast", task + " " + subject, re.I):
        names = {"temperature": ("温度", "temperature"), "humidity": ("湿度", "humidity"), "wind": ("风速", "wind speed")}
        observed = (", " if english else "、").join(names[name][english] for name in fields)
        return f"📊 Received {observed} data; reviewing {subject or 'the weather'}…" if english else f"📊 已获取{observed}数据，正在整理{subject or '天气信息'}…"
    if "search_count" in facts:
        count = facts["search_count"]
        if count == 0:
            return f"🔎 No results returned for {subject or 'this search'}" if english else f"🔎 这次搜索{subject}没有返回结果"
        return f"📊 Found {count} search results; reviewing {subject or 'the sources'}…" if english else f"📊 已找到 {count} 条搜索结果，正在整理{subject or '相关资料'}…"
    if facts.get("test_completed"):
        return "🧪 Test command completed; reviewing the result…" if english else "🧪 测试命令已执行完，正在整理执行结果…"
    if facts.get("read_completed") and info.get("stage") in {"read", "inspect", "read_data", "read_web", "read_guide"}:
        return f"📖 Read {subject or 'the requested material'}; reviewing its contents…" if english else f"📖 已读取{subject or '所需资料'}，正在梳理内容…"
    if facts.get("success") and info.get("stage") == "calculate":
        return f"🧮 Calculation completed; reviewing {subject or 'the result'}…" if english else f"🧮 已完成{subject or '本次'}计算，正在核对结果…"
    if facts.get("success") and info.get("stage") == "check_time":
        return f"🕒 Checked the date for {subject or 'this task'}; continuing to review sources…" if english else f"🕒 已核对{subject or '本任务'}所用的日期，继续整理资料…"
    if facts.get("success"):
        return f"📊 The current step completed; reviewing its result for {subject or 'this task'}…" if english else f"📊 当前步骤已完成，正在核对{subject or '本任务'}的结果…"
    return ""


def summary_text(turn, language, final=False):
    """An observed follow-up model request, not a claim about hidden reasoning."""
    partial = turn.progress.get("facts", {}).get("partial_failure")
    subject = summary_subject(turn.user_task or (turn.progress.get("subject", "") if partial else ""))
    if subject:
        if language == "en":
            return f"⚠️ Some sources could not be read; summarizing {subject}…" if partial else f"✍️ Summarizing {subject}…"
        verb = "总结" if re.search(r"代码|逻辑|插件|测试", subject) else "汇总" if "新闻" in subject else "整理"
        return f"⚠️ 部分资料读取失败，正在{verb}{subject}…" if partial else f"✍️ 正在{verb}{subject}…"
    if partial:
        return "⚠️ Some sources could not be read; reviewing available results…" if language == "en" else "⚠️ 部分资料读取失败，正在整理已有结果…"
    return LABELS[language]["finalizing"] if final else ("🤔 Reviewing the available information…" if language == "en" else "🤔 正在梳理已有信息…")


def note_text(turn, language):
    """An explicitly public model report, never treated as verified tool evidence."""
    action = turn.note.get("action")
    goal = turn.note.get("goal")
    if action and re.fullmatch(r"(?:正在)?(?:处理|思考|组织回复(?:内容)?|运行任务|使用工具|执行当前步骤)[。.!…]*|(?i:thinking|working|processing|using tools|preparing (?:a |the )?response)[.!…]*", action):
        return ""
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
    """Execution/result evidence outranks generic model activity.

    A short result hold is followed by a task-specific synthesis label only
    after a public model-request event. Display ticks never invent new work.
    """
    language = language if language in LABELS else "zh"
    phase, detail = turn.phase()
    if ending:
        phase = "finalizing" if ending == "ended" else ending
    info = turn.progress
    text = LABELS[language].get(phase, LABELS[language]["working"])
    clock = turn.touched if now is None else now
    if phase == "finalizing":
        text = failure_text(info, turn.user_task, language) if info.get("status") in {"error", "blocked"} else summary_text(turn, language, final=True)
    elif phase in {"tool_error", "tool_cancelled"}:
        text = failure_text(info, turn.user_task, language)
    elif not ending and phase in {"tool", "working", "api"}:
        if turn.current_kind == "tool":
            text = action_text(info, turn.user_task, language)
        else:
            text = note_text(turn, language) if turn.current_kind == "note" else ""
            if not text and info.get("status"):
                summarizing = turn.model_since >= turn.result_at and turn.model_since > 0 and clock - max(turn.result_at, turn.model_since) >= 3
                if info.get("status") in {"error", "blocked", "cancelled"}:
                    text = failure_text(info, turn.user_task, language)
                elif summarizing:
                    text = summary_text(turn, language)
                else:
                    text = result_text(info, turn.user_task, language)
                    if not text and info.get("status") == "ok":
                        subject = info.get("subject") or turn.user_task
                        text = (f"📊 Reviewing the result for {subject}…" if subject else "📊 Reviewing the current result…") if language == "en" else (f"📊 正在核对{subject}的执行结果…" if subject else "📊 正在核对当前结果…")
            if not text:
                text = note_text(turn, language)
            if not text and turn.current_kind != "initial" and turn.user_task and not re.fullmatch(r"[\d\s+*/().%=-]+(?:等于多少)?", turn.user_task):
                # No search/read claim until an actual tool starts. A model
                # request alone only justifies understanding the user's task.
                text = (f"🤔 Analyzing {turn.user_task}…" if language == "en" else f"🤔 正在分析{turn.user_task}…")
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
