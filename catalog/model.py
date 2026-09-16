"""Bounded, event-based UX state. No host, transport, prompt, or tool-result access."""
from dataclasses import dataclass, field
import re


def identity(value):
    return value if isinstance(value, str) and 0 < len(value) <= 512 else ""


def tool_label(value):
    # Tool names may be supplied by third parties. Never render markup/commands.
    return value if isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9_.:-]{1,64}", value) else "tool"


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

    def put(self, bucket, key, value):
        if not key:
            return False
        if key not in bucket and sum(map(len, (self.tools, self.apis, self.approvals, self.interims))) >= 512:
            self.capped = True
            return False
        bucket[key] = value
        return True

    def observe(self, event, data, now):
        self.touched = now
        call = identity(data.get("tool_call_id"))
        request = identity(data.get("api_request_id"))
        if event == "pre_tool_call":
            if call not in self.tools:
                self.put(self.tools, call, (tool_label(data.get("tool_name")), "running"))
            self.last = "working"
        elif event == "post_tool_call":
            status = data.get("status")
            status = status if status in {"ok", "error", "blocked", "cancelled"} else "returned"
            self.put(self.tools, call, (tool_label(data.get("tool_name")), status))
            self.last = "tool_error" if status in {"error", "blocked"} else "working"
        elif event == "pre_api_request":
            if request not in self.apis:
                self.put(self.apis, request, "running")
            self.last = "working"
        elif event in {"post_api_request", "api_request_error"}:
            self.put(self.apis, request, "ok" if event == "post_api_request" else "error")
            self.last = "api_error" if event == "api_request_error" else "working"
        elif event == "pre_approval_request":
            if call not in self.approvals:
                self.put(self.approvals, call, "smart" if data.get("surface") == "smart" else "pending")
        elif event == "post_approval_response":
            choice = data.get("choice")
            choices = {"once", "session", "always", "deny", "timeout", "cancelled", "notify_failed", "smart_approve", "smart_deny"}
            self.put(self.approvals, call, choice if choice in choices else "unknown")
            self.last = {"timeout": "approval_timeout", "notify_failed": "approval_failed", "cancelled": "approval_cancelled", "deny": "approval_denied", "smart_deny": "approval_denied"}.get(choice, "working")
        elif event == "on_interim_message":
            iteration = data.get("iteration")
            if isinstance(iteration, int) and not isinstance(iteration, bool) and iteration not in self.interims:
                if sum(map(len, (self.tools, self.apis, self.approvals, self.interims))) < 512:
                    self.interims.add(iteration)
                else:
                    self.capped = True
            self.last = "interim"

    def phase(self):
        if "pending" in self.approvals.values():
            return "approval", ""
        if "smart" in self.approvals.values():
            return "smart", ""
        if self.last in {"approval_timeout", "approval_failed", "approval_cancelled", "approval_denied", "tool_error", "api_error"}:
            return self.last, ""
        running = [name for name, status in self.tools.values() if status == "running"]
        if running:
            return "tool", ", ".join(running[:3])
        if "running" in self.apis.values():
            return "api", ""
        return self.last, ""

    def counts(self):
        return len(self.tools), len(self.apis), sum(status in {"error", "blocked"} for _, status in self.tools.values())
