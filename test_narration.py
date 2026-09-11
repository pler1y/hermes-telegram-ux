"""Behavior at the native hook seam; no scenario-specific templates are used."""
import time
import unittest
from types import SimpleNamespace as S

from plugin.narration import tool_note, with_progress_schema, PROGRESS_FIELD
from plugin.progress import TaskProgress
from plugin.runtime import InteractionRuntime
from plugin.status import TurnState


def response(text, calls=(('call', 'terminal'),), **extra):
    return S(content=text, tool_calls=[S(id=cid, function=S(name=name)) for cid,name in calls], **extra)


class PublicNarrationTests(unittest.TestCase):
    def setUp(self):
        ctx = S(get_config=lambda key, default=None: default)
        self.r = InteractionRuntime(ctx)
        self.s = TurnState('root','key',None,None,1,[None],[],None,None,progress=TaskProgress())
        self.r.registry.bind(self.s)

    def text(self):
        return self.s.render(time.monotonic())

    def request(self, rid='r', owner='root', text='帮我整理资料'):
        self.r.pre_api(session_id=owner, user_message=text, api_request_id=rid)

    def note(self, text, rid='r', owner='root', calls=(('call','terminal'),)):
        self.r.post_api(session_id=owner, api_request_id=rid, assistant_message=response(text,calls))

    def start(self, cid='call', name='terminal', owner='root', **args):
        self.r.pre_tool(name,args,owner,tool_call_id=cid)

    def finish(self, cid='call', name='terminal', result=None, owner='root'):
        self.r.post_tool(name, owner, result or {'exit_code':0}, tool_call_id=cid)

    def test_public_note_is_only_displayed_when_persisted_tool_execution_begins(self):
        self.request()
        self.note('我先对齐几份材料里的日期，避免把不同批次混在一起。')
        self.assertNotIn('不同批次',self.text())
        self.start(command='python inspect_data.py')
        self.assertIn('不同批次',self.text())
        self.assertEqual(self.s.progress.snapshot()['source'],'narrative')

    def test_unseen_tasks_can_share_a_tool_without_sharing_a_script(self):
        notes=['我先比较订货数量和库存，看看哪些需要补货。',
               '我来调整练习顺序，先补上后面几课要用到的基础。',
               '我先把几个活动的时间对齐，避免同一天来回跑。']
        for i,text in enumerate(notes):
            self.request(str(i))
            self.note(text,str(i),calls=((str(i),'execute_code'),))
            self.start(str(i),'execute_code')
            self.assertIn(text,self.text())
            self.finish(str(i),'execute_code')

    def test_related_tool_changes_keep_the_purpose_visible(self):
        self.request();self.note('我先核对后续费用，避免只看购买价格。',calls=(('a','web_search'),))
        self.start('a','web_search');self.finish('a','web_search',{'results':[{},{}]})
        self.request('b');self.start('b','web_extract')
        self.assertIn('后续费用',self.text())
        self.assertIn('2 条候选资料',self.text())

    def test_unrelated_action_without_new_explanation_uses_honest_fallback(self):
        self.request();self.note('我先核对资料来源。',calls=(('a','web_search'),))
        self.start('a','web_search');self.finish('a','web_search')
        self.start('b','terminal',command='systemctl restart demo')
        self.assertNotIn('我先核对资料来源',self.text())
        self.assertIn('执行部署',self.text())

    def test_old_model_reply_cannot_overwrite_a_new_user_supplement(self):
        self.request('old')
        self.r.registry.receipt('root','重复文件先别删')
        self.note('我来删除重复文件。','old')
        self.start()
        self.assertNotIn('我来删除',self.text())
        self.assertIn('补充已记下',self.text())
        self.finish()
        self.request('new');self.note('重复文件会保留，我先把它们列出来供你查看。','new',calls=(('new','terminal'),))
        self.start('new')
        self.assertIn('重复文件会保留',self.text())
        self.assertNotIn('补充已记下',self.text())

    def test_goal_and_constraints_live_only_in_this_task(self):
        self.request()
        self.r.pre_tool('interaction_update',{'activity':'先核对文件内容','goal':'把资料整理成可交付清单','constraints':['保留全部原件']},'root',api_request_id='r')
        self.assertEqual(self.s.progress.goal,'把资料整理成可交付清单')
        self.assertEqual(self.s.progress.constraints,('保留全部原件',))
        fresh = TaskProgress()
        self.assertEqual(fresh.constraints,())

    def test_stale_structured_update_cannot_mark_a_supplement_applied(self):
        self.request('old');self.r.registry.receipt('root')
        self.r.pre_tool('interaction_update',{'activity':'已经按新要求修改','constraints':['错误限制']},'root',api_request_id='old')
        self.assertNotIn('已经按新要求',self.text())
        self.assertEqual(self.s.progress.constraints,())

    def test_failure_keeps_existing_results_and_drops_invalid_plan(self):
        self.request();self.note('我先查找相关来源。',calls=(('a','web_search'),))
        self.start('a','web_search');self.finish('a','web_search',{'results':[{},{}]})
        self.start('b','web_extract');self.finish('b','web_extract',{'error':'timeout'})
        self.assertIn('没成功',self.text());self.assertIn('2 条候选资料',self.text())
        self.assertNotIn('我先查找',self.text())

    def test_child_note_is_owned_and_does_not_hide_another_running_step(self):
        self.r.child_start(parent_session_id='root',child_session_id='child')
        self.request(owner='child');self.note('我在核对预约条件。',owner='child')
        self.start(owner='child')
        self.assertIn('预约条件',self.text())
        self.request('other',owner='unrelated');self.note('别人的私密内容','other',owner='unrelated')
        self.assertNotIn('私密',self.text())
        self.r.child_stop(child_session_id='child')
        self.assertNotIn('预约条件',self.text())

    def test_final_answer_and_button_only_messages_are_not_status_text(self):
        self.request()
        self.r.post_api(session_id='root',api_request_id='r',assistant_message=response('最终完整答案',()))
        self.assertNotIn('最终完整答案',self.text())
        self.note('下面是最终完整答案。',calls=(('a','interaction_actions'),))
        self.assertNotIn('最终完整答案',self.text())

    def test_claimed_completion_before_any_result_is_not_published(self):
        self.request();self.note('已完成全部修改。');self.start()
        self.assertNotIn('已完成全部修改',self.text())

    def test_auxiliary_model_calls_cannot_supply_visible_progress(self):
        self.request()
        self.r.post_api(session_id='root',api_request_id='r',platform='memory_review',assistant_message=response('正在修改长期偏好'))
        self.start();self.assertNotIn('长期偏好',self.text())

    def test_private_scratchpads_paths_and_secrets_are_not_exposed(self):
        self.request();self.note('<think>private reasoning</think>我先核对 /root/private/data.json，token=abcdef。')
        self.start()
        for text in ['private reasoning','/root/private','abcdef']:
            self.assertNotIn(text,self.text())


