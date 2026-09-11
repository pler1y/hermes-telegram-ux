"""Pure state and phase classification for the Telegram interaction layer."""

from __future__ import annotations

from dataclasses import dataclass, field
import asyncio
import re
import json
import threading
import time
from typing import Any
from .progress import TaskProgress
from .i18n import localize, decorate


INITIAL = "想一下…"
ANALYZE = "看看刚查到的内容…"
FINALIZE = "整理一下…"
STEER = "收到，补充已记下。"
RETRY = "⚠️ 本次模型请求未成功，正在等待后续处理。"
FAILED = "⚠️ 这次未能完成。可直接问我已完成哪些，以及下一步怎么处理。"
INTERRUPTED = "⏹️ 当前任务已中断；已执行的操作不会自动撤销。"


TOOL_GROUPS = (
    (("web_search", "search", "search_files", "session_search", "grep"), "查找资料…"),
    (("web_extract", "read_file", "skill_view", "vision", "pdf", "document"), "看看这份内容…"),
    (("browser", "playwright", "navigate", "screenshot"), "核对一下来源…"),
    (("write_file", "patch", "edit", "replace"), "正在修改…"),
    (("execute_code", "calculator", "python"), "算一下…"),
    (("delegate", "subagent", "handoff"), "后台还在处理…"),
    (("image", "video", "audio", "generate"), "正在制作…"),
)

_TEST_RE = re.compile(r"(?:^|\s)(?:pytest|unittest|vitest|jest|npm\s+(?:run\s+)?test|pnpm\s+test|yarn\s+test|cargo\s+test|go\s+test)(?:\s|$)", re.I)
_DEPLOY_RE = re.compile(r"(?:systemctl\s+(?:restart|start|stop|reload|enable|disable)|docker\s+(?:compose\s+)?(?:up|restart|build)|kubectl|helm|scp|rsync|deploy)", re.I)


def phase_for_tool(name: str, args: dict[str, Any] | None = None) -> str:
    clean = (name or "").strip().lower()
    args = args or {}
    if clean in {"interaction_actions", "telegram_followup_actions"}:
        return FINALIZE
    if any(token in clean for token in ("terminal", "shell", "exec", "command")):
        command = str(args.get("command") or args.get("cmd") or "")[:1000]
        if _TEST_RE.search(command):
            return "验证一下结果…"
        if _DEPLOY_RE.search(command):
            return "正在部署…"
        return "还在处理…"
    for needles, text in TOOL_GROUPS:
        if any(needle in clean for needle in needles):
            return text
    return "还在处理…"


@dataclass
class TurnState:
    session_id: str
    session_key: str
    source: Any
    adapter: Any
    generation: int | None
    stream_holder: list
    cleanup_ids: list
    metadata: dict | None
    loop: Any
    phase: str = INITIAL
    phase_version: int = 0
    tool_count: int = 0
    status_message_id: str | None = None
    status_sent_at: float | None = None
    failed: bool = False
    interrupted: bool = False
    completed: bool = False
    callback_registered: bool = False
    created_at: float = field(default_factory=time.monotonic)
    last_event_at: float = field(default_factory=time.monotonic)
    activity: str = ""
    finding: str = ""
    active_tools: int = 0
    tool_errors: int = 0
    ended: bool = False
    receipt_turn: bool = False
    receipt_text: str = ""
    foreground_active: bool = True
    last_shown_text: str = ""
    soft_wait: bool = False
    last_typing_at: float = 0.0
    progress: TaskProgress | None = None
    send_lock: Any = field(default_factory=asyncio.Lock)
    status_closed: bool = False
    approval_phase: str | None = None
    language: str = "zh"
    emoji: bool = False
    internal_status: str = ""

    def render(self, now: float, slow_after: float = 45.0) -> str:
        priority = self.ended or self.approval_phase or self.phase == RETRY
        text = self._render(now, slow_after) if priority else (self.internal_status or self._render(now, slow_after))
        stage = self.progress.snapshot()["stage"] if self.progress else "opening"
        return decorate(localize(text, self.language), stage, self.emoji)

    def _render(self, now: float, slow_after: float = 45.0) -> str:
        if self.ended or self.phase.startswith(("等待你确认", "正在检查操作权限")):
            return self.phase
        if self.progress is not None:
            if self.phase == RETRY:
                return "这次请求没有成功，还没有拿到结果。"
            return self.progress.render(now, slow_after)
        if self.soft_wait:
            if self.phase == RETRY:
                return "这次请求没有成功，还没有拿到结果。"
            lines = [self.activity] if self.activity else []
            if self.finding:
                lines.append(self.finding)
            if not lines and now - self.last_event_at >= slow_after:
                lines.append('还在处理。你可以继续补充，也可以说“停一下”。')
            return "\n".join(lines)
        lines = []
        if self.activity:
            lines.append(self.activity)
        if not self.activity or self.phase in {STEER, RETRY}:
            lines.append(self.phase)
        if self.finding:
            lines.append("已确认：" + self.finding)
        if now - self.last_event_at >= slow_after:
            lines.append("这一步等待较久，暂未收到新结果。需要结束可发送 /stop。")
        return "\n".join(lines)


