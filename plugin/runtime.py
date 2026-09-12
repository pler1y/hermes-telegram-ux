"""Runtime integration: one stable patch seam plus event-driven hooks."""

from __future__ import annotations

import asyncio
from contextlib import suppress
import logging
import math
import time
import threading
import re
import weakref
import hashlib

from .actions import ActionStore, TelegramActions, TOOL_SCHEMA, tool_handler
from .status import ANALYZE, FINALIZE, RETRY, STEER, TurnRegistry, TurnState, phase_for_tool

logger = logging.getLogger(__name__)


from .experience import PROMPT, PROGRESS_SCHEMA, progress_handler
from .background import owned_children, acknowledgement_only
from .status import safe_status_text
from .progress import TaskProgress
from .narration import tool_note, SETUP_TOOLS, UI_TOOLS, PROGRESS_FIELD, public_text, with_progress_schema, accepts_null
from .controls import ALIASES
from .i18n import package_language, localize, tr
from .intake import IntakeFeedback
from .bindings import Overrides, Handlers

# Tool catalogue and skill loading are implementation setup, not user-facing search/read work.
_SETUP_TOOLS = SETUP_TOOLS



def clean_stream_text(text):
    # Partial MEDIA paths have no extension yet and bypass the native completed-tag filter.
    text = re.sub(r"(?m)^[ \t]*MEDIA:[^\n]*(?:\n|$)", "", text)
    text = re.sub(r"(?:^|\n)[ \t]*(?:M|ME|MED|MEDI|MEDIA)$", "", text)
    return text.rstrip()


