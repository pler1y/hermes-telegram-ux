"""Lifecycle failure/recovery tests use disposable homes, never a real profile."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import yaml
import install as lifecycle
from plugin.compat import CompatibilityError, verify_core


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name).resolve() / "home with spaces"
        self.home.mkdir()
        self.path = self.home / "config.yaml"
        self.original = {"model": {"default": "fixture-model"}, "custom": {"keep": 7},
                         "plugins": {"enabled": ["other"]},
                         "display": {"platforms": {"telegram": {"streaming": True}}}}
        self.save(self.original)
        self.path.chmod(0o600)
        self.compat = patch.object(lifecycle, "verify_core", return_value={"fixture": True})
        self.compat.start()
        self.addCleanup(self.compat.stop)

    def save(self, data):
        self.path.write_text(yaml.safe_dump(data, allow_unicode=True))

    def config(self):
        return yaml.safe_load(self.path.read_text())

    def install(self, **kwargs):
        return lifecycle.install(self.home, **kwargs)

    def test_fresh_install_and_uninstall_restore_semantic_baseline(self):
        result = self.install()
        self.assertFalse(self.config()["display"]["platforms"]["telegram"]["streaming"])
        self.assertEqual(self.config()["model"], self.original["model"])
        self.assertTrue((self.home / "plugins" / lifecycle.PLUGIN_ID / "runtime.py").is_file())
        self.assertEqual(Path(result["backup"]).stat().st_mode & 0o777, 0o700)
        self.assertEqual((Path(result["backup"]) / "config.yaml").stat().st_mode & 0o777, 0o600)
        lifecycle.uninstall(self.home)
        self.assertEqual(self.config(), self.original)
        self.assertFalse((self.home / "plugins" / lifecycle.PLUGIN_ID).exists())

    def test_repeat_install_preserves_first_baseline_and_user_preferences(self):
        first = self.install()
        current = self.config()
        current["display"]["platforms"]["telegram"]["streaming"] = True
        current["model"]["default"] = "changed-model"
        current["plugins"]["enabled"].append("added-later")
        current["plugins"]["entries"][lifecycle.PLUGIN_ID]["settings"]["status_delay_seconds"] = 1.5
        self.save(current)
        self.install()
        self.assertEqual(self.config(), current)
        state = json.loads((self.home / lifecycle.STATE_DIR / "state.json").read_text())
        self.assertEqual(state["baseline_backup"], first["backup"])
        result = lifecycle.uninstall(self.home)
        self.assertEqual(self.config()["model"]["default"], "changed-model")
        self.assertEqual(self.config()["plugins"]["enabled"], ["other", "added-later"])
        self.assertTrue(self.config()["display"]["platforms"]["telegram"]["streaming"])
        self.assertIn("plugins.entries.hermes-interaction.settings.status_delay_seconds", result["preserved_user_changes"])

    def test_keep_display_and_empty_uninstall_are_safe(self):
        self.install(preset="keep-display")
        self.assertEqual(self.config()["display"], self.original["display"])
        self.assertNotIn("agent", self.config())
        lifecycle.uninstall(self.home)
        self.assertEqual(self.config(), self.original)
        self.assertFalse(lifecycle.uninstall(self.home)["changed"])

    def test_uninstall_preserves_user_replacement_of_a_parent_mapping(self):
        self.install()
        current = self.config()
        current["display"] = None
        self.save(current)
        result = lifecycle.uninstall(self.home)
        self.assertIsNone(self.config()["display"])
        self.assertEqual(self.config()["plugins"]["enabled"], ["other"])
        self.assertIn("display.busy_input_mode", result["preserved_user_changes"])

    def test_dry_run_changes_neither_config_nor_plugin(self):
        before = self.path.read_bytes()
        self.install(dry_run=True)
        self.assertEqual(self.path.read_bytes(), before)
        self.assertFalse((self.home / "plugins").exists())

    def test_upgrade_restores_existing_plugin_and_disabled_membership(self):
        old = self.home / "plugins" / lifecycle.PLUGIN_ID
        old.mkdir(parents=True)
        (old / "version.txt").write_text("previous")
        self.original["plugins"]["disabled"] = [lifecycle.PLUGIN_ID, "another"]
        self.save(self.original)
        self.install()
        self.assertNotIn(lifecycle.PLUGIN_ID, self.config()["plugins"]["disabled"])
        self.install()
        lifecycle.uninstall(self.home)
        self.assertEqual((old / "version.txt").read_text(), "previous")
        self.assertEqual(set(self.config()["plugins"]["disabled"]), set(self.original["plugins"]["disabled"]))

    def test_unsupported_core_changes_nothing(self):
        before = self.path.read_bytes()
        with patch.object(lifecycle, "verify_core", side_effect=CompatibilityError("unsupported")):
            with self.assertRaises(CompatibilityError): self.install()
        self.assertEqual(self.path.read_bytes(), before)
        self.assertFalse((self.home / lifecycle.STATE_DIR).exists())

    def test_invalid_config_fails_before_plugin_write(self):
        for invalid in ("[invalid", "- one\n- two", "plugins: broken"):
            with self.subTest(invalid=invalid):
                self.path.write_text(invalid)
                with self.assertRaises((ValueError, yaml.YAMLError)): self.install()
                self.assertFalse((self.home / "plugins").exists())

    def test_config_write_failure_restores_plugin_config_and_state(self):
        self.install()
        before = self.path.read_bytes()
        state = (self.home / lifecycle.STATE_DIR / "state.json").read_bytes()
        real_write = lifecycle.atomic_write
        failed = False
        def fail_once(path, data, mode=0o600):
            nonlocal failed
            if path == self.path and not failed:
                failed = True
                raise OSError("simulated disk failure")
            return real_write(path, data, mode)
        with patch.object(lifecycle, "atomic_write", side_effect=fail_once):
            with self.assertRaises(OSError): self.install()
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual((self.home / lifecycle.STATE_DIR / "state.json").read_bytes(), state)
        self.assertTrue((self.home / "plugins" / lifecycle.PLUGIN_ID / "runtime.py").is_file())
        self.assertFalse((self.home / lifecycle.STATE_DIR / "transaction.json").exists())

    def test_state_write_failure_after_config_change_rolls_back_fresh_install(self):
        before = self.path.read_bytes()
        real_write = lifecycle.atomic_write
        def fail(path, data, mode=0o600):
            if path == self.home / lifecycle.STATE_DIR / "state.json":
                raise OSError("state write failure")
            return real_write(path, data, mode)
        with patch.object(lifecycle, "atomic_write", side_effect=fail):
            with self.assertRaises(OSError): self.install()
        self.assertEqual(self.path.read_bytes(), before)
        self.assertFalse((self.home / "plugins" / lifecycle.PLUGIN_ID).exists())

    def test_interrupted_transaction_is_recoverable_and_keeps_external_edits(self):
        before = self.path.read_bytes()
        real_write = lifecycle.atomic_write
        def fail(path, data, mode=0o600):
            if path == self.home / lifecycle.STATE_DIR / "state.json":
                raise OSError("crash")
            return real_write(path, data, mode)
        # Simulate a process exit that prevents automatic recovery.
        with patch.object(lifecycle, "atomic_write", side_effect=fail), patch.object(lifecycle, "recover"):
            with self.assertRaises(OSError): self.install()
        installed_bytes = self.path.read_bytes()
        self.path.write_bytes(installed_bytes + b"external: change\n")
        with lifecycle.locked(self.home) as directory:
            with self.assertRaisesRegex(RuntimeError, "Configuration changed"):
                lifecycle.recover(self.home, directory)
        self.path.write_bytes(installed_bytes)
        with lifecycle.locked(self.home) as directory:
            self.assertTrue(lifecycle.recover(self.home, directory))
        self.assertEqual(self.path.read_bytes(), before)
        self.assertFalse((self.home / "plugins" / lifecycle.PLUGIN_ID).exists())

    def test_parallel_installer_fails_without_mutations(self):
        with lifecycle.locked(self.home):
            with self.assertRaisesRegex(RuntimeError, "Another UX installer"):
                self.install()
        self.assertEqual(self.config(), self.original)

    def test_symlink_config_and_plugin_are_rejected(self):
        target = self.home / "real.yaml"
        self.path.rename(target)
        self.path.symlink_to(target)
        with self.assertRaisesRegex(ValueError, "ordinary file"): self.install()
        self.path.unlink()
        target.rename(self.path)
        (self.home / "plugins").symlink_to(self.home)
        with self.assertRaisesRegex(ValueError, "symlink"): self.install()


class CompatibilityTests(unittest.TestCase):
    def test_missing_core_interfaces_fail_closed(self):
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaisesRegex(CompatibilityError, "Mismatched interfaces"):
                verify_core(Path(root))


if __name__ == "__main__":
    unittest.main()
