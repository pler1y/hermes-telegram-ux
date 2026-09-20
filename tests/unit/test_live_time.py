"""Timestamp/time-zone conversions observed in public tool calls, never notes."""
import shlex
import unittest

from catalog.intelligence import code_stage, shell_stage, tool_context
from catalog.model import Turn
from catalog.presentation import status_text


# Exact public arguments from round-4/case-A seq 22 and 26.
CAPTURED_PYTHON = 'python3 -c "from datetime import datetime, timezone; i=2087562800982077492; ms=(i>>22)+1288834974657; print(ms); print(datetime.fromtimestamp(ms/1000, timezone.utc).isoformat())"'
CAPTURED_DATES = "TZ=Asia/Shanghai date -d '@1786548731.452' '+%Y-%m-%d %H:%M:%S.%3N %Z (UTC%:z)' && TZ=America/Los_Angeles date -d '@1786548731.452' '+%Y-%m-%d %H:%M:%S.%3N %Z (UTC%:z)'"
# Exact public execute_code argument from round-3/case-A seq 36.
CAPTURED_CODE = "from datetime import datetime, timezone\nsnowflake=2087562800982077492\nms=(snowflake >> 22)+1288834974657\nprint(ms)\nprint(datetime.fromtimestamp(ms/1000, tz=timezone.utc).isoformat(timespec='milliseconds'))\nfrom zoneinfo import ZoneInfo\nprint(datetime.fromtimestamp(ms/1000, tz=ZoneInfo('Asia/Shanghai')).isoformat(timespec='milliseconds'))\nprint(datetime.fromtimestamp(ms/1000, tz=ZoneInfo('America/Los_Angeles')).isoformat(timespec='milliseconds'))"

# Exact public terminal argument from round-5/case-A seq 28.
CAPTURED_HEREDOC = "python3 - <<'PY'\nfrom datetime import datetime, timezone\nfrom zoneinfo import ZoneInfo\nsid=2087562804194902477\nms=(sid >> 22)+1288834974657\ndt=datetime.fromtimestamp(ms/1000, tz=timezone.utc)\nprint('milliseconds:', ms)\nprint('UTC:', dt.isoformat(timespec='milliseconds'))\nprint('US Pacific:', dt.astimezone(ZoneInfo('America/Los_Angeles')).isoformat(timespec='milliseconds'))\nprint('China:', dt.astimezone(ZoneInfo('Asia/Shanghai')).isoformat(timespec='milliseconds'))\nPY"

# Exact public terminal argument from round-6/case-A seq 22.
CAPTURED_LITERAL_IMPORT = 'python3 -c "from datetime import datetime,timezone; i=2087565020158992709; ms=(i>>22)+1288834974657; print(ms); print(datetime.fromtimestamp(ms/1000,timezone.utc).isoformat()); print(datetime.fromtimestamp(ms/1000,timezone.utc).astimezone(__import__(\'zoneinfo\').ZoneInfo(\'Asia/Shanghai\')).isoformat())"'


