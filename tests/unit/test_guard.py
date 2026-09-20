from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from check_boundary import check, scan


class BoundaryTests(unittest.TestCase):
    def test_payload_passes(self):
        self.assertEqual(check(), [])

    def test_private_imports_and_dynamic_rebinding_rejected(self):
        for source in (
            "from gateway.run import GatewayRunner", "from hermes_cli.plugins import _secret",
            "import importlib", "target._private()", "getattr(target, '_private')()",
            "setattr(target, 'send', replacement)", "self.adapter.send = replacement",
            "GatewayRunner.run = replacement", "exec(source)", "getattr(target, name)",
        ):
            with self.subTest(source=source):
                self.assertTrue(scan(source, "fixture.py"))

    def test_native_sdk_imports_are_rejected_even_inside_factory(self):
        for source in (
            "from telegram import InlineKeyboardButton",
            "from telegram.ext import CallbackQueryHandler",
            "def wire_telegram():\n    from telegram import InlineKeyboardButton\n",
            "def wire_telegram():\n    from telegram.ext import CallbackQueryHandler\n",
        ):
            with self.subTest(source=source):
                self.assertTrue(scan(source, "catalog/adapter.py"))


if __name__ == "__main__":
    unittest.main()
