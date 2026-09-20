"""Concise rendering of the latest meaningful public progress observation."""
import re

from .intelligence import safe_label

LABELS = {
    "zh": {
        "working": "🤔 思考中…", "api": "🤔 思考中…",
        "approval": "🔐 等待审批，请使用 Hermes 的审批消息",
        "smart": "🔐 正在评估审批",
        "tool_error": "⚠️ 这一步没有成功，等待后续处理",
        "tool_cancelled": "↩️ 这一步已取消",
        "api_error": "⚠️ 模型请求失败，等待 Hermes 后续处理",
        "approval_timeout": "⌛ 审批已超时", "approval_failed": "⚠️ 审批通知发送失败",
        "approval_cancelled": "↩️ 审批请求已撤回", "approval_denied": "🚫 审批未通过",
        "finalizing": "✍️ 整理回答…", "failed": "⚠️ 本轮运行异常结束",
        "interrupted": "⏹ 本轮运行已中断", "unknown_end": "清理临时状态…",
        "expired": "⌛ 状态更新已超时，请以 Hermes 后续回复为准",
    },
    "en": {
        "working": "🤔 Thinking…", "api": "🤔 Thinking…",
        "approval": "🔐 Awaiting approval — use the Hermes approval message",
        "smart": "🔐 Evaluating approval",
        "tool_error": "⚠️ This step did not succeed; awaiting further handling",
        "tool_cancelled": "↩️ This step was cancelled",
        "api_error": "⚠️ Model request failed; awaiting Hermes handling",
        "approval_timeout": "⌛ Approval timed out", "approval_failed": "⚠️ Approval notification failed",
        "approval_cancelled": "↩️ Approval request withdrawn", "approval_denied": "🚫 Approval denied",
        "finalizing": "✍️ Preparing the final answer…", "failed": "⚠️ Turn ended with an error",
        "interrupted": "⏹ Turn interrupted", "unknown_end": "Clearing temporary status…",
        "expired": "⌛ Status updates expired; see subsequent Hermes replies",
    },
}


def _zh_object(value):
    return (" " if re.match(r"[A-Za-z0-9]", value) else "") + value


def action_text(info, task, language):
    # The tool interpreter owns its safe object. A missing object must never
    # silently become the whole user request in this rendering layer.
    stage, subject = info.get("stage"), info.get("subject", "")
    english = language == "en"
    labels = {
        "search": ("🔎", "搜索", "Searching for", "", "information"),
        "read_web": ("📖", "阅读", "Reading", "", "web pages"),
        "read_data": ("📖", "读取", "Reading", "数据", "the requested data"),
        "read": ("📖", "读取", "Reading", "文件", "files"),
        "inspect": ("📖", "检查", "Inspecting", "代码", "code"),
        "read_guide": ("📖", "查阅", "Reading the guide for", "使用说明", "the current task"),
        "write": ("✏️", "修改", "Updating", "", "files"),
        "locate": ("🔍", "定位", "Locating", "", "relevant code"),
        "calculate": ("🧮", "计算", "Calculating", "", ""),
        "create": ("🎨", "生成", "Generating", "", "an image"),
        "delegate": ("⚙️", "协作处理", "Working on", "子任务", "a subtask"),
        "execute": ("⚙️", "执行当前步骤", "Executing the current step", "", ""),
    }
    if stage == "test":
        text = "🧪 Running project tests…" if english else "🧪 运行相关测试…"
    elif stage == "convert_time":
        text = "🕒 Converting timestamps and time zones…" if english else "🕒 换算时间…"
    elif stage == "check_time":
        text = "🕒 Checking the current date…" if english else "🕒 核对当前日期…"
    else:
        emoji, chinese, verb, fallback, english_fallback = labels.get(stage, labels["execute"])
        obj = subject or (english_fallback if english else fallback)
        text = f"{emoji} {verb}{' ' + obj if obj else ''}…" if english else f"{emoji} {chinese}{_zh_object(obj)}…"
    recovery = info.get("recovery")
    if recovery:
        # Set only after a real subsequent tool action, never from a timer.
        body = re.sub(r"^[^\w\u3400-\u9fff]+\s*", "", text)
        text = "↪️ " + (("Trying another method: " if recovery == "alternative" else "Trying again: ") if english else ("换一种方式，" if recovery == "alternative" else "再次尝试，")) + body
    return text