class InteractionRuntime:
    def __init__(self, ctx):
        self.ctx = ctx
        selected_language = ctx.get_config("language", "package")
        self.language = selected_language if selected_language in {"zh", "en"} else package_language()
        self.emoji = bool(ctx.get_config("status_emoji", True))
        self.registry = TurnRegistry()
        self.intake = IntakeFeedback(self)
        self.actions = ActionStore()
        self.telegram = TelegramActions(ctx, self.actions)
        self.delay = max(0.4, min(float(ctx.get_config("status_delay_seconds", 1.2)), 8.0))
        self.soft_wait = bool(ctx.get_config("soft_wait", False))
        self.min_edit = max(0.7, min(float(ctx.get_config("status_min_edit_seconds", 2.5)), 10.0))
        self.slow_after = max(15.0, float(ctx.get_config("slow_notice_seconds", 45.0)))
        self._overrides = Overrides()
        self._wired = []
        self._original_stop = None
        self._original_idle_stop = None
        self._original_send_ack = None
        self._original_completion_group = None
        state_store = getattr(ctx, "state", None)
        # Admission contexts need not provide optional durable state. A generic
        # no-op registration stub is not a state store.
        self._state_store = state_store if callable(getattr(state_store, "get", None)) and callable(getattr(state_store, "set", None)) else None
        self._cancelled_delegations = self._state_store.get("cancelled_delegations", {}) if self._state_store is not None else {}
        if not isinstance(self._cancelled_delegations,dict):self._cancelled_delegations={}
        self._raw_sends = {}
        self._status_cooldowns = {}
        self._stream_overrides = weakref.WeakKeyDictionary()
        self._child_roots = {}
        self._children = {}
        self._background_lock = threading.RLock()
        self._background_tasks = {}
        self._narration_nulls = {}
        self._control_cleanup = []
        self._runner_cls = None
        self._original_notify = None
        self._original_busy_text = None

    def install(self) -> None:
        self.ctx.register_tool(
            name=TOOL_SCHEMA["name"], toolset="interaction", schema=TOOL_SCHEMA,
            handler=tool_handler, is_async=False,
            description=TOOL_SCHEMA["description"], emoji="✨",
        )
        self.ctx.register_tool(
            name=PROGRESS_SCHEMA["name"], toolset="interaction", schema=PROGRESS_SCHEMA,
            handler=progress_handler, is_async=False,
            description=PROGRESS_SCHEMA["description"], emoji="💬")
        from .experience import prompt_for
        self.ctx.register_system_prompt_section(
            "hermes_interaction.telegram", prompt_for(self.language), position="after_memory", max_chars=4000)
        self.ctx.register_platform_handler("telegram", self.wire_telegram)
        self.ctx.register_middleware("llm_request", self.narration_request)
        self.ctx.register_middleware("tool_request", self.narration_arguments)
        for hook_name, callback in (
            ("pre_api_request", self.pre_api), ("post_api_request", self.post_api),
            ("api_request_error", self.api_error), ("pre_tool_call", self.pre_tool),
            ("post_tool_call", self.post_tool), ("on_session_end", self.session_end),
            ("on_session_reset", self.session_reset),
            ("pre_gateway_dispatch", self.dispatch),
            ("pre_approval_request", self.approval_wait),
            ("post_approval_response", self.approval_done),
            ("subagent_start", self.child_start), ("subagent_stop", self.child_stop),
            ("post_llm_call", self.model_end),
        ):
            self.ctx.register_hook(hook_name, callback)
        self.ctx.on_unload(self.uninstall)
        logger.info("Hermes Interaction: event-driven status runtime registered")

    def wire_telegram(self, application, adapter) -> None:
        if any(app is application and bot is adapter for app, bot in self._wired):
            return
        # Record each handler addition, even if a factory fails before returning cleanup.
        handlers = Handlers(application)
        checkpoint = len(self._control_cleanup)
        previous_runner = self._runner_cls
        previous_sends = set(self._raw_sends)
        self._control_cleanup.append(handlers.close)
        try:
            with self._overrides.transaction(), self.intake.patches.transaction():
                self._wire_telegram(handlers, adapter)
        except BaseException:
            for cleanup in reversed(self._control_cleanup[checkpoint:]):
                with suppress(Exception):
                    cleanup()
            del self._control_cleanup[checkpoint:]
            self._runner_cls = previous_runner
            for bot in set(self._raw_sends) - previous_sends:
                self._raw_sends.pop(bot, None)
            raise
        self._wired.append((application, adapter))

    def _wire_telegram(self, application, adapter) -> None:
        # Defer gateway imports until native platform factories run after discovery.
        if self._runner_cls is None:
            self._patch_runner()
        seconds = max(0.3, min(float(self.ctx.get_config("text_batch_seconds", 0.8)), 1.5))
        for name in ("_text_batch_delay_seconds", "_TEXT_BATCH_FAST_DELAY_S", "_TEXT_BATCH_SHORT_DELAY_S"):
            if hasattr(adapter, name):
                self._overrides.set(adapter, name, seconds)
        self._wire_send(adapter)
        self._control_cleanup.append(self.telegram.wire(application, adapter))
        from .controls import wire as wire_controls
        self._control_cleanup.append(wire_controls(application, adapter, language=self.language))
        from .welcome import wire
        self._control_cleanup.append(wire(application, adapter, language=self.language))
        self._control_cleanup.append(self.intake.wire(application, adapter))

    def _patch_runner(self) -> None:
        previous = self._runner_cls
        try:
            with self._overrides.transaction(), self.intake.patches.transaction():
                self._install_runner_patches()
        except BaseException:
            self._runner_cls = previous
            raise

    def _install_runner_patches(self) -> None:
        from gateway.run import GatewayRunner

        current = GatewayRunner._run_agent_notify_long_running
        if (getattr(current, "_hermes_interaction", False)
                and getattr(current, "_hermes_interaction_active", [True])[0]):
            raise RuntimeError("Hermes Interaction is already installed in this process")
        self._runner_cls = GatewayRunner
        self.intake.patch_gateway(GatewayRunner)
        self._original_notify = GatewayRunner._run_agent_notify_long_running
        self._original_busy_text = GatewayRunner._compose_busy_ack_message
        runtime = self

        def notify(runner, disp, turn_ctx, executor_holder):
            # Called synchronously by create_task(...). Bind before the executor worker starts so
            # an immediate pre_api_request/pre_tool_call event cannot outrun the registry.
            if not runtime.is_telegram(turn_ctx.source):
                return runtime._original_notify(runner, disp, turn_ctx, executor_holder)
            return runtime.prepare_status_lifecycle(runner, turn_ctx, executor_holder)

        notify._hermes_interaction = True

        def busy_text(runner, event, now, busy_state, running_agent, *, is_steer_mode,
                      is_queue_mode, is_redirect_mode, demoted_for_subagents,
                      demoted_for_compression):
            if not runtime.is_telegram(event.source):
                return runtime._original_busy_text(runner, event, now, busy_state, running_agent,
                    is_steer_mode=is_steer_mode, is_queue_mode=is_queue_mode,
                    is_redirect_mode=is_redirect_mode, demoted_for_subagents=demoted_for_subagents,
                    demoted_for_compression=demoted_for_compression)
            if is_steer_mode:
                return tr("收到，补充已记下。", runtime.language)
            if is_queue_mode:
                return tr("收到，这条会在当前任务后处理。", runtime.language)
            if is_redirect_mode:
                return tr("收到，会按你的新要求处理。", runtime.language)
            return tr("收到，正在切换到你的新要求。", runtime.language)

        runtime._original_stop = GatewayRunner._busy_stop_command
        runtime._original_idle_stop = GatewayRunner._handle_stop_command
        runtime._original_send_ack = GatewayRunner._send_busy_ack_reply
        runtime._original_completion_group = GatewayRunner._deliver_async_delegation_group

        async def completion_group(runner,group):
            from tools.async_delegation import claim_event_delivery,drop_completion_delivery,release_completion_delivery
            remaining=[]
            for evt in group:
                did=evt.get('delegation_id')
                cancelled=runtime._cancelled_delegations.get(did)
                if not cancelled or cancelled.get('owner')!=evt.get('parent_session_id'):
                    remaining.append(evt);continue
                claim=claim_event_delivery(evt,'hermes-interaction-stop')
                if claim is None:
                    continue  # Owned elsewhere or already settled; native delivery state is authoritative.
                if not drop_completion_delivery(did,claim):
                    release_completion_delivery(did,claim)
                    return False
                runtime._cancelled_delegations.pop(did,None)
                runtime._save_cancellations()
                logger.info('Hermes Interaction: cancelled background completion consumed without a new turn')
            if remaining:
                return await runtime._original_completion_group(runner,remaining)
            return True

        completion_group._hermes_interaction=True
        self._overrides.set(GatewayRunner, "_deliver_async_delegation_group", completion_group)

        async def send_ack(runner, event, adapter, message):
            if not runtime.is_telegram(event.source):
                return await runtime._original_send_ack(runner,event,adapter,message)
            state=runtime._state_for_source(event.source)
            if state:
                runtime.registry.receipt(state.session_id, getattr(event, "text", ""), message=message)
                state.activity=message
                await runtime._send_status(state,state.render(time.monotonic(),runtime.slow_after) if state.progress else message)
            else:
                await adapter.send(str(event.source.chat_id),message,
                    metadata=runner._thread_metadata_for_source(event.source))

        async def idle_stop(runner,event):
            if not runtime.is_telegram(event.source):
                return await runtime._original_idle_stop(runner,event)
            entry=await runner.async_session_store.get_or_create_session(event.source)
            stopped=runtime._stop_owned_children(entry.session_id)
            state=runtime.registry.by_key(entry.session_key)
            if stopped and state:
                state.status_closed=True
                runtime.registry.finish(state.session_id, failed=False, interrupted=True, completed=False)
            result=await runtime._original_idle_stop(runner,event)
            if stopped:
                if state:
                    state.ended=True;state.interrupted=True
                    async with state.send_lock:
                        state.status_closed=True
                        with suppress(Exception):
                            if state.status_message_id:
                                await state.adapter.delete_message(state.source.chat_id,state.status_message_id)
                    runtime.registry.pop(state.session_id,expected=state)
                from gateway.platforms.base import EphemeralReply
                return EphemeralReply(tr("好，正在停止后台任务。", runtime.language))
            return result

        send_ack._hermes_interaction=True
        idle_stop._hermes_interaction=True
        self._overrides.set(GatewayRunner, "_send_busy_ack_reply", send_ack)
        self._overrides.set(GatewayRunner, "_handle_stop_command", idle_stop)

        async def stop(runner, event, quick_key, source):
            if not runtime.is_telegram(source):
                return await runtime._original_stop(runner, event, quick_key, source)
            state = runtime.registry.by_key(quick_key)
            finding = state.finding if state else ""
            activity = (state.activity or state.phase) if state else ""
            if state and state.progress:
                snapshot = state.progress.snapshot()
                finding, activity = snapshot["finding"], snapshot["activity"]
            if state:
                runtime._stop_owned_children(state.session_id)
                # Capture and retire this turn before native stop yields. A successor
                # admitted during platform cleanup must keep its own state and bubble.
                state.status_closed=True
                runtime.registry.finish(state.session_id, failed=False, interrupted=True, completed=False)
            result = await runtime._original_stop(runner, event, quick_key, source)
            if state:
                async with state.send_lock:
                    state.status_closed=True
                    if state.status_message_id:
                        with suppress(Exception):
                            await state.adapter.delete_message(state.source.chat_id,state.status_message_id)
                        if state.status_message_id in state.cleanup_ids:
                            state.cleanup_ids.remove(state.status_message_id)
                        state.status_message_id=None
            text = "好，已请求停止。"
            if finding:
                text += "\n已经确认：" + finding
            elif activity:
                text += "\n刚才在做：" + activity
            text += "\n之前的操作不会自动撤销。"
            return type(result)(localize(text, runtime.language)) if isinstance(result, str) else result

        stop._hermes_interaction = True
        busy_text._hermes_interaction = True
        self._overrides.set(GatewayRunner, "_busy_stop_command", stop)

        self._overrides.set(GatewayRunner, "_run_agent_notify_long_running", notify)
        self._overrides.set(GatewayRunner, "_compose_busy_ack_message", busy_text)

    def uninstall(self) -> None:
        self.intake.close()
        for cleanup in reversed(self._control_cleanup):
            with suppress(Exception):
                cleanup()
        self._control_cleanup.clear()
        with self.actions._lock:
            self.actions.pending.clear()
            self.actions.menus.clear()
        with self.registry._lock:
            for state in self.registry._states.values():
                state.status_closed = True
            self.registry._states.clear()
        self._overrides.rollback()
        self._runner_cls = None
        self._wired.clear()
        self._raw_sends.clear()
        self._status_cooldowns.clear()
        for consumer, (original_ref, installed_ref, active, owned) in list(self._stream_overrides.items()):
            active[0] = False
            if consumer._clean_for_display is installed_ref():
                if owned:
                    consumer._clean_for_display = original_ref()
                else:
                    del consumer._clean_for_display
        self._stream_overrides.clear()
        for task in self._background_tasks.values():
            task.cancel()
        self._background_tasks.clear()

    def _root(self,sid):
        with self._background_lock:
            return self._child_roots.get(sid,sid)

    def _has_background(self,sid):
        with self._background_lock:
            return bool(self._children.get(sid))

    def child_start(self,parent_session_id="",child_session_id="",**kwargs):
        root=self._root(parent_session_id)
        if not child_session_id or self.registry.get(root) is None:
            return
        with self._background_lock:
            self._child_roots[child_session_id]=root
            self._children.setdefault(root,set()).add(child_session_id)

    def child_stop(self,parent_session_id="",child_session_id="",**kwargs):
        root=self._root(child_session_id)
        with self._background_lock:
            self._children.get(root,set()).discard(child_session_id)
        state=self.registry.get(root)
        if state and state.progress is not None:
            with self.registry._lock:
                state.progress.close_owner(child_session_id)
                state.active_tools = len(state.progress.active)
        if state and not self._has_background(root):
            state.activity="后台步骤已结束，正在核对结果。"
            state.last_event_at=time.monotonic()

    def _state_for_source(self,source):
        return self._state_for_chat(source.chat_id,getattr(source,"thread_id",None))

    def _state_for_chat(self,chat_id,thread,adapter=None):
        with self.registry._lock:
            states=[s for s in self.registry._states.values() if
                (adapter is None or s.adapter is adapter) and
                str(getattr(s.source,"chat_id",None))==str(chat_id) and
                str(getattr(s.source,"thread_id",None))==str(thread)]
        return states[0] if len(states)==1 else None

    def _wire_send(self,adapter):
        if adapter in self._raw_sends:return
        original=adapter.send
        if hasattr(adapter, "_edit_text"):
            from plugins.platforms.telegram.telegram_ids import normalize_telegram_chat_id
            async def edit_text(chat_id, message_id, text, parse_mode=None):
                kwargs = dict(chat_id=normalize_telegram_chat_id(chat_id), message_id=int(message_id), text=text)
                kwargs.update(adapter._link_preview_kwargs())
                if parse_mode is not None:
                    kwargs["parse_mode"] = parse_mode
                await adapter._bot.edit_message_text(**kwargs)
            self._overrides.set(adapter, "_edit_text", edit_text)
        self._raw_sends[adapter]=original
        runtime=self
        async def send(chat_id,content,reply_to=None,metadata=None):
            # A root private chat already supplies conversational context. Avoid repeating the
            # user's whole message above every reply; explicit topic routing remains untouched.
            if str(chat_id).isdigit() and not (metadata or {}).get("thread_id"):
                reply_to = None
            notices = {
                "⚠️ Gateway shutting down — Your current task will be interrupted.": "服务暂时离线，恢复后可以继续发消息。",
                "💾 Self-improvement review: User profile updated": "已更新使用偏好。",
            }
            content = localize(notices[content], runtime.language) if isinstance(content, str) and content in notices else content
            state=runtime._state_for_chat(chat_id,(metadata or {}).get("thread_id"),adapter=adapter)
            if state and runtime._has_background(state.session_id) and (
                acknowledgement_only(content) or (state.receipt_text and str(content).strip()==state.receipt_text)):

                state.activity=safe_status_text(content).replace("**","")
                if state.progress:
                    state.progress.plan(state.activity, owner=state.session_id)
                state.last_event_at=time.monotonic()
                await runtime._send_status(state,state.render(time.monotonic(),runtime.slow_after))
                if state.status_message_id:
                    from gateway.platforms.base import SendResult
                    return SendResult(success=True,message_id=state.status_message_id)
            return await original(chat_id,content,reply_to=reply_to,metadata=metadata)
        self._overrides.set(adapter, "send", send)

    def _ensure_background_watch(self,state):
        previous=self._background_tasks.get(state.session_id)
        if previous and not previous.done():return
        self._background_tasks[state.session_id]=asyncio.create_task(self._watch_background(state.session_id))

    async def _watch_background(self,sid):
        try:
            while True:
                state=self.registry.get(sid)
                if state is None or state.ended:return
                now=time.monotonic()
                if not state.foreground_active:
                    await self._typing(state)
                    text=state.render(now,self.slow_after)
                    if text!=state.last_shown_text and now-(state.status_sent_at or 0)>=self.min_edit:
                        with suppress(Exception):
                            await self._send_status(state,text)
                await asyncio.sleep(.5)
        except asyncio.CancelledError:
            pass

    def _stop_owned_children(self,sid):
        from tools.delegate_tool_registry import list_active_subagents,interrupt_subagent
        owned=owned_children(sid,list_active_subagents())
        stopped=0
        for record in owned:
            if interrupt_subagent(record['subagent_id']):
                stopped+=1
                if record.get('delegation_id'):
                    self._cancelled_delegations[record['delegation_id']]={
                        'owner':record.get('owner_agent_session_id') or sid,'at':time.time()}
        if stopped:self._save_cancellations()
        if stopped:
            with self._background_lock:
                self._children.pop(sid,None)
        return stopped

    def _save_cancellations(self):
        cutoff=time.time()-7*86400
        retained={k:v for k,v in self._cancelled_delegations.items() if v.get('at',0)>=cutoff}
        self._cancelled_delegations=dict(list(retained.items())[-512:])
        if self._state_store is not None:
            self._state_store.set('cancelled_delegations',self._cancelled_delegations)

    @staticmethod
    def is_telegram(source):
        platform = getattr(source, "platform", "")
        return str(getattr(platform, "value", platform)).lower() == "telegram"

    def dispatch(self, event=None, **_kwargs):
        if event is None or not self.is_telegram(event.source):
            return None
        # Exact standalone phrases only; native dispatch still handles authorization and scope.
        text = (getattr(event, "text", "") or "").strip().rstrip("。！!")
        aliases = {
            **ALIASES, "打开控制菜单": "/control", "开始使用": "/hello", "你能做什么": "/hello",
        }
        return {"action": "rewrite", "text": aliases[text]} if text in aliases else None

    def session_reset(self, old_session_id="", **_kwargs):
        self.actions.invalidate_session_id(old_session_id)
        self.actions.clear_pending(old_session_id)

    def approval_wait(self, session_key="", **_kwargs):
        state = self.registry.by_key(session_key)
        if state:
            if state.approval_phase is None:
                state.approval_phase = state.phase
            text = ("正在检查操作权限。" if _kwargs.get("surface") == "smart" else
                    "等待你确认：请先处理聊天中的操作确认请求。")
            self.registry.update(state.session_id, text)

    def approval_done(self, session_key="", **_kwargs):
        state = self.registry.by_key(session_key)
        if state and state.approval_phase is not None:
            previous, state.approval_phase = state.approval_phase, None
            self.registry.update(state.session_id, previous)

    def _wire_stream(self, state):
        consumer = state.stream_holder[0] if state.stream_holder else None
        if consumer is not None and hasattr(consumer, "_clean_for_display") and consumer not in self._stream_overrides:
            original = consumer._clean_for_display
            active = [True]
            def cleaned(text):
                return original(clean_stream_text(text) if active[0] else text)
            # Weak records must not retain bound methods (and their consumer) forever.
            original_ref = weakref.WeakMethod(original) if getattr(original, "__self__", None) is not None else weakref.ref(original)
            self._stream_overrides[consumer] = (original_ref, weakref.ref(cleaned), active,
                                                "_clean_for_display" in vars(consumer))
            consumer._clean_for_display = cleaned

    def narration_request(self, request, session_id="", platform="", **_kwargs):
        root = self._root(session_id)
        state = self.registry.get(root)
        if (state is None or state.ended or state.progress is None
                or (root == session_id and platform != "telegram")):
            return None
        provider = _kwargs.get('provider', '')
        updated = with_progress_schema(request, strict_tools=provider in {'', 'openai', 'openai-codex'},
            require_note=state.progress.needs_narration(), language=self.language)
        if updated:
            optional_args = {}
            for before,after in zip(request.get('tools', []),updated.get('tools', [])):
                if not isinstance(before, dict) or not isinstance(after, dict):
                    continue
                old = before.get('function', before)
                new = after.get('function', after)
                schema = old.get('parameters', {})
                if new.get('strict') and not old.get('strict'):
                    key = (session_id, _kwargs.get('api_request_id',''), old.get('name'))
                    optional_args[key] = {name for name,prop in schema.get('properties',{}).items()
                        if name not in schema.get('required',[]) and not accepts_null(prop)}
            with self.registry._lock:
                self._narration_nulls.update(optional_args)
                self._narration_nulls = dict(list(self._narration_nulls.items())[-256:])
        return {"request": updated, "source": "hermes-interaction", "reason": "public action status"} if updated else None

    def narration_arguments(self, tool_name, args, session_id="", api_request_id="", tool_call_id="", **_kwargs):
        if not isinstance(args, dict) or PROGRESS_FIELD not in args:
            return None
        # The reserved presentation field never reaches tool hooks, approvals or execution.
        cleaned = dict(args)
        raw_note = cleaned.pop(PROGRESS_FIELD)
        note = public_text(raw_note)
        continuation = isinstance(raw_note,str) and not raw_note.strip()
        with self.registry._lock:
            optional_args = self._narration_nulls.get((session_id,api_request_id,tool_name), ())
        for key in optional_args:
            if cleaned.get(key, object()) is None:
                cleaned.pop(key)
        state = self.registry.get(self._root(session_id))
        if state and not state.ended and state.progress and (note or continuation) and tool_name not in SETUP_TOOLS | UI_TOOLS:
            state.progress.propose(session_id, api_request_id, safe_status_text(note), [(tool_call_id, tool_name)])
        return {"args": cleaned, "source": "hermes-interaction", "reason": "remove public status metadata"}

    def pre_api(self, session_id="", **_kwargs):
        root=self._root(session_id)
        if root == session_id and _kwargs.get("platform") and _kwargs["platform"] != "telegram":
            return
        self.registry.model_request(root)
        state=self.registry.get(root)
        if state:
            state.internal_status = ""
            self._wire_stream(state)
            if state.progress is not None and session_id == root:
                with self.registry._lock:
                    state.progress.initialize(_kwargs.get("user_message", ""))
            if state.progress is not None:
                state.progress.request_started(session_id, _kwargs.get("api_request_id", ""))

    def post_api(self, session_id="", **_kwargs):
        owner = session_id
        session_id=self._root(session_id)
        if owner == session_id and _kwargs.get("platform") and _kwargs["platform"] != "telegram":
            return
        state = self.registry.get(session_id)
        if state and not state.ended and state.progress:
            note = tool_note(_kwargs.get("assistant_message"))
            if note:
                text, calls = note
                state.progress.propose(owner, _kwargs.get("api_request_id", ""), safe_status_text(text), calls)
        if state and state.tool_count and not state.active_tools:
            self.registry.update(session_id, ANALYZE)

    def api_error(self, session_id="", **_kwargs):
        state = self.registry.get(self._root(session_id))
        if state:
            state.internal_status = ""
        self.registry.update(self._root(session_id), RETRY)

    def pre_tool(self, tool_name="", args=None, session_id="", **_kwargs):
        if tool_name in _SETUP_TOOLS:
            return None
        original_session_id=session_id
        session_id=self._root(session_id)
        state=self.registry.get(session_id)
        if state:
            state.internal_status = ""
        if state and original_session_id==session_id and tool_name not in {TOOL_SCHEMA['name'],PROGRESS_SCHEMA['name']}:
            state.receipt_turn=(tool_name=='delegate_task' and (args or {}).get('action','spawn') in {'spawn','steer'})
        if tool_name == PROGRESS_SCHEMA["name"]:
            self.registry.progress(session_id, (args or {}).get("activity", ""), (args or {}).get("finding", ""),
                (args or {}).get("next_step", ""), (args or {}).get("task_type", ""),
                goal=(args or {}).get("goal", ""), constraints=(args or {}).get("constraints"),
                owner=original_session_id, request_id=_kwargs.get("api_request_id", ""))
            return None
        if tool_name == TOOL_SCHEMA["name"]:
            clean = self.actions.remember(session_id, (args or {}).get("actions"))
            self.registry.update(session_id, FINALIZE)
            if clean != (args or {}).get("actions"):
                return {"action": "modify", "args": {"actions": clean}}
            return None
        self.registry.tool_started(session_id, original_session_id, _kwargs.get("tool_call_id", ""), tool_name, args)
        return None

    def post_tool(self, tool_name="", session_id="", result=None, **_kwargs):
        if tool_name in _SETUP_TOOLS:
            return
        owner = session_id
        session_id=self._root(session_id)
        if tool_name not in {TOOL_SCHEMA["name"], PROGRESS_SCHEMA["name"]}:
            self.registry.tool_finished(session_id, result, owner=owner,
                call_id=_kwargs.get("tool_call_id", ""), name=tool_name, status=_kwargs.get("status", ""))

    def model_end(self,session_id="",assistant_response="",**kwargs):
        if self._root(session_id)!=session_id:return
        state=self.registry.get(session_id)
        if state and state.receipt_turn and self._has_background(session_id) and isinstance(assistant_response,str):
            if len(assistant_response)<=320 and 'http://' not in assistant_response and 'https://' not in assistant_response:
                state.receipt_text=assistant_response.strip()

    def session_end(self, session_id="", failed=False, interrupted=False, completed=False, **_kwargs):
        if _kwargs.get("platform") and _kwargs["platform"] != "telegram":
            return
        if self._root(session_id) != session_id:
            return
        if self._has_background(session_id) and not failed and not interrupted:
            state=self.registry.get(session_id)
            if state:
                state.ended=False
            return
        self.registry.finish(session_id, failed=failed, interrupted=interrupted, completed=completed)
        if failed or interrupted:
            self.actions.clear_pending(session_id)

    async def _send_status(self, state: TurnState, text: str) -> None:
        async with state.send_lock:
            return await self._deliver_status(state, text)

    async def _deliver_status(self, state: TurnState, text: str) -> None:
        current = self.registry.get(state.session_id) if state.session_id else None
        if state.status_closed or (current is not None and current is not state):
            return
        now = time.monotonic()
        if now < max(state.status_retry_at, self._status_cooldowns.get(state.adapter, 0)):
            return
        text = localize(text, self.language)
        if not text:
            await self._typing(state)
            return
        if state.status_message_id and text == state.last_shown_text:
            return
        action = "edit" if state.status_message_id else "send"
        try:
            if state.status_message_id:
                result = await state.adapter.edit_message(
                    state.source.chat_id, state.status_message_id, text)
            else:
                from gateway.run import _interim_metadata, _non_conversational_metadata
                metadata = _interim_metadata(_non_conversational_metadata(
                    state.metadata, platform=getattr(state.source, "platform", None)))
                sender = self._raw_sends.get(state.adapter, state.adapter.send)
                result = await sender(state.source.chat_id, text, metadata=metadata)
        except Exception as error:
            self._defer_status(state, error)
            logger.debug("Interaction status %s unavailable (%s)", action, type(error).__name__)
            return
        if not getattr(result, "success", False) or (
                action == "send" and not getattr(result, "message_id", None)):
            self._defer_status(state, result)
            return
        if action == "send":
            state.status_message_id = str(result.message_id)
            if state.status_message_id not in state.cleanup_ids:
                state.cleanup_ids.append(state.status_message_id)
        state.status_failures = 0
        state.status_retry_at = 0.0
        state.status_sent_at = time.monotonic()
        state.last_shown_text = text
        self._record_delivery(state, action, text)

    def _defer_status(self, state, result):
        state.status_failures += 1
        delay = min(60.0, self.min_edit * 2 ** min(state.status_failures - 1, 8))
        retry_after = getattr(result, "retry_after", None)
        try:
            retry_after = float(retry_after.total_seconds() if hasattr(retry_after, "total_seconds") else retry_after)
        except (TypeError, ValueError, OverflowError):
            retry_after = 0.0
        now = time.monotonic()
        if math.isfinite(retry_after) and retry_after > 0:
            delay = max(delay, retry_after)
            # Flood control applies to the bot, including other turns and early acknowledgements.
            self._status_cooldowns[state.adapter] = max(
                self._status_cooldowns.get(state.adapter, 0), now + retry_after)
        state.status_retry_at = now + delay

    @staticmethod
    def _record_delivery(state, action, text):
        snapshot = state.progress.snapshot() if state.progress else {"source": "legacy", "stage": "unknown"}
        logger.info("Hermes Interaction: status %s id=%s source=%s stage=%s age=%.2fs text_hash=%s",
            action, state.status_message_id, snapshot["source"], snapshot["stage"],
            time.monotonic()-state.created_at, hashlib.sha256(text.encode()).hexdigest()[:12])

    async def _typing(self, state):
        if not hasattr(state.adapter, "send_typing"):
            return
        now = time.monotonic()
        if now < self._status_cooldowns.get(state.adapter, 0):
            return
        if now - state.last_typing_at >= 4:
            state.last_typing_at = now
            with suppress(Exception):
                await state.adapter.send_typing(state.source.chat_id, metadata=state.metadata)

    def _register_action_callback(self, state: TurnState) -> None:
        if (self.registry.get(state.session_id) is not state or state.status_closed
                or state.callback_registered or state.failed or state.interrupted):
            return
        actions = self.actions.take_pending(state.session_id)
        if not actions or not hasattr(state.adapter, "register_post_delivery_callback"):
            return
        state.callback_registered = True

        async def attach():
            await self.telegram.attach(state, actions)

        state.adapter.register_post_delivery_callback(
            state.session_key, attach, generation=state.generation)

    async def _noop_lifecycle(self) -> None:
        return None

    def prepare_status_lifecycle(self, runner, turn_ctx, executor_holder):
        source = turn_ctx.source
        adapter = runner._adapter_for_source(source)
        if not adapter or not turn_ctx.session_id or not turn_ctx.session_key:
            return self._noop_lifecycle()
        state = TurnState(
            session_id=turn_ctx.session_id, session_key=turn_ctx.session_key,
            source=source, adapter=adapter, generation=turn_ctx.run_generation,
            stream_holder=turn_ctx.stream_consumer_holder,
            cleanup_ids=turn_ctx._cleanup_msg_ids, metadata=turn_ctx._status_thread_metadata,
            loop=asyncio.get_running_loop(), soft_wait=self.soft_wait,
            progress=TaskProgress(),
            language=self.language, emoji=self.emoji,
        )
        early = self.intake.take(source)
        previous=self.registry.get(state.session_id)
        if previous and (previous.status_closed or (
                previous.foreground_active and previous.generation != state.generation
                and not self._has_background(state.session_id))):
            # Native cleanup still owns this foreground message. Reusing it lets an
            # old finalizer delete the successor's progress after /stop or eviction.
            previous = None
        if previous is None or previous.ended:
            previous = early or previous
        if previous:
            state.send_lock=previous.send_lock
            state.status_message_id=previous.status_message_id
            state.status_sent_at=previous.status_sent_at
            state.status_retry_at=previous.status_retry_at
            state.status_failures=previous.status_failures
            state.last_shown_text=previous.last_shown_text
            state.finding=previous.finding
            if self._has_background(state.session_id):
                state.progress=previous.progress or state.progress
            if state.status_message_id and state.status_message_id not in state.cleanup_ids:
                state.cleanup_ids.append(state.status_message_id)
        self.actions.invalidate_session(state.session_key)
        self.actions.clear_pending(state.session_id)
        self.registry.bind(state)
        return self._run_status_lifecycle(turn_ctx, executor_holder, state)

    async def status_lifecycle(self, runner, turn_ctx, executor_holder) -> None:
        """Async convenience entry used by tests; production uses prepare_status_lifecycle()."""
        await self.prepare_status_lifecycle(runner, turn_ctx, executor_holder)

    async def _run_status_lifecycle(self, turn_ctx, executor_holder, state: TurnState) -> None:
        try:
            await asyncio.sleep(self.delay)
            while True:
                if self.registry.get(state.session_id) is not state or state.status_closed:
                    break
                worker = executor_holder[0]
                if worker is not None and getattr(worker, "done", lambda: False)():
                    break
                agent = turn_ctx.agent_holder[0]
                now = time.monotonic()
                self._wire_stream(state)
                await self._typing(state)
                text = state.render(now, self.slow_after)
                if (state.progress and state.progress.stage == "opening" and not state.tool_count
                        and state.last_shown_text and now - state.created_at < self.slow_after):
                    text = state.last_shown_text
                if state.progress is None and agent is not None and getattr(agent, "_pending_steer", None) and not state.ended:
                    text = STEER + ("\n已确认：" + state.finding if state.finding else "")
                if text != state.last_shown_text and now - (state.status_sent_at or 0) >= self.min_edit:
                    await self._send_status(state, text)
                await asyncio.sleep(0.25)
        except asyncio.CancelledError:
            pass
        except Exception:
            logger.debug("Interaction status lifecycle failed", exc_info=True)
        finally:
            if self.registry.get(state.session_id) is state:
                if state.status_message_id and (state.failed or state.interrupted):
                    with suppress(Exception):
                        await self._send_status(state, state.phase)
                if self._has_background(state.session_id) and not state.failed and not state.interrupted:
                    if state.status_message_id in state.cleanup_ids:
                        state.cleanup_ids.remove(state.status_message_id)
                    if self.registry.get(state.session_id) is state:
                        state.ended=False
                        state.foreground_active=False
                        self._ensure_background_watch(state)
                else:
                    self._register_action_callback(state)
                    removed=self.registry.pop(state.session_id, expected=state)
                    if removed is state:
                        with self._background_lock:
                            for child,root in list(self._child_roots.items()):
                                if root==state.session_id:self._child_roots.pop(child,None)
                            self._children.pop(state.session_id,None)
