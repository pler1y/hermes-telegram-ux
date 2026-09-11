"""Acceptance regression: the deployed busy reply must read like ordinary chat."""
import sys
import unittest
from types import SimpleNamespace
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from plugin.runtime import InteractionRuntime

class Ctx:
    def get_config(self,key,default=None):return default

class BusyCopyAcceptance(unittest.TestCase):
    def test_read_only_supplement_has_short_plain_ack(self):
        from gateway.run import GatewayRunner
        runtime=InteractionRuntime(Ctx());runtime._patch_runner()
        try:
            reply=GatewayRunner._compose_busy_ack_message(
                object(),SimpleNamespace(text='只讲普通人能用到的产品，不讲融资和论文。',source=SimpleNamespace(platform='telegram')),
                0,None,None,is_steer_mode=True,is_queue_mode=False,is_redirect_mode=False,
                demoted_for_subagents=False,demoted_for_compression=False)
            for internal in ['下一处理步骤','送入当前任务','撤回']:
                self.assertNotIn(internal,reply)
            self.assertLessEqual(len(reply),28)
        finally:runtime.uninstall()

class BackgroundLifecycleAcceptance(unittest.IsolatedAsyncioTestCase):
    async def test_background_child_keeps_status_after_parent_ack(self):
        from plugin.status import TurnState
        runtime=InteractionRuntime(Ctx())
        state=TurnState('parent','key',SimpleNamespace(platform='telegram'),None,1,[None],['17'],None,None,status_message_id='17')
        runtime.registry.bind(state)
        self.assertTrue(hasattr(runtime,'child_start'),'Background children are not observed')
        runtime.child_start(parent_session_id='parent',child_session_id='child')
        runtime.session_end(session_id='parent',completed=True)
        self.assertFalse(state.ended,'A parent acknowledgement must not mark background work finished')

    async def test_nested_child_updates_visible_parent_and_does_not_finish_it(self):
        from plugin.status import TurnState
        runtime=InteractionRuntime(Ctx());s=TurnState('p','k',None,None,1,[None],[],None,None)
        runtime.registry.bind(s)
        runtime.child_start(parent_session_id='p',child_session_id='c')
        runtime.child_start(parent_session_id='c',child_session_id='g')
        runtime.pre_tool('web_search',{},'g')
        self.assertIn('查找',s.phase)
        runtime.session_end(session_id='g',completed=True)
        self.assertFalse(s.ended)
        runtime.child_stop(child_session_id='g')
        self.assertTrue(runtime._has_background('p'))
        runtime.child_stop(child_session_id='c')
        self.assertFalse(runtime._has_background('p'))
    async def test_acknowledgement_updates_one_bubble_and_real_answer_is_not_swallowed(self):
        from plugin.status import TurnState
        from gateway.platforms.base import SendResult
        from unittest.mock import AsyncMock
        class Adapter:pass
        adapter=Adapter();adapter.send=AsyncMock(return_value=SendResult(True,'final'))
        original=adapter.send
        runtime=InteractionRuntime(Ctx());runtime._wire_send(adapter)
        source=SimpleNamespace(platform='telegram',chat_id='1',thread_id=None)
        s=TurnState('p','k',source,adapter,1,[None],[],None,None,status_message_id='17')
        runtime.registry.bind(s);runtime.child_start(parent_session_id='p',child_session_id='c')
        runtime._send_status=AsyncMock()
        result=await adapter.send('1','收到：只看普通人可以用到的产品。')
        self.assertEqual(result.message_id,'17');original.assert_not_called()
        runtime._send_status.assert_awaited_once()
        await adapter.send('1','1. 产品A更新了图片功能。来源：https://example.com')
        original.assert_awaited_once()
        runtime.uninstall()
    async def test_background_watcher_survives_foreground_end_and_stops_after_delivery(self):
        import asyncio
        from plugin.status import TurnState
        from unittest.mock import AsyncMock
        runtime=InteractionRuntime(Ctx());runtime.min_edit=0
        s=TurnState('p','k',None,None,1,[None],[],None,None,foreground_active=False)
        runtime.registry.bind(s);runtime._send_status=AsyncMock()
        task=asyncio.create_task(runtime._watch_background('p'))
        await asyncio.sleep(.02)
        runtime._send_status.assert_awaited()
        runtime.registry.pop('p')
        await asyncio.wait_for(task,1)

class BackgroundIsolation(unittest.TestCase):
    def test_stop_tree_never_includes_another_conversation(self):
        from plugin.background import owned_children
        records=[{'subagent_id':'a','owner_agent_session_id':'mine'},
            {'subagent_id':'b','parent_id':'a','owner_agent_session_id':'child'},
            {'subagent_id':'x','owner_agent_session_id':'other'}]
        self.assertEqual({r['subagent_id'] for r in owned_children('mine',records)},{'a','b'})
    def test_real_answers_are_not_classified_as_receipts(self):
        from plugin.background import acknowledgement_only
        self.assertTrue(acknowledgement_only('收到：只看普通人能用到的产品。'))
        self.assertFalse(acknowledgement_only('收到：以下是结果\n1. 内容A\n2. 内容B'))
        self.assertFalse(acknowledgement_only('收到，资料在 https://example.com'))
        self.assertFalse(acknowledgement_only('好的，'+ '详细内容'*70))

    def test_constraint_ack_with_bullets_is_still_a_receipt(self):
        from plugin.background import acknowledgement_only
        self.assertTrue(acknowledgement_only('收到，改为只比较：\n\n- 免费版能力\n- 离线使用\n- 免费同步方式与限制\n\n不讲团队协作。'))

