import unittest
from plugin.status import TurnState, phase_for_tool

class QuietWaiting(unittest.TestCase):
    def state(self):
        s=TurnState('s','k',None,None,1,[None],[],None,None)
        s.soft_wait=True
        return s
    def test_tool_churn_does_not_become_chat_churn(self):
        s=self.state()
        s.phase=phase_for_tool('web_search')
        first=s.render(s.last_event_at+1)
        s.phase=phase_for_tool('read_file')
        self.assertEqual(first,s.render(s.last_event_at+2))
        self.assertEqual(first,'')
    def test_verified_update_is_visible_and_failure_is_not_hidden(self):
        s=self.state();s.activity='这篇文章没有注明发布时间。'
        self.assertIn('没有注明',s.render(s.last_event_at+1))
        s.ended=True;s.phase='这次没能完成。'
        self.assertEqual(s.render(s.last_event_at+1),s.phase)
    def test_long_wait_has_plain_stop_without_command_jargon(self):
        s=self.state()
        text=s.render(s.last_event_at+60)
        self.assertIn('停一下',text)
        self.assertNotIn('/stop',text)

class WelcomeSecurity(unittest.IsolatedAsyncioTestCase):
    async def test_other_user_and_double_click_cannot_submit(self):
        from plugin.welcome import WelcomeMenu
        from types import SimpleNamespace as NS
        from unittest.mock import AsyncMock
        menu=WelcomeMenu(NS(_is_callback_user_authorized=lambda *a,**k: True))
        token,_,_,_=menu._view(dict(user=1,chat=2,thread=None,message=3),'write')
        menu._dispatch=AsyncMock();menu._render=AsyncMock()
        q=NS(data=f'hw:{token}:0',from_user=NS(id=9,username='u'),message=NS(chat=NS(type='private'),chat_id=2,message_thread_id=None,message_id=3),answer=AsyncMock())
        u=NS(callback_query=q)
        await menu.callback(u,None)
        menu._dispatch.assert_not_called()
        q.from_user.id=1
        await menu.callback(u,None);await menu.callback(u,None)
        menu._dispatch.assert_awaited_once()
    async def test_expired_welcome_does_not_dispatch(self):
        from plugin.welcome import WelcomeMenu
        from types import SimpleNamespace as NS
        from unittest.mock import AsyncMock
        clock=[0];menu=WelcomeMenu(None,clock=lambda:clock[0])
        token,_,_,_=menu._view(dict(user=1,chat=2,thread=None,message=3),'write')
        menu._dispatch=AsyncMock();clock[0]=2000
        await menu.callback(NS(callback_query=NS(data=f'hw:{token}:0',answer=AsyncMock())),None)
        menu._dispatch.assert_not_called()

class PrivateReplyPresentation(unittest.IsolatedAsyncioTestCase):
    async def test_private_reply_omits_redundant_quote_but_topic_keeps_anchor(self):
        from plugin.runtime import InteractionRuntime
        from types import SimpleNamespace as NS
        from unittest.mock import AsyncMock
        class Ctx:
            def get_config(self,k,default=None):return default
        class Adapter: pass
        a=Adapter();a.send=AsyncMock();original=a.send
        r=InteractionRuntime(Ctx());r._wire_send(a)
        try:
            await a.send('123','答案',reply_to='77')
            self.assertIsNone(original.call_args.kwargs['reply_to'])
            await a.send('123','答案',reply_to='77',metadata={'thread_id':'8'})
            self.assertEqual(original.call_args.kwargs['reply_to'],'77')
            await a.send('-123','答案',reply_to='77')
            self.assertEqual(original.call_args.kwargs['reply_to'],'77')
        finally:r.uninstall()

class StreamingPreviewRegression(unittest.IsolatedAsyncioTestCase):
    async def test_stream_edits_keep_link_previews_disabled(self):
        from plugins.platforms.telegram.adapter import TelegramAdapter
        from plugin.runtime import InteractionRuntime
        from types import SimpleNamespace as NS
        from unittest.mock import AsyncMock
        class Ctx:
            def get_config(self,k,default=None):return default
        a=object.__new__(TelegramAdapter);a._bot=NS(edit_message_text=AsyncMock());a._disable_link_previews=True
        r=InteractionRuntime(Ctx());r._wire_send(a)
        try:
            await a._edit_text('123','77','来源 https://example.com')
            self.assertTrue(a._bot.edit_message_text.call_args.kwargs.get('link_preview_options').is_disabled)
        finally:r.uninstall()

class FileDraftRegression(unittest.TestCase):
    def test_partial_media_path_never_appears_in_stream(self):
        from plugin.runtime import clean_stream_text
        for text in ['MEDIA:/root/.hermes/cache/通知', 'MEDIA:/root/通知.txt', 'MEDI']:
            self.assertEqual(clean_stream_text(text),'')
        self.assertEqual(clean_stream_text('说明\nMEDIA:/root/通知'),'说明')
        self.assertEqual(clean_stream_text('MEDICAL 信息'),'MEDICAL 信息')

class StreamIntegration(unittest.TestCase):
    def test_native_consumer_filters_partial_file_directive_and_restores(self):
        from gateway.stream_consumer import GatewayStreamConsumer
        from plugin.runtime import InteractionRuntime
        class Ctx:
            def get_config(self,k,default=None):return default
        consumer=object.__new__(GatewayStreamConsumer)
        original=consumer._clean_for_display
        s=TurnState('s','k',None,None,1,[consumer],[],None,None)
        r=InteractionRuntime(Ctx());r._wire_stream(s)
        self.assertEqual(consumer._clean_for_display('MEDIA:/root/活动通'),'')
        self.assertEqual(consumer._clean_for_display('已改好\nMEDIA:/root/活动通'),'已改好')
        r.uninstall()
        self.assertEqual(consumer._clean_for_display,original)
    def test_non_telegram_auxiliary_exit_does_not_end_visible_task(self):
        from plugin.runtime import InteractionRuntime
        class Ctx:
            def get_config(self,k,default=None):return default
        r=InteractionRuntime(Ctx());s=TurnState('s','k',None,None,1,[None],[],None,None)
        r.registry.bind(s);r.session_end(session_id='s',interrupted=True,platform='cli')
        self.assertFalse(s.ended)