def failure_text(info, task, language):
    english = language == "en"
    subject = info.get("subject", "")
    if info.get("facts", {}).get("missing_file"):
        return "⚠️ The requested file was not found; preparing an explanation…" if english else "⚠️ 未找到指定文件，整理说明…"
    if info.get("status") == "cancelled":
        return LABELS[language]["tool_cancelled"]
    if not subject:
        return LABELS[language]["tool_error"]
    action = {"search": ("搜索", "search"), "read_web": ("读取", "read"),
              "read_data": ("读取", "read"), "read": ("读取", "read"),
              "inspect": ("检查", "inspect"), "test": ("测试", "test"),
              "calculate": ("计算", "calculate")}.get(info.get("stage"), ("执行", "process"))
    return f"⚠️ This attempt to {action[1]} {subject} did not succeed" if english else f"⚠️ 这次{action[0]}{_zh_object(subject)}没有成功"


def result_text(info, task, language):
    status, facts = info.get("status"), info.get("facts", {})
    if status in {"error", "blocked", "cancelled"}:
        return failure_text(info, task, language)
    if status not in {"ok", "mixed"}:
        return ""
    subject = info.get("subject", "")
    english = language == "en"
    if facts.get("partial_failure"):
        return "⚠️ Some sources could not be read; reviewing available results…" if english else "⚠️ 部分资料读取失败，核对已有结果…"
    fields = facts.get("weather_fields", ())
    if fields and re.search(r"天气|气温|预报|weather|forecast", task + " " + subject, re.I):
        names = {"temperature": ("温度", "temperature"), "humidity": ("湿度", "humidity"), "wind": ("风速", "wind speed")}
        observed = (", " if english else "、").join(names[name][english] for name in fields)
        return f"📊 Received {observed} data; reviewing the data…" if english else f"📊 已获取{observed}数据，继续核对…"
    if "search_count" in facts:
        count = facts["search_count"]
        if count == 0:
            return "🔎 No results returned for this search" if english else "🔎 这次搜索没有返回结果"
        return f"📊 Found {count} search results; reviewing the sources…" if english else f"📊 找到 {count} 条结果，继续核对…"
    if facts.get("test_completed"):
        return "🧪 Test command completed; reviewing the result…" if english else "🧪 测试命令已执行完，核对结果…"
    if facts.get("read_completed") and info.get("stage") in {"read", "inspect", "read_data", "read_web", "read_guide"}:
        return f"📖 Read {subject or 'the requested material'}; reviewing its contents…" if english else f"📖 已读取{_zh_object(subject or '所需资料')}，继续核对…"
    if facts.get("success") and info.get("stage") == "calculate":
        return "🧮 Calculation completed; reviewing the result…" if english else "🧮 计算已完成，核对结果…"
    if facts.get("success") and info.get("stage") == "convert_time":
        return "🕒 Time conversion executed; reviewing the result…" if english else "🕒 时间换算已执行，核对结果…"
    if facts.get("success") and info.get("stage") == "check_time":
        return "🕒 Checked the current date; continuing the task…" if english else "🕒 已核对当前日期，继续处理…"
    if facts.get("success"):
        return "📊 The current step completed; reviewing its result…" if english else "📊 当前步骤已完成，核对结果…"
    return ""


def summary_text(turn, language, final=False):
    """Final rendering is justified only by an explicit public end event."""
    if turn.progress.get("facts", {}).get("partial_failure"):
        return "⚠️ Some sources could not be read; reviewing available results…" if language == "en" else "⚠️ 部分资料读取失败，整理已有结果…"
    return LABELS[language]["finalizing"] if final else LABELS[language]["working"]


def _note_body(value):
    value = safe_label(value, 72)
    value = re.sub(r"^(?:我(?:目前|现在)?(?:正在|在)|目前正在|现在正在|正在)\s*", "", value)
    value = re.sub(r"(?i)^(?:i(?:['’]m| am)\s+|currently\s+|now\s+)+", "", value)
    return value.strip(" 。.!…")


def _fingerprint(value):
    return re.sub(r"\s+", "", _note_body(value)).casefold()


def note_fingerprint(note):
    """Narrow equivalence: formatting/prefix changes, never fuzzy topic matching."""
    return tuple((key, _fingerprint(note[key])) for key in ("action", "finding", "next") if note.get(key))


