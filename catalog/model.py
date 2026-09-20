"""Bounded public-event observations; only safe summaries survive a callback.

Tool execution and results remain owned by Hermes. We retain neither commands,
file contents, provider text nor hidden reasoning. A started action owns its
status until a newer action starts; late completions cannot rewind that status.
"""
from dataclasses import dataclass, field
import json
import math
import re
import shlex
from urllib.parse import urlsplit

from .experience import TOOL, normalize_note


def identity(value):
    return value if isinstance(value, str) and 0 < len(value) <= 512 else ""


def tool_label(value):
    return value if isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9_.:-]{1,64}", value) else "tool"


def safe_text(value, limit=72):
    """Conservative public label, not a general-purpose secret-redaction system."""
    if not isinstance(value, str) or len(value) > 8000:
        return ""
    if re.search(r"(?i)<\s*/?\s*(?:think|thinking|analysis|reasoning)\b|chain.of.thought|隐藏思考|思维链|```|~~~|MEDIA:|NO_REPLY", value):
        return ""
    if re.search(r"(?i)(?:api[_ -]?key|access[_ -]?token|token|password|passwd|secret|authorization|cookie)\s*[:：=]|\bBearer\s+|\b(?:sk|ghp|github_pat|xox[baprs])[-_][\w-]+|\b\d{6,}:[A-Za-z0-9_-]{20,}|\b[A-Za-z0-9_=-]{28,}\b", value):
        return ""
    # Never echo a URL, URL query, full path, shell/code or markup into the bubble.
    value = re.sub(r"https?://[^\s<>]+|(?:[A-Za-z]:[\\/]|~/|/)[^\s，。；,;]+", " ", value)
    value = re.sub(r"[\x00-\x1f\x7f\u200b-\u200f\u202a-\u202e\u2066-\u2069]", " ", value)
    value = " ".join(value.split()).strip(" \"'`，。！？,.!?：:；;")
    if re.search(r"[<>{}\[\]`$\\]|(?:^|\s)[A-Za-z_][A-Za-z0-9_]*=", value):
        return ""
    return value[:limit].rstrip()


def task_subject(value):
    """A small grammatical reduction, not an LLM or an inferred work plan."""
    text = safe_text(value, 300)
    if not text:
        return ""
    text = re.sub(r"(?i)^(?:(?:please|can you|could you|would you|help me)\s+)+", "", text)
    text = re.sub(r"(?i)^(?:look up|look for|search for|find|investigate|check|read|analyze)\s+", "", text)
    text = re.sub(r"^(?:(?:请|麻烦|能不能|可以|你|帮我|给我|一下|先|帮忙)\s*)+", "", text)
    text = re.sub(r"^(?:查一下|查查|查询|查找|搜索|调查|找一下|看看|检查|分析|了解|研究|帮我)\s*", "", text)
    text = re.sub(r"^(?:一下|这个项目(?:里)?|项目里)\s*", "", text)
    # Remove requests for secondary advice rather than attaching an entire question.
    text = re.split(r"[，,。；;！!？?]|然后|尤其|顺便|并且|看看(?:温度|湿度|风速)|我出门", text, maxsplit=1)[0]
    text = re.sub(r"(?:怎么样|如何|有什么重要新闻|有什么新闻|要穿什么|帮我看看.*)$", lambda m: "重要新闻" if "新闻" in m.group() else "", text)
    text = re.sub(r"(?<=\D)(\d+)\s*天", r" \1 天", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:64]


def file_subject(value):
    if not isinstance(value, str) or len(value) > 2048:
        return ""
    name = value.replace("\\", "/").rsplit("/", 1)[-1]
    if name.startswith(".") or re.search(r"(?i)secret|credential|token|password|\.pem$|\.key$|\.env", name):
        return ""
    return safe_text(name, 48) if re.fullmatch(r"[\w .-]{1,64}", name) else ""


def host_subject(value):
    if not isinstance(value, str) or len(value) > 2048:
        return ""
    try:
        host = urlsplit(value).hostname or ""
        # A hostname is enough for a partial label; never retain userinfo/query/path.
        return safe_text(host, 60) if re.fullmatch(r"[A-Za-z0-9.-]+", host) else ""
    except ValueError:
        return ""