def safe_status_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    text = " ".join(value.split())[:240]
    # Native redaction when available, plus a conservative fallback for standalone tests.
    try:
        from agent.redact import redact_sensitive_text
        text = redact_sensitive_text(text, force=True)
    except ImportError:
        pass
    text = re.sub(r"(?i)(?:https?://|www\.)\S+", "[链接]", text)
    text = re.sub(r"(?i)(?:sk-|ghp_|github_pat_)[a-z0-9_-]+", "[已隐藏]", text)
    text = re.sub(r"(?i)(?:token|api[_-]?key|password|secret)\s*[:=]\s*\S+", "[已隐藏]", text)
    text = re.sub(r"(?<![A-Za-z0-9])(?:/(?:Users|root|home|tmp|var|usr|etc|private|opt)/|[A-Z]:\\)[^\s，。；]+", "[文件位置]", text)
    return text[:160]


def tool_failed(result: Any) -> bool:
    if isinstance(result, str):
        try:
            result = json.loads(result)
        except (ValueError, TypeError):
            return False
    return isinstance(result, dict) and (result.get("success") is False or
        result.get("is_error") is True or result.get("isError") is True or
        bool(result.get("error")) or
        (isinstance(result.get("exit_code"), int) and result["exit_code"] != 0))



class TurnRegistry:
    def __init__(self):
        self._states: dict[str, TurnState] = {}
        self._lock = threading.RLock()

    def bind(self, state: TurnState) -> None:
        with self._lock:
            self._states[state.session_id] = state

    def get(self, session_id: str) -> TurnState | None:
        with self._lock:
            return self._states.get(session_id)

    def update(self, session_id: str, phase: str, *, tool_started: bool = False) -> None:
        with self._lock:
            state = self._states.get(session_id)
            if state is None:
                return
            if state.ended:
                return
            state.last_event_at = time.monotonic()
            if tool_started:
                state.tool_count += 1
                state.active_tools += 1
            if phase != state.phase:
                state.phase = phase
                state.phase_version += 1

    def progress(self, session_id: str, activity: str = "", finding: str = "", next_step: str = "", task_type: str = "", *, goal="", constraints=None, owner="", request_id="") -> None:
        with self._lock:
            state = self._states.get(session_id)
            if state is None or state.ended:
                return
            if state.progress is not None:
                clean_constraints = [safe_status_text(c) for c in constraints[:6]] if isinstance(constraints, list) else None
                accepted = state.progress.plan(safe_status_text(activity), safe_status_text(finding), safe_status_text(next_step), task_type,
                    goal=safe_status_text(goal), constraints=clean_constraints, owner=owner or session_id, request_id=request_id)
                if not accepted:
                    return
            if activity:
                state.activity = safe_status_text(activity)
            if finding:
                state.finding = safe_status_text(finding)
            state.last_event_at = time.monotonic()
            state.phase_version += 1

    def receipt(self, session_id, text=""):
        with self._lock:
            state = self._states.get(session_id)
            if state and not state.ended:
                if state.progress is not None:
                    state.progress.received(text)
                state.last_event_at = time.monotonic()

    def tool_started(self, session_id, owner, call_id, name, args):
        with self._lock:
            state = self._states.get(session_id)
            if state is None or state.ended:
                return
            if state.progress is not None:
                if not state.progress.start(owner, call_id, name, args):
                    return
                if state.activity != state.progress.activity:
                    state.activity = ""
            self.update(session_id, phase_for_tool(name, args), tool_started=True)

    def tool_finished(self, session_id: str, result: Any, *, owner="", call_id="", name="", status="") -> None:
        with self._lock:
            state = self._states.get(session_id)
            if state is None or state.ended:
                return
            failed = tool_failed(result) or status in {"error", "failed", "blocked", "denied", "cancelled"}
            if state.progress is not None:
                if not state.progress.finish(owner, call_id, name, result, failed):
                    return
                state.activity = ""
            state.active_tools = max(0, state.active_tools - 1)
            state.tool_errors += int(failed)
            state.last_event_at = time.monotonic()
            if not state.active_tools:
                self.update(session_id, "⚠️ 有一步未成功，正在核对影响和后续办法。" if failed else ANALYZE)
                state.activity = ""

    def by_key(self, session_key: str) -> TurnState | None:
        with self._lock:
            return next((s for s in self._states.values() if s.session_key == session_key), None)

    def model_request(self, session_id: str) -> None:
        state = self.get(session_id)
        self.update(session_id, ANALYZE if state and state.tool_count else INITIAL)

    def finish(self, session_id: str, *, failed: bool, interrupted: bool, completed: bool) -> None:
        with self._lock:
            state = self._states.get(session_id)
            if state is None:
                return
            state.ended = True
            state.failed = bool(failed)
            state.interrupted = bool(interrupted)
            state.completed = bool(completed)
            phase = FAILED if failed else INTERRUPTED if interrupted else FINALIZE
            if phase != state.phase:
                state.phase = phase
                state.phase_version += 1

    def pop(self, session_id: str, expected: TurnState | None = None) -> TurnState | None:
        with self._lock:
            if expected is not None and self._states.get(session_id) is not expected:
                return None
            return self._states.pop(session_id, None)
