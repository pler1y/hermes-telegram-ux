"""Behavior tests; Telegram transport is simulated, no live chat messages are sent."""
import asyncio
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock
sys.path.insert(0, str(Path(__file__).parent))
from plugin.status import TurnRegistry, TurnState, ANALYZE, RETRY, phase_for_tool, tool_failed, safe_status_text
from plugin.runtime import InteractionRuntime
from plugin.actions import ActionStore, TelegramActions
from plugin.experience import PROGRESS_SCHEMA

class Context:
    def get_config(self, key, default=None): return default
    def inject_message(self, *args, **kwargs): return True

class ExperienceTests(unittest.TestCase):
    def setUp(self):
        self.r = TurnRegistry()
        self.s = TurnState('s','k',None,None,1,[None],[],None,None)
        self.r.bind(self.s)
    def test_progress_keeps_verified_finding_between_steps(self):
        self.r.progress('s','正在核对服务器配置','服务正常运行')
        self.r.update('s',phase_for_tool('read_file'),tool_started=True)
        self.r.tool_finished('s',{'success':True})
        text=self.s.render(self.s.last_event_at)
        self.assertIn('服务正常运行',text)
        self.assertNotIn('正在核对服务器配置',text)
    def test_slow_notice_is_based_on_time_without_events(self):
        self.assertNotIn('/stop',self.s.render(self.s.last_event_at+44))
        self.assertIn('/stop',self.s.render(self.s.last_event_at+46))
        self.r.update('s',ANALYZE)
        self.assertNotIn('/stop',self.s.render(self.s.last_event_at))
    def test_parallel_tools_do_not_claim_analysis_while_other_tool_runs(self):
        self.r.update('s','读取内容',tool_started=True)
        self.r.update('s','核对状态',tool_started=True)
        self.r.tool_finished('s',{'success':True})
        self.assertEqual(self.s.active_tools,1)
        self.assertEqual(self.s.phase,'核对状态')
    def test_tool_failure_is_not_whole_task_failure(self):
        self.r.update('s','读取内容',tool_started=True)
        self.r.tool_finished('s',json.dumps({'error':'network timeout'}))
        self.assertFalse(self.s.failed)
        self.assertEqual(self.s.tool_errors,1)
        self.assertIn('有一步未成功',self.s.phase)
    def test_completion_cannot_be_overwritten_by_late_tool_event(self):
        self.r.finish('s',failed=True,interrupted=False,completed=False)
        final=self.s.phase
        self.r.tool_finished('s',{'success':True})
        self.r.progress('s','继续处理')
        self.r.update('s',ANALYZE)
        self.assertEqual(self.s.phase,final)
    def test_status_does_not_invent_retry(self): self.assertNotIn('自动重试',RETRY)
    def test_readonly_service_command_is_not_a_deployment(self):
        self.assertNotIn('部署',phase_for_tool('terminal',{'command':'systemctl status app'}))
    def test_status_redacts_common_secrets_and_urls(self):
        text=safe_status_text('核对 token=abc123 https://private.example?q=secret sk-abcdef123456')
        for secret in ['abc123','private.example','abcdef123456']: self.assertNotIn(secret,text)
    def test_tool_failure_only_reads_structured_signals(self):
        self.assertFalse(tool_failed('The error documentation was found'))
        self.assertTrue(tool_failed({'exit_code':1}))
        self.assertFalse(tool_failed({'exit_code':0}))
    def test_session_isolation(self):
        self.r.progress('another','不应出现')
        self.assertEqual(self.s.activity,'')
    def test_invalid_button_index_does_not_consume_menu(self):
        store=ActionStore()
        menu=store.create_menu(session_key='k',user_id='u',chat_id='c',thread_id=None,message_id='m',actions=[{'label':'查看详情','prompt':'查看具体检查结果'}])
        self.assertIsNone(store.claim(menu.token,99))
        self.assertIsNotNone(store.claim(menu.token,0))
    def test_new_turn_invalidates_only_its_own_buttons(self):
        store=ActionStore()
        menus=[store.create_menu(session_key=k,user_id='u',chat_id='c',thread_id=None,message_id='m',actions=[]) for k in ['a','b']]
        store.invalidate_session('a')
        self.assertIsNone(store.peek(menus[0].token))
        self.assertIsNotNone(store.peek(menus[1].token))