def shell_stage(command, depth=0):
    if not isinstance(command, str) or len(command) > 8000 or depth > 2:
        return "execute"
    try:
        tokens = shlex.split(command)
    except ValueError:
        return "execute"
    segments, segment = [], []
    for token in tokens + [";"]:
        if token and all(char in ";&|" for char in token):
            if segment:
                segments.append(segment)
            segment = []
        else:
            segment.append(token)
    stages = []
    for words in segments[:12]:
        while words and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=.*", words[0]):
            words = words[1:]
        if not words:
            continue
        exe = words[0].rsplit("/", 1)[-1]
        rest = words[1:]
        if exe in {"bash", "sh", "zsh"} and len(rest) == 2 and rest[0] in {"-c", "-lc"}:
            stages.append(shell_stage(rest[1], depth + 1))
        elif exe == "uv" and rest[:1] == ["run"]:
            stages.append(shell_stage(shlex.join(rest[1:]), depth + 1))
        elif exe in {"pytest", "py.test"} or (re.fullmatch(r"python(?:\d(?:\.\d+)?)?", exe) and rest[:1] == ["-m"] and rest[1:2] in (["pytest"], ["unittest"])):
            stages.append("test")
        elif (exe in {"npm", "pnpm", "yarn", "cargo", "go", "dotnet"} and rest[:1] == ["test"]) or (exe == "node" and rest[:1] == ["--test"]):
            stages.append("test")
        elif exe in {"rg", "grep", "find"}:
            stages.append("locate")
        elif exe in {"cat", "head", "tail", "sed"}:
            stages.append("read")
        elif exe != "cd":
            stages.append("execute")
    # Mixed operations do not prove a particular substep is currently executing.
    return stages[0] if stages and len(set(stages)) == 1 else "execute"


def tool_context(name, args, task):
    args = args if isinstance(args, dict) else {}
    stage, subject = "execute", ""
    if name in {"web_search", "web.search", "web.search_query", "search_web"}:
        stage = "search"
        subject = task_subject(args.get("query") or args.get("q"))
    elif name in {"web_extract", "web.extract", "browse", "browser_navigate"}:
        stage = "read_web"
        urls = args.get("urls")
        subject = host_subject(args.get("url") or (urls[0] if isinstance(urls, list) and urls else None))
        if task:
            subject = task
    elif name in {"read_file", "write_file", "patch", "edit_file"}:
        stage = "read" if name == "read_file" else "write"
        subject = file_subject(args.get("path") or args.get("file_path"))
        if ("Telegram" in task or "telegram" in task) and re.search(r"状态|消息|删除|清理", task) and re.search(r"(?i)telegram|adapter|message|runtime|progress", subject):
            subject = "Telegram 状态消息处理代码"
    elif name in {"search_files", "grep"}:
        stage = "locate"
        subject = safe_text(args.get("pattern"), 48)
        if subject and re.search(r"delete|cleanup|清理|删除", subject, re.I) and re.search(r"Telegram|telegram", task):
            subject = "Telegram 状态消息清理逻辑"
    elif name in {"terminal", "exec_command", "execute_command"}:
        stage = shell_stage(args.get("command") or args.get("cmd"))
        subject = ""
    elif name in {"calculator", "calculate"}:
        stage = "calculate"
    elif name in {"image_generate", "generate_image"}:
        stage = "create"
        subject = task
    elif name == "delegate_task":
        stage = "delegate"
        subject = task_subject(args.get("goal") or args.get("task"))
    return {"stage": stage, "subject": subject}


def result_object(result):
    if isinstance(result, dict):
        return result
    if isinstance(result, str) and len(result) <= 131072:
        try:
            value = json.loads(result)
            return value if isinstance(value, dict) else {}
        except (ValueError, RecursionError):
            pass
    return {}


def numeric_values(value):
    values = value if isinstance(value, list) else [value]
    return bool(values) and len(values) <= 1000 and all(type(item) is int or (type(item) is float and math.isfinite(item)) for item in values)


