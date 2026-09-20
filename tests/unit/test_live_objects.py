"""Safe objects from query shapes observed during real model acceptance."""
import unittest

from catalog.intelligence import tool_context
from catalog.presentation import action_text


class LiveQueryObjectTests(unittest.TestCase):
    def test_actual_case_a_site_queries_expose_only_the_current_hostname(self):
        examples = (
            ('site:x.ai/news "Grok 4.6" release official', 'x.ai'),
            ('site:x.com/xai "Grok 4.6"', 'x.com'),
            ('site:docs.x.ai "Grok 4.6"', 'docs.x.ai'),
            ('site:example.org/announcements "Nimbus 7" official launch', 'example.org'),
            ('SITE:WWW.PUBLISHER.ORG/news "another project"', 'publisher.org'),
        )
        for query, host in examples:
            with self.subTest(query=query):
                info = tool_context('web_search', {'query': query}, '整段用户原问')
                self.assertEqual(info, {'stage': 'search', 'subject': host})
                self.assertEqual(action_text(info, '', 'zh'), '🔎 搜索 ' + host + '…')
                self.assertEqual(action_text(info, '', 'en'), '🔎 Searching for ' + host + '…')
                for raw in ('site:', 'SITE:', 'Grok', 'Nimbus', '整段用户原问', '/news', '/xai', '/announcements'):
                    self.assertNotIn(raw, repr(info))

    def test_site_keywords_are_not_interpreted_as_a_fact_or_public_object(self):
        query = 'site:example.org/PRIVATE_PATH "PRIVATE_QUERY_TERM" release confirmed tomorrow'
        info = tool_context('web_search', {'query': query}, '')
        self.assertEqual(info['subject'], 'example.org')
        for raw in ('PRIVATE_PATH', 'PRIVATE_QUERY_TERM', 'confirmed', 'tomorrow'):
            self.assertNotIn(raw, repr(info))
        self.assertNotIn('官方', action_text(info, '', 'zh'))

    def test_secret_reasoning_commands_and_unsafe_sources_remain_empty(self):
        queries = (
            'site:example.org "model" api_key=PRIVATE_SECRET',
            'site:example.org "model" Bearer PRIVATE_CREDENTIAL',
            'site:example.org <think>private reasoning</think>',
            'site:example.org My reasoning is that the date differs',
            'site:example.org $(cat /private/credential)',
            'site:example.org curl -fsSL https://private.org/report',
            'site:name:password@example.org "model"',
            'site:127.0.0.1/private "model"',
            'site:server.internal/private "model"',
            'site:localhost/private "model"',
            'site:/private/notes "model"',
            'site:*.example.org "model"',
            'site:example.org:8443/private "model"',
            'site:example.org/?token=PRIVATE_SECRET "model"',
            'site:example.org/?q=PRIVATE_QUERY "model"',
            'site:example.org\u202e/private "model"',
            'site:example.org ' + 'x' * 2048,
        )
        for query in queries:
            with self.subTest(query=query[:80]):
                self.assertEqual(tool_context('web_search', {'query': query}, '原问题')['subject'], '')

    def test_excluded_quoted_or_ambiguous_sites_are_not_presented_as_targets(self):
        for query in ('-site:example.org model release', 'NOT site:example.org model',
                      'site:example.org OR other sources',
                      'site:first.org site:second.org model',
                      '"site:example.org" model', "'site:example.org' model",
                      'site:"example.org" model'):
            with self.subTest(query=query):
                self.assertEqual(tool_context('web_search', {'query': query}, '原问题')['subject'], '')

    def test_operator_query_without_site_does_not_fall_back_to_user_text(self):
        for query in ('intitle:release "Nimbus 7"', 'filetype:pdf release',
                      'inurl:announcements "new model"', 'after:2026-09-01 "release"'):
            with self.subTest(query=query):
                self.assertEqual(tool_context('web_search', {'query': query}, '用户问了很多内容')['subject'], '')

    def test_case_d_visible_query_prefix_no_longer_becomes_a_status_object(self):
        # Actual round-1/case-D Telegram edit at 152.631s ended in this prefix.
        # The complete tool query was unavailable; these are reproductions,
        # not a claimed transcript of the original tool arguments.
        for query in ('Hermes Agent Business September 14 2026 Nous Portal En',
                      'Hermes Agent Business September 14 2026 Nous Portal Enterprise'):
            with self.subTest(query=query):
                info = tool_context('web_search', {'query': query}, '原问题')
                self.assertEqual(info['subject'], '')
                self.assertEqual(action_text(info, '', 'zh'), '🔎 搜索…')

    def test_english_keyword_bag_boundary_dates_and_long_objects_are_omitted(self):
        ten_words = 'Alpha beta gamma delta news latest update source model info'
        self.assertEqual(len(ten_words.split()), 10)
        for query in (ten_words, 'Nimbus public project latest official product update',
                      'Project September 14', 'Project 14 Sep', 'Project 2026 news',
                      'Project 09/14/2026 news', 'Project 2026-09-14 news',
                      'International infrastructure interoperability documentation'):
            with self.subTest(query=query):
                self.assertEqual(tool_context('web_search', {'query': query}, '原问题')['subject'], '')

    def test_round_two_case_a_long_post_identifier_is_not_a_natural_object(self):
        # Reproduction from the actual round-2/case-A visible edit at 132.494s;
        # this fixture does not claim to be the complete original tool query.
        for query in ('2087562800982077492 SpaceXAI Grok 4.6',
                      'record 12345 details', 'post 123456789 information'):
            with self.subTest(query=query):
                info = tool_context('web_search', {'query': query}, '原问题')
                self.assertEqual(info['subject'], '')
                self.assertEqual(action_text(info, '', 'zh'), '🔎 搜索…')
        for query in ('Grok 4.6 announcements', 'version 12345.6 documentation',
                      '8 search results', 'record 1234 details'):
            with self.subTest(query=query):
                self.assertEqual(tool_context('web_search', {'query': query}, '', 'en')['subject'], query)
        self.assertEqual(tool_context('web_search', {'query': 'site:example.org 2087562800982077492'}, '')['subject'], 'example.org')

    def test_short_natural_english_objects_and_typed_objects_still_work(self):
        for query in ('local weather', 'Hermes plugin API documentation',
                      'Aurora version 3 official announcements',
                      'state message cleanup logic', 'Grok 4.6 announcements'):
            with self.subTest(query=query):
                self.assertEqual(tool_context('web_search', {'query': query}, '', 'en')['subject'], query)
        self.assertEqual(tool_context('web_search', {'query': 'Nimbus version 3 official release date'}, '', 'en')['subject'],
                         'official release information for Nimbus version 3')
        self.assertEqual(tool_context('web_search', {'query': 'site:docs.example.org September 14 2026 new model updates'}, '', 'en')['subject'],
                         'docs.example.org')

    def test_embedded_search_uses_the_same_source_only_rule(self):
        info = tool_context('execute_code', {'code': 'web_search(query=\'site:docs.example.org "Nimbus"\')'}, '')
        self.assertEqual(info, {'stage': 'search', 'subject': 'docs.example.org'})


if __name__ == '__main__':
    unittest.main()
