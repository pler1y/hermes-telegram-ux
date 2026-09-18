"""Catalog declarations and fail-closed support policy, through real entry points."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import yaml

from plugin.compat import CompatibilityError, load_contract, verify_core

ROOT = Path(__file__).resolve().parent


class RecordingContext:
    def __init__(self):
        self.registered = {"provides_tools": [], "provides_hooks": [], "provides_middleware": []}
        self.cleanup = None

    def get_config(self, key, default=None):
        return default

    def register_tool(self, name, **kwargs):
        self.registered["provides_tools"].append(name)

    def register_hook(self, name, callback):
        self.registered["provides_hooks"].append(name)

    def register_middleware(self, name, callback):
        self.registered["provides_middleware"].append(name)

    def register_system_prompt_section(self, *args, **kwargs):
        pass

    def register_platform_handler(self, *args, **kwargs):
        pass

    def on_unload(self, callback):
        self.cleanup = callback


class CatalogDeclarations(unittest.TestCase):
    def test_both_manifests_match_real_registration_without_optional_state(self):
        from plugin import register
        ctx = RecordingContext()
        register(ctx)
        self.addCleanup(ctx.cleanup)
        root = yaml.safe_load((ROOT / "plugin.yaml").read_text())
        self.assertEqual(root, yaml.safe_load((ROOT / "plugin/plugin.yaml").read_text()))
        self.assertEqual(set(ctx.registered["provides_middleware"]), {"llm_request", "tool_request"})
        for key, actual in ctx.registered.items():
            self.assertCountEqual(root[key], actual, key)

    def test_invalid_contract_cannot_silently_accept_a_partial_or_empty_baseline(self):
        contract = load_contract()
        malformed = []
        for field, value in (("profiles", []), ("guarded_files", []), ("schema", 3),
                             ("policy", "allow-unknown")):
            bad = copy.deepcopy(contract)
            bad[field] = value
            malformed.append(bad)
        for field in ("files", "python_ast_v1"):
            bad = copy.deepcopy(contract)
            del bad["profiles"][0][field][bad["guarded_files"][0]]
            malformed.append(bad)
        bad = copy.deepcopy(contract)
        bad["profiles"].append(bad["profiles"][0])
        malformed.append(bad)
        for bad in malformed:
            with self.subTest(contract=bad), patch("plugin.compat.json.loads", return_value=bad):
                with self.assertRaisesRegex(CompatibilityError, "Invalid compatibility contract"):
                    load_contract()


class CorePolicy(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="ux-core-policy-")
        self.addCleanup(self.temp.cleanup)
        self.core = Path(self.temp.name)
        spec = importlib.util.find_spec("hermes_cli")
        real = Path(spec.origin).resolve().parent.parent
        for name in [*load_contract()["guarded_files"], "pyproject.toml"]:
            target = self.core / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(real / name, target)

    def test_source_archive_without_git_is_supported(self):
        result = verify_core(self.core)
        self.assertIsNone(result["source_commit"])
        self.assertEqual(result["policy"], "reviewed-source")

    def test_matching_interfaces_do_not_implicitly_support_another_core_version(self):
        metadata = self.core / "pyproject.toml"
        metadata.write_text('[project]\nversion = "0.22.0"\n')
        with self.assertRaisesRegex(CompatibilityError, "Unsupported Hermes version"):
            verify_core(self.core)
        metadata.unlink()
        with self.assertRaisesRegex(CompatibilityError, "Cannot read Hermes core version"):
            verify_core(self.core)

    def test_explicitly_reviewed_version_with_identical_sources_selects_its_own_baseline(self):
        result = verify_core(self.core)
        contract = load_contract()
        profile = copy.deepcopy(next(p for p in contract["profiles"] if p["core_commit"] == result["core_commit"]))
        # Use an unclaimed patch version so this remains a synthetic selection test
        # after the running 0.21.3 core gains its real reviewed baseline.
        profile.update(core_commit="f" * 40, hermes_version="0.21.4")
        contract["profiles"].append(profile)
        (self.core / "pyproject.toml").write_text('[project]\nversion = "0.21.4"\n')
        with patch("plugin.compat.json.loads", return_value=contract):
            self.assertEqual(verify_core(self.core)["core_commit"], "f" * 40)

    def test_runtime_refuses_changed_core_before_any_registration_even_with_python_optimization(self):
        target = self.core / "gateway/run.py"
        target.write_bytes(target.read_bytes() + b"\nUNREVIEWED_CORE_CHANGE = True\n")
        # A shadow source package lets the actual plugin entry resolve this core
        # without importing or executing any of its changed gateway code.
        (self.core / "hermes_cli/__init__.py").write_text("")
        code = '''
import json, sys
from plugin import register
from plugin.compat import CompatibilityError
calls = []
class Context:
    def __getattr__(self, name):
        def called(*args, **kwargs):
            calls.append(name)
        return called
try:
    register(Context())
except CompatibilityError as exc:
    print(json.dumps({"error": str(exc), "calls": calls,
                      "runtime_imported": "plugin.runtime" in sys.modules,
                      "gateway_imported": "gateway.run" in sys.modules}))
else:
    raise SystemExit("unreviewed core was accepted")
'''
        env = dict(os.environ, PYTHONPATH=os.pathsep.join((str(self.core), str(ROOT))),
                   HERMES_HOME=str(self.core / "home"))
        result = subprocess.run([sys.executable, "-O", "-c", code], cwd=self.core,
                                env=env, text=True, capture_output=True, timeout=20, check=True)
        report = json.loads(result.stdout)
        self.assertIn("gateway/run.py", report["error"])
        self.assertEqual(report["calls"], [])
        self.assertFalse(report["runtime_imported"])
        self.assertFalse(report["gateway_imported"])


if __name__ == "__main__":
    unittest.main()