def result_facts(result, stage):
    """Only recognized structural evidence, never prose or requested field names."""
    obj = result_object(result)
    facts = {}
    failed = obj.get("success") is False or obj.get("ok") is False or obj.get("isError") is True or bool(obj.get("error")) or obj.get("status") in ("error", "failed")
    exit_code = obj.get("exit_code")
    if isinstance(exit_code, int) and not isinstance(exit_code, bool) and exit_code != 0:
        failed = True
    if failed:
        return {"failed": True}
    if stage == "search":
        data = obj.get("data")
        entries = data.get("web") if isinstance(data, dict) else None
        if entries is None:
            entries = obj.get("results")
        if isinstance(entries, list) and len(entries) <= 1000 and all(isinstance(item, dict) and isinstance(item.get("title"), str) and bool(item.get("title")) and isinstance(item.get("url"), str) and item.get("url", "").startswith(("https://", "http://")) for item in entries):
            facts["search_count"] = len(entries)
    # Common structured weather API objects; string snippets and *_units are not data.
    nodes = [obj]
    for key in ("data", "daily", "hourly", "current", "forecast"):
        if isinstance(obj.get(key), dict):
            nodes.append(obj[key])
    if isinstance(obj.get("data"), dict):
        nodes.extend(obj["data"][key] for key in ("daily", "hourly", "current", "forecast") if isinstance(obj["data"].get(key), dict))
    fields = set()
    for node in nodes:
        for key, value in list(node.items())[:80]:
            if isinstance(key, str) and numeric_values(value):
                if re.fullmatch(r"temperature(?:_2m)?(?:_(?:min|max|mean))?|temp", key):
                    fields.add("temperature")
                elif re.fullmatch(r"(?:relative_)?humidity(?:_2m)?(?:_(?:min|max|mean))?", key):
                    fields.add("humidity")
                elif re.fullmatch(r"wind(?:_?speed)?(?:_10m)?(?:_(?:min|max|mean))?", key):
                    fields.add("wind")
    if fields:
        facts["weather_fields"] = tuple(key for key in ("temperature", "humidity", "wind") if key in fields)
    if stage == "test" and type(exit_code) is int and exit_code == 0:
        facts["test_completed"] = True  # Process completed, not a claim that all tests passed.
    return facts