class VisibleContentTests(unittest.TestCase):
    def test_never_reads_reasoning_fields(self):
        msg=response('',reasoning_content='private',reasoning='private')
        self.assertIsNone(tool_note(msg))
        self.assertIsNone(tool_note(response('<think>unfinished private text')))

    def test_structured_commentary_wins_over_partial_final_content(self):
        msg=response('A partial final answer',_raw_response_output=[
            {'type':'message','channel':'final','content':[{'type':'output_text','text':'final'}]},
            {'type':'message','channel':'commentary','content':[{'type':'output_text','text':'我先核对预约要求。'}]},
            {'type':'reasoning','summary':[{'text':'secret'}]}])
        self.assertEqual(tool_note(msg)[0],'我先核对预约要求。')
        msg._raw_response_output=msg._raw_response_output[:1]
        self.assertIsNone(tool_note(msg))

    def test_reports_internal_file_tags_and_plain_final_recommendations_are_rejected(self):
        for text in ['报告正文'*100,'MEDIA:/tmp/a.txt','推荐 B，原因如下。','```python\nsecret\n```']:
            self.assertIsNone(tool_note(response(text)))


class MetadataContractTests(unittest.TestCase):
    def setUp(self):
        self.r = InteractionRuntime(S(get_config=lambda key, default=None: default))
        self.s = TurnState('root','key',None,None,1,[None],[],None,None,progress=TaskProgress())
        self.r.registry.bind(self.s)

    def test_schemas_support_native_provider_shapes_and_preserve_every_operational_field(self):
        from copy import deepcopy
        base = {'name':'read_file','parameters':{'type':'object','properties':{'path':{'type':'string'}},'required':['path'],'additionalProperties':False},'strict':True}
        for tool in [{'type':'function','function':base}, {'type':'function',**base},
                     {'name':'read_file','input_schema':base['parameters']}]:
            request = {'tools':[tool],'temperature':0.2,'messages':[{'role':'user','content':'task'}],'tool_choice':'auto'}
            before = deepcopy(request)
            result = self.r.narration_request(request, session_id='root',platform='telegram')['request']
            modified = result['tools'][0].get('function',result['tools'][0])
            schema = modified.get('parameters',modified.get('input_schema'))
            self.assertIn(PROGRESS_FIELD,schema['required'])
            self.assertEqual(schema['properties']['path'],{'type':'string'})
            self.assertEqual(schema['required'][:-1],['path'])
            self.assertFalse(schema['additionalProperties'])
            self.assertEqual(request,before)
            self.assertEqual(result['messages'][:-1],request['messages'])
            self.assertEqual(result['tool_choice'],'auto')

    def test_non_telegram_auxiliary_and_unknown_sessions_are_unchanged(self):
        request = {'tools':[{'name':'terminal','parameters':{'type':'object','properties':{}}}]}
        for sid,platform in [('other','telegram'),('root','memory_review'),('root','cli')]:
            self.assertIsNone(self.r.narration_request(request,session_id=sid,platform=platform))
        for name in ['tool_search','skill_view','interaction_actions','interaction_update']:
            self.assertIsNone(with_progress_schema({'tools':[{'name':name,'parameters':{'type':'object','properties':{}}}]}))

    def test_request_reminder_does_not_modify_saved_history_or_duplicate_provider_system_slots(self):
        tools = [{'name':'terminal','parameters':{'type':'object','properties':{}}}]
        for field,system in [('instructions','base'),('system','base'),('system',[{'type':'text','text':'base'}])]:
            request = {'tools':tools,field:system}
            updated = with_progress_schema(request)
            self.assertEqual(request[field],system)
            self.assertNotIn('messages',updated)
            self.assertIn('Telegram delivery requirement',str(updated[field]))

    def test_strict_progress_preserves_omitted_optional_arguments_before_execution(self):
        request={'tools':[{'type':'function','name':'read_file','strict':False,'parameters':{'type':'object',
            'properties':{'path':{'type':'string'},'limit':{'type':'integer','default':100},'mode':{'type':'string','enum':['text','lines']}},'required':['path']}}]}
        result=self.r.narration_request(request,session_id='root',platform='telegram',api_request_id='r')['request']
        schema=result['tools'][0]['parameters']
        self.assertTrue(result['tools'][0]['strict'])
        self.assertEqual(schema['properties']['limit']['type'],['integer','null'])
        self.assertIn(None,schema['properties']['mode']['enum'])
        args={'path':'/tmp/input','limit':None,'mode':None,PROGRESS_FIELD:'先核对通知里的日期。'}
        clean=self.r.narration_arguments('read_file',args,session_id='root',api_request_id='r')['args']
        self.assertEqual(clean,{'path':'/tmp/input'})
        args['limit']=0
        clean=self.r.narration_arguments('read_file',args,session_id='root',api_request_id='r')['args']
        self.assertEqual(clean,{'path':'/tmp/input','limit':0})

    def test_native_terminal_union_and_original_nullable_values_keep_their_meaning(self):
        request={'tools':[{'type':'function','name':'terminal','strict':False,'parameters':{'type':'object',
            'properties':{'command':{'type':'string'},'notify':{'anyOf':[{'type':'boolean'},{'type':'array','items':{'type':'string'}}]},'nullable':{'type':['string','null']}},'required':['command']}}]}
        result=self.r.narration_request(request,session_id='root',platform='telegram',api_request_id='r')['request']
        self.assertTrue(result['tools'][0]['strict'])
        for notify in [True,False,['ready'],None]:
            args={'command':'run','notify':notify,'nullable':None,PROGRESS_FIELD:'我先验证一下结果。'}
            clean=self.r.narration_arguments('terminal',args,session_id='root',api_request_id='r')['args']
            self.assertEqual(clean,{'command':'run','nullable':None,**({'notify':notify} if notify is not None else {})})

    def test_opening_failure_and_supplement_require_a_new_explanation(self):
        request={'tools':[{'type':'function','name':'read_file','parameters':{'type':'object','properties':{'path':{'type':'string'}},'required':['path']}}]}
        def minimum():
            r=self.r.narration_request(request,session_id='root',platform='telegram')['request']
            return r['tools'][0]['parameters']['properties'][PROGRESS_FIELD].get('minLength',0)
        self.assertEqual(minimum(),1)
        self.s.progress.plan('我先把资料里的时间对一下。',owner='root')
        self.assertEqual(minimum(),0)
        self.r.pre_tool('read_file',{},'root',tool_call_id='a')
        self.r.post_tool('read_file','root',{'error':'not found'},tool_call_id='a')
        self.assertEqual(minimum(),1)
        self.s.progress.plan('我先用能读取的资料整理。',owner='root')
        self.r.registry.receipt('root')
        self.assertEqual(minimum(),1)

    def test_metadata_is_removed_and_only_the_matching_started_call_displays_it(self):
        self.r.pre_api(session_id='root',api_request_id='r')
        args = {'path':'/tmp/input.txt',PROGRESS_FIELD:'我先对照两份材料的日期，看看有没有冲突。'}
        cleaned = self.r.narration_arguments('read_file',args,session_id='root',api_request_id='r',tool_call_id='a')['args']
        self.assertEqual(cleaned,{'path':'/tmp/input.txt'})
        self.assertIn(PROGRESS_FIELD,args)
        self.assertNotIn('两份材料',self.s.render(time.monotonic()))
        self.r.pre_tool('read_file',cleaned,'root',tool_call_id='a',api_request_id='r')
        self.assertIn('两份材料',self.s.render(time.monotonic()))

    def test_stale_metadata_is_stripped_without_overwriting_supplement(self):
        self.r.pre_api(session_id='root',api_request_id='old')
        self.r.registry.receipt('root')
        result = self.r.narration_arguments('terminal',{'command':'check',PROGRESS_FIELD:'我来删除旧版本。'},session_id='root',api_request_id='old',tool_call_id='a')
        self.r.pre_tool('terminal',result['args'],'root',tool_call_id='a')
        self.assertNotIn('删除旧版本',self.s.render(time.monotonic()))
        self.assertIn('补充已记下',self.s.render(time.monotonic()))

    def test_explicit_continuation_keeps_one_purpose_across_read_calculate_and_write(self):
        for i,(name,note) in enumerate([('read_file','我先把库存和消耗对一遍，整理出真正缺少的物料。'),('terminal',''),('write_file','')]):
            rid=str(i)
            self.r.pre_api(session_id='root',api_request_id=rid)
            self.r.narration_arguments(name,{PROGRESS_FIELD:note},session_id='root',api_request_id=rid,tool_call_id=rid)
            self.r.pre_tool(name,{},'root',tool_call_id=rid,api_request_id=rid)
            self.assertIn('真正缺少的物料',self.s.render(time.monotonic()))
            self.r.post_tool(name,'root',{'success':True},tool_call_id=rid)
        self.r.registry.receipt('root')
        self.r.pre_api(session_id='root',api_request_id='new')
        self.r.narration_arguments('read_file',{PROGRESS_FIELD:''},session_id='root',api_request_id='new',tool_call_id='new')
        self.r.pre_tool('read_file',{},'root',tool_call_id='new',api_request_id='new')
        self.assertIn('补充已记下',self.s.render(time.monotonic()))
        self.assertNotIn('真正缺少的物料',self.s.render(time.monotonic()))

    def test_native_middleware_contract_preserves_actual_tool_parameters(self):
        try:
            from hermes_cli.middleware import apply_llm_request_middleware, apply_tool_request_middleware
        except ModuleNotFoundError:
            self.skipTest('Requires the actual Hermes runtime')
        from unittest.mock import patch
        def middleware(kind, **kwargs):
            callback = self.r.narration_request if kind=='llm_request' else self.r.narration_arguments
            return [callback(**kwargs)]
        self.r.pre_api(session_id='root',api_request_id='r')
        context = {'session_id':'root','platform':'telegram','api_request_id':'r','tool_call_id':'a'}
        with patch('hermes_cli.plugins.has_middleware',return_value=True),patch('hermes_cli.plugins.invoke_middleware',side_effect=middleware):
            request = apply_llm_request_middleware({'tools':[{'name':'terminal','parameters':{'type':'object','properties':{'command':{'type':'string'}}}}]},**context)
            self.assertIn(PROGRESS_FIELD,request.payload['tools'][0]['parameters']['required'])
            result = apply_tool_request_middleware('terminal',{'command':'python report.py',PROGRESS_FIELD:'我来把缺少的数量整理成清单。'},skip_relay=True,**context)
        self.assertEqual(result.payload,{'command':'python report.py'})
        self.r.pre_tool('terminal',result.payload,'root',tool_call_id='a',api_request_id='r')
        self.assertIn('缺少的数量',self.s.render(time.monotonic()))