class CallbackTests(unittest.IsolatedAsyncioTestCase):
    async def test_double_click_dispatches_once_and_unauthorized_user_cannot_claim(self):
        store=ActionStore(); ctx=Context(); ctx.inject_message=Mock(return_value=True)
        ui=TelegramActions(ctx,store)
        ui.adapter=SimpleNamespace(_is_callback_user_authorized=lambda *a,**k: True)
        menu=store.create_menu(session_key='k',user_id='1',chat_id='2',thread_id=None,message_id='3',actions=[{'label':'查看详情','prompt':'查看本次详情'}])
        q=SimpleNamespace(data=f'hi:{menu.token}:0',from_user=SimpleNamespace(id=9,username='user'),message=SimpleNamespace(chat_id=2,message_thread_id=None,message_id=3,chat=SimpleNamespace(type='private'),reply_text=AsyncMock()),answer=AsyncMock(),edit_message_reply_markup=AsyncMock())
        update=SimpleNamespace(callback_query=q)
        await ui.callback(update,None)
        ctx.inject_message.assert_not_called()
        q.from_user.id=1
        await asyncio.gather(ui.callback(update,None),ui.callback(update,None))
        ctx.inject_message.assert_called_once_with('查看本次详情',session_key='k')
    async def test_progress_hook_updates_existing_bubble_state(self):
        runtime=InteractionRuntime(Context())
        state=TurnState('s','k',None,None,1,[None],[],None,None)
        runtime.registry.bind(state)
        runtime.pre_tool(PROGRESS_SCHEMA['name'],{'activity':'正在核对设置','finding':'服务运行正常'},'s')
        runtime.post_tool(PROGRESS_SCHEMA['name'],'s',{'ok':True})
        self.assertEqual(state.tool_count,0)
        self.assertIn('服务运行正常',state.render(state.last_event_at))

class NativeCompatibilityTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        try:
            from gateway.run import GatewayRunner
        except ModuleNotFoundError:
            self.skipTest('Requires isolated Hermes runtime')
        self.Runner=GatewayRunner
        self.runtime=InteractionRuntime(Context())
    async def test_stop_preserves_native_control_and_reports_verified_progress(self):
        original=self.Runner._busy_stop_command
        calls=[]
        async def fake(runner,event,key,source):
            calls.append(key); return 'Stopped'
        self.Runner._busy_stop_command=fake
        self.runtime._patch_runner()
        try:
            adapter=SimpleNamespace(delete_message=AsyncMock(),send=AsyncMock())
            state=TurnState('s','k',SimpleNamespace(chat_id='1'),adapter,1,[None],['17'],None,None,finding='配置读取完成',status_message_id='17')
            self.runtime.registry.bind(state)
            result=await self.Runner._busy_stop_command(object(),None,'k',SimpleNamespace(platform='telegram'))
            self.assertEqual(calls,['k'])
            self.assertIn('配置读取完成',result)
            self.assertIn('不会自动撤销',result)
            self.assertTrue(state.interrupted)
            adapter.delete_message.assert_awaited_once_with('1','17')
            self.assertTrue(state.status_closed)
            await self.runtime._send_status(state,'迟到的中断状态')
            adapter.send.assert_not_awaited()
            result=await self.Runner._busy_stop_command(object(),None,'x',SimpleNamespace(platform='discord'))
            self.assertEqual(result,'Stopped')
        finally:
            self.runtime.uninstall(); self.Runner._busy_stop_command=original
    async def test_native_telegram_batching_uses_quiet_window(self):
        from plugins.platforms.telegram.adapter import TelegramAdapter
        # Exercise native buffering/dispatch without constructing a network client.
        adapter=object.__new__(TelegramAdapter)
        adapter._pending_text_batches={'a':SimpleNamespace(text='检查一下\n洛杉矶那台',_last_chunk_len=5)}
        adapter._pending_text_batch_tasks={}
        adapter._text_batch_delay_seconds=.8
        adapter._TEXT_BATCH_FAST_DELAY_S=.8
        adapter._TEXT_BATCH_SHORT_DELAY_S=.8
        adapter._text_batch_split_delay_seconds=1
        adapter._flush_buffered=AsyncMock()
        await adapter._flush_text_batch('a')
        self.assertEqual(adapter._flush_buffered.call_args.args[3],.8)

if __name__=='__main__': unittest.main()