@dataclass
class Turn:
    session_id: str
    turn_id: str
    touched: float
    tools: dict = field(default_factory=dict)
    apis: dict = field(default_factory=dict)
    approvals: dict = field(default_factory=dict)
    interims: set = field(default_factory=set)
    last: str = "working"
    capped: bool = False
    started: float = 0.0
    preferences: dict = field(default_factory=dict)
    note: dict = field(default_factory=dict)
    children: dict = field(default_factory=dict)
    retries: int = 0
    user_task: str = ""
    observations: dict = field(default_factory=dict)
    progress: dict = field(default_factory=dict)
    note_calls: dict = field(default_factory=dict)
    revision: int = 0
    current_call: str = ""
    current_request: str = ""
    current_kind: str = "initial"
    iteration: int = -1
    finalizing: bool = False

    def __post_init__(self):
        self.started = self.touched
        self.set_task(self.user_task)

    def set_task(self, text):
        # The public pre_llm_call user_message may contain multimodal blocks.
        # Select only explicit user text; never inspect image/reasoning payloads.
        if isinstance(text, list):
            text = " ".join(block["text"][:1000] for block in text[:32] if isinstance(block, dict) and block.get("type") == "text" and isinstance(block.get("text"), str))
        self.user_task = task_subject(text)

    def put(self, bucket, key, value):
        if not key:
            return False
        if key not in bucket and sum(map(len, (self.tools, self.apis, self.approvals, self.interims, self.children, self.note_calls))) >= 512:
            self.capped = True
            return False
        bucket[key] = value
        return True

    def observe(self, event, data, now):
        if self.finalizing:
            return
        self.touched = now
        if data.get("tool_name") == TOOL and event in {"pre_tool_call", "post_tool_call"}:
            note_call = identity(data.get("tool_call_id"))
            if event == "pre_tool_call" and note_call not in self.note_calls:
                self.put(self.note_calls, note_call, self.revision)
            expected = self.note_calls.get(note_call)
            if event == "post_tool_call" and data.get("status") == "ok" and (expected == self.revision or (expected is None and self.current_kind == "initial")):
                self.put(self.note_calls, note_call, -1)
                note = normalize_note(data.get("args"))
                self.note = {key: text for key in ("goal", "action", "finding", "next") if (text := safe_text(note.get(key)))}
                if self.note and self.current_kind != "tool":
                    self.current_kind = "note"
            return
        if event in {"subagent_start", "subagent_stop"}:
            child = identity(data.get("child_session_id"))
            status = "running" if event == "subagent_start" else data.get("child_status")
            status = status if status in {"running", "completed", "failed", "interrupted", "error"} else "ended"
            if event != "subagent_start" or child not in self.children:
                self.put(self.children, child, status)
            return
        call, request = identity(data.get("tool_call_id")), identity(data.get("api_request_id"))
        if event == "pre_tool_call":
            if call in self.tools or not self.put(self.tools, call, (tool_label(data.get("tool_name")), "running")):
                return
            self.observations[call] = tool_context(tool_label(data.get("tool_name")), data.get("args"), self.user_task or task_subject(self.note.get("goal")))
            self.progress = self.observations[call]
            self.note = {}
            self.revision += 1
            self.current_call, self.current_kind, self.last = call, "tool", "working"
        elif event == "post_tool_call":
            old = self.tools.get(call)
            if old and old[1] != "running":
                return
            name = old[0] if old else tool_label(data.get("tool_name"))
            info = self.observations.get(call) or tool_context(name, data.get("args"), self.user_task)
            facts = result_facts(data.get("result"), info["stage"])
            status = data.get("status")
            status = status if status in ("ok", "error", "blocked", "cancelled") else "returned"
            if status == "ok" and facts.get("failed"):
                status = "error"
            if not self.put(self.tools, call, (name, status)):
                return
            info = dict(info, status=status, facts=facts if status == "ok" else {})
            self.observations[call] = info
            if (call == self.current_call and self.current_kind == "tool") or self.current_kind == "initial":
                self.progress = info
                self.current_call, self.current_kind = call, "result"
                self.last = "tool_error" if status in {"error", "blocked"} else "tool_cancelled" if status == "cancelled" else "working"
        elif event == "pre_api_request":
            if request in self.apis or not self.put(self.apis, request, "running"):
                return
            if self.current_kind == "tool":
                self.progress = {}
            self.revision += 1
            self.current_request, self.current_kind, self.last = request, "api", "working"
            count = data.get("api_call_count")
            if type(count) is int:
                self.iteration = max(self.iteration, count)
            retry = data.get("retry_count", 0)
            if type(retry) is int and 0 <= retry <= 100:
                self.retries = retry
        elif event in {"post_api_request", "api_request_error"}:
            if self.apis.get(request) in {"ok", "error"}:
                return
            if not self.put(self.apis, request, "ok" if event == "post_api_request" else "error"):
                return
            if request == self.current_request and self.current_kind in {"api", "stream", "note"}:
                self.last = "api_error" if event == "api_request_error" else "working"
                if event == "post_api_request":
                    message = data.get("assistant_message")
                    # Observe shape only. Content, reasoning and final answer are never copied.
                    self.current_kind = "working" if isinstance(message, dict) and message.get("tool_calls") else "generating"
        elif event == "pre_approval_request":
            # Approval observers can arrive after the tool or after its response.
            # Neither event may resurrect a settled call's waiting/error state.
            if call in self.tools and self.tools[call][1] != "running":
                return
            if call not in self.approvals:
                self.put(self.approvals, call, "smart" if data.get("surface") == "smart" else "pending")
        elif event == "post_approval_response":
            if call in self.tools and self.tools[call][1] != "running":
                return
            if call in self.approvals and self.approvals[call] not in {"pending", "smart"}:
                return
            choice = data.get("choice")
            choices = {"once", "session", "always", "deny", "timeout", "cancelled", "notify_failed", "smart_approve", "smart_deny"}
            if self.put(self.approvals, call, choice if isinstance(choice, str) and choice in choices else "unknown") and (self.current_kind != "tool" or call == self.current_call):
                self.last = {"timeout": "approval_timeout", "notify_failed": "approval_failed", "cancelled": "approval_cancelled", "deny": "approval_denied", "smart_deny": "approval_denied"}.get(choice, "working")
        elif event in {"on_stream_start", "on_stream_delta", "on_stream_end"}:
            count = data.get("iteration")
            if type(count) is not int or count != self.iteration or self.current_kind not in {"api", "stream"}:
                return
            if event == "on_stream_delta" and data.get("kind") != "text":
                return
            # Text may belong to an intermediate tool iteration. Never call it a final answer.
            self.current_kind = "stream"
        elif event == "on_interim_message":
            count = data.get("iteration")
            if type(count) is int and count not in self.interims:
                if sum(map(len, (self.tools, self.apis, self.approvals, self.interims, self.children, self.note_calls))) < 512:
                    self.interims.add(count)
                else:
                    self.capped = True
            # No raw text: asynchronous interim notifications may arrive after newer tools.
        elif event == "post_llm_call":
            self.finalizing = True
            self.current_kind, self.last = "finalizing", "finalizing"

    def phase(self):
        if self.finalizing:
            return "finalizing", ""
        active_approvals = [status for call, status in self.approvals.items() if call not in self.tools or self.tools[call][1] == "running"]
        if "pending" in active_approvals:
            return "approval", ""
        if "smart" in active_approvals:
            return "smart", ""
        if self.last in {"approval_timeout", "approval_failed", "approval_cancelled", "approval_denied", "tool_error", "tool_cancelled", "api_error"}:
            return self.last, ""
        if self.current_kind == "tool":
            return "tool", self.tools.get(self.current_call, ("tool", ""))[0]
        if self.current_kind in {"api", "stream", "generating"}:
            return "api", ""
        return "working", ""

    def counts(self):
        return len(self.tools), len(self.apis), sum(status in {"error", "blocked"} for _, status in self.tools.values())
