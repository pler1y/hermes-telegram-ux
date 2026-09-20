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


def verified_finding(value, info):
    """Accept only a whole claim whose meaning is covered by structural facts.

    Public model prose is not evidence. In particular, source agreement, dates
    and bug diagnoses cannot be checked from the bounded facts retained here.
    Do not retain that prose or try to infer truth from a successful tool exit.
    """
    if not value:
        return ""
    facts = info.get("facts", {})
    claim = value.strip(" 。.!…")
    missing = r"(?:未找到指定文件|指定文件不存在|(?:The )?requested file (?:was not found|does not exist))"
    if facts.get("missing_file") and re.fullmatch(missing, claim, re.I):
        return claim
    if info.get("status") != "ok":
        return ""
    count = re.fullmatch(r"(?:已)?找到\s*(\d+)\s*条(?:搜索)?结果|Found\s+(\d+)\s+(?:search )?results?", claim, re.I)
    if count and type(facts.get("search_count")) is int and int(count.group(1) or count.group(2)) == facts["search_count"]:
        return claim
    if info.get("stage") in {"read", "read_data", "read_web", "read_guide", "inspect"} and facts.get("read_completed") and re.fullmatch(r"(?:已读取(?:所需资料|资料|文件|数据)|(?:Requested )?(?:material|file|data) (?:has been |was )?read)", claim, re.I):
        return claim
    if facts.get("test_completed") and re.fullmatch(r"测试命令已执行完|Test command completed", claim, re.I):
        return claim
    return ""



@dataclass
class Turn:
    session_id: str
    turn_id: str
    touched: float
    tools: dict = field(default_factory=dict)
    apis: dict = field(default_factory=dict)
    api_attempts: dict = field(default_factory=dict)
    approvals: dict = field(default_factory=dict)
    last: str = "working"
    language: str = "zh"
    note: dict = field(default_factory=dict)
    user_task: str = ""
    observations: dict = field(default_factory=dict)
    progress: dict = field(default_factory=dict)
    note_calls: dict = field(default_factory=dict)
    revision: int = 0
    current_call: str = ""
    current_request: str = ""
    current_kind: str = "initial"
    display_kind: str = "initial"
    finalizing: bool = False
    last_failure: dict = field(default_factory=dict)

    def __post_init__(self):
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
        if key not in bucket and sum(map(len, (self.tools, self.apis, self.approvals, self.note_calls))) >= 512:
            return False
        bucket[key] = value
        return True

    def merge_source_batch(self):
        """Summarize mixed source outcomes without changing any tool outcome.

        Only source operations in the just-finished public API batch participate.
        The resulting warning names no specific source. A successful clock or
        process call is not successful research.
        """
        if self.display_kind != "result" or self.progress.get("batch") != self.current_request:
            return
        sources = {"search", "read_web", "read_data", "read", "inspect"}
        outcomes = [item for item in self.observations.values()
                    if item.get("batch") == self.current_request
                    and item.get("stage") in sources]
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
            if event == "post_tool_call" and expected is not None and expected >= 0:
                if not self.put(self.note_calls, note_call, -1):
                    return
                if expected != self.revision or data.get("status") != "ok":
                    return
                # A still-running observed action owns the bubble. A late note
                # cannot rewind a newer action/result, even across API events.
                if self.tools.get(self.current_call, ("", ""))[1] == "running":
                    return
                from .presentation import meaningful_note, note_fingerprint
                note = normalize_note(data.get("args"))
                note = {key: text for key in ("goal", "action", "finding", "next") if (text := safe_text(note.get(key)))}
                if "finding" in note:
                    finding = verified_finding(note["finding"], self.observations.get(self.current_call, {}))
                    if finding:
                        note["finding"] = finding
                    else:
                        note.pop("finding")
                note = meaningful_note(note, self.user_task)
                if set(note) == {"finding"} and self.display_kind == "result":
                    # Matching the fact already on screen adds no information.
                    # A new action/next can still accompany verified evidence.
                    return
                if note and (self.display_kind != "note" or note_fingerprint(note) != note_fingerprint(self.note)):
                    self.note = note
                    self.revision += 1
                    self.current_kind, self.display_kind, self.last = "note", "note", "working"
            return
        if event in {"subagent_start", "subagent_stop", "on_interim_message"}:
            # Preserve correlated activity/TTL without a second task tree,
            # interim transcript, or unused statistics. Never render raw text.
            return
        call, request = identity(data.get("tool_call_id")), identity(data.get("api_request_id"))
        if event == "pre_tool_call":
            if call in self.tools or not self.put(self.tools, call, (tool_label(data.get("tool_name")), "running")):
                return
            name = tool_label(data.get("tool_name"))
            info = tool_context(name, data.get("args"), self.user_task, self.language)
            info = dict(info, tool=name, batch=self.current_request)
            previous = self.last_failure
            # A recovery label is permitted only once a real subsequent action
            # on the same object starts, never merely when a model is requested.
            related = {"search", "read_web", "read_data", "read", "inspect", "locate", "execute"}
            if previous and previous.get("subject") == info.get("subject") and info.get("subject") and previous.get("stage") in related and info.get("stage") in related:
                info["recovery"] = "alternative" if previous.get("tool") != name else "retry"
            self.last_failure = {}
            self.observations[call] = info
            self.revision += 1
            self.current_call, self.current_kind, self.last = call, "tool", "working"
            # A new recognizable execution stage is fresh information. An
            # opaque helper with no safe object must not erase a concrete note.
            if info.get("stage") != "execute" or info.get("subject") or self.display_kind == "initial":
                self.progress = info
                self.note = {}
                self.display_kind = "tool"
        elif event == "post_tool_call":
            old = self.tools.get(call)
            if old and old[1] != "running":
                return
            name = old[0] if old else tool_label(data.get("tool_name"))
            info = self.observations.get(call) or tool_context(name, data.get("args"), self.user_task, self.language)
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
            if call == self.current_call or self.display_kind == "initial":
                self.current_kind = "result"
                opaque_success = info.get("stage") == "execute" and not info.get("subject") and not (set(facts) - {"success"})
                if (opaque_success or not facts) and status not in {"error", "blocked", "cancelled"} and self.display_kind in {"note", "result"}:
                    return
                self.progress = info
                self.note = {}
                self.revision += 1
                self.current_call, self.current_kind = call, "result"
                self.display_kind = "result"
                self.last = "tool_error" if status in {"error", "blocked"} else "tool_cancelled" if status == "cancelled" else "working"
        elif event == "pre_api_request":
            retry = data.get("retry_count", 0)
            retry = retry if type(retry) is int and 0 <= retry <= 100 else 0
            if request in self.apis and retry <= self.api_attempts.get(request, 0):
                return
            if not self.put(self.apis, request, "running"):
                return
            self.api_attempts[request] = retry
            self.merge_source_batch()
            self.current_request, self.current_kind = request, "api"
            if self.last not in {"tool_error", "tool_cancelled"}:
                status = self.progress.get("status") if self.display_kind == "result" else ""
                self.last = "tool_error" if status in {"error", "blocked"} else "tool_cancelled" if status == "cancelled" else "working"
        elif event in {"post_api_request", "api_request_error"}:
            retry = data.get("retry_count")
            if type(retry) is int and retry < self.api_attempts.get(request, 0):
                return
            if self.apis.get(request) in {"ok", "error"}:
                return
            if not self.put(self.apis, request, "ok" if event == "post_api_request" else "error"):
                return
            if request == self.current_request and self.current_kind in {"api", "note"}:
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
        if self.current_kind in {"api", "generating"}:
            return "api", ""
        return "working", ""
