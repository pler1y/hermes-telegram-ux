"""Bound Telegram navigation; action buttons re-enter Hermes' native command path."""

from collections import OrderedDict
import logging
import secrets
import time

logger = logging.getLogger(__name__)
TTL = 30 * 60
MAX_MENUS = 256

# Actions are server-side constants. A callback contains only an opaque token and index.
PAGES = {
    "home": ("从一件小事开始", "发个问题、链接或者文件过来就行。\n也可以先选一件试试。", [
        [("查点资料", "page", "search"), ("读链接或文件", "page", "read")],
        [("写几句话", "page", "write"), ("更多设置", "page", "advanced")],
    ]),
    "search": ("想查什么？", "直接告诉我想知道的事，也可以试试下面这个。", [
        [("看看最近的 AI 产品更新", "request", "帮我找最近三条普通人能直接用的 AI 产品更新，每条两句话，附官网来源。不需要深入研究。")],
    ]),
    "read": ("把内容发过来", "发链接、图片或文件，再说一句你想看什么。\n\n比如：这篇文章主要讲什么？有哪些地方需要留意？", []),
    "write": ("想写什么？", "告诉我写给谁、想说什么，或者把草稿贴过来。\n\n比如：帮我把这段话写得自然一点，意思别变。", [
        [("试一段改写", "request", "把这句话改得自然一点，只给改好的话：您好，烦请您于方便之时向我提供该文件，非常感谢您的配合。")],
    ]),
}
PAGES.update({
    "advanced": ("更多设置", "日常使用直接发消息即可。这里保留任务与设置入口。", [
        [("正在运行的任务", "command", "/agents"), ("历史对话", "command", "/sessions")],
        [("用量与限额", "command", "/usage"), ("当前设置", "command", "/reasoning")],
        [("停止当前任务", "command", "/stop")],
    ]),
})
PARENTS = {"advanced": "home","home": None, "search": "home", "read": "home", "write": "home"}
COMMANDS = frozenset(value for _, _, rows in PAGES.values() for row in rows
                     for _, kind, value in row if kind in {"command", "request"})