class LiveTimeTests(unittest.TestCase):
    def test_captured_python_and_date_conversions_have_a_real_distinct_stage(self):
        self.assertEqual(shell_stage(CAPTURED_PYTHON), 'convert_time')
        self.assertEqual(shell_stage(CAPTURED_DATES), 'convert_time')
        self.assertEqual(code_stage(CAPTURED_CODE), 'convert_time')
        for name, args in (('terminal', {'command': CAPTURED_PYTHON}),
                           ('terminal', {'command': CAPTURED_DATES}),
                           ('terminal', {'command': CAPTURED_HEREDOC}),
                           ('terminal', {'command': CAPTURED_LITERAL_IMPORT}),
                           ('execute_code', {'code': CAPTURED_CODE})):
            self.assertEqual(tool_context(name, args, '发布日期问题'), {'stage': 'convert_time', 'subject': ''})

    def test_captured_quoted_heredoc_and_only_its_standalone_variants(self):
        for command in (CAPTURED_HEREDOC, CAPTURED_HEREDOC + '\n',
                        CAPTURED_HEREDOC.replace("python3 - <<'PY'", 'python3.12 - <<"PY"'),
                        CAPTURED_HEREDOC.replace("python3 - <<'PY'", "python - << 'PY'")):
            with self.subTest(header=command.splitlines()[0]):
                self.assertEqual(shell_stage(command), 'convert_time')

    def test_heredoc_shell_composition_or_unquoted_delimiters_are_not_interpreted(self):
        for command in (
            CAPTURED_HEREDOC.replace("<<'PY'", '<<PY'),
            CAPTURED_HEREDOC.replace("<<'PY'", "<<-'PY'"),
            CAPTURED_HEREDOC.replace("<<'PY'", "<<'P'Y"),
            CAPTURED_HEREDOC.replace("<<'PY'", "<<'$(command)'"),
            CAPTURED_HEREDOC.replace("python3 -", 'python3 -u -'),
            CAPTURED_HEREDOC.replace("python3 -", 'python3 - > /private/output'),
            'TZ=UTC ' + CAPTURED_HEREDOC,
            'bash -lc ' + shlex.quote(CAPTURED_HEREDOC),
            'echo before; ' + CAPTURED_HEREDOC,
            CAPTURED_HEREDOC + '\necho after',
            CAPTURED_HEREDOC + ' && echo after',
            CAPTURED_HEREDOC + '\n# trailing shell content',
            CAPTURED_HEREDOC + '\n\n',
            CAPTURED_HEREDOC + '\nprint(1)\nPY',
            CAPTURED_HEREDOC.replace("\nfrom datetime", "\nPY\nfrom datetime", 1),
        ):
            with self.subTest(command=command[:100]):
                self.assertEqual(shell_stage(command), 'execute')

    def test_heredoc_body_reuses_the_pure_time_ast_gate(self):
        conversion = 'from datetime import datetime; print(datetime.fromtimestamp(100))'
        for body in (
            'open("/private/output", "w"); ' + conversion,
            'import requests; requests.get("https://example.org"); ' + conversion,
            'unknown_side_effect(); ' + conversion,
            'print("datetime.fromtimestamp(100)")',
            '# datetime.fromtimestamp(100)\nprint(1)',
            'from datetime import datetime\nif False:\n print(datetime.fromtimestamp(100))',
            'from datetime import datetime\ndef unused():\n return datetime.fromtimestamp(100)',
            'from datetime import datetime\nif unknown:\n print(datetime.fromtimestamp(100))',
            'print("$(touch /private/output)")',
        ):
            with self.subTest(body=body):
                command = "python3 - <<'PY'\n" + body + '\nPY'
                self.assertEqual(shell_stage(command), 'execute')

    def test_literal_datetime_and_zoneinfo_imports_follow_known_call_chains(self):
        for code in (
            "from datetime import datetime, timezone; print(datetime.fromtimestamp(100, timezone.utc).astimezone(__import__('zoneinfo').ZoneInfo('Asia/Shanghai')).isoformat())",
            "print(__import__('datetime').datetime.fromtimestamp(100).isoformat())",
            "dates=__import__('datetime'); zones=__import__('zoneinfo'); dt=dates.datetime.fromtimestamp(100, dates.timezone.utc); print(dt.astimezone(zones.ZoneInfo('Asia/Shanghai')).isoformat())",
            "Date=__import__('datetime').datetime; Zone=__import__('zoneinfo').ZoneInfo; print(Date.fromtimestamp(100, Zone('Asia/Shanghai')).isoformat())",
        ):
            with self.subTest(code=code):
                self.assertEqual(code_stage(code), 'convert_time')
                self.assertEqual(shell_stage('python3 -c ' + shlex.quote(code)), 'convert_time')

    def test_only_single_literal_standard_time_module_imports_are_supported(self):
        conversion = 'from datetime import datetime; print(datetime.fromtimestamp(100)); '
        for suffix in (
            "__import__('os')", "module='zoneinfo'; __import__(module)",
            "__import__('zone'+'info')", "__import__('zoneinfo', {})",
            "__import__('zoneinfo', fromlist=['ZoneInfo'])", "__import__(name='zoneinfo')",
            "__import__(*['zoneinfo'])", "loader=__import__; loader('zoneinfo')",
            "__import__=unknown; __import__('zoneinfo')",
            "__import__('zoneinfo').reset_tzpath([])",
            "eval('__import__(\"zoneinfo\")')", "unknown_side_effect()",
            "open('/private/output', 'w')",
        ):
            with self.subTest(suffix=suffix):
                self.assertNotEqual(code_stage(conversion + suffix), 'convert_time')
                self.assertEqual(shell_stage('python3 -c ' + shlex.quote(conversion + suffix)), 'execute')
        self.assertEqual(code_stage("__import__('zoneinfo').ZoneInfo('Asia/Shanghai')"), 'execute')

    def test_supported_datetime_imports_aliases_and_zone_conversion(self):
        for code in (
            'import datetime as dates; print(dates.datetime.fromtimestamp(100).isoformat())',
            'from datetime import datetime as Date; print(Date.fromtimestamp(100))',
            'from datetime import datetime, timezone; from zoneinfo import ZoneInfo; dt=datetime.fromtimestamp(100, timezone.utc); print(dt.astimezone(ZoneInfo("Asia/Shanghai")).isoformat())',
            'from datetime import datetime; print(datetime.fromisoformat("2026-01-01T01:00:00").timestamp())',
        ):
            with self.subTest(code=code):
                self.assertEqual(code_stage(code), 'convert_time')
                self.assertEqual(shell_stage('python3 -c ' + shlex.quote(code)), 'convert_time')

    def test_strings_comments_dead_calls_unknown_imports_or_calls_do_not_prove_conversion(self):
        for code in (
            '# datetime.fromtimestamp(100)\nprint(1)',
            'print("datetime.fromtimestamp(100)")',
            'datetime.fromtimestamp(100)',
            'from other_package import datetime; datetime.fromtimestamp(100)',
            'from datetime import datetime; datetime = unknown; datetime.fromtimestamp(100)',
            'from datetime import datetime\nif False:\n print(datetime.fromtimestamp(100))',
            'from datetime import datetime\ndef unused():\n return datetime.fromtimestamp(100)',
            'from datetime import datetime\nif unknown:\n print(datetime.fromtimestamp(100))',
            'from zoneinfo import ZoneInfo; print(ZoneInfo("Asia/Shanghai"))',
            'from datetime import datetime; unknown_side_effect(); print(datetime.fromtimestamp(100))',
            'from datetime import datetime; print(datetime.fromtimestamp(100), file=output)',
        ):
            with self.subTest(code=code):
                self.assertNotEqual(code_stage(code), 'convert_time')
                self.assertNotEqual(shell_stage('python3 -c ' + shlex.quote(code)), 'convert_time')

    def test_fetch_and_explicit_write_take_precedence_over_conversion(self):
        time_code = 'from datetime import datetime; print(datetime.fromtimestamp(100))'
        self.assertEqual(code_stage('import requests; requests.get("https://example.org"); ' + time_code), 'read_web')
        self.assertEqual(code_stage('web_search("example"); ' + time_code), 'search')
        self.assertEqual(code_stage('open("/private/output.txt", "w"); ' + time_code), 'write')
        self.assertEqual(code_stage('write_file("/private/output.txt", "data"); ' + time_code), 'write')
        self.assertEqual(shell_stage('python3 -c ' + shlex.quote('open("out.txt", "w"); ' + time_code)), 'execute')

    def test_date_conversion_flags_are_read_only_and_keep_current_time_separate(self):
        for command in ("date -d '@100' '+%F'", "date --date='@100' '+%F'", "date -u --date '2026-01-01 01:00:00 UTC' '+%F %T'", "TZ=UTC date --date=@-100 +%s"):
            with self.subTest(command=command):
                self.assertEqual(shell_stage(command), 'convert_time')
        for command in ('date', 'date -u', "date '+%Y-%m-%d'", "TZ=UTC date '+%s'"):
            self.assertEqual(shell_stage(command), 'check_time')
        for command in (
            "date -s '@100' '+%F'", "date --set='@100' '+%F'", 'date 092017002026',
            "date -d '@100' -s '@200' '+%F'", "date -d '@100' --unknown '+%F'",
            "date -d '@100' --file=private '+%F'", "date -d '@100' '+%F' extra",
            "date -d '@100'", "date -d '@100' '+%F' && echo done",
            "date -d '@100' '+%F' > private.txt", "date -d '@100' +%F>/private/output",
            "date -d '@100' +%F;touch/private/output", "date -d '@100' '+%F' && date -s '@200'",
            "LD_PRELOAD=private.so date -d '@100' '+%F'", "TZ=$(command) date -d '@100' '+%F'",
        ):
            with self.subTest(command=command):
                self.assertNotEqual(shell_stage(command), 'convert_time')

    def test_observed_conversion_replaces_search_result_and_survives_api_without_exposing_values(self):
        for name, args in (('terminal', {'command': CAPTURED_PYTHON}),
                           ('terminal', {'command': CAPTURED_DATES}),
                           ('terminal', {'command': CAPTURED_HEREDOC}),
                           ('terminal', {'command': CAPTURED_LITERAL_IMPORT}),
                           ('execute_code', {'code': CAPTURED_CODE})):
            with self.subTest(name=name, args_kind=next(iter(args))):
                turn = Turn('s', 't', 0)
                search = {'tool_name': 'web_search', 'tool_call_id': 'search', 'args': {'query': 'site:example.org release'}}
                turn.observe('pre_tool_call', search, 1)
                turn.observe('post_tool_call', dict(search, status='ok', result={'results': [{'title': 'A source', 'url': 'https://example.org'}]}), 2)
                self.assertIn('找到 1 条结果', status_text(turn, 'zh'))
                data = {'tool_name': name, 'tool_call_id': 'time', 'args': args}
                turn.observe('pre_tool_call', data, 3)
                self.assertEqual(status_text(turn, 'zh'), '🕒 换算时间…')
                self.assertEqual(status_text(turn, 'en'), '🕒 Converting timestamps and time zones…')
                turn.observe('post_tool_call', dict(data, status='ok', result={'exit_code': 0, 'output': '1786548731.452 PRIVATE_RESULT'}), 4)
                expected = '🕒 时间换算已执行，核对结果…'
                self.assertEqual(status_text(turn, 'zh'), expected)
                turn.observe('pre_api_request', {'api_request_id': 'next'}, 5)
                turn.observe('post_api_request', {'api_request_id': 'next'}, 6)
                self.assertEqual(status_text(turn, 'zh', now=1000), expected)
                self.assertFalse(turn.note_calls)
                for forbidden in ('2087562800982077492', '2087562804194902477', '2087565020158992709', '1786548731.452', 'PRIVATE_RESULT', 'datetime', 'date -d', 'Asia/Shanghai'):
                    self.assertNotIn(forbidden, repr(turn))
                    self.assertNotIn(forbidden, status_text(turn, 'zh'))

    def test_failure_does_not_claim_time_conversion_completed(self):
        turn = Turn('s', 't', 0)
        data = {'tool_name': 'terminal', 'tool_call_id': 'time', 'args': {'command': CAPTURED_DATES}}
        turn.observe('pre_tool_call', data, 1)
        turn.observe('post_tool_call', dict(data, status='ok', result={'exit_code': 1, 'output': 'private failed date'}), 2)
        self.assertIn('没有成功', status_text(turn, 'zh'))
        self.assertNotIn('已执行', status_text(turn, 'zh'))
        self.assertNotIn('private', repr(turn))


if __name__ == '__main__':
    unittest.main()
