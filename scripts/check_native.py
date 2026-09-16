#!/usr/bin/env python3
"""Real native Git + ZIP lifecycle and official validators in disposable homes."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

from build_release import ROOT, build, verify

NAME = "hermes-telegram-ux-catalog"


def run(argv, cwd, env, expected=0):
    result = subprocess.run(argv, cwd=cwd, env=env, text=True, capture_output=True, timeout=120)
    if result.returncode != expected:
        raise RuntimeError(f"Command failed ({result.returncode}): {argv}\n{result.stdout}\n{result.stderr}")
    return result.stdout


def source_hashes(core):
    paths = subprocess.check_output(["git", "ls-files", "-z"], cwd=core).decode().split("\0")
    return {name: hashlib.sha256((core / name).read_bytes()).hexdigest()
            for name in paths if name and (core / name).is_file()}


def probe(enabled):
    from hermes_cli.plugins import PluginManager
    manager = PluginManager()
    manager.discover_and_load()
    info = next((p for p in manager.list_plugins() if p["name"] == NAME), None)
    assert info is not None, "Installed plugin not discovered"
    assert info["enabled"] is enabled, info
    if enabled:
        assert info["error"] is None, info
        assert info["hooks"] == 14 and info["tools"] == 0 and info["middleware"] == 0, info
        assert manager.has_hook("transform_llm_output")
        assert manager.invoke_hook("pre_llm_call", session_id="smoke", turn_id="turn", platform="telegram") == []
        assert manager.invoke_hook("pre_tool_call", session_id="smoke", turn_id="turn", tool_call_id="c", tool_name="read_file") == []
        result = manager.invoke_hook("transform_llm_output", session_id="smoke", turn_id="turn", platform="telegram", response_text="Preserved final reply")
        assert len(result) == 1 and result[0].startswith("Preserved final reply"), result
        manager.invoke_hook("on_session_end", session_id="smoke", turn_id="turn", completed=True)
        manager.unload(NAME)
    else:
        assert info["hooks"] == 0, info
        assert info["error"] == "disabled via config" or "not enabled in config" in (info["error"] or ""), info
    assert not manager.has_hook("pre_tool_call")
    manager.unload()
    print(json.dumps({"enabled": enabled, "discovery": "pass", "native_final_path": "pass"}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--core", type=Path)
    parser.add_argument("--ref", default="HEAD")
    parser.add_argument("--report", type=Path, default=ROOT / "artifacts/native.json")
    parser.add_argument("--probe", choices=("enabled", "disabled"))
    args = parser.parse_args()
    if args.probe:
        probe(args.probe == "enabled")
        return
    if not args.core:
        parser.error("--core is required")
    core = args.core.resolve()
    baseline = source_hashes(core)
    core_sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=core, text=True).strip()
    with tempfile.TemporaryDirectory(prefix="catalog-native-") as raw:
        temp = Path(raw)
        release = build(args.ref, temp / "release")
        env = dict(os.environ, PYTHONPATH=str(core), PYTHONDONTWRITEBYTECODE="1")
        env["HERMES_BUNDLED_PLUGINS"] = str(temp / "empty-bundled")
        Path(env["HERMES_BUNDLED_PLUGINS"]).mkdir()
        cli = [sys.executable, "-m", "hermes_cli.main", "plugins"]
        reports = {"core_commit": core_sha, "release": release, "lifecycles": {}}
        for edition in ("git", "zip"):
            home = temp / edition
            home.mkdir()
            env["HERMES_HOME"] = str(home)
            (home / "config.yaml").write_text("plugins:\n  enabled: []\ncustom_fixture:\n  keep: true\n")
            target = home / "plugins" / NAME
            if edition == "git":
                # Scan remains enabled. --force acknowledges only reviewed local fixture cautions;
                # the host still rejects dangerous findings and validate is always mandatory.
                run(cli + ["install", ROOT.as_uri(), "--ref", release["source_commit"], "--no-enable", "--force"], temp, env)
                installed_sha = run(["git", "rev-parse", "HEAD"], target, env).strip()
                assert installed_sha == release["source_commit"]
            else:
                verify(Path(release["artifact"]))
                with zipfile.ZipFile(release["artifact"]) as archive:
                    archive.extractall(target)
            validated = json.loads(run(cli + ["validate", str(target), "--json"], temp, env))
            assert validated["ok"] and not validated["warnings"], validated
            run(cli + ["doctor", str(target), "--ci"], temp, env)
            child = [sys.executable, str(ROOT / "scripts/check_native.py"), "--probe"]
            run(child + ["disabled"], temp, env)
            run(cli + ["enable", NAME], temp, env)
            run(child + ["enabled"], temp, env)
            run(cli + ["disable", NAME], temp, env)
            run(child + ["disabled"], temp, env)
            # Demonstrate that undeclared registration is still rejected by the official probe.
            import yaml
            manifest_path = target / "plugin.yaml"
            original = manifest_path.read_text()
            manifest = yaml.safe_load(original)
            manifest["provides_hooks"].remove("pre_tool_call")
            manifest_path.write_text(yaml.safe_dump(manifest))
            rejected = json.loads(run(cli + ["validate", str(target), "--json"], temp, env, expected=1))
            assert not rejected["ok"] and any("pre_tool_call" in check["detail"] for check in rejected["checks"] if not check["ok"])
            manifest_path.write_text(original)
            run(cli + ["remove", NAME], temp, env)
            assert not target.exists()
            assert yaml.safe_load((home / "config.yaml").read_text())["custom_fixture"]["keep"] is True
            reports["lifecycles"][edition] = {"install_enable_disable_remove": "pass", "doctor": "pass",
                "validation": validated, "undeclared_hook_rejected": True}
        assert source_hashes(core) == baseline, "Hermes tracked core files changed"
        reports["core_files_unchanged"] = True
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(reports, indent=2) + "\n")
        print(json.dumps({"core": core_sha, "source": release["source_commit"], "git": "pass", "zip": "pass", "core_files_unchanged": True}))


if __name__ == "__main__":
    main()