def _completed_action(text):
    """Reject outcome clauses while allowing checks of completed objects."""
    direct = (
        r"^(?:核对|核验|组装|比较|对比|区分|对照|对齐|比对|交叉核对|交叉验证|追踪|检查|验证|阅读|读取|分析|计算|测试|整理)(?:工作)?(?:已|已经)?(?:完成|完毕|结束)(?=$|[，,；;：:。.!])"
        r"|[，,；;：:]\s*(?:已经|已完成|已确认|已核实|找到|发现|确认了|确定.*(?:一致|无误|成功))"
        r"|[，,；;：:]\s*(?:(?:发布|上线|上市)?(?:日期|时间)(?:为|是))"
        r"|(?i:^(?:checking|comparing|verifying|testing|reviewing|reading|analysis|calculation)\s+(?:is\s+)?(?:complete|completed|done|finished)(?=$|[\s]*[,;:.!]))"
        r"|(?i:[,;:]\s*(?:(?:the\s+)?release(?:\s+date)?\s+(?:is|was)\b|found\b|confirmed\b))"
    )
    if re.search(direct, text):
        return True
    completion = (
        r"(?:已经|已)(?:确认|核实|验证|完成)$"
        r"|(?i:\b(?:is|are|was|were|has been|have been)\s+(?:already\s+)?(?:confirmed|verified|completed|finished)\b)"
    )
    # "Check whether orders are completed" describes an open verification,
    # unlike the declarative "the orders are completed".
    return any(re.search(completion, clause) and not re.search(r"是否|是不是|(?i:\b(?:whether|if)\b)", clause)
               for clause in re.split(r"[，,；;：:]", text))


def _classification_action(text):
    """Recognize a bounded 把-object classification action, not arbitrary prose."""
    match = re.fullmatch(
        r"把(?P<object>[^，,。；;：:!?！？]{2,36}?)(?:按(?P<criterion>[^，,。；;：:!?！？]{2,36}?))?"
        r"(?:归类|分类)(?:[，,]并(?:统一)?(?:换算|核对|比较|检查|筛选|整理)[^，,。；;：:!?！？]{2,32})?", text)
    if not match:
        return False
    subject = re.sub(r"^(?:(?:这些|那些|全部|所有|当前|本次|相关|上述|需要处理的)\s*)+", "", match.group("object"))
    subject = re.sub(r"(?:进行|重新|再次)$", "", subject)
    criterion = match.group("criterion") or ""
    generic = {"事情", "东西", "信息", "资料", "数据", "内容", "结果", "任务", "工作", "问题", "它们"}
    if subject in generic and (not criterion or criterion in {"类别", "类型", "情况", "需要", "结果", "要求"}):
        return False
    # Completed records can be classified; a clause claiming that a result is
    # already confirmed cannot be smuggled in as the classification object.
    claim = r"(?:已经|已)(?:完成|确认|核实|验证|对齐)(?:后|因此|所以)?$"
    return not any(_completed_action(part) or re.search(claim, part) for part in (subject, criterion))


def meaningful_note(note, task=""):
    """Require a concrete stage, not a goal restatement or activity filler.

    Finding evidence is checked by the model before calling this function. This
    helper only normalizes public text and checks its information content.
    """
    if not isinstance(note, dict):
        return {}
    result = {key: body for key in ("action", "finding", "next") if (body := _note_body(note.get(key)))}
    generic = re.compile(r"^(?:(?:继续|补充|准备|开始|重新|再次|尝试|逐一)\s*)?(?:处理(?:你的|这个)?(?:问题|任务|工作)?|思考(?:中)?|组织回复(?:内容)?|运行任务|使用工具|执行当前步骤|工作|整理(?:回答|回复|结果)|分析(?:问题|任务)?|搜索|阅读|核对|核验|组装|检查|比较|区分|对照|对齐|比对|交叉核对|交叉验证|追踪|验证|归纳|总结|查找|筛选)$|^(?i:thinking|working|processing(?: (?:the |your )?(?:request|task|problem))?|using tools|continuing(?: the task)?|preparing (?:a |the )?response|organizing (?:the )?response|reviewing (?:the )?(?:results|information)|searching|reading|checking|comparing|analyzing)$")
    task_key = _fingerprint(task)
    for key in ("action", "next"):
        text = result.get(key, "")
        # Strip analysis/processing framing only when checking repetition; a
        # concrete new object is required to establish an informative stage.
        object_text = re.sub(r"^(?:分析|处理|了解|研究)\s*|^(?i:analyzing|processing|understanding)\s+", "", text)
        stage_action = re.match(r"^(?:(?:继续|补充|准备|开始|重新|再次|尝试|逐一)\s*)?(?:搜索|查找|查询|核对|核验|组装|比较|对比|区分|对照|对齐|比对|交叉核对|交叉验证|追踪|确认|验证|筛选|整理|归纳|总结|汇总|阅读|读取|查阅|检查|定位|测试|运行|执行|计算|统计|修改|修复|编辑|生成|绘制|调查|研究|分析|排查|梳理|提取|清理|换|改用|协作|检索|审查|评估|匹配|合并|复核)|^(?i:(?:(?:continue|continuing|prepare|preparing|start|starting|now)\s+(?:to\s+)?)?(?:search|look|check|compar|verif|confirm|filter|select|review|summar|organiz|organis|synthes|read|inspect|locat|test|run|execut|calculat|comput|updat|edit|fix|generat|draw|investigat|research|analyz|analys|debug|extract|clean|retry|trying|reconcil|validat|cross[ -](?:check|referenc)|assess|triag))", text)
        completion = re.match(r"^(?:已经|已完成|已确认|找到|发现|确认了)|^(?i:found|confirmed|verified|completed|finished)\b", text)
        if not text or not (stage_action or _classification_action(text)) or generic.fullmatch(text) or completion or _completed_action(text) or (task_key and _fingerprint(object_text) == task_key):
            result.pop(key, None)
    return result