class NativeNarrationCompatibility(unittest.TestCase):
    def test_native_response_hook_reaches_status_before_the_tool(self):
        try:
            from agent.turn_response_intake import _fire_post_api_request_hook
        except ModuleNotFoundError:
            self.skipTest('Requires the actual Hermes runtime')
        from unittest.mock import patch
        r = InteractionRuntime(S(get_config=lambda key, default=None: default))
        state = TurnState('root','key',None,None,1,[None],[],None,None,progress=TaskProgress())
        r.registry.bind(state)
        r.pre_api(session_id='root',api_request_id='native',user_message='整理物料需求')
        agent = S(session_id='root',platform='telegram',model='fixture',provider='fixture',base_url='',api_mode='chat',
            _api_response_payload_for_hook=lambda *a,**k:{}, _usage_summary_for_api_request_hook=lambda *a:{})
        msg = response('我先对照库存和需求，确认哪些还需要补充。')
        def hook(name, **kwargs):
            self.assertEqual(name,'post_api_request')
            r.post_api(**kwargs)
        with patch('hermes_cli.lifecycle.has_hook',return_value=True), patch('hermes_cli.lifecycle.invoke_hook',side_effect=hook), patch('agent.conversation_loop._moa_reference_metrics_for_hook',return_value=None):
            _fire_post_api_request_hook(agent,S(model='fixture'),msg,'tool_calls',api_messages=[],api_call_count=1,
                api_duration=1,api_start_time=0,api_request_id='native',effective_task_id='task',turn_id='turn')
        self.assertNotIn('库存',state.render(time.monotonic()))
        r.pre_tool('terminal',{'command':'python inspect.py'},'root',tool_call_id='call',api_request_id='native')
        self.assertIn('库存和需求',state.render(time.monotonic()))


if __name__ == '__main__':
    unittest.main()