class WelcomeMenu:
    def __init__(self, adapter, clock=time.monotonic):
        self.adapter = adapter
        self.clock = clock
        self.states = OrderedDict()

    def _prune(self):
        for token, state in list(self.states.items()):
            if self.clock() - state["created"] >= TTL:
                self.states.pop(token, None)
        while len(self.states) >= MAX_MENUS:
            self.states.popitem(last=False)

    def _view(self, owner, page="home", submitted=None):
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup

        self._prune()
        token = secrets.token_hex(8)
        actions = {}

        def button(label, kind, value=None):
            key = str(len(actions))
            actions[key] = (kind, value, label)
            return InlineKeyboardButton(label, callback_data=f"hw:{token}:{key}")

        title, detail, layout = PAGES[page]
        if submitted:
            text = f"{submitted}\n\n也可以直接在下面继续说。"
            rows = [[button("返回", "page", page)]]
        else:
            text = title + "\n\n" + detail
            rows = [[button(*item) for item in row] for row in layout]
            parent = PARENTS[page]
            if parent is not None:
                rows.append([button("返回", "page", parent)])
        rows.append([button("关闭", "close")])
        state = {key: owner[key] for key in ("user", "chat", "thread", "message")}
        state.update(created=self.clock(), page=page, actions=actions)
        self.states[token] = state
        return token, text, InlineKeyboardMarkup(rows), state

    async def open(self, update, context):
        msg = update.effective_message
        if not msg or not msg.from_user:
            return
        if not self.adapter._should_process_message(msg, is_command=True):
            return
        if not self.adapter._is_user_authorized_from_message(msg):
            return
        if msg.chat.type != "private":
            await msg.reply_text("请在与机器人的私聊中打开开始页面。")
            return
        owner = {"user": msg.from_user.id, "chat": msg.chat_id,
                 "thread": msg.message_thread_id, "message": None}
        token, text, markup, state = self._view(owner, "advanced" if (msg.text or "").strip().rstrip("。！!") == "打开控制菜单" else "home")
        try:
            sent = await msg.reply_text(text, reply_markup=markup)
        except Exception:
            self.states.pop(token, None)
            raise
        state["message"] = sent.message_id

    def _authorized(self, query, state):
        msg = query.message
        if not msg or not query.from_user or msg.chat.type != "private":
            return False
        if (query.from_user.id, msg.chat_id, msg.message_thread_id, msg.message_id) != (
            state["user"], state["chat"], state["thread"], state["message"]
        ):
            return False
        return self.adapter._is_callback_user_authorized(
            str(query.from_user.id), chat_id=str(msg.chat_id), chat_type=msg.chat.type,
            thread_id=str(msg.message_thread_id) if msg.message_thread_id is not None else None,
            user_name=query.from_user.username,
        )

    async def _answer(self, query, text=None, *, alert=False):
        from telegram.error import TelegramError
        try:
            await query.answer(text, show_alert=alert)
        except TelegramError:
            # An expired callback acknowledgement must not prevent a valid control action.
            logger.debug("Control menu callback acknowledgement unavailable")

    async def _render(self, query, owner, page, submitted=None):
        from telegram.error import TelegramError
        token, text, markup, _ = self._view(owner, page, submitted)
        try:
            await query.edit_message_text(text, reply_markup=markup)
        except TelegramError:
            self.states.pop(token, None)
            logger.warning("Control menu display update failed; reopen /control")

    async def callback(self, update, context):
        query = update.callback_query
        if not query or not isinstance(query.data, str):
            return
        parts = query.data.split(":")
        if len(parts) != 3 or parts[0] != "hw":
            return
        _, token, choice = parts
        state = self.states.get(token)
        if not state or self.clock() - state["created"] >= TTL:
            self.states.pop(token, None)
            await self._answer(query, "这个入口已过期，发送“开始使用”可以重新打开。", alert=True)
            return
        if not self._authorized(query, state):
            await self._answer(query, "只能由打开菜单的用户在原会话中操作。", alert=True)
            return
        selected = state["actions"].get(choice)
        if selected is None:
            await self._answer(query, "选项无效，请重新打开菜单。", alert=True)
            return
        # Consume before any await. Replayed or concurrent taps cannot execute an action twice.
        self.states.pop(token)
        await self._answer(query)
        kind, value, label = selected
        if kind == "page":
            await self._render(query, state, value)
        elif kind == "close":
            from telegram.error import TelegramError
            try:
                await query.edit_message_text("随时直接发消息就行。", reply_markup=None)
            except TelegramError:
                logger.debug("Control menu close display unavailable")
        elif kind in {"command", "request"}:
            await self._render(query, state, state["page"], submitted=label)
            try:
                await self._dispatch(update, context, value)
            except Exception as error:
                # Do not retry a potentially completed action or log token-bearing SDK errors.
                logger.warning("Control menu native dispatch failed (%s)", type(error).__name__)
                from telegram.error import TelegramError
                try:
                    await query.message.reply_text("操作结果暂时无法确认，请查看 Hermes 回复后再操作。")
                except TelegramError:
                    logger.debug("Control menu failure notice unavailable")

    async def _dispatch(self, update, context, command):
        from telegram import Message, Update

        if command not in COMMANDS:
            raise ValueError("Unknown control command")
        query = update.callback_query
        payload = query.message.to_dict()
        payload.update({"from": query.from_user.to_dict(), "text": command,
                        "date": int(time.time()),
                        "entities": [{"type": "bot_command", "offset": 0,
                                      "length": len(command.split()[0])}]})
        for key in ("reply_markup", "edit_date", "reply_to_message"):
            payload.pop(key, None)
        forwarded = Update(update_id=update.update_id, message=Message.de_json(payload, context.bot))
        # Preserve clicker/topic identity and run all native authorization and busy policies.
        if command.startswith("/"):
            await self.adapter._handle_command(forwarded, context)
        else:
            payload["entities"] = []
            forwarded = Update(update_id=update.update_id, message=Message.de_json(payload, context.bot))
            await self.adapter._handle_text_message(forwarded, context)


def wire(application, adapter):
    from telegram.ext import CallbackQueryHandler, CommandHandler, MessageHandler, filters, ApplicationHandlerStop
    menu = WelcomeMenu(adapter)
    async def start(update, context):
        # Existing deep links retain their native handling.
        if getattr(context, "args", None):
            return
        await menu.open(update, context)
        raise ApplicationHandlerStop
    handlers = [CommandHandler(["start", "hello"], start),
        MessageHandler(filters.TEXT & filters.Regex(r"^(?:开始使用|你能做什么|打开控制菜单)[。！!]*$"), start),
        CallbackQueryHandler(menu.callback, pattern=r"^hw:")]
    for handler in handlers:
        application.add_handler(handler, group=-2)
    logger.info("Hermes Interaction: everyday welcome registered")
    def cleanup():
        for handler in handlers:
            application.remove_handler(handler, group=-2)
        menu.states.clear()
    return cleanup
