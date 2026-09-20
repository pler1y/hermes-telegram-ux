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

    def test_telegram_import_allowlist_is_exact_and_factory_scoped(self):
        source = "def wire_telegram():\n    from telegram import InlineKeyboardButton\n"
        self.assertEqual(scan(source, "catalog/adapter.py"), [])
        for bad, filename in ((source, "catalog/interface.py"),
                              ("from telegram import InlineKeyboardButton", "catalog/adapter.py"),
                              (source.replace("InlineKeyboardButton", "Bot"), "catalog/adapter.py"),
                              (source.replace("wire_telegram", "other"), "catalog/adapter.py")):
            self.assertTrue(scan(bad, filename))


if __name__ == "__main__":
    unittest.main()
