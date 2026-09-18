"""Lifecycle failure/recovery tests use disposable homes, never a real profile."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import hashlib
import unittest
from unittest.mock import patch
from types import SimpleNamespace

import yaml
import install as lifecycle
from plugin.compat import CompatibilityError, python_ast_v1, verify_core


class _LifecycleFixture(unittest.TestCase):
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


class LifecycleTests(_LifecycleFixture):
    def test_upgrade_preview_reports_restored_global_settings_without_writing(self):
        self.original["agent"] = {"gateway_notify_interval": 180}
        self.save(self.original)
        desired = lifecycle.desired_values
        def old_defaults(preset, language=None):
            values = desired(preset, language)
            values[("agent", "gateway_notify_interval")] = 1
            return values
        with patch.object(lifecycle, "desired_values", side_effect=old_defaults):
            self.install()
        before = self.path.read_bytes()
        preview = self.install(dry_run=True)
        self.assertEqual(self.path.read_bytes(), before)
        self.assertIn("agent.gateway_notify_interval", preview["changed_paths"])
        self.install()
        self.assertEqual(self.config()["agent"]["gateway_notify_interval"], 180)

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
    @staticmethod
    def contract(profiles):
        for profile in profiles:
            profile.setdefault("python_ast_v1", {name: "0" * 64 for name in profile["files"]})
        return {"schema": 4, "policy": "reviewed-source",
                "guarded_files": list(profiles[0]["files"]), "profiles": profiles}

    @staticmethod
    def version(root):
        (root / "pyproject.toml").write_text('[project]\nversion = "0.21.2"\n')

    def test_comment_and_indentation_formatting_do_not_disable_the_plugin(self):
        source = "def allowed(user):\n    return user == 7\n"
        # Published fixture for the versioned fingerprint format; do not generate
        # the expected hash using the implementation under test.
        digest = "e19ea29f359e818906e3979e253c2e729748a8592d95cc0f9d075c56d7a500d9"
        profile = {"core_commit": "a" * 40, "hermes_version": "0.21.2",
                   "files": {"interface.py": hashlib.sha256(source.encode()).hexdigest()},
                   "python_ast_v1": {"interface.py": digest}}
        with tempfile.TemporaryDirectory() as raw, patch("plugin.compat.json.loads", return_value=self.contract([profile])):
            root = Path(raw)
            self.version(root)
            (root / "interface.py").write_text("# revised explanation\n\ndef allowed( user ):\n  return user == 7  # authorized id\n")
            self.assertEqual(verify_core(root)["core_commit"], "a" * 40)
            for changed in ("def allowed(user):\n  return True\n",
                            "def allowed(user):\n  return user != 7\n",
                            "def allowed(user):\n  return user == 8\n",
                            "def allowed(user):\nreturn user == 7\n",
                            source + "raise AssertionError('must not execute')\n"):
                with self.subTest(source=changed):
                    (root / "interface.py").write_text(changed)
                    with self.assertRaises(CompatibilityError):
                        verify_core(root)

    def test_ast_string_canonicalization_cannot_collide_with_tag_like_source(self):
        non_bmp = 'VALUE = "😀"\n'.encode()
        old_tag_collision = b'VALUE = "\\0HERMES_AST_NONBMP_V1:\\\\U0001f600"\n'
        self.assertNotEqual(python_ast_v1(non_bmp), python_ast_v1(old_tag_collision))

    def test_missing_core_interfaces_fail_closed(self):
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaisesRegex(CompatibilityError, "Mismatched interfaces"):
                verify_core(Path(root))

    def test_content_match_accepts_unrelated_commit_but_rejects_changed_interface(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self.version(root)
            (root / ".git").mkdir()
            (root / "interface.py").write_text("tested")
            profile = {"core_commit": "a" * 40, "hermes_version": "0.21.2",
                       "files": {"interface.py": hashlib.sha256(b"tested").hexdigest()}}
            with patch("plugin.compat.json.loads", return_value=self.contract([profile])), patch(
                "plugin.compat.subprocess.run", return_value=SimpleNamespace(returncode=0, stdout="b" * 40)
            ):
                result = verify_core(root)
                self.assertEqual(result["core_commit"], "a" * 40)
                self.assertEqual(result["source_commit"], "b" * 40)
                (root / "interface.py").write_text("unreviewed change")
                with self.assertRaisesRegex(CompatibilityError, "interface.py"):
                    verify_core(root)

    def test_cannot_mix_files_from_different_baselines(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self.version(root)
            profiles = [{"core_commit": letter * 40, "hermes_version": "0.21.2",
                         "files": {name: hashlib.sha256(letter.encode()).hexdigest()
                                   for name in ("a.py", "b.py")}} for letter in ("a", "b")]
            (root / "a.py").write_text("a")
            (root / "b.py").write_text("b")
            with patch("plugin.compat.json.loads", return_value=self.contract(profiles)):
                with self.assertRaises(CompatibilityError):
                    verify_core(root)
                (root / "a.py").write_text("b")
                self.assertEqual(verify_core(root)["core_commit"], "b" * 40)


class ConfigurationScopeTests(unittest.TestCase):
    def test_recommended_settings_do_not_change_global_notification_policy(self):
        base = {"agent": {"gateway_notify_interval": 180},
                "display": {"busy_ack_enabled": False, "busy_steer_ack_enabled": False}}
        configured, _records = lifecycle.plan_install(base, None, "recommended")
        self.assertEqual(configured["agent"], base["agent"])
        for name in ("busy_ack_enabled", "busy_steer_ack_enabled"):
            self.assertEqual(configured["display"][name], base["display"][name])
            self.assertTrue(configured["display"]["platforms"]["telegram"][name])

    def test_upgrade_retires_global_defaults_and_preserves_later_user_edits(self):
        records = [{"path": ["agent", "gateway_notify_interval"], "kind": "value",
                    "before": {"exists": True, "value": 180}, "after": {"exists": True, "value": 1}},
                   {"path": ["display", "busy_ack_enabled"], "kind": "value",
                    "before": {"exists": False}, "after": {"exists": True, "value": True}}]
        for interval, expected in ((1, 180), (240, 240)):
            config = {"agent": {"gateway_notify_interval": interval}, "display": {"busy_ack_enabled": True}}
            configured, current = lifecycle.plan_install(config, {"records": records}, "recommended")
            self.assertEqual(configured["agent"]["gateway_notify_interval"], expected)
            self.assertNotIn("busy_ack_enabled", configured["display"])
            self.assertFalse(any(r["path"] == ["agent", "gateway_notify_interval"] for r in current))


class NativeConfigurationTests(_LifecycleFixture):
    def native_tree(self):
        target = self.home / "plugins" / lifecycle.PLUGIN_ID
        lifecycle.copy_plugin(Path(__file__).parent / "plugin", target)
        (target / ".git").mkdir()
        (target / ".git" / "HEAD").write_text("fixture native checkout")
        (target / ".hermes-catalog.json").write_text('{"sha": "fixture"}')
        return target

    def tree_bytes(self, target):
        return {str(p.relative_to(target)): p.read_bytes() for p in target.rglob("*") if p.is_file()}

    def test_configure_restore_preserves_native_checkout_and_user_edits(self):
        target = self.native_tree()
        before = self.tree_bytes(target)
        result = lifecycle.configure(self.home, language="en")
        self.assertEqual(result["management"], "config-only")
        self.assertEqual(self.config()["plugins"]["entries"][lifecycle.PLUGIN_ID]["settings"]["language"], "en")
        changed = self.config()
        changed["model"]["default"] = "user-changed"
        changed["display"]["platforms"]["telegram"]["streaming"] = True
        self.save(changed)
        lifecycle.configure(self.home, language="en")
        self.assertEqual(self.config(), changed)
        lifecycle.uninstall(self.home, config_only=True)
        self.assertEqual(self.tree_bytes(target), before)
        expected = deepcopy(self.original)
        expected["model"]["default"] = "user-changed"
        self.assertEqual(self.config(), expected)

    def test_wrong_management_command_cannot_replace_native_checkout(self):
        target = self.native_tree()
        before = self.tree_bytes(target)
        lifecycle.configure(self.home)
        with self.assertRaisesRegex(RuntimeError, "managed by Hermes"):
            self.install()
        with self.assertRaisesRegex(RuntimeError, "restore-config"):
            lifecycle.uninstall(self.home)
        self.assertEqual(self.tree_bytes(target), before)

    def test_configure_refuses_existing_zip_management(self):
        self.install()
        before = self.path.read_bytes()
        with self.assertRaisesRegex(RuntimeError, "ZIP installation"):
            lifecycle.configure(self.home)
        self.assertEqual(self.path.read_bytes(), before)

    def test_interrupted_configuration_recovers_without_replacing_checkout(self):
        target = self.native_tree()
        before = self.tree_bytes(target)
        config_before = self.path.read_bytes()
        real_write = lifecycle.atomic_write
        def fail(path, data, mode=0o600):
            if path == self.home / lifecycle.STATE_DIR / "state.json":
                raise OSError("simulated crash")
            return real_write(path, data, mode)
        with patch.object(lifecycle, "atomic_write", side_effect=fail), patch.object(lifecycle, "recover"):
            with self.assertRaises(OSError):
                lifecycle.configure(self.home)
        # An independent native update after the crash must survive config recovery.
        (target / ".git" / "HEAD").write_text("updated by native manager")
        before[".git/HEAD"] = b"updated by native manager"
        with lifecycle.locked(self.home) as directory:
            self.assertTrue(lifecycle.recover(self.home, directory))
        self.assertEqual(self.path.read_bytes(), config_before)
        self.assertEqual(self.tree_bytes(target), before)

    def test_configure_dry_run_is_read_only_for_config_and_checkout(self):
        target = self.native_tree()
        before = self.tree_bytes(target)
        config_before = self.path.read_bytes()
        lifecycle.configure(self.home, dry_run=True)
        self.assertEqual(self.path.read_bytes(), config_before)
        self.assertEqual(self.tree_bytes(target), before)


if __name__ == "__main__":
    unittest.main()
