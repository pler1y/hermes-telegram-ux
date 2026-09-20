"""Public milestone grammar observed in real acceptance, replayed through Turn."""
import unittest

from catalog.model import Turn
from catalog.presentation import meaningful_note, status_text


CAPTURED_ACTION = '区分已发布版本与仅合入主分支的后续改动，并筛选真正影响用户的项目'
CAPTURED_FINDING = '9 月 15 日官方还发布了 Hermes Business：团队账户、共享余额、成员额度和共享技能。'
# Exact R6 D-current public-hook-events seq278 action/finding.
CAPTURED_CLASSIFICATION = {
    'action': '把核实结果按“已发布版本／产品公告／仅 main”归类，并统一换算为北京时间。',
    'finding': 'GitHub API 显示最新正式 release 为 v2026.9.14，published_at 为 2026-09-14T16:04:14Z。',
}
NEW_VERBS = ('区分', '对照', '比对', '交叉核对', '交叉验证', '追踪', '核验', '组装', '对齐')
CAPTURED_DATA_NOTES = (
    {
        'action': '核验月度与地区汇总口径，并量化重复、缺失和异常记录对结论的影响',
        'finding': '文件含 26 条数据记录，已看到重复订单、缺失地区、缺失成本及极端收入候选。',
    },
    {
        'action': '组装去重基准与异常剔除敏感性对照，重点确认各月地区领先关系是否翻转',
        'finding': '重复记录会改变 3 月华东与华北的收入排序；4 月零收入、5 月负收入和 8 月极端收入会显著扭曲对应利润。',
    },
)


