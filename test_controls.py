"""Exercise natural controls through the real Telegram command entry, before busy batching."""
import unittest
from types import SimpleNamespace as S
from unittest.mock import AsyncMock,Mock,patch
from plugin.runtime import InteractionRuntime


class NativeNaturalControls(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        try:
            from plugins.platforms.telegram.adapter import TelegramAdapter
            from telegram import Update
        except ModuleNotFoundError:
            self.skipTest('Requires the actual Hermes Telegram runtime')
        self.Update=Update
        self.adapter=object.__new__(TelegramAdapter)
        self.adapter._should_process_message=Mock(return_value=True)
        self.adapter._is_user_authorized_from_message=Mock(return_value=True)
        self.adapter._log_blocked_user=Mock()
        self.adapter._ensure_forum_commands=AsyncMock()
        async def build(msg,update,kind):
            return S(text=msg.text,message_type=kind,user=msg.from_user.id,chat=msg.chat_id,thread=msg.message_thread_id)
        self.adapter._build_triggered_event=AsyncMock(side_effect=build)
        self.adapter.handle_message=AsyncMock()
        self.adapter._enqueue_text_event=Mock()
        self.handlers=[]
        self.app=S(add_handler=lambda h,group=0:self.handlers.append((h,group)),remove_handler=Mock())
        self.r=InteractionRuntime(S(get_config=lambda key,default=None:default))
        self.r._runner_cls=object()
        self.r._wire_send=Mock()
        self.r.telegram.wire=Mock()
        self.r.wire_telegram(self.app,self.adapter)

    async def asyncTearDown(self):
        if hasattr(self,'r'):
            self.r._runner_cls=None
            self.r.uninstall()

    def update(self,text='停一下。'):
        return self.Update.de_json({'update_id':99,'message':{'message_id':42,'date':1,
            'chat':{'id':123,'type':'private'},'from':{'id':7,'is_bot':False,'first_name':'Fixture'},
            'message_thread_id':11,'text':text}},None)

    def handler(self):
        found=[h for h,g in self.handlers if g==-3]
        self.assertEqual(len(found),1,'No natural command entry exists before Telegram text batching')
        return found[0]

    async def test_busy_stop_enters_native_command_path_with_original_identity(self):
        from telegram.ext import ApplicationHandlerStop
        from gateway.platforms.base import MessageType
        handler=self.handler();update=self.update()
        self.assertTrue(handler.check_update(update))
        with self.assertRaises(ApplicationHandlerStop):
            await handler.callback(update,S(bot=None))
        event=self.adapter.handle_message.call_args.args[0]
        self.assertEqual((event.text,event.message_type),('/stop',MessageType.COMMAND))
        self.assertEqual((event.user,event.chat,event.thread),(7,123,11))
        self.adapter._enqueue_text_event.assert_not_called()
        self.assertEqual(update.effective_message.text,'停一下。')

    async def test_native_authorization_still_blocks_the_translated_command(self):
        from telegram.ext import ApplicationHandlerStop
        self.adapter._is_user_authorized_from_message.return_value=False
        with self.assertRaises(ApplicationHandlerStop):
            await self.handler().callback(self.update(),S(bot=None))
        self.adapter.handle_message.assert_not_awaited()
        self.adapter._log_blocked_user.assert_called_once()

    async def test_consumed_stop_reaches_native_observer_once_with_original_update(self):
        from telegram.ext import ApplicationHandlerStop
        update = self.update()
        observer = AsyncMock(wraps=self.adapter._on_platform_update)
        self.adapter._on_platform_update = observer
        with self.assertRaises(ApplicationHandlerStop):
            await self.handler().callback(update, S(bot=None))
        self.assertIs(observer.call_args.args[0], update)
        self.assertEqual(observer.await_count, 1)
        self.assertEqual(update.effective_message.text, '停一下。')
        if hasattr(self.adapter, '_check_ingress_dispatch_stall'):
            self.assertEqual(self.adapter._updates_dispatched_total, 1)

    async def test_consumed_menu_reaches_native_observer_but_deep_link_continues(self):
        from telegram.ext import ApplicationHandlerStop, CommandHandler
        handler = next(h for h, g in self.handlers if g == -2 and isinstance(h, CommandHandler))
        observer = AsyncMock(wraps=self.adapter._on_platform_update)
        self.adapter._on_platform_update = observer
        update = self.update('/start')
        with patch('plugin.welcome.WelcomeMenu.open', new_callable=AsyncMock) as opened:
            with self.assertRaises(ApplicationHandlerStop):
                await handler.callback(update, S(bot=None, args=[]))
            opened.assert_awaited_once()
            observer.assert_awaited_once_with(update, S(bot=None, args=[]))
            await handler.callback(update, S(bot=None, args=['native-deep-link']))
            self.assertEqual(observer.await_count, 1)
            self.assertEqual(opened.await_count, 1)

    async def test_unhandled_or_unaddressed_control_leaves_native_observer_to_ptb(self):
        observer = AsyncMock(wraps=self.adapter._on_platform_update)
        self.adapter._on_platform_update = observer
        await self.handler().callback(self.update('do not stop'), S(bot=None))
        self.adapter._should_process_message.return_value = False
        await self.handler().callback(self.update(), S(bot=None))
        observer.assert_not_awaited()

    async def test_native_observer_failure_does_not_redispatch_a_consumed_stop(self):
        from telegram.ext import ApplicationHandlerStop
        self.adapter._on_platform_update = AsyncMock(side_effect=RuntimeError('observer failed'))
        with self.assertRaises(ApplicationHandlerStop):
            await self.handler().callback(self.update(), S(bot=None))
        self.adapter.handle_message.assert_awaited_once()
        self.adapter._enqueue_text_event.assert_not_called()

    async def test_new_stop_phrases_reach_native_command_handler(self):
        from telegram.ext import ApplicationHandlerStop
        handler = self.handler()
        for text in ('等一下', '等一下呀', '等下', '等等', '停', '暂停一下'):
            with self.subTest(text=text):
                update = self.update(text + '！')
                self.assertTrue(handler.check_update(update))
                with self.assertRaises(ApplicationHandlerStop):
                    await handler.callback(update, S(bot=None))
                self.assertEqual(self.adapter.handle_message.call_args.args[0].text, '/stop')
        for text in ('等一下再部署', '不要停', '如果出错就停一下'):
            self.assertFalse(handler.check_update(self.update(text)))

    async def test_conditional_text_and_unaddressed_group_text_are_not_commands(self):
        handler=self.handler()
        self.assertFalse(handler.check_update(self.update('如果出错就停一下')))
        self.adapter._should_process_message.return_value=False
        await handler.callback(self.update(),S(bot=None))
        self.adapter.handle_message.assert_not_awaited()
        self.adapter._is_user_authorized_from_message.assert_not_called()

    async def test_unload_removes_every_registered_handler_once(self):
        self.r._runner_cls = None
        self.r.uninstall()
        removed = [(call.args[0], call.kwargs.get('group', 0)) for call in self.app.remove_handler.call_args_list]
        self.assertCountEqual(removed, self.handlers)
        self.r.uninstall()
        self.assertEqual(self.app.remove_handler.call_count, len(self.handlers))
