"""Reusable, evidence-driven task progress. No model calls or tool arguments are displayed."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
import hashlib
import json
from pathlib import PurePosixPath
import re
import shlex
import time
import threading
from functools import wraps


def locked(method):
    @wraps(method)
    def call(self, *args, **kwargs):
        with self._lock:
            return method(self, *args, **kwargs)
    return call


def shell_stage(command, deployed=False, depth=0):
    """Conservative executable matching; quoted output such as echo 'pytest' is not a test."""
    if not isinstance(command, str) or depth > 2:
        return "operate"
    try:
        lex = shlex.shlex(command[:12000], posix=True, punctuation_chars=";&|()\n")
        lex.whitespace = " \t\r"
        tokens = list(lex)
    except ValueError:
        return "operate"
    groups, group = [], []
    for token in tokens + [";"]:
        if token and all(c in ";&|()\n" for c in token):
            if group:
                groups.append(group)
                group = []
        else:
            group.append(token)
    stages = []
    for words in groups:
        while words and (re.match(r"^[A-Za-z_][A-Za-z_0-9]*=", words[0]) or words[0] in {"sudo", "env", "command"}):
            words = words[1:]
        if not words:
            continue
        exe = PurePosixPath(words[0]).name.lower()
        args = words[1:]
        if exe in {"bash", "sh", "zsh"} and "-c" in args:
            i = args.index("-c")
            stages.append(shell_stage(args[i+1] if len(args)>i+1 else "", deployed, depth+1))
        elif exe in {"pytest", "vitest", "jest"} or (exe in {"python", "python3"} and args[:1] == ["-m"] and len(args)>1 and args[1] in {"pytest", "unittest"}):
            stages.append("test")
        elif exe in {"npm", "pnpm", "yarn", "cargo", "go"} and (args[:1] == ["test"] or args[:2] == ["run", "test"]):
            stages.append("test")
        elif (exe == "systemctl" and any(a in {"restart", "start", "reload"} for a in args)) or (exe == "docker" and ((args[:1] in [["run"], ["restart"]]) or (args[:1] == ["compose"] and "up" in args))) or (exe == "kubectl" and (args[:1] == ["apply"] or args[:2] == ["rollout", "restart"])) or (exe == "helm" and args[:1] in [["install"], ["upgrade"]]):
            stages.append("deploy")
        elif exe in {"curl", "wget", "systemctl", "journalctl"}:
            stages.append("verify" if deployed else "inspect")
        elif exe in {"cat", "head", "tail", "sed", "ls", "rg", "grep", "find", "stat", "pwd"}:
            stages.append("inspect")
        elif exe not in {"cd", "echo", "printf", "true", "sleep"}:
            stages.append("operate")
    unique = set(stages)
    # A bundled command has no per-step events. Don't pretend to know its current substep.
    if "test" in unique and "deploy" in unique:
        return "test_deploy"
    if "deploy" in unique and ("inspect" in unique or "verify" in unique):
        return "deploy_verify"
    for stage in ("deploy", "test", "verify", "operate", "inspect"):
        if stage in unique:
            return stage
    return "operate"


def stage_for_tool(name, args, deployed=False):
    name = (name or "").lower()
    args = args or {}
    if name == "terminal" or any(x in name for x in ("shell", "exec_command")):
        return shell_stage(args.get("command") or args.get("cmd"), deployed)
    if name in {"search_files", "grep"}:
        return "inspect"
    if name == "session_search":
        return "recall"
    if "search" in name:
        return "search"
    if any(x in name for x in ("web_extract", "browser", "read", "vision", "pdf", "skill_view")):
        return "read"
    if any(x in name for x in ("write", "patch", "edit", "replace")):
        return "write"
    if any(x in name for x in ("image", "video", "audio", "generate")):
        return "create"
    if any(x in name for x in ("delegate", "subagent")):
        return "background"
    if any(x in name for x in ("calculate", "execute_code", "python")):
        return "calculate"
    return "operate"


def result_object(result):
    if isinstance(result, str):
        try:
            result = json.loads(result)
        except (ValueError, TypeError):
            return {}
    return result if isinstance(result, dict) else {}


def search_count(data):
    """Count returned candidates only in known structured result containers."""
    for key in ("web", "results", "items"):
        if isinstance(data.get(key), list):
            return len(data[key])
    nested = data.get("data")
    return search_count(nested) if isinstance(nested, dict) else None


def step_group(stage):
    if stage in {"search", "read", "inspect", "recall"}:
        return "gather"
    if stage in {"test", "verify", "calculate"}:
        return "check"
    if stage in {"write", "create"}:
        return "produce"
    return stage


def evidence_stages(stage):
    """Bundled commands can invalidate either part of an earlier result."""
    return {"test_deploy": {"test", "deploy"},
            "deploy_verify": {"deploy", "verify"}}.get(stage, {stage})


def step_identity(owner, name, args):
    # A call id identifies one attempt, not a retry. Match the operation without
    # retaining arguments (which can contain private data) in result bookkeeping.
    operation = {k: v for k, v in args.items()
                 if k not in {"timeout", "timeout_ms", "yield_time_ms", "max_output_tokens", "background", "notify"}}
    signature = hashlib.sha256(json.dumps(operation, sort_keys=True, default=str).encode()).hexdigest()
    # Display stages can change (for example inspect -> verify after deployment)
    # without changing the operation that is being retried.
    return owner, name, signature


@dataclass
class TaskProgress:
    """One task, its revisions, public step explanations and observed execution evidence."""
    _lock: object = field(default_factory=threading.RLock, repr=False)
    initialized: bool = False
    request: str = ""
    goal: str = ""
    constraints: tuple = ()
    revision: int = 0
    receipt: str = ""
    requests: dict = field(default_factory=dict)
    pending: dict = field(default_factory=dict)
    notes: dict = field(default_factory=dict)
    latest_owner: str = ""
    active: dict = field(default_factory=dict)
    processes: dict = field(default_factory=dict)
    stage: str = "opening"
    changed_at: float = field(default_factory=time.monotonic)
    completed_note: str = ""
    problem: str = ""
    activity: str = ""
    finding: str = ""
    next_step: str = ""
    deployed: bool = False
    serial: int = 0
    evidence_count: int = 0
    _evidence: dict = field(default_factory=dict, repr=False)
    _problems: dict = field(default_factory=dict, repr=False)
    _overflow_problems: dict = field(default_factory=dict, repr=False)
    _attempts: dict = field(default_factory=dict, repr=False)

    def _retire_attempt(self, step):
        # Keep the latest sequence while any older call/process can still report.
        # Once all attempts settle there is no late hook left to pair with it.
        if not any(item[3] == step for item in self.active.values()) and not any(
                item[1] == step for item in self.processes.values()):
            self._attempts.pop(step, None)

    def _refresh_evidence(self):
        problems = list(self._overflow_problems.items()) + list(self._problems.values())
        self.problem = problems[-1][1] if problems else ""
        blocked = set().union(*(evidence_stages(stage) for stage, _ in problems))
        self.completed_note = next((text for stage, text in reversed(self._evidence.values())
                                    if not evidence_stages(stage) & blocked), "")

    def _record_problem(self, step, stage, message):
        self._problems.pop(step, None)
        self._problems[step] = (stage, message)
        if len(self._problems) > 128:
            old_stage, old_message = self._problems.pop(next(iter(self._problems)))
            # An unusually long task keeps a conservative stage warning instead
            # of silently declaring forgotten failures fixed. This summary is
            # bounded by the small stage vocabulary and expires with the task.
            self._overflow_problems[old_stage] = old_message
        # Invalidate old claims for the failed stage, while keeping independent
        # evidence such as sources already found before a read or test failed.
        failed_stages = evidence_stages(stage)
        self._evidence = {key: value for key, value in self._evidence.items()
                          if key != step and not evidence_stages(value[0]) & failed_stages}

    def _record_evidence(self, step, stage, text):
        self._evidence.pop(step, None)
        self._evidence[step] = (stage, text)
        self._evidence = dict(list(self._evidence.items())[-64:])

    @locked
    def initialize(self, text):
        if not self.initialized:
            self.initialized = True
            self.request = text[:4000] if isinstance(text, str) else ""

    @locked
    def request_started(self, owner, request_id):
        self.requests[(owner, request_id)] = self.revision
        # Bounded turn-local bookkeeping. No task text is written to persistent memory.
        self.requests = dict(list(self.requests.items())[-64:])

    @locked
    def received(self, text="", *, message="收到，补充已记下。"):
        self.revision += 1
        self.receipt = message
        self.activity = ""
        self.next_step = ""
        self.changed_at = time.monotonic()

    @locked
    def propose(self, owner, request_id, text, calls):
        revision = self.requests.get((owner, request_id), -1)
        if revision != self.revision:
            return False
        if not self.evidence_count and re.search(r"^(?:已完成|已经完成|全部通过|验收通过|已部署|已发送|已删除)", text):
            return False
        for call_id, name in calls:
            self.pending[(owner, call_id or name)] = (text, revision)
        self.pending = dict(list(self.pending.items())[-128:])
        return True

    @locked
    def plan(self, activity, finding="", next_step="", task_type="", *, goal="", constraints=None, owner="", request_id=""):
        # Legacy task_type is accepted but does not drive presentation or task classification.
        if request_id and self.requests.get((owner, request_id), -1) != self.revision:
            return False
        if goal:
            self.goal = goal
        if constraints is not None:
            self.constraints = tuple(constraints)
        if activity:
            self.notes[owner] = {"text": activity, "revision": self.revision, "group": None}
            self.latest_owner = owner
            self.activity = activity
            self.receipt = ""
        if finding:
            self.finding = finding
            self._evidence.clear()
            self.completed_note = ""
        self.next_step = next_step
        self.changed_at = time.monotonic()
        return True

    @locked
    def start(self, owner, call_id, name, args):
        args = args or {}
        self.serial += 1
        key = (owner, call_id or f"{name}:{self.serial}")
        if key in self.active:
            return False
        stage = stage_for_tool(name, args, self.deployed)
        handle = str(args.get("session_id") or args.get("process_id") or "")
        step = step_identity(owner, name, args)
        attempt = self.serial
        if name in {"process", "write_stdin"} and (owner, handle) in self.processes:
            stage, step, attempt = self.processes[(owner, handle)]
        else:
            self._attempts[step] = attempt
        proposed = self.pending.pop((owner, call_id or name), None)
        current_note = self.notes.get(owner)
        continuation = (proposed and proposed[1] == self.revision and not proposed[0]
            and current_note and current_note['revision'] == self.revision)
        if continuation:
            # An explicit empty presentation field means this tool continues the same public
            # step. Keep its purpose across tool kinds; a user revision still invalidates it.
            current_note['group'] = step_group(stage)
        elif proposed and proposed[1] == self.revision and proposed[0]:
            self.notes[owner] = {"text": proposed[0], "revision": self.revision, "group": step_group(stage)}
            self.latest_owner = owner
            self.activity = proposed[0]
            self.receipt = ""
            self.changed_at = time.monotonic()
        else:
            note = self.notes.get(owner)
            if note and note["group"] is None:
                note["group"] = step_group(stage)
            elif note and note["group"] != step_group(stage):
                self.notes.pop(owner, None)
                self.activity = ""
        self.active[key] = (stage, name, handle, step, attempt)
        if self.stage != stage:
            self.changed_at = time.monotonic()
        self.stage = stage
        return True

    @locked
    def finish(self, owner, call_id, name, result, failed=False):
        key = (owner, call_id)
        if not call_id:
            key = next((k for k, v in self.active.items() if k[0] == owner and v[1] == name), None)
        item = self.active.pop(key, None)
        if item is None:
            return False
        stage, _, old_handle, step, attempt = item
        data = result_object(result)
        handle = str(data.get("session_id") or data.get("process_id") or old_handle or "")
        running = data.get("status") in {"running", "background"} or (bool(handle) and data.get("exit_code") is None and data.get("status") not in {"completed", "exited", "already_exited", "failed", "killed"})
        success = (type(data.get("exit_code")) is int and data["exit_code"] == 0) or data.get("success") is True
        if handle and (failed or not running):
            process = self.processes.get((owner, handle))
            if process and process[1:] == (step, attempt):
                self.processes.pop((owner, handle), None)
        if running and not failed:
            self.processes[(owner, handle)] = (stage, step, attempt)
        latest_attempt = self._attempts.get(step, attempt)
        self._retire_attempt(step)
        if attempt < latest_attempt:
            return True
        if running and not failed:
            self.stage = stage
        elif failed:
            self._record_problem(step, stage, {"search": "这次搜索没拿到结果。", "test": "这轮测试没通过。", "deploy": "部署这一步没有成功。"}.get(stage, "刚才这一步没成功。"))
            self.next_step = ""
            self.notes.pop(owner, None)
            self.activity = ""
            self.stage = "recover"
        else:
            # A return without an exit result is not proof that a failed test or
            # deployment recovered. Other tools use the native failure flag.
            if success or stage not in {"test", "deploy", "test_deploy", "deploy_verify"}:
                self._problems.pop(step, None)
            self.evidence_count += 1
            self.stage = "analyze"
            completed_note = ""
            if stage == "search":
                count = search_count(data)
                completed_note = "这次没有找到匹配的资料。" if count == 0 else f"已找到 {count} 条候选资料。" if count is not None else "搜索已返回。"
            elif stage == "test":
                completed_note = "这轮测试通过了。" if success else "测试有返回，正在核对结果。"
            elif stage in {"deploy", "test_deploy", "deploy_verify"}:
                self.deployed = success
                completed_note = "执行命令已结束，还需要确认实际运行情况。" if success else "部署步骤有返回，还需要核对结果。"
            elif stage == "verify":
                completed_note = "检查有返回，正在核对是否符合预期。"
            elif stage == "write" and success:
                completed_note = "内容已写入，正在检查。"
            elif stage == "create" and success:
                completed_note = "内容已生成，正在检查效果。"
            if completed_note:
                self._record_evidence(step, stage, completed_note)
        self._refresh_evidence()
        if not running or failed:
            self.changed_at = time.monotonic()
        return True

    @locked
    def close_owner(self, owner):
        self.active = {k:v for k,v in self.active.items() if k[0] != owner}
        self.processes = {k:v for k,v in self.processes.items() if k[0] != owner}
        self._attempts = {k:v for k,v in self._attempts.items() if k[0] != owner}
        self.pending = {k:v for k,v in self.pending.items() if k[0] != owner}
        self.notes.pop(owner, None)
        self.activity = ""
        self.next_step = ""
        self.stage = "analyze"
        self.changed_at = time.monotonic()

    def _current(self, stage):
        if stage == "analyze":
            return "正在核对资料，整理与你有关的部分…" if "搜索" in self.completed_note or "候选资料" in self.completed_note else "正在核对这一步的结果…"
        return {
            "opening": "思考中…",
            "search": "正在搜索相关资料…",
            "read": "正在阅读，核对具体内容…",
            "inspect": "先看看现有内容和情况…",
            "write": "正在修改内容…",
            "test": "先运行测试，看看结果是否符合预期…",
            "deploy": "正在执行部署步骤…",
            "test_deploy": "正在执行包含测试和部署的步骤…",
            "deploy_verify": "正在执行部署和运行检查…",
            "verify": "正在检查部署后的运行情况…",
            "calculate": "正在计算并核对结果…",
            "create": "正在制作内容…",
            "background": "任务已交给后台继续处理…",
            "recall": "我在翻一下前面的对话…",
            "recover": "正在核对失败的影响，看看下一步怎么处理…",
            "operate": "正在执行这一步，等它返回结果…",
        }.get(stage, "正在处理这一步…")

    def _view(self):
        current = [(k[0], v[0]) for k,v in self.active.items()]
        current += [(k[0], v[0]) for k,v in self.processes.items() if k not in {(a[0], b[2]) for a,b in self.active.items()}]
        concrete = [(o,s) for o,s in current if s != "background"]
        owner, stage = (concrete or current or [(self.latest_owner, self.stage)])[-1]
        note = self.notes.get(owner)
        if not note and not current:
            note = self.notes.get(self.latest_owner)
        if note and note["revision"] != self.revision:
            note = None
        return stage, note, len(concrete), bool(current)

    @locked
    def needs_narration(self):
        _, note, _, _ = self._view()
        return bool(self.receipt or self.problem or not note)

    @locked
    def snapshot(self):
        stage, note, _, _ = self._view()
        return {"activity": note["text"] if note else self._current(stage),
            "finding": self.completed_note or self.finding,
            "goal": self.goal, "revision": self.revision,
            "source": "narrative" if note else "fallback", "stage": stage}

    @locked
    def render(self, now, slow_after, *, soft_wait=False):
        stage, note, count, running = self._view()
        line = note["text"] if note else self._current(stage)
        slow = now - self.changed_at >= slow_after
        if stage == "opening" and slow:
            line = "还在想，回答还没准备好。"
        if count > 1:
            line += f"（还有 {count-1} 步同时进行）"
        lines = [line]
        if soft_wait and stage == "opening" and not note and not slow:
            lines = []
        if self.receipt:
            lines = [self.receipt, self._current(stage)]
        detail = self.completed_note or self.finding
        if self.problem:
            lines.append(self.problem)
        if detail:
            lines.append(detail)
        if self.next_step and not self.receipt:
            lines.append("接下来：" + self.next_step)
        if slow and stage != "opening":
            lines.append("这一步还没返回新结果，可以继续补充，也可以说“停一下”。" if running else "还在核对这些结果，暂时没有新的进展。")
        return "\n".join(lines[:4])
