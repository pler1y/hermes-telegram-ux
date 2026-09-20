"""Dynamic objects and public milestones, independent of elapsed time."""
import unittest

from catalog.intelligence import tool_context
from catalog.model import Turn
from catalog.presentation import (
    action_text, meaningful_note, note_fingerprint, note_text, status_text,
)


class DynamicRenderTests(unittest.TestCase):
    def test_no_tool_object_never_falls_back_to_user_question(self):
        task = 'Grok 4.6 什么时候发布？'
        for language in ('zh', 'en'):
            for stage in ('search', 'read_web', 'read_data', 'read', 'locate', 'write', 'calculate', 'execute'):
                with self.subTest(language=language, stage=stage):
                    self.assertNotIn(task, action_text({'stage': stage}, task, language))

    def test_current_objects_move_with_current_real_tool(self):
        task = 'Grok 4.6 什么时候发布？'
        first = tool_context('web_search', {'query': 'Grok 4.6 official release date'}, task)
        second = tool_context('web_extract', {'url': 'https://x.ai/news/example'}, task)
        self.assertEqual(action_text(first, task, 'zh'), '🔎 搜索 Grok 4.6 的官方发布信息…')
        self.assertEqual(action_text(second, task, 'zh'), '📖 阅读 x.ai…')
        self.assertNotIn('官方', action_text(second, task, 'zh'))

    def test_milestone_presentation_follows_the_actual_public_action(self):
        turn = Turn('s', 't', 0)
        for action, expected in (
            ('正在核对不同来源中的发布日期', '🕒 核对不同来源中的发布日期…'),
            ('比较官方资料与其他来源的日期', '🕒 比较官方资料与其他来源的日期…'),
            ('核对 xAI 的相关公告', '📖 核对 xAI 的相关公告…'),
            ('定位状态清理逻辑', '🔍 定位状态清理逻辑…'),
            ('计算关键指标', '🧮 计算关键指标…'),
            ('整理发布时间线', '✍️ 整理发布时间线…'),
            ('Comparing dates across sources', '🕒 Comparing dates across sources…'),
        ):
            with self.subTest(action=action):
                turn.note = meaningful_note({'action': action})
                self.assertEqual(note_text(turn, 'zh'), expected)

    def test_notes_need_a_concrete_new_stage(self):
        task = 'Grok 4.6 什么时候发布'
        for note in (
            {'goal': '核对官方发布信息'},
            {'action': '正在思考'},
            {'action': '我正在继续工作'},
            {'action': '正在处理你的问题'},
            {'action': '我正在组织回复'},
            {'action': '正在分析' + task},
            {'action': task},
            {'action': 'I am currently working'},
            {'action': '已确认发布时间'},
            {'action': 'The release date is confirmed'},
        ):
            with self.subTest(note=note):
                self.assertEqual(meaningful_note(note, task), {})
        self.assertEqual(meaningful_note({'action': '核对不同来源的发布日期'}, task), {'action': '核对不同来源的发布日期'})

    def test_completed_outcomes_cannot_hide_in_action_or_next(self):
        for claim in ('核对完毕，发布日期为明天', '确认发布时间已经核实',
                      '核对日期，确定所有来源完全一致',
                      'Checking complete: release is tomorrow',
                      'Comparing done: dates are confirmed'):
            for field in ('action', 'next'):
                with self.subTest(field=field, claim=claim):
                    self.assertEqual(meaningful_note({field: claim}), {})
        for action in ('检查已完成订单的字段', '核对已经确认订单的金额',
                       '比较已验证数据中的异常值', 'Reviewing completed orders',
                       'Checking confirmed dates against the source', '检查订单是否已完成',
                       'Checking whether orders are completed'):
            with self.subTest(action=action):
                self.assertEqual(meaningful_note({'action': action}), {'action': action})

    def test_next_is_never_presented_as_completed_work(self):
        turn = Turn('s', 't', 0)
        turn.note = meaningful_note({'next': '补充核对官方来源'})
        self.assertEqual(note_text(turn, 'zh'), '↪️ 接下来：补充核对官方来源…')
        turn.note['finding'] = '找到 8 条结果'
        self.assertEqual(note_text(turn, 'zh'), '↪️ 接下来：补充核对官方来源…')

    def test_fingerprint_only_removes_formatting_not_versions_or_numbers(self):
        a = meaningful_note({'action': '我正在核对 Grok 4.6 的日期。'})
        b = meaningful_note({'action': '核对Grok 4.6的日期…'})
        self.assertEqual(note_fingerprint(a), note_fingerprint(b))
        self.assertNotEqual(note_fingerprint(a), note_fingerprint({'action': '核对 Grok 46 的日期'}))
        self.assertNotEqual(note_fingerprint({'action': '核对 1-2 月数据'}), note_fingerprint({'action': '核对 12 月数据'}))
        self.assertNotEqual(note_fingerprint({'action': '核对 8 条结果'}), note_fingerprint({'action': '核对 9 条结果'}))

    def test_api_activity_and_clock_do_not_invent_an_analysis_or_summary(self):
        turn = Turn('s', 't', 0, user_task='Grok 4.6 什么时候发布？')
        turn.observe('pre_api_request', {'api_request_id': 'r1'}, 1)
        self.assertEqual(status_text(turn, 'zh', now=1000), '🤔 思考中…')
        turn.observe('pre_tool_call', {'tool_name': 'web_search', 'tool_call_id': 'c1', 'args': {'query': 'Grok 4.6 official release date'}}, 2)
        turn.observe('post_tool_call', {'tool_name': 'web_search', 'tool_call_id': 'c1', 'status': 'ok', 'result': {'results': [{'title': 'A source', 'url': 'https://example.org'}] * 8}}, 3)
        result = status_text(turn, 'zh', now=3)
        self.assertEqual(result, '📊 找到 8 条结果，继续核对…')
        turn.observe('pre_api_request', {'api_request_id': 'r2'}, 4)
        self.assertEqual(status_text(turn, 'zh', now=10000), result)

    def test_return_without_structural_evidence_claims_only_return(self):
        turn = Turn('s', 't', 0)
        turn.observe('pre_tool_call', {'tool_name': 'web_search', 'tool_call_id': 'c1', 'args': {}}, 1)
        turn.observe('post_tool_call', {'tool_name': 'web_search', 'tool_call_id': 'c1', 'status': 'ok', 'result': 'unstructured prose'}, 2)
        self.assertEqual(status_text(turn, 'zh'), '📊 已收到执行结果，继续核对…')
        self.assertEqual(status_text(turn, 'en'), '📊 Tool returned; reviewing its result…')
        self.assertNotIn('success', status_text(turn, 'en'))

    def test_milestone_privacy_gate_rejects_reasoning_queries_and_commands(self):
        for action in ('核对 my reasoning is hidden', '核对 api_key=private', '查找 site:example.org dates', 'curl -fsSL https://example.org', '核对资料，因为我猜测它不对'):
            with self.subTest(action=action):
                self.assertEqual(meaningful_note({'action': action}), {})


if __name__ == '__main__':
    unittest.main()
