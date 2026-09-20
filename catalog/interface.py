"""Independent /tgux settings menu; never attached to a task status message."""
import asyncio
from collections import OrderedDict
from dataclasses import dataclass
import logging
import secrets
import time

from .preferences import CHOICES

LOG = logging.getLogger("hermes-telegram-ux-catalog")
PREFIX = "tgux2:"


@dataclass
class Card:
    token: str
    route: object
    message_id: str
    expires: float
    busy: bool = False


class TelegramInterface:
    def __init__(self, ctx, native, sdk, preferences):
        self.ctx, self.native, self.sdk = ctx, native, sdk
        self.preferences = preferences
        self.loop = asyncio.get_running_loop()
        self.cards = OrderedDict()
        self.closed = False
        self.handler = sdk["handler"](self.callback, pattern=r"^tgux2:")
        native.add_handler(self.handler)

    def prune(self):
        for token, card in list(self.cards.items()):
            if card.expires <= time.monotonic():
                self.cards.pop(token, None)
        while len(self.cards) >= 256:
            self.cards.popitem(last=False)

    def button(self, card, text, action):
        return self.sdk["button"](text, callback_data=f"{PREFIX}{card.token}:{action}")

    def markup(self, card, rows):
        return self.sdk["markup"]([[self.button(card, text, action) for text, action in row] for row in rows])

    def words(self, route):
        return self.preferences.read(route)["language"] == "zh"

    def home(self, route):
        if not self.closed and not self.loop.is_closed():
            self.loop.call_soon_threadsafe(self.schedule_home, route)
            return True
        return False

    def schedule_home(self, route):
        if not self.closed:
            self.ctx.spawn_task(self.send_home(route), name="catalog-home")

    async def send_home(self, route):
        try:
            self.prune()
            card = Card(secrets.token_hex(8), route, "", time.monotonic() + 3600)
            text, markup = self.page(card, "home")
            result = await self.native.bot.send_message(
                chat_id=route.chat_id, text=text, message_thread_id=route.thread_id,
                reply_to_message_id=route.message_id, reply_markup=markup, parse_mode=None,
            )
            card.message_id = str(result.message_id)
            self.cards[card.token] = card
        except Exception as exc:
            LOG.warning("Catalog menu unavailable (%s)", type(exc).__name__)

    def page(self, card, page):
        prefs, zh = self.preferences.read(card.route), self.words(card.route)
        if page == "settings":
            names = {"language": ("语言", "Language"),
                     "progress": ("进度提示", "Progress"), "emoji": ("提示表情", "Status emoji")}
            rows = []
            for key in CHOICES:
                value = prefs[key]
                if isinstance(value, bool):
                    value = ("开" if value else "关") if zh else ("On" if value else "Off")
                rows.append([(f"{names[key][not zh]} · {value}", "set_" + key)])
            text = "显示设置\n仅影响你在当前聊天/话题中的插件体验。修改后从下一轮任务生效。" if zh else "Display settings\nApply only to you in this chat/topic, from your next turn."
        elif page == "help":
            text = ("直接发消息开始任务；执行中可补充要求。\n/stop 停止当前任务；/new 新建会话。\n补充、排队、审批和文件交付由 Hermes 处理。\n临时气泡报告当前任务进度，回合结束后自动清理。" if zh else
                    "Send a message to start; add requirements during a task.\n/stop stops work; /new starts a session.\nHermes handles queues, approvals and file delivery.\nThe temporary status reports task progress and is removed after the turn ends.")
            rows = []
        else:
            text = "Hermes · 任务助手\n直接发消息开始，或选择下面的入口。" if zh else "Hermes · Task assistant\nSend a message or choose an entry below."
            rows = [[("示例任务" if zh else "Examples", "examples"), ("常用功能" if zh else "Commands", "commands")],
                    [("显示设置" if zh else "Settings", "settings"), ("使用帮助" if zh else "Help", "help")]]
        if page != "home":
            rows.append([("返回首页" if zh else "Home", "home")])
        rows.append([("关闭" if zh else "Close", "close")])
        return text, self.markup(card, rows)

    async def send_choices(self, card, action):
        zh = self.words(card.route)
        if action == "commands":
            choices = ["/agents", "/sessions", "/usage", "/reasoning", "/stop", "/new", "/tgux"]
            text = ("选择下方命令发送：\n/agents 任务 · /sessions 历史会话 · /usage 用量\n/reasoning 推理设置 · /stop 停止 · /new 新会话\n权限和可用功能由 Hermes 管理。" if zh else
                    "Choose a command to send:\n/agents tasks · /sessions history · /usage usage\n/reasoning settings · /stop stop · /new new session\nHermes manages access and availability.")
        elif action == "examples":
            choices = (["介绍一下你可以帮我做什么", "帮我整理一份本周计划", "帮我比较两个方案，我接下来会提供内容"] if zh else
                       ["Tell me what you can help with", "Help me plan my week", "Help me compare two options; I will send the details"])
            text = "点击下方示例发送，也可以直接输入自己的任务。" if zh else "Choose an example to send, or type your own task."
        else:
            return
        await self.native.bot.send_message(
            chat_id=card.route.chat_id, text=text, message_thread_id=card.route.thread_id,
            reply_to_message_id=card.route.message_id, parse_mode=None,
            reply_markup=self.sdk["keyboard"]([[value] for value in choices],
                resize_keyboard=True, one_time_keyboard=True, selective=True),
        )

    async def callback(self, update, context):
        query = update.callback_query
        if not query or not isinstance(query.data, str):
            return
        parts = query.data.split(":")
        card = self.cards.get(parts[1]) if len(parts) == 3 else None
        message = query.message
        allowed = (not self.closed and card and card.expires > time.monotonic() and message
                   and str(query.from_user.id) == card.route.owner_id
                   and str(message.chat.id) == card.route.chat_id
                   and str(message.message_id) == card.message_id
                   and str(getattr(message, "message_thread_id", None) or "") == str(card.route.thread_id or ""))
        if not allowed:
            await query.answer("此按钮已过期或不属于你。请发送 /tgux 打开自己的菜单。 / Open your own menu with /tgux.", show_alert=True)
            return
        if card.busy:
            await query.answer()
            return
        action = parts[2]
        card.busy = True
        try:
            await query.answer()
            if action == "close":
                self.cards.pop(card.token, None)
                try:
                    await query.delete_message()
                except Exception:
                    pass
            elif action in {"commands", "examples"}:
                await self.send_choices(card, action)
            else:
                if action.startswith("set_"):
                    self.preferences.toggle(card.route, action[4:])
                    page = "settings"
                elif action in {"home", "settings", "help"}:
                    page = action
                else:
                    return
                text, markup = self.page(card, page)
                await query.edit_message_text(text=text, reply_markup=markup, parse_mode=None)
        except Exception as exc:
            LOG.warning("Catalog button unavailable (%s)", type(exc).__name__)
            try:
                await query.answer("操作未完成，请重试。 / Action failed; please retry.", show_alert=True)
            except Exception:
                pass
        finally:
            card.busy = False

    def close(self):
        if self.closed:
            return
        self.closed = True
        self.cards.clear()
        if not self.loop.is_closed():
            self.loop.call_soon_threadsafe(self.native.remove_handler, self.handler)
