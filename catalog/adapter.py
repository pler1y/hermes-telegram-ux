"""A narrow public-hook adapter. Imports only stdlib and this distribution.

An ingress ticket is plugin-owned data carried by Python's ContextVar. It is a
single-use, short-lived association, not a lookup of Hermes session internals.
If a host does not propagate that context, live display is omitted. Native execution and
final delivery continue independently.
"""
from contextvars import ContextVar
from dataclasses import dataclass
from functools import partial
import logging
import math
from threading import RLock
import time

from .model import Turn, identity
from .presentation import status_text
from .telegram import Route, TelegramPanels
from .experience import TOOL, SCHEMA, progress_tool, turn_guidance
from .language import resolve_language

LOG = logging.getLogger("hermes-telegram-ux-catalog")
OBSERVERS = (
    "pre_tool_call", "post_tool_call", "pre_api_request", "post_api_request",
    "api_request_error", "pre_approval_request", "post_approval_response", "on_interim_message",
    "subagent_start", "subagent_stop", "post_llm_call",
)
HOOKS = ("pre_gateway_dispatch", "pre_llm_call", *OBSERVERS,
         "on_session_end", "on_session_finalize", "on_session_reset")


def bounded_number(value, default, low, high):
    try:
        number = float(value)
        return min(high, max(low, number)) if math.isfinite(number) else default
    except (ValueError, TypeError):
        return default


def platform_name(value):
    return getattr(value, "value", value)


@dataclass
class IngressTicket:
    event: object
    transport: object
    created: float
    consumed: bool = False