def _note_icon(action):
    if re.match(r"换|改用|再次|重新|(?i:retry|trying another)", action):
        return "↪️"
    if re.search(r"日期|时间|发布日|(?i:\bdate|timeline|release time)", action) and re.match(r"核对|比较|对比|对照|对齐|比对|交叉核对|交叉验证|确认|验证|(?i:check|compar|verif|confirm)", action):
        return "🕒"
    patterns = (
        (r"(?:补充)?(?:搜索|查找|查询)|(?i:search|look for|look up)", "🔎"),
        (r"定位|查找.*代码|(?i:locat)", "🔍"),
        (r"读取|阅读|查阅|检查.*代码|核对.*(?:来源|公告|资料)|(?i:read|inspect)", "📖"),
        (r"计算|统计|(?i:calculat|comput)", "🧮"),
        (r"(?:运行|执行)?.*测试|(?i:(?:run|execut).*test|test)", "🧪"),
        (r"修改|修复|编辑|(?i:updat|edit|fix)", "✏️"),
        (r"生成|绘制|(?i:generat|draw)", "🎨"),
        (r"整理|归纳|总结|汇总|(?i:summariz|summaris|organiz|organis|synthesiz|synthesis)", "✍️"),
    )
    return next((icon for pattern, icon in patterns if re.match(pattern, action)), "📝")


def note_text(turn, language):
    note = turn.note
    if note.get("action"):
        action = _note_body(note["action"])
        return f"{_note_icon(action)} {action}…"
    if note.get("next"):
        return ("↪️ Next: " if language == "en" else "↪️ 接下来：") + _note_body(note["next"]) + "…"
    if note.get("finding"):
        # Only allowlisted findings matched to current tool evidence survive
        # model acceptance; this is never arbitrary assistant prose.
        return "📝 " + note["finding"].rstrip("。.!…") + "…"
    return ""


def status_text(turn, language, ending=None, now=None):
    """Render the selected observation; clocks and API requests add no work."""
    language = language if language in LABELS else "zh"
    phase, _ = turn.phase()
    if ending:
        phase = "finalizing" if ending == "ended" else ending
    info = turn.progress
    text = LABELS[language].get(phase, LABELS[language]["working"])
    if phase == "finalizing":
        text = failure_text(info, "", language) if info.get("status") in {"error", "blocked"} else summary_text(turn, language, final=True)
    elif phase in {"tool_error", "tool_cancelled"}:
        text = failure_text(info, "", language)
    elif not ending and phase in {"tool", "working", "api"}:
        source = turn.display_kind
        if source == "note":
            text = note_text(turn, language) or LABELS[language]["working"]
        elif source == "tool":
            text = action_text(info, "", language)
        elif source == "result":
            # The callback establishes return, not success or available data.
            text = result_text(info, turn.user_task, language) or ("📊 Tool returned; reviewing its result…" if language == "en" else "📊 已收到执行结果，继续核对…")
        else:
            text = LABELS[language]["working"]
    limit = 110 if language == "en" else 60
    if len(text) > limit:
        shortened = text[:limit - 1].rstrip(" ，,。.!…")
        if language == "en" and " " in shortened[int(limit * .65):]:
            shortened = shortened.rsplit(" ", 1)[0]
        text = shortened + "…"
    return text
