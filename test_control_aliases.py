"""Stop phrases must match whole messages, never instructions containing them."""
import unittest

from plugin.controls import command_for


class StopAliases(unittest.TestCase):
    def test_natural_stop_requests(self):
        for text in ('等一下', '等一下呀', '等下', '等等', '停', '停下',
                     '停止', '先停一下', '先停', '暂停', '暂停一下',
                     '先暂停', '暂停任务', '停一下', '先停下',
                     '停止当前任务', '停止任务'):
            for message in (text, '  ' + text + '。  ', text + '！'):
                with self.subTest(message=message):
                    self.assertEqual(command_for(message), '/stop')

    def test_mentions_and_conditional_requests_do_not_stop(self):
        for text in ('等一下再部署', '如果出错就停一下', '不要停', '别暂停',
                     '解释一下暂停是什么意思', '等下一步完成后继续',
                     '苹果、香蕉等等', '“停”', ''):
            with self.subTest(text=text):
                self.assertIsNone(command_for(text))


if __name__ == '__main__':
    unittest.main()
