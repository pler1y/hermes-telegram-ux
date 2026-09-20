"""Bounded public-event observations; only safe summaries survive a callback.

Tool execution and results remain owned by Hermes. We retain neither commands,
file contents, provider text nor hidden reasoning. A started action owns its
status until a newer action starts; late completions cannot rewind that status.
"""
from dataclasses import dataclass, field
import re

from .experience import TOOL, normalize_note
from .intelligence import task_subject, tool_context, result_facts, shell_stage


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
    if re.search(r"(?i)\b(?:site|inurl|intitle|filetype|before|after):|\b(?:AND|OR)\b", value):
        return ""
    # Never echo a URL, URL query, full path, shell/code or markup into the bubble.
    value = re.sub(r"https?://[^\s<>]+|(?:[A-Za-z]:[\\/]|~/|/)[^\s，。；,;]+", " ", value)
    value = re.sub(r"[\x00-\x1f\x7f\u200b-\u200f\u202a-\u202e\u2066-\u2069]", " ", value)
    value = " ".join(value.split()).strip(" \"'`，。！？,.!?：:；;")
    if re.search(r"[<>{}\[\]`$\\]|(?:^|\s)[A-Za-z_][A-Za-z0-9_]*=", value):
        return ""
    return value[:limit].rstrip()



@dataclass
class Turn:
    session_id: str
    turn_id: str
    touched: float
    tools: dict = field(default_factory=dict)
    apis: dict = field(default_factory=dict)
    api_attempts: dict = field(default_factory=dict)
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
    result_at: float = 0.0
    model_since: float = 0.0
    last_failure: dict = field(default_factory=dict)

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

    def merge_source_batch(self):
        """Summarize mixed source outcomes without changing any tool outcome.

        Only the just-finished public API batch and the same safe task object
        participate. A successful clock/process call is not successful research.
        """
        subject = self.progress.get("subject")
        if not subject or self.progress.get("batch") != self.current_request:
            return
        sources = {"search", "read_web", "read_data", "read", "inspect"}
        outcomes = [item for item in self.observations.values()
                    if item.get("batch") == self.current_request
                    and item.get("subject") == subject and item.get("stage") in sources]
        succeeded = any(item.get("status") == "ok"
                        and (item.get("facts", {}).get("read_completed")
                             or (item.get("stage") == "search"
                                 and type(item.get("facts", {}).get("search_count")) is int
                                 and item["facts"]["search_count"] > 0))
                        for item in outcomes)
        failed = any(item.get("status") in {"error", "blocked"}
                     or item.get("facts", {}).get("partial_failure") for item in outcomes)
        if succeeded and failed:
            # This display record represents the batch. The original failure
            # remains in tools/observations and is never relabelled successful.
            self.progress = dict(self.progress, status="mixed", facts={"partial_failure": True})
            self.last = "working"

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
            name = tool_label(data.get("tool_name"))
            info = tool_context(name, data.get("args"), self.user_task or task_subject(self.note.get("goal")))
            info = dict(info, tool=name, batch=self.current_request)
            previous = self.last_failure
            # A recovery label is permitted only once a real subsequent action
            # on the same object starts, never merely when a model is requested.
            related = {"search", "read_web", "read_data", "read", "inspect", "locate", "execute"}
            if previous and previous.get("subject") == info.get("subject") and info.get("subject") and previous.get("stage") in related and info.get("stage") in related:
                info["recovery"] = "alternative" if previous.get("tool") != name else "retry"
            self.last_failure = {}
            self.observations[call] = info
            self.progress = info
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
            # Negative facts (notably file absence) are evidence too. Never
            # retain positive result facts when the host reports a failed call.
            if status != "ok":
                facts = {key: value for key, value in facts.items() if key in {"failed", "missing_file"}}
            info = dict(info, status=status, facts=facts)
            if status in {"error", "blocked"} and info.get("batch", "") == self.current_request:
                self.last_failure = info
            self.observations[call] = info
            if (call == self.current_call and self.current_kind == "tool") or self.current_kind == "initial":
                self.progress = info
                self.result_at = now
                self.current_call, self.current_kind = call, "result"
                self.last = "tool_error" if status in {"error", "blocked"} else "tool_cancelled" if status == "cancelled" else "working"
        elif event == "pre_api_request":
            retry = data.get("retry_count", 0)
            retry = retry if type(retry) is int and 0 <= retry <= 100 else 0
            if request in self.apis and retry <= self.api_attempts.get(request, 0):
                return
            if not self.put(self.apis, request, "running"):
                return
            self.api_attempts[request] = retry
            if self.current_kind == "tool":
                # A new model cycle without a matching result cannot prove the
                # old operation completed. Late callbacks must not rewind it.
                self.progress = {}
            else:
                self.merge_source_batch()
            self.revision += 1
            self.model_since = now
            self.current_request, self.current_kind = request, "api"
            if self.last not in {"tool_error", "tool_cancelled"}:
                self.last = "working"
            count = data.get("api_call_count")
            if type(count) is int:
                self.iteration = max(self.iteration, count)
            retry = data.get("retry_count", 0)
            if type(retry) is int and 0 <= retry <= 100:
                self.retries = retry
        elif event in {"post_api_request", "api_request_error"}:
            retry = data.get("retry_count")
            if type(retry) is int and retry < self.api_attempts.get(request, 0):
                return
            if self.apis.get(request) in {"ok", "error"}:
                return
            if not self.put(self.apis, request, "ok" if event == "post_api_request" else "error"):
                return
            if request == self.current_request and self.current_kind in {"api", "stream", "note"}:
                if event == "api_request_error":
                    self.last = "api_error"
                elif self.last not in {"tool_error", "tool_cancelled"}:
                    self.last = "working"
                if event == "post_api_request":
                    # Public count works for normalized assistant objects too;
                    # never read model text, reasoning or final answer content.
                    count = data.get("assistant_tool_call_count")
                    message = data.get("assistant_message")
                    has_tools = count > 0 if type(count) is int else bool(isinstance(message, dict) and message.get("tool_calls"))
                    self.current_kind = "working" if has_tools else "generating"
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