class RoutingTests(unittest.TestCase):
    def test_only_exact_natural_commands_are_rewritten(self):
        runtime=InteractionRuntime(Context())
        def event(text,platform='telegram'):
            return SimpleNamespace(text=text,source=SimpleNamespace(platform=platform))
        self.assertEqual(runtime.dispatch(event('停一下。')),{'action':'rewrite','text':'/stop'})
        self.assertIsNone(runtime.dispatch(event('如果出错就停一下')))
        self.assertIsNone(runtime.dispatch(event('停一下','discord')))
    def test_approval_is_not_displayed_as_a_stuck_task(self):
        runtime=InteractionRuntime(Context());s=TurnState('s','k',None,None,1,[None],[],None,None)
        runtime.registry.bind(s); runtime.approval_wait('k')
        text=s.render(s.last_event_at+1000)
        self.assertIn('等待你确认',text);self.assertNotIn('等待较久',text)

    def test_approval_completion_restores_actual_running_step(self):
        from plugin.progress import TaskProgress
        runtime = InteractionRuntime(Context())
        s = TurnState('s','k',None,None,1,[None],[],None,None,progress=TaskProgress())
        runtime.registry.bind(s)
        s.progress.plan('正在核对库存数量。', owner='s')
        runtime.pre_tool('terminal', {'command':'python check_inventory.py'}, 's', tool_call_id='t')
        runtime.approval_wait('k')
        self.assertIn('等待你确认', s.render(s.last_event_at))
        runtime.approval_done('k')
        self.assertIn('正在核对库存数量', s.render(s.last_event_at))
        self.assertNotIn('确认结果', s.render(s.last_event_at + 60))

    def test_smart_approval_does_not_ask_user_for_a_nonexistent_prompt(self):
        runtime = InteractionRuntime(Context())
        s = TurnState('s','k',None,None,1,[None],[],None,None)
        runtime.registry.bind(s)
        before = s.phase
        runtime.approval_wait('k', surface='smart')
        self.assertEqual(s.render(s.last_event_at), '正在检查操作权限。')
        runtime.approval_done('k', surface='smart', choice='smart_approve')
        self.assertEqual(s.phase, before)
        runtime.registry.update('s', '新步骤')
        runtime.approval_done('k', surface='smart', choice='smart_approve')
        self.assertEqual(s.phase, '新步骤')
    def test_late_lifecycle_cannot_remove_new_generation(self):
        r=TurnRegistry();old=TurnState('s','k',None,None,1,[None],[],None,None)
        new=TurnState('s','k',None,None,2,[None],[],None,None)
        r.bind(old);r.bind(new);r.pop('s',expected=old)
        self.assertIs(r.get('s'),new)
    def test_session_reset_expires_old_buttons_without_expiring_other_sessions(self):
        runtime=InteractionRuntime(Context())
        def create(sid):return runtime.actions.create_menu(session_key=sid,user_id='u',chat_id='c',thread_id=None,message_id='m',actions=[],session_id=sid)
        old=create('old');other=create('other')
        runtime.session_reset(old_session_id='old')
        self.assertIsNone(runtime.actions.peek(old.token));self.assertIsNotNone(runtime.actions.peek(other.token))
    def test_prompt_migration_preserves_other_sections_and_conversation_prefix(self):
        try:
            from hermes_cli.plugins import format_system_prompt_sections, RenderedPluginSystemPromptSection as S
        except ModuleNotFoundError:self.skipTest('Requires Hermes prompt formatter')
        from migrate_prompts import replace_section
        from plugin.experience import prompt_for
        PROMPT = prompt_for("zh")
        prefix='Original instructions unchanged\n'
        suffix='\n\nConversation started: 2026-09-10'
        sections=[S(id='other.plugin',content='Keep verbatim',position='after_memory',plugin='other'),S(id='hermes_interaction.telegram',content='Old instructions',position='after_memory',plugin='test')]
        before=prefix+format_system_prompt_sections(sections)+suffix
        after=replace_section(before)
        self.assertTrue(after.startswith(prefix));self.assertTrue(after.endswith(suffix))
        self.assertIn('Keep verbatim',after);self.assertIn(PROMPT,after)
        self.assertNotIn('Old instructions',after);self.assertEqual(replace_section(after),after)
        self.assertEqual(replace_section('Ordinary text'), 'Ordinary text')
        unframed=prefix+suffix
        upgraded=replace_section(unframed)
        self.assertIn(PROMPT,upgraded)
        self.assertTrue(upgraded.startswith(prefix))
        self.assertTrue(upgraded.endswith(suffix))
        self.assertEqual(replace_section(upgraded),upgraded)