class StoppedCompletionAcceptance(unittest.IsolatedAsyncioTestCase):
    async def test_stopped_completion_is_dropped_without_waking_model(self):
        from gateway.run import GatewayRunner
        from unittest.mock import AsyncMock,patch
        runtime=InteractionRuntime(Ctx());runtime._patch_runner()
        try:
            self.assertTrue(hasattr(runtime,'_cancelled_delegations'))
            runtime._cancelled_delegations={'cancelled':{'owner':'mine','at':0}}
            runtime._original_completion_group=AsyncMock(return_value=True)
            with patch('tools.async_delegation.claim_event_delivery',return_value='claim'),patch('tools.async_delegation.drop_completion_delivery',return_value=True) as drop:
                result=await GatewayRunner._deliver_async_delegation_group(object(),[{'type':'async_delegation','delegation_id':'cancelled','parent_session_id':'mine'}])
            self.assertTrue(result);drop.assert_called_once_with('cancelled','claim')
            runtime._original_completion_group.assert_not_awaited()
        finally:runtime.uninstall()
    async def test_mixed_completion_batch_keeps_unrelated_result(self):
        from gateway.run import GatewayRunner
        from unittest.mock import AsyncMock,patch
        runtime=InteractionRuntime(Ctx());runtime._patch_runner()
        try:
            self.assertTrue(hasattr(runtime,'_cancelled_delegations'))
            runtime._cancelled_delegations={'cancelled':{'owner':'mine','at':0}}
            runtime._original_completion_group=AsyncMock(return_value=True)
            other={'type':'async_delegation','delegation_id':'live','parent_session_id':'mine'}
            with patch('tools.async_delegation.claim_event_delivery',return_value='claim'),patch('tools.async_delegation.drop_completion_delivery',return_value=True):
                await GatewayRunner._deliver_async_delegation_group(object(),[{'type':'async_delegation','delegation_id':'cancelled','parent_session_id':'mine'},other])
            runtime._original_completion_group.assert_awaited_once()
            self.assertEqual(runtime._original_completion_group.call_args.args[1],[other])
        finally:runtime.uninstall()

    async def test_stop_marker_survives_plugin_reload_and_is_owner_scoped(self):
        from unittest.mock import patch,AsyncMock
        from gateway.run import GatewayRunner
        class Store:
            def __init__(self):self.data={}
            def get(self,key,default=None):return self.data.get(key,default)
            def set(self,key,value):self.data[key]=dict(value)
        ctx=Ctx();ctx.state=Store();runtime=InteractionRuntime(ctx)
        record={'subagent_id':'child','owner_agent_session_id':'mine','delegation_id':'d'}
        with patch('tools.delegate_tool_registry.list_active_subagents',return_value=[record]),patch('tools.delegate_tool_registry.interrupt_subagent',return_value=True):
            self.assertEqual(runtime._stop_owned_children('mine'),1)
        reloaded=InteractionRuntime(ctx)
        self.assertIn('d',reloaded._cancelled_delegations)
        reloaded._patch_runner()
        try:
            reloaded._original_completion_group=AsyncMock(return_value=True)
            event={'type':'async_delegation','delegation_id':'d','parent_session_id':'someone-else'}
            await GatewayRunner._deliver_async_delegation_group(object(),[event])
            reloaded._original_completion_group.assert_awaited_once()
        finally:reloaded.uninstall()

class ModelReceiptAcceptance(unittest.IsolatedAsyncioTestCase):
    async def test_delegate_receipt_is_matched_by_turn_output_not_wording(self):
        from plugin.status import TurnState
        from gateway.platforms.base import SendResult
        from unittest.mock import AsyncMock
        class Adapter:pass
        a=Adapter();a.send=AsyncMock(return_value=SendResult(True,'new'))
        original=a.send;r=InteractionRuntime(Ctx());r._wire_send(a)
        s=TurnState('p','k',SimpleNamespace(chat_id='1',thread_id=None),a,1,[None],[],None,None,status_message_id='17')
        r.registry.bind(s);r.child_start(parent_session_id='p',child_session_id='c')
        r.pre_tool('delegate_task',{'tasks':[{'goal':'查询官方资料'}]},'p')
        text='已在后台查询，只看两家官网；完成后用三点简短对比免费离线使用方式。'
        self.assertTrue(hasattr(r,'model_end'))
        r.model_end(session_id='p',assistant_response=text)
        r._send_status=AsyncMock()
        await a.send('1',text)
        original.assert_not_awaited()
        await a.send('1','这是单独的真实答案。')
        original.assert_awaited_once()
        r.uninstall()
