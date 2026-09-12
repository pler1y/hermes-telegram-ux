"""Server-side, one-shot contextual Telegram actions."""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
import json
import logging
import secrets
import threading
import time
from typing import Any
from .i18n import tr, package_language

logger = logging.getLogger(__name__)
TTL_SECONDS = 30 * 60
MAX_MENUS = 256
MAX_ACTIONS = 3


def normalize_actions(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    result: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for item in value:
        if len(result) >= MAX_ACTIONS:
            break
        if not isinstance(item, dict):
            continue
        label = " ".join(str(item.get("label") or "").split()).strip()[:24]
        prompt = str(item.get("prompt") or "").strip()[:1500]
        if not (2 <= len(label) <= 24 and 2 <= len(prompt) <= 1500):
            continue
        key = (label, prompt)
        if key in seen:
            continue
        seen.add(key)
        result.append({"label": label, "prompt": prompt})
    return result


@dataclass
class MenuState:
    token: str
    session_key: str
    user_id: str
    chat_id: str
    thread_id: str | None
    message_id: str
    actions: list[dict[str, str]]
    created_at: float
    session_id: str = ""
    adapter: Any = None


class ActionStore:
    def __init__(self, clock=time.monotonic):
        self.clock = clock
        self.pending: dict[str, list[dict[str, str]]] = {}
        self.menus: OrderedDict[str, MenuState] = OrderedDict()
        self._lock = threading.RLock()

    def remember(self, session_id: str, actions: Any) -> list[dict[str, str]]:
        clean = normalize_actions(actions)
        with self._lock:
            if clean:
                self.pending[session_id] = clean
            else:
                self.pending.pop(session_id, None)
        return clean

    def take_pending(self, session_id: str) -> list[dict[str, str]]:
        with self._lock:
            return self.pending.pop(session_id, [])

    def invalidate_session_id(self, session_id: str) -> None:
        with self._lock:
            for token, state in list(self.menus.items()):
                if session_id and state.session_id == session_id:
                    self.menus.pop(token, None)

    def invalidate_session(self, session_key: str) -> None:
        with self._lock:
            for token, state in list(self.menus.items()):
                if state.session_key == session_key:
                    self.menus.pop(token, None)

    def clear_pending(self, session_id: str) -> None:
        with self._lock:
            self.pending.pop(session_id, None)

    def _prune(self) -> None:
        cutoff = self.clock() - TTL_SECONDS
        for token, state in list(self.menus.items()):
            if state.created_at <= cutoff:
                self.menus.pop(token, None)
        while len(self.menus) >= MAX_MENUS:
            self.menus.popitem(last=False)

    def create_menu(self, *, session_key: str, user_id: str, chat_id: str,
                    thread_id: str | None, message_id: str,
                    actions: list[dict[str, str]], session_id: str = "", adapter=None) -> MenuState:
        with self._lock:
            self._prune()
            token = secrets.token_hex(8)
            state = MenuState(token, session_key, user_id, chat_id, thread_id,
                              message_id, actions, self.clock(), session_id, adapter)
            self.menus[token] = state
            return state

    def peek(self, token: str) -> MenuState | None:
        with self._lock:
            self._prune()
            return self.menus.get(token)

    def claim(self, token: str, index: int) -> tuple[MenuState, dict[str, str]] | None:
        with self._lock:
            self._prune()
            state = self.menus.get(token)
            if state is None or not (0 <= index < len(state.actions)):
                return None
            self.menus.pop(token, None)
            return state, state.actions[index]


class TelegramActions:
    def __init__(self, ctx, store: ActionStore):
        self.ctx = ctx
        language = ctx.get_config("language", "package")
        self.language = language if language in {"zh", "en"} else package_language()
        self.store = store

    def wire(self, application, adapter):
        from telegram.ext import CallbackQueryHandler

        async def callback(update, context):
            await self.callback(update, context, adapter=adapter)

        handler = CallbackQueryHandler(callback, pattern=r"^hi:")
        application.add_handler(handler, group=-1)
        logger.info("Hermes Interaction: contextual Telegram actions registered")
        return lambda: application.remove_handler(handler, group=-1)

    async def attach(self, state, actions: list[dict[str, str]]) -> bool:
        adapter = state.adapter
        if not actions or not adapter or state.failed or state.interrupted:
            return False
        source = state.source
        user_id = str(getattr(source, "user_id", "") or "")
        chat_id = str(getattr(source, "chat_id", "") or "")
        thread = getattr(source, "thread_id", None)
        consumer = state.stream_holder[0] if state.stream_holder else None
        message_id = str(getattr(consumer, "message_id", "") or "")
        if not user_id or not chat_id:
            return False
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup

        menu = None
        if message_id and message_id != "__no_edit__":
            menu = self.store.create_menu(
                session_key=state.session_key, user_id=user_id, chat_id=chat_id,
                thread_id=str(thread) if thread is not None else None,
                message_id=message_id, actions=actions, session_id=state.session_id, adapter=adapter,
            )
            try:
                await adapter._bot.edit_message_reply_markup(
                    chat_id=int(chat_id) if chat_id.lstrip("-").isdigit() else chat_id,
                    message_id=int(message_id), reply_markup=self._markup(menu),
                )
                return True
            except Exception:
                self.store.menus.pop(menu.token, None)
                logger.debug("Could not attach actions to final Telegram message", exc_info=True)
        try:
            kwargs = {"chat_id": int(chat_id) if chat_id.lstrip("-").isdigit() else chat_id,
                      "text": tr("接下来可以：", self.language)}
            if thread is not None:
                kwargs["message_thread_id"] = int(thread)
            sent = await adapter._bot.send_message(**kwargs)
            message_id = str(sent.message_id)
            menu = self.store.create_menu(
                session_key=state.session_key, user_id=user_id, chat_id=chat_id,
                thread_id=str(thread) if thread is not None else None,
                message_id=message_id, actions=actions, session_id=state.session_id, adapter=adapter,
            )
            await adapter._bot.edit_message_reply_markup(
                chat_id=kwargs["chat_id"], message_id=int(message_id), reply_markup=self._markup(menu))
            return True
        except Exception:
            if menu:
                self.store.menus.pop(menu.token, None)
            logger.warning("Contextual Telegram actions could not be delivered")
            return False

    @staticmethod
    def _markup(menu: MenuState):
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        rows = [[InlineKeyboardButton(action["label"], callback_data=f"hi:{menu.token}:{i}")]
                for i, action in enumerate(menu.actions)]
        return InlineKeyboardMarkup(rows)

    def _authorized(self, query, state: MenuState, adapter) -> bool:
        msg = query.message
        if not msg or not query.from_user:
            return False
        actual = (str(query.from_user.id), str(msg.chat_id),
                  str(msg.message_thread_id) if msg.message_thread_id is not None else None,
                  str(msg.message_id))
        expected = (state.user_id, state.chat_id, state.thread_id, state.message_id)
        if actual != expected or state.adapter is not adapter:
            return False
        return bool(adapter and adapter._is_callback_user_authorized(
            actual[0], chat_id=actual[1], chat_type=getattr(msg.chat, "type", None),
            thread_id=actual[2], user_name=getattr(query.from_user, "username", None)))

    async def callback(self, update, context, *, adapter) -> None:
        query = update.callback_query
        if not query or not isinstance(query.data, str):
            return
        parts = query.data.split(":")
        if len(parts) != 3:
            return
        token = parts[1]
        try:
            index = int(parts[2])
        except ValueError:
            await query.answer(tr("选项无效。", self.language), show_alert=True)
            return
        state = self.store.peek(token)
        if state is None:
            await query.answer(tr("这组选项已过期、已使用或对话已更新。请直接输入想做的事。", self.language), show_alert=True)
            return
        if not self._authorized(query, state, adapter):
            await query.answer(tr("只能由原会话中的用户操作。", self.language), show_alert=True)
            return
        claimed = self.store.claim(token, index)
        if claimed is None:
            await query.answer(tr("这组选项已使用。", self.language), show_alert=True)
            return
        state, action = claimed
        try:
            await query.answer(tr("已选择：{label}，正在提交。", self.language, label=action["label"]))
        except Exception:
            logger.debug("Selection acknowledgement failed")
        try:
            await query.edit_message_reply_markup(reply_markup=None)
        except Exception:
            logger.debug("Could not remove consumed interaction buttons")
        accepted = self.ctx.inject_message(action["prompt"], session_key=state.session_key)
        if not accepted:
            try:
                await query.message.reply_text(tr("暂时无法继续这个操作，请直接发送一条消息。", self.language))
            except Exception:
                pass


TOOL_SCHEMA = {
    "name": "interaction_actions",
    "description": (
        "When a Telegram answer is complete and 1-3 genuinely useful, safe next actions exist, "
        "call this exactly once immediately before the final answer. The UI renders the actions as "
        "one-shot contextual buttons. Do not call it for greetings, failures, ambiguous choices, "
        "or actions that would be destructive or expose secrets."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "actions": {
                "type": "array", "minItems": 1, "maxItems": 3,
                "items": {
                    "type": "object",
                    "properties": {
                        "label": {"type": "string", "description": "Short button label in the selected interface language."},
                        "prompt": {"type": "string", "description": "Concrete follow-up request to Hermes."},
                    },
                    "required": ["label", "prompt"],
                },
            }
        },
        "required": ["actions"],
    },
}


def tool_handler(actions=None, **_kwargs) -> str:
    return json.dumps({"ok": True, "count": len(normalize_actions(actions))}, ensure_ascii=False)
