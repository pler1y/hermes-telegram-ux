"""Regressions reproduced by real Telegram's fast tool/model event sequences."""
import asyncio
from types import SimpleNamespace
import unittest

from catalog.model import Turn
from catalog.presentation import status_text
from catalog.adapter import HermesCatalogAdapter
from test_catalog import ContextStub, TelegramStub, event, start


class PriorityTests(unittest.TestCase):
    def begin(self, task):
        turn = Turn('session', 'turn', 1, user_task=task)
        turn.observe('pre_api_request', {'api_request_id': 'api-1'}, 2)
        return turn

    def tool(self, turn, name, args, result, status='ok', call='tool-1'):
        turn.observe('pre_tool_call', {'tool_call_id': call, 'tool_name': name, 'args': args}, 3)
        turn.observe('post_tool_call', {'tool_call_id': call, 'tool_name': name, 'result': result, 'status': status}, 3.01)

    def test_missing_file_remains_visible_through_next_model_and_completion(self):
        turn = self.begin('请读取 /tmp/TGUX_DOES_NOT_EXIST_20260920_A7F91.txt，并告诉我里面是什么内容。')
        self.tool(turn, 'read_file', {'path': '/tmp/TGUX_DOES_NOT_EXIST_20260920_A7F91.txt'}, {'content': '', 'error': 'File not found: /private/path'}, 'error')
        turn.observe('pre_api_request', {'api_request_id': 'api-2'}, 3.02)
        turn.observe('post_api_request', {'api_request_id': 'api-2', 'assistant_tool_call_count': 0, 'assistant_message': SimpleNamespace(tool_calls=[])}, 9)
        self.assertIn('未找到指定文件', status_text(turn, 'zh', now=9))
        turn.observe('post_llm_call', {'assistant_response': 'native only'}, 9.01)
        self.assertIn('未找到指定文件', status_text(turn, 'zh', ending='finalizing', now=9.02))
        self.assertNotIn('其他方式', status_text(turn, 'zh'))
        self.assertNotIn('/private', repr(turn))

    def test_normalized_host_response_with_tools_is_not_text_generation(self):
        turn = self.begin('调查最近 7 天的公开新闻')
        turn.observe('post_api_request', {'api_request_id': 'api-1', 'assistant_tool_call_count': 2, 'assistant_message': SimpleNamespace(tool_calls=[object(), object()])}, 3)
        self.assertEqual(turn.current_kind, 'working')
        self.assertNotIn('组织回复', status_text(turn, 'zh'))

    def test_clock_query_names_its_observed_action_and_task(self):
        turn = self.begin('上海未来 7 天的天气')
        turn.observe('pre_tool_call', {'tool_call_id': 'date', 'tool_name': 'terminal', 'args': {'command': "date '+%Y-%m-%d %H:%M:%S %Z (%z)'"}}, 3)
        self.assertIn('正在核对上海未来 7 天的天气所用的日期', status_text(turn, 'zh'))

    def test_successful_clock_query_does_not_claim_news_task_completed(self):
        turn = self.begin('调查最近 7 天 OpenAI 的重要公开新闻')
        self.tool(turn, 'terminal', {'command': "date '+%Y-%m-%d %H:%M:%S %Z (%z)'"}, {'output': '2026-09-20 18:00:00 UTC (+0000)\n', 'exit_code': 0})
        text = status_text(turn, 'zh')
        self.assertEqual(text, '🕒 已核对最近 7 天 OpenAI 的重要公开新闻所用的日期，继续整理资料…')
        self.assertNotIn('新闻已执行成功', text)
        self.assertIn('Checked the date for', status_text(turn, 'en'))

    def test_successful_program_describes_current_step_not_whole_weather_task(self):
        turn = self.begin('上海未来 7 天的天气')
        self.tool(turn, 'execute_code', {'code': 'print("daily comparison")'}, {'status': 'success', 'output': 'date min max\n2026-09-20 22.5 30.4\n', 'exit_code': 0})
        text = status_text(turn, 'zh')
        self.assertEqual(text, '📊 当前步骤已完成，正在核对上海未来 7 天的天气的结果…')
        self.assertNotIn('天气已执行成功', text)
        self.assertIn('The current step completed', status_text(turn, 'en'))

    def test_short_read_result_survives_next_model_request(self):
        turn = self.begin('只读取插件代码，检查 Telegram 状态消息是怎样清理的')
        self.tool(turn, 'read_file', {'path': '/tmp/catalog/telegram.py'}, {'content': 'public source', 'total_lines': 40})
        turn.observe('pre_api_request', {'api_request_id': 'api-2'}, 3.02)
        self.assertIn('已读取Telegram 状态消息的清理代码', status_text(turn, 'zh', now=4))
        self.assertNotIn('组织回复', status_text(turn, 'zh', now=4))
        self.assertIn('总结Telegram 状态消息的清理逻辑', status_text(turn, 'zh', now=8))

    def test_search_facts_age_into_task_summary_only_after_followup_request(self):
        turn = self.begin('调查最近7天 OpenAI 的重要公开新闻')
        self.tool(turn, 'web_search', {'query': 'site:openai.com "Sep 18" OpenAI long private query'}, {'data': {'web': [{'title': 'Public news', 'url': 'https://example.org'}]}})
        self.assertIn('1 条搜索结果', status_text(turn, 'zh', now=80))
        turn.observe('pre_api_request', {'api_request_id': 'api-2'}, 81)
        self.assertIn('1 条搜索结果', status_text(turn, 'zh', now=82))
        text = status_text(turn, 'zh', now=85)
        self.assertIn('汇总最近 7 天 OpenAI 的重要公开新闻', text)
        self.assertNotIn('搜索结果', text)
        self.assertNotIn('site:', repr(turn))
        self.assertNotIn('private query', repr(turn))

    def test_error_does_not_claim_recovery_until_a_real_new_action(self):
        turn = self.begin('上海未来7天天气')
        self.tool(turn, 'web_extract', {'urls': ['https://example.org']}, {'results': [{'error': 'HTTP error'}]})
        turn.observe('pre_api_request', {'api_request_id': 'api-2'}, 4)
        self.assertIn('没有成功', status_text(turn, 'zh', now=9))
        self.assertNotIn('方式', status_text(turn, 'zh', now=9))
        turn.observe('pre_tool_call', {'tool_call_id': 'tool-2', 'tool_name': 'execute_code', 'args': {'code': "from hermes_tools import terminal\nterminal('curl https://example.org')"}}, 10)
        text = status_text(turn, 'zh')
        self.assertIn('换一种方式', text)
        self.assertIn('读取上海未来 7 天天气数据', text)
        self.assertNotIn('已恢复', text)

    def test_parallel_failure_is_retained_without_rewinding_newer_action(self):
        turn = self.begin('上海天气')
        for call in ['one', 'two']:
            turn.observe('pre_tool_call', {'tool_call_id': call, 'tool_name': 'web_extract', 'args': {}}, 3)
        turn.observe('post_tool_call', {'tool_call_id': 'one', 'tool_name': 'web_extract', 'status': 'error', 'result': {'error': 'HTTP error'}}, 4)
        self.assertIn('正在读取上海天气数据', status_text(turn, 'zh'))
        turn.observe('post_tool_call', {'tool_call_id': 'two', 'tool_name': 'web_extract', 'status': 'ok', 'result': {'results': [{'content': 'Weather data'}]}}, 5)
        turn.observe('pre_api_request', {'api_request_id': 'api-2'}, 5.01)
        self.assertIn('部分上海天气资料读取失败', status_text(turn, 'zh', now=6))
        self.assertNotIn('HTTP', repr(turn))

    def test_mixed_source_batch_is_symmetric_and_retains_failed_tool_evidence(self):
        for order in (('failed', 'read'), ('read', 'failed')):
            with self.subTest(order=order):
                turn = self.begin('调查最近 7 天 OpenAI 的重要公开新闻')
                for call in order:
                    turn.observe('pre_tool_call', {'tool_call_id': call, 'tool_name': 'web_extract', 'args': {}}, 3)
                for number, call in enumerate(order):
                    result = {'results': [{'content': 'Official source', 'error': None}]} if call == 'read' else {'results': [{'content': '', 'error': 'Fetch failed'}]}
                    turn.observe('post_tool_call', {'tool_call_id': call, 'tool_name': 'web_extract', 'status': 'ok', 'result': result}, 4 + number)
                turn.observe('pre_api_request', {'api_request_id': 'api-2'}, 5.1)
                self.assertEqual(turn.progress['status'], 'mixed')
                self.assertIn('部分最近 7 天 OpenAI 的重要公开新闻资料读取失败', status_text(turn, 'zh', now=6))
                self.assertIn('正在整理已有结果', status_text(turn, 'zh', now=6))
                self.assertEqual(turn.tools['failed'][1], 'error')
                self.assertTrue(turn.observations['failed']['facts']['failed'])
                self.assertNotIn('已恢复', status_text(turn, 'zh', now=6))

    def test_search_success_and_last_extract_failure_age_into_qualified_summary(self):
        turn = self.begin('调查最近 7 天 OpenAI 的重要公开新闻')
        turn.observe('pre_tool_call', {'tool_call_id': 'search', 'tool_name': 'web_search', 'args': {}}, 3)
        turn.observe('pre_tool_call', {'tool_call_id': 'failed', 'tool_name': 'web_extract', 'args': {}}, 3.1)
        turn.observe('post_tool_call', {'tool_call_id': 'search', 'tool_name': 'web_search', 'status': 'ok', 'result': {'data': {'web': [{'title': 'Public source', 'url': 'https://example.test'}]}}}, 4)
        turn.observe('post_tool_call', {'tool_call_id': 'failed', 'tool_name': 'web_extract', 'status': 'error', 'result': {'results': [{'content': '', 'error': 'Fetch failed'}]}}, 5)
        turn.observe('pre_api_request', {'api_request_id': 'api-2'}, 5.1)
        self.assertIn('正在整理已有结果', status_text(turn, 'zh', now=6))
        text = status_text(turn, 'zh', now=10)
        self.assertIn('部分资料读取失败', text)
        self.assertIn('汇总最近 7 天 OpenAI 的重要公开新闻', text)
        self.assertNotIn('没有成功', text)
        turn.observe('post_api_request', {'api_request_id': 'api-2', 'assistant_tool_call_count': 0}, 20)
        self.assertIn('部分资料读取失败', status_text(turn, 'zh', now=21))
        turn.observe('post_llm_call', {}, 22)
        final = status_text(turn, 'zh', ending='finalizing', now=22)
        self.assertIn('部分资料读取失败', final)
        self.assertIn('汇总最近 7 天 OpenAI 的重要公开新闻', final)
        self.assertIn('Some sources could not be read', status_text(turn, 'en', ending='finalizing'))

    def test_all_failed_source_batch_stays_failed_through_finalization(self):
        turn = self.begin('调查最近 7 天 OpenAI 的重要公开新闻')
        for number in range(2):
            self.tool(turn, 'web_extract', {}, {'results': [{'error': 'Fetch failed'}]}, call=str(number))
        turn.observe('pre_api_request', {'api_request_id': 'api-2'}, 5)
        self.assertEqual(turn.progress['status'], 'error')
        self.assertIn('这次读取最近 7 天 OpenAI 的重要公开新闻没有成功', status_text(turn, 'zh', now=20))
        self.assertIn('This attempt to read', status_text(turn, 'en', now=20))
        self.assertNotIn('部分', status_text(turn, 'zh', now=20))
        turn.observe('post_llm_call', {}, 21)
        self.assertIn('没有成功', status_text(turn, 'zh', ending='finalizing'))

    def test_empty_user_task_keeps_partial_warning_and_safe_tool_subject_at_final(self):
        turn = self.begin('')
        self.tool(turn, 'web_search', {'query': '杭州天气'}, {'results': [{'title': 'Weather', 'url': 'https://example.test'}]}, call='read')
        self.tool(turn, 'web_search', {'query': '杭州天气'}, {'error': 'Search failed'}, call='failed')
        turn.observe('pre_api_request', {'api_request_id': 'api-2'}, 5)
        self.assertEqual(turn.progress['status'], 'mixed')
        self.assertIn('部分杭州天气资料读取失败', status_text(turn, 'zh', now=6))
        self.assertIn('部分资料读取失败，正在整理杭州天气变化', status_text(turn, 'zh', now=10))
        turn.observe('post_llm_call', {}, 20)
        self.assertIn('部分资料读取失败，正在整理杭州天气变化', status_text(turn, 'zh', ending='finalizing'))

    def test_partial_warning_survives_summary_even_without_any_safe_subject(self):
        turn = self.begin('')
        self.tool(turn, 'web_extract', {}, {'results': [{'content': 'A source'}, {'error': 'Fetch failed'}]})
        turn.observe('pre_api_request', {'api_request_id': 'api-2'}, 5)
        self.assertEqual(status_text(turn, 'zh', now=10), '⚠️ 部分资料读取失败，正在整理已有结果…')
        turn.observe('post_llm_call', {}, 20)
        self.assertEqual(status_text(turn, 'zh', ending='finalizing'), '⚠️ 部分资料读取失败，正在整理已有结果…')

    def test_unrelated_success_does_not_turn_source_failure_into_partial_success(self):
        for name, args, result in (
                ('terminal', {'command': 'date +%s'}, {'output': '1234567890', 'exit_code': 0}),
                ('execute_code', {'code': 'print("ok")'}, {'status': 'success', 'output': 'ok', 'exit_code': 0}),
                ('web_search', {}, {'data': {'web': []}})):
            with self.subTest(name=name):
                turn = self.begin('调查最近 7 天 OpenAI 的重要公开新闻')
                self.tool(turn, name, args, result, call='unrelated')
                self.tool(turn, 'web_extract', {}, {'error': 'Fetch failed'}, call='failed')
                turn.observe('pre_api_request', {'api_request_id': 'api-2'}, 5)
                self.assertIn('没有成功', status_text(turn, 'zh', now=20))
                self.assertNotIn('部分', status_text(turn, 'zh', now=20))

    def test_success_from_older_api_batch_does_not_qualify_current_failure(self):
        turn = self.begin('调查最近 7 天 OpenAI 的重要公开新闻')
        self.tool(turn, 'web_extract', {}, {'results': [{'content': 'Old source'}]}, call='old')
        turn.observe('pre_api_request', {'api_request_id': 'api-2'}, 5)
        self.tool(turn, 'web_extract', {}, {'error': 'Fetch failed'}, call='failed')
        turn.observe('pre_api_request', {'api_request_id': 'api-3'}, 8)
        self.assertEqual(turn.progress['status'], 'error')
        self.assertIn('没有成功', status_text(turn, 'zh', now=20))
        self.assertNotIn('部分', status_text(turn, 'zh', now=20))

    def test_generic_public_note_cannot_overwrite_tool_failure(self):
        turn = self.begin('上海天气')
        self.tool(turn, 'web_search', {}, {'error': 'offline'})
        turn.observe('pre_tool_call', {'tool_call_id': 'note', 'tool_name': 'telegram_ux_update'}, 4)
        turn.observe('post_tool_call', {'tool_call_id': 'note', 'tool_name': 'telegram_ux_update', 'status': 'ok', 'args': {'action': '正在处理'}}, 5)
        self.assertIn('没有成功', status_text(turn, 'zh'))

    def test_same_public_request_id_retry_recovers_without_counting_a_new_call(self):
        turn = self.begin('上海天气')
        turn.observe('api_request_error', {'api_request_id': 'api-1', 'retry_count': 0}, 3)
        self.assertIn('模型请求失败', status_text(turn, 'zh'))
        turn.observe('pre_api_request', {'api_request_id': 'api-1', 'retry_count': 1}, 4)
        turn.observe('api_request_error', {'api_request_id': 'api-1', 'retry_count': 0}, 4.1)
        self.assertNotIn('模型请求失败', status_text(turn, 'zh'))
        turn.observe('post_api_request', {'api_request_id': 'api-1', 'retry_count': 1, 'assistant_tool_call_count': 1}, 5)
        self.assertEqual(turn.current_kind, 'working')
        self.assertEqual(turn.apis, {'api-1': 'ok'})
        self.assertEqual(len(turn.apis), 1)

    def test_generic_public_note_does_not_replace_verified_search_result(self):
        turn = self.begin('上海天气')
        self.tool(turn, 'web_search', {}, {'results': [{'title': 'Weather', 'url': 'https://example.org'}]})
        turn.observe('pre_tool_call', {'tool_call_id': 'note', 'tool_name': 'telegram_ux_update'}, 4)
        turn.observe('post_tool_call', {'tool_call_id': 'note', 'tool_name': 'telegram_ux_update', 'status': 'ok', 'args': {'action': '正在处理'}}, 5)
        self.assertIn('1 条搜索结果', status_text(turn, 'zh'))

    def test_display_ticks_do_not_make_an_unobserved_stage_or_refresh_ttl(self):
        turn = self.begin('上海天气')
        touched = turn.touched
        self.assertNotIn('汇总', status_text(turn, 'zh', now=100))
        self.assertEqual(turn.touched, touched)