class LiveNoteTests(unittest.TestCase):
    def note(self, turn, fields, call='note'):
        data = {'tool_name': 'telegram_ux_update', 'tool_call_id': call, 'args': fields}
        turn.observe('pre_tool_call', data, 4)
        turn.observe('post_tool_call', dict(data, status='ok'), 5)

    def test_captured_round_two_d_action_survives_api_and_yields_to_new_tool(self):
        # Exact action/finding captured in R2D public-hook-events seq 261/262.
        # The surrounding sequence here is a deterministic public-event replay.
        turn = Turn('s', 't', 0, user_task='调查最近一周项目的主要变化')
        source = {'tool_name': 'web_extract', 'tool_call_id': 'read',
                  'args': {'url': 'https://example.org/news'}}
        turn.observe('pre_tool_call', source, 1)
        turn.observe('post_tool_call', dict(source, status='ok', result={'content': 'public source text'}), 2)
        self.note(turn, {'action': CAPTURED_ACTION, 'finding': CAPTURED_FINDING})
        self.assertEqual(turn.note, {'action': CAPTURED_ACTION})
        expected = '📝 ' + CAPTURED_ACTION + '…'
        self.assertEqual(status_text(turn, 'zh'), expected)
        self.assertNotIn('9 月 15 日', status_text(turn, 'zh'))
        turn.observe('pre_api_request', {'api_request_id': 'next'}, 6)
        turn.observe('post_api_request', {'api_request_id': 'next', 'assistant_tool_call_count': 1}, 7)
        self.assertEqual(status_text(turn, 'zh', now=1000), expected)
        turn.observe('pre_tool_call', {'tool_name': 'web_search', 'tool_call_id': 'fresh',
                     'args': {'query': 'site:docs.example.org release notes'}}, 8)
        self.assertEqual(status_text(turn, 'zh'), '🔎 搜索 docs.example.org…')
        self.assertFalse(turn.note)

    def test_captured_classification_action_is_visible_and_keeps_finding_evidence_boundary(self):
        turn = Turn('s', 't', 0, user_task='调查最近一周项目进展')
        tool = {'tool_name': 'web_extract', 'tool_call_id': 'read', 'args': {'url': 'https://example.org/releases'}}
        turn.observe('pre_tool_call', tool, 1)
        turn.observe('post_tool_call', dict(tool, status='ok', result={'content': 'source text'}), 2)
        self.note(turn, CAPTURED_CLASSIFICATION)
        action = CAPTURED_CLASSIFICATION['action'].rstrip('。')
        self.assertEqual(turn.note, {'action': action})
        expected = '📝 ' + action + '…'
        self.assertEqual(status_text(turn, 'zh'), expected)
        self.assertNotIn('published_at', repr(turn))
        turn.observe('pre_api_request', {'api_request_id': 'next'}, 6)
        turn.observe('post_api_request', {'api_request_id': 'next', 'assistant_tool_call_count': 1}, 7)
        self.assertEqual(status_text(turn, 'zh', now=1000), expected)
        turn.observe('pre_tool_call', {'tool_name': 'web_search', 'tool_call_id': 'fresh',
                     'args': {'query': 'site:docs.example.org release notes'}}, 8)
        self.assertEqual(status_text(turn, 'zh'), '🔎 搜索 docs.example.org…')
        self.assertFalse(turn.note)

    def test_captured_round_seven_source_alignment_is_visible(self):
        # R7 D-current seq268/269: concrete comparison, not a completed claim.
        action = '对齐 GitHub release、tag、main 提交与官方公告的时间和交付状态'
        turn = Turn('s', 't', 0, user_task='调查最近一周项目进展')
        self.note(turn, {'action': action, 'finding': '最新版本已经确认'})
        self.assertEqual(turn.note, {'action': action})
        expected = '🕒 ' + action + '…'
        self.assertEqual(status_text(turn, 'zh'), expected)
        turn.observe('pre_api_request', {'api_request_id': 'next'}, 6)
        turn.observe('post_api_request', {'api_request_id': 'next', 'assistant_tool_call_count': 1}, 7)
        self.assertEqual(status_text(turn, 'zh', now=1000), expected)
        turn.observe('pre_tool_call', {'tool_name': 'web_extract', 'tool_call_id': 'fresh',
                     'args': {'url': 'https://api.github.com/repos/example/project/releases/latest'}}, 8)
        self.assertEqual(status_text(turn, 'zh'), '📖 阅读 api.github.com…')
        self.assertFalse(turn.note)
        for rejected in ('对齐 api_key=private', '对齐 <think>private reasoning</think>',
                         '证据已对齐；正在汇总不同来源的信息'):
            self.assertEqual(meaningful_note({'action': rejected}), {})
        self.assertEqual(meaningful_note({'action': action}, action), {})

    def test_ba_classification_requires_a_specific_object_or_dimension(self):
        for action in ('把发布记录按来源分类', '把公告与主分支改动归类',
                       '把订单按地区归类', '把数据按月份分类',
                       '把已完成订单按地区分类', '把公告分类，并核对发布时间'):
            with self.subTest(action=action):
                self.assertEqual(meaningful_note({'action': action}), {'action': action})
                self.assertEqual(meaningful_note({'next': action}), {'next': action})
        for action in ('把归类', '把分类', '把结果分类', '把任务归类',
                       '把所有内容分类', '把信息按类别分类', '把结果进行归类',
                       '把结果处理一下', '把这个事情弄清楚', '把发布日期说成明天'):
            with self.subTest(action=action):
                self.assertEqual(meaningful_note({'action': action}), {})
                self.assertEqual(meaningful_note({'next': action}), {})

    def test_ba_classification_does_not_bypass_outcome_echo_or_secret_filters(self):
        for action in ('把公告归类完毕，发布日期为明天', '把结果已确认归类',
                       '把核实结果按已确认分类', '把公告归类，并已确认发布时间',
                       '把公告归类，并核对发布日期已确认',
                       '把 api_key=private 的资料归类', '把 site:example.org 查询归类',
                       '把 <think>private reasoning</think> 归类',
                       '证据已对齐；正在汇总不同来源的信息'):
            with self.subTest(action=action):
                self.assertEqual(meaningful_note({'action': action}), {})
        task = '把发布记录按来源分类'
        self.assertEqual(meaningful_note({'action': task}, task), {})

    def test_new_stage_verbs_accept_concrete_work_objects(self):
        for action in ('区分发布版本与主分支改动', '对照公告与变更记录',
                       '比对不同来源中的日期', '交叉核对发布记录',
                       '交叉验证异常数据', '追踪消息删除事件的触发条件'):
            with self.subTest(action=action):
                self.assertEqual(meaningful_note({'action': action}), {'action': action})
                self.assertEqual(meaningful_note({'next': action}), {'next': action})

    def test_captured_round_three_data_stages_keep_api_and_fact_boundaries(self):
        # Exact inputs from R3C public-hook-events seq113/114 and seq121/122.
        for fields in CAPTURED_DATA_NOTES:
            with self.subTest(action=fields['action']):
                turn = Turn('s', 't', 0, user_task='分析数据质量对汇总的影响')
                tool = {'tool_name': 'execute_code', 'tool_call_id': 'compute',
                        'args': {'code': 'print(26)'}}
                turn.observe('pre_tool_call', tool, 1)
                turn.observe('post_tool_call', dict(tool, status='ok', result={'output': '26'}), 2)
                self.note(turn, fields)
                self.assertEqual(turn.note, {'action': fields['action']})
                expected = '📝 ' + fields['action'] + '…'
                self.assertEqual(status_text(turn, 'zh'), expected)
                self.assertNotIn(fields['finding'], status_text(turn, 'zh'))
                turn.observe('pre_api_request', {'api_request_id': 'next'}, 6)
                turn.observe('post_api_request', {'api_request_id': 'next', 'assistant_tool_call_count': 1}, 7)
                self.assertEqual(status_text(turn, 'zh', now=1000), expected)
                turn.observe('pre_tool_call', {'tool_name': 'read_file', 'tool_call_id': 'fresh',
                             'args': {'path': '/tmp/sales.csv'}}, 8)
                self.assertEqual(status_text(turn, 'zh'), '📖 读取 sales.csv…')
                self.assertFalse(turn.note)

    def test_new_verbs_still_require_an_object(self):
        for verb in NEW_VERBS:
            for prefix in ('', '正在', '我正在', '继续', '准备', '补充'):
                with self.subTest(verb=verb, prefix=prefix):
                    self.assertEqual(meaningful_note({'action': prefix + verb}), {})
                    self.assertEqual(meaningful_note({'next': prefix + verb}), {})

    def test_new_verbs_do_not_allow_completed_or_disguised_outcomes(self):
        for verb in NEW_VERBS:
            for claim in (verb + '完毕，发布日期为明天', verb + '结果已确认',
                          verb + '资料，发现发布日期为明天'):
                with self.subTest(claim=claim):
                    self.assertEqual(meaningful_note({'action': claim}), {})
                    self.assertEqual(meaningful_note({'next': claim}), {})
        turn = Turn('s', 't', 0)
        self.note(turn, {'action': '交叉验证异常记录', 'finding': '发布日期已经确认'})
        self.assertEqual(turn.note, {'action': '交叉验证异常记录'})
        self.assertNotIn('已经确认', status_text(turn, 'zh'))

    def test_new_verbs_do_not_bypass_question_echo_or_privacy_rules(self):
        task = '区分哪些版本已经发布'
        self.assertEqual(meaningful_note({'action': task}, task), {})
        for action in ('交叉核对 api_key=private', '追踪 <think>private reasoning</think>',
                       '对照 site:example.org private-query', '比对资料，因为我猜测日期不对'):
            with self.subTest(action=action):
                self.assertEqual(meaningful_note({'action': action}), {})
        self.assertEqual(meaningful_note({'action': '这些资料的发布日期就是明天'}), {})


if __name__ == '__main__':
    unittest.main()
