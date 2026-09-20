"""Temporary bubble lifecycle, including real asynchronous delivery races."""
import asyncio
from types import SimpleNamespace
import unittest

from catalog.telegram import Route, TelegramPanels


class TaskContext:
    def __init__(self):
        self.tasks = []

    def spawn_task(self, coro, **kwargs):
        task = asyncio.create_task(coro)
        self.tasks.append(task)
        return task


class PublicAdapter:
    def __init__(self):
        self.sent, self.edits, self.deleted = [], [], []
        self.send_gate = None
        self.edit_gate = None
        self.send_failure = None
        self.edit_failure = False
        self.delete_results = []

    async def send(self, **kwargs):
        self.sent.append(kwargs)
        if self.send_gate:
            await self.send_gate.wait()
        if self.send_failure:
            raise self.send_failure
        return SimpleNamespace(success=True, message_id="owned-status")

    async def edit_message(self, **kwargs):
        self.edits.append(kwargs)
        if self.edit_gate:
            await self.edit_gate.wait()
        if self.edit_failure:
            return SimpleNamespace(success=False)
        return SimpleNamespace(success=True)

    async def delete_message(self, **kwargs):
        self.deleted.append(kwargs)
        result = self.delete_results.pop(0) if self.delete_results else True
        if isinstance(result, Exception):
            raise result
        return result


class ForbiddenStatusUI:
    def __getattr__(self, name):
        raise AssertionError("Temporary status must not access UI: " + name)


class TemporaryTransportTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.ctx, self.adapter = TaskContext(), PublicAdapter()
        self.expired = []
        self.transport = TelegramPanels(self.ctx, self.adapter, 0.025, 1,
            self.expire, interface=ForbiddenStatusUI(), cleanup_delay=0.01)
        self.key = ("session", "turn")
        self.route = Route("-10042", "user-message", "7", "user")

    def expire(self, key):
        self.expired.append(key)
        return "状态更新已停止"

    async def asyncTearDown(self):
        if self.adapter.send_gate:
            self.adapter.send_gate.set()
        if self.adapter.edit_gate:
            self.adapter.edit_gate.set()
        self.transport.close()
        await asyncio.sleep(0)
        await asyncio.wait_for(asyncio.gather(*self.ctx.tasks, return_exceptions=True), 2)

    async def until(self, condition, timeout=1):
        async def wait():
            while not condition():
                await asyncio.sleep(0.001)
        await asyncio.wait_for(wait(), timeout)

    def publish(self, text, terminal=False, route=None):
        self.transport.publish(self.key, route or self.route, text, terminal)

    async def start(self):
        self.publish("🤔 正在思考中…")
        await self.until(lambda: bool(self.adapter.sent))
        await self.until(lambda: bool(self.transport.panels[self.key].message_id))

    async def finish(self):
        self.publish("✍️ 正在整理最终回答…", True)
        await self.until(lambda: self.key not in self.transport.panels)

    async def test_same_message_edits_and_then_deletes_without_keyboard(self):
        await self.start()
        self.publish("🔎 正在搜索上海天气…")
        await self.until(lambda: bool(self.adapter.edits))
        self.publish("📊 正在整理天气预报…")
        await self.until(lambda: len(self.adapter.edits) == 2)
        await self.finish()
        self.assertEqual(len(self.adapter.sent), 1)
        self.assertEqual(self.adapter.sent[0]["metadata"], {"thread_id": "7"})
        self.assertEqual(self.adapter.sent[0]["reply_to"], "user-message")
        self.assertTrue(all(item["message_id"] == "owned-status" for item in self.adapter.edits))
        self.assertTrue(self.adapter.edits[-1]["finalize"])
        self.assertEqual(self.adapter.deleted, [{"chat_id": "-10042", "message_id": "owned-status"}])
        self.assertFalse(any("reply_markup" in item for item in self.adapter.sent + self.adapter.edits))

    async def test_identical_updates_are_deduplicated_and_burst_is_coalesced(self):
        await self.start()
        for unused in range(5):
            self.publish("🤔 正在思考中…")
        await asyncio.sleep(0.04)
        self.assertFalse(self.adapter.edits)
        self.publish("搜索 1")
        self.publish("搜索 2")
        self.publish("搜索 3")
        await self.until(lambda: bool(self.adapter.edits))
        self.assertEqual([item["content"] for item in self.adapter.edits], ["搜索 3"])
        await self.finish()

    async def test_complete_before_worker_starts_never_sends_late_bubble(self):
        self.transport.accept(self.key, self.route, "开始", False)
        self.transport.accept(self.key, self.route, "最终整理", True)
        await asyncio.gather(*self.ctx.tasks)
        self.assertFalse(self.adapter.sent or self.adapter.deleted)
        self.publish("迟到的搜索事件")
        await asyncio.sleep(0.01)
        self.assertFalse(self.adapter.sent)

    async def test_initial_feedback_is_preserved_when_tool_events_are_already_queued(self):
        self.transport.accept(self.key, self.route, "🤔 正在思考中…", False)
        self.transport.accept(self.key, self.route, "🔎 正在搜索上海天气…", False)
        await self.until(lambda: bool(self.adapter.edits))
        self.assertEqual(self.adapter.sent[0]["content"], "🤔 正在思考中…")
        self.assertEqual(self.adapter.edits[0]["content"], "🔎 正在搜索上海天气…")
        await self.finish()

    async def test_terminal_without_known_turn_cannot_create_message(self):
        self.publish("最终整理", True)
        self.publish("迟到的开始")
        await asyncio.sleep(0.01)
        self.assertFalse(self.adapter.sent)
        self.assertFalse(self.transport.panels)

    async def test_completion_during_initial_send_awaits_id_then_cleans(self):
        self.adapter.send_gate = asyncio.Event()
        self.publish("开始")
        await self.until(lambda: bool(self.adapter.sent))
        self.publish("最终整理", True)
        await self.until(lambda: self.transport.panels[self.key].terminal)
        self.assertFalse(self.adapter.deleted)
        self.adapter.send_gate.set()
        await self.until(lambda: self.key not in self.transport.panels)
        self.assertEqual(len(self.adapter.sent), 1)
        self.assertEqual(self.adapter.edits[-1]["content"], "最终整理")
        self.assertEqual(self.adapter.deleted[0]["message_id"], "owned-status")

    async def test_completion_during_edit_flushes_finalizing_not_stale_content(self):
        await self.start()
        self.adapter.edit_gate = asyncio.Event()
        self.publish("搜索天气")
        await self.until(lambda: bool(self.adapter.edits))
        self.publish("最终整理", True)
        self.publish("迟到的读取事件")
        await self.until(lambda: self.transport.panels[self.key].terminal)
        self.adapter.edit_gate.set()
        await self.until(lambda: self.key not in self.transport.panels)
        self.assertEqual([item["content"] for item in self.adapter.edits], ["搜索天气", "最终整理"])
        self.assertEqual(len(self.adapter.sent), 1)
        self.assertEqual(len(self.adapter.deleted), 1)

    async def test_cleanup_window_cannot_be_overwritten_or_resurrected(self):
        self.transport.cleanup_delay = 0.08
        await self.start()
        self.publish("最终整理", True)
        await self.until(lambda: self.transport.panels[self.key].cleaning)
        self.publish("旧状态")
        self.publish("另一个结束文案", True)
        await asyncio.sleep(0.02)
        self.assertFalse(self.adapter.deleted)
        await self.until(lambda: self.key not in self.transport.panels)
        self.publish("已经删除之后的旧事件")
        await asyncio.sleep(0.01)
        self.assertEqual([item["content"] for item in self.adapter.edits], ["最终整理"])
        self.assertEqual(len(self.adapter.sent), 1)

    async def test_terminal_wakes_throttle_without_waiting_interval(self):
        self.transport.interval = 10
        await self.start()
        self.publish("搜索天气")
        await asyncio.sleep(0.01)
        await self.finish()
        self.assertEqual([item["content"] for item in self.adapter.edits], ["✍️ 正在整理最终回答…"])

    async def test_discard_during_send_awaits_known_id_and_cleans(self):
        self.adapter.send_gate = asyncio.Event()
        self.publish("开始")
        await self.until(lambda: bool(self.adapter.sent))
        self.transport.discard(self.key)
        await self.until(lambda: self.transport.panels[self.key].stopping)
        self.adapter.send_gate.set()
        await self.until(lambda: self.key not in self.transport.panels)
        self.assertEqual(len(self.adapter.sent), 1)
        self.assertFalse(self.adapter.edits)
        self.assertEqual(len(self.adapter.deleted), 1)
        self.publish("迟到事件")
        await asyncio.sleep(0.01)
        self.assertEqual(len(self.adapter.sent), 1)

    async def test_unload_during_send_cleans_acknowledged_message(self):
        self.adapter.send_gate = asyncio.Event()
        self.publish("开始")
        await self.until(lambda: bool(self.adapter.sent))
        self.transport.close()
        self.adapter.send_gate.set()
        await self.until(lambda: self.key not in self.transport.panels)
        self.assertFalse(self.adapter.edits)
        self.assertEqual(len(self.adapter.deleted), 1)

    async def test_host_cancellation_during_send_preserves_ack_for_cleanup(self):
        self.adapter.send_gate = asyncio.Event()
        self.publish("开始")
        await self.until(lambda: bool(self.adapter.sent))
        self.ctx.tasks[0].cancel()
        await asyncio.sleep(0.01)
        self.adapter.send_gate.set()
        await self.until(lambda: self.key not in self.transport.panels)
        result = await asyncio.gather(*self.ctx.tasks, return_exceptions=True)
        self.assertIsInstance(result[0], asyncio.CancelledError)
        self.assertEqual(len(self.adapter.deleted), 1)

    async def test_unknown_send_timeout_is_never_retried(self):
        self.adapter.send_failure = TimeoutError("secret")
        self.publish("开始")
        await self.until(lambda: bool(self.ctx.tasks) and self.ctx.tasks[0].done())
        self.publish("搜索")
        self.publish("最终整理", True)
        self.publish("迟到事件")
        await asyncio.sleep(0.01)
        self.assertEqual(len(self.adapter.sent), 1)
        self.assertFalse(self.adapter.deleted or self.adapter.edits)

    async def test_edit_failure_deletes_known_message_without_replacement(self):
        await self.start()
        self.adapter.edit_failure = True
        self.publish("搜索天气")
        await self.until(lambda: self.key not in self.transport.panels)
        self.publish("新状态")
        await asyncio.sleep(0.01)
        self.assertEqual(len(self.adapter.sent), 1)
        self.assertEqual(len(self.adapter.deleted), 1)

    async def test_delete_failure_is_bounded_and_cannot_fail_native_answer(self):
        self.adapter.delete_results = [RuntimeError("secret"), False]
        await self.start()
        await self.finish()
        result = await asyncio.gather(*self.ctx.tasks, return_exceptions=True)
        self.assertEqual(result, [None])
        self.assertEqual(len(self.adapter.deleted), 2)
        self.assertEqual(len(self.adapter.sent), 1)

    async def test_transient_delete_failure_gets_one_bounded_retry(self):
        self.adapter.delete_results = [False, True]
        await self.start()
        await self.finish()
        self.assertEqual(len(self.adapter.deleted), 2)

    async def test_status_expiry_deletes_bubble_without_stopping_native_task(self):
        self.transport.ttl = 0.02
        await self.start()
        await self.until(lambda: self.key not in self.transport.panels)
        self.assertEqual(self.expired, [self.key])
        self.assertEqual(len(self.adapter.deleted), 1)
        self.assertEqual(len(self.adapter.sent), 1)

    async def test_changed_route_cannot_edit_or_delete_another_chat(self):
        await self.start()
        self.publish("发错聊天", route=Route("999", "other"))
        await asyncio.sleep(0.04)
        self.assertFalse(self.adapter.edits)
        await self.finish()
        self.assertTrue(all(item["chat_id"] == "-10042" for item in self.adapter.edits + self.adapter.deleted))

    async def test_cancellation_shortens_cleanup_window(self):
        self.transport.cleanup_delay = 5
        await self.start()
        self.publish("最终整理", True)
        await self.until(lambda: self.transport.panels[self.key].cleaning)
        self.transport.discard(self.key)
        await self.until(lambda: self.key not in self.transport.panels)
        self.assertEqual(len(self.adapter.deleted), 1)

    async def test_configured_cleanup_delay_is_finite_and_bounded(self):
        for value, expected in ((-1, 0), (9, 5), ("nan", 1), (None, 1), (0.25, 0.25)):
            transport = TelegramPanels(self.ctx, self.adapter, 1, 60, self.expire, cleanup_delay=value)
            self.assertEqual(transport.cleanup_delay, expected)
            transport.close()


if __name__ == "__main__":
    unittest.main()