class VisiblePriorityTests(unittest.IsolatedAsyncioTestCase):
    async def test_fast_missing_file_is_visible_even_when_finalization_coalesces(self):
        ctx, telegram = ContextStub(cleanup_delay=0.01), TelegramStub()
        clock = [1.0]
        adapter = HermesCatalogAdapter(ctx, clock=lambda: clock[0])
        adapter.wire_telegram(None, telegram)
        adapter.transport.interval = 0.02
        adapter.pre_gateway_dispatch(event=event())
        start(adapter, user_message='请读取 /tmp/TGUX_DOES_NOT_EXIST.txt')
        await asyncio.sleep(0.01)
        ids = {'session_id': 's1', 'turn_id': 't1'}
        adapter.observe('pre_tool_call', **ids, tool_call_id='read', tool_name='read_file', args={'path': '/tmp/TGUX_DOES_NOT_EXIST.txt'})
        adapter.observe('post_tool_call', **ids, tool_call_id='read', tool_name='read_file', status='error', result={'error': 'File not found: /tmp/TGUX_DOES_NOT_EXIST.txt'})
        adapter.observe('pre_api_request', **ids, api_request_id='next')
        adapter.observe('post_llm_call', **ids, assistant_response='native failure explanation')
        adapter.on_session_end(**ids, completed=True)
        await asyncio.wait_for(asyncio.gather(*ctx.tasks), 1)
        self.assertEqual(len(telegram.sent), 1)
        self.assertTrue(any('未找到指定文件' in item['content'] for item in telegram.edits))
        self.assertEqual(len(telegram.deleted), 1)
        self.assertTrue(all(item['message_id'] == '1' for item in telegram.edits + telegram.deleted))
        self.assertFalse(any('native failure explanation' in item['content'] for item in telegram.edits))
        adapter.close()

    async def test_heartbeat_ages_result_without_new_tool_or_ttl_refresh(self):
        ctx, telegram = ContextStub(cleanup_delay=0.01), TelegramStub()
        clock = [10.0]
        adapter = HermesCatalogAdapter(ctx, clock=lambda: clock[0])
        adapter.wire_telegram(None, telegram)
        adapter.transport.interval = 0.01
        adapter.pre_gateway_dispatch(event=event())
        start(adapter, user_message='调查最近7天 OpenAI 新闻')
        await asyncio.sleep(0.01)
        ids = {'session_id': 's1', 'turn_id': 't1'}
        adapter.observe('pre_tool_call', **ids, tool_call_id='search', tool_name='web_search', args={'query': 'site:openai.com long query'})
        adapter.observe('post_tool_call', **ids, tool_call_id='search', tool_name='web_search', status='ok', result={'results': [{'title': 'News', 'url': 'https://example.org'}]})
        adapter.observe('pre_api_request', **ids, api_request_id='next')
        clock[0] = 15
        await asyncio.sleep(2.1)
        self.assertTrue(any('汇总最近 7 天 OpenAI 新闻' in item['content'] for item in telegram.edits))
        self.assertEqual(adapter.turns[('s1', 't1')].touched, 10)
        self.assertEqual(adapter.transport.panels[('s1', 't1')].text, adapter.refresh(('s1', 't1')))
        adapter.on_session_end(**ids, completed=True)
        await asyncio.wait_for(asyncio.gather(*ctx.tasks), 1)
        adapter.close()