class HermesCatalogAdapter:
    def __init__(self, ctx, clock=time.monotonic):
        self.ctx, self.clock = ctx, clock
        language = ctx.get_config("language", "auto")
        self.language = language if language in ("auto", "zh", "en") else "auto"
        self.interval = bounded_number(ctx.get_config("update_interval", 1.5), 1.5, 1, 30)
        self.ttl = bounded_number(ctx.get_config("status_ttl", 600), 600, 30, 3600)
        self.cleanup_delay = bounded_number(ctx.get_config("cleanup_delay", 1), 1, 0, 5)
        self.lock = RLock()
        self.turns, self.routes = {}, {}
        self.transport = None
        self.closed = False
        self.ingress = ContextVar("catalog_ingress", default=None)

    def register(self):
        for hook in HOOKS:
            callback = partial(self.observe, hook) if hook in OBSERVERS else getattr(self, hook)
            self.ctx.register_hook(hook, callback)
        self.ctx.register_platform_handler("telegram", self.wire_telegram)
        self.ctx.register_tool(name=TOOL, toolset="telegram_ux", schema=SCHEMA, handler=progress_tool,
                               description="Public task milestones for one temporary Telegram status message")
        self.ctx.on_unload(self.close)

    def wire_telegram(self, native, adapter):
        with self.lock:
            if self.closed:
                return
            if self.transport:
                self.transport.close()
            self.routes.clear()
            self.transport = TelegramPanels(self.ctx, adapter, self.interval, self.ttl, self.expire,
                                             heartbeat=self.refresh, cleanup_delay=self.cleanup_delay)

    def pre_gateway_dispatch(self, event=None, **kwargs):
        # This hook precedes auth: record only. No network, no reply, no directive.
        self.ingress.set(None)
        try:
            if self.closed or not self.transport or event is None or event.internal:
                return
            source = event.source
            if platform_name(source.platform) != "telegram":
                return
            if not identity(source.user_id) or not identity(str(event.message_id or "")):
                return
            self.ingress.set(IngressTicket(event, self.transport, self.clock()))
        except Exception:
            return None

    def claim_route(self, sender_id):
        ticket = self.ingress.get()
        if ticket is None or ticket.consumed:
            return None
        # Consume even a rejected ticket: an unrelated future turn must never reuse it.
        ticket.consumed = True
        if ticket.transport is not self.transport or self.clock() - ticket.created > 60:
            return None
        try:
            source = ticket.event.source
            if platform_name(source.platform) != "telegram" or identity(source.user_id) != identity(sender_id):
                return None
            if not identity(sender_id):
                return None
            profile = getattr(source, "profile", None)
            if profile and profile != self.ctx.profile_name:
                return None
            chat = str(source.chat_id or "")
            message = str(ticket.event.message_id or "")
            thread = str(source.thread_id) if source.thread_id else None
            if not chat.lstrip("-").isdigit() or not message.isdigit() or (thread and not thread.isdigit()):
                return None
            return Route(chat, message, thread, identity(sender_id))
        except Exception:
            return None

    def pre_llm_call(self, session_id="", turn_id="", platform="", sender_id="", parent_session_id="", user_message="", **kwargs):
        if self.closed or platform != "telegram" or parent_session_id:
            return None
        key = (identity(session_id), identity(turn_id))
        if not all(key):
            return None
        with self.lock:
            self.prune()
            if key in self.turns or len(self.turns) >= 128:
                return None
            turn = Turn(*key, touched=self.clock(), language=resolve_language(user_message, self.language))
            self.turns[key] = turn
            route = self.claim_route(sender_id)
            if route and self.transport:
                self.routes[key] = route
                # Earliest reliable public per-turn stage after authorization.
                # Schedule the initial feedback before any task-text analysis.
                self.publish(key, turn)
                turn.set_task(user_message)
        return turn_guidance() if route else None

    def find_key(self, data):
        session, turn = identity(data.get("session_id")), identity(data.get("turn_id"))
        if session and turn:
            return (session, turn) if (session, turn) in self.turns else None
        # Approval payloads can omit session_id. Join only a unique explicit turn_id.
        if turn and not session:
            matches = [key for key in self.turns if key[1] == turn]
            return matches[0] if len(matches) == 1 else None
        return None

    def observe(self, event, **kwargs):
        if self.closed:
            return None
        try:
            with self.lock:
                self.prune()
                key = self.find_key({"session_id": kwargs.get("parent_session_id"),
                                     "turn_id": kwargs.get("parent_turn_id")}) if event.startswith("subagent_") else self.find_key(kwargs)
                if key:
                    turn = self.turns[key]
                    turn.observe(event, kwargs, self.clock())
                    self.publish(key, turn)
        except Exception as exc:
            LOG.warning("Catalog event omitted (%s)", type(exc).__name__)
        # Especially pre_tool_call: never block, rewrite, or approve an action.
        return None

    def publish(self, key, turn, ending=None):
        route = self.routes.get(key)
        if route and self.transport:
            self.transport.publish(key, route, self.render(turn, ending), bool(ending))

    def render(self, turn, ending=None):
        now = self.clock()
        return status_text(turn, turn.language, ending, now)

    def refresh(self, key):
        # Presentation aging only: no fabricated heartbeat activity, no TTL
        # extension, no model polling and no ownership of the native response.
        with self.lock:
            turn = self.turns.get(key)
            if self.closed or turn is None or turn.finalizing:
                return None
            return self.render(turn)

    def on_session_end(self, completed=False, failed=False, interrupted=False, **kwargs):
        with self.lock:
            key = self.find_key(kwargs)
            if key is None:
                return None
            # Agent completion is not a Telegram delivery receipt. The transport
            # uses a short bounded window, then removes only its own message.
            ending = "interrupted" if interrupted else "failed" if failed else "finalizing" if completed else "unknown_end"
            self.publish(key, self.turns[key], ending)
            self.turns.pop(key, None)
            self.routes.pop(key, None)
        return None

    def on_session_finalize(self, session_id="", **kwargs):
        self.discard_session(session_id)

    def on_session_reset(self, session_id="", old_session_id="", **kwargs):
        self.discard_session(old_session_id or session_id)

    def discard_session(self, session_id):
        with self.lock:
            for key in list(self.turns):
                if key[0] == session_id:
                    self.turns.pop(key, None)
                    self.routes.pop(key, None)
                    if self.transport:
                        self.transport.discard(key)

    def expire(self, key):
        with self.lock:
            turn = self.turns.pop(key, None)
            self.routes.pop(key, None)
            return status_text(turn, turn.language, "expired", self.clock()) if turn else None

    def prune(self):
        now = self.clock()
        for key, turn in list(self.turns.items()):
            if now - turn.touched >= self.ttl:
                self.publish(key, turn, "expired")
                self.turns.pop(key, None)
                self.routes.pop(key, None)

    def close(self):
        with self.lock:
            self.closed = True
            self.turns.clear()
            self.routes.clear()
            self.ingress.set(None)
            if self.transport:
                self.transport.close()
