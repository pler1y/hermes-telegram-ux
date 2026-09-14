#!/usr/bin/env python3
"""Exercise Hermes' real Git installer and discovery in a disposable home; no network/model calls."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def run(args, *, cwd, env, expected=0):
    result = subprocess.run(args, cwd=cwd, env=env, text=True, capture_output=True, timeout=120)
    if result.returncode != expected:
        raise RuntimeError(f"Command failed ({result.returncode}): {args}\n{result.stdout}\n{result.stderr}")
    return result.stdout


def tree_hashes(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob("*") if p.is_file() and "__pycache__" not in p.parts}


def probe(*, disabled=False, language=None, configured=False):
    # Called only in a subprocess with a throwaway HERMES_HOME set before imports.
    from hermes_cli.plugins import discover_plugins, get_plugin_manager, render_system_prompt_sections
    from model_tools import get_tool_definitions
    from gateway.config import PlatformConfig
    from gateway.run import GatewayRunner
    from plugins.platforms.telegram.adapter import TelegramAdapter
    from types import SimpleNamespace
    discover_plugins()
    names = {d["function"]["name"] for d in get_tool_definitions(
        enabled_toolsets=["interaction"], quiet_mode=True, skip_tool_search_assembly=True)}
    if disabled:
        assert not {"interaction_actions", "interaction_update"} & names
        assert not any(getattr(cb, "__name__", "") == "narration_request"
                       for cb in get_plugin_manager()._middleware.get("llm_request", []))
        assert not getattr(GatewayRunner._run_agent_notify_long_running, "_hermes_interaction", False)
        print(json.dumps({"disabled_discovery": True}))
        return
    assert {"interaction_actions", "interaction_update"} <= names
    runtime = next(cb.__self__ for cb in get_plugin_manager()._middleware["llm_request"]
                   if getattr(cb, "__name__", "") == "narration_request")
    assert runtime.language == language
    if configured:
        assert runtime.ctx._gateway_injection_allowed()
    assert any(("Use English" if language == "en" else "先给结论") in section.content for section in render_system_prompt_sections(
        {"platform": "telegram", "session_id": "native-fixture"}))
    handlers = []
    application = SimpleNamespace(
        add_handler=lambda handler, group=0: handlers.append((handler, group)),
        remove_handler=lambda handler, group=0: handlers.remove((handler, group)))
    adapter = TelegramAdapter(PlatformConfig())
    original_notify = GatewayRunner._run_agent_notify_long_running
    original_send = adapter.send
    try:
        runtime.wire_telegram(application, adapter)
        assert {group for _, group in handlers} >= {-3, -2, -1}
        assert getattr(GatewayRunner._run_agent_notify_long_running, "_hermes_interaction", False)
    finally:
        runtime.uninstall()
    assert not handlers
    assert GatewayRunner._run_agent_notify_long_running is original_notify
    assert adapter.send == original_send
    print(json.dumps({"native_discovery": True, "telegram_wiring_and_unload": True,
                      "language": language, "configured": configured}))


def validate(cli, source, temp, env):
    report = json.loads(run(cli + ["validate", str(source), "--json"], cwd=temp, env=env))
    assert report["ok"] and not report["warnings"], report
    checks = {c["name"]: c for c in report["checks"]}
    for name in ("capability probe", "declared tools", "declared hooks", "declared middleware"):
        assert checks[name]["ok"], report
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--probe", action="store_true")
    parser.add_argument("--require-validator", action="store_true")
    parser.add_argument("--expect-disabled", action="store_true")
    parser.add_argument("--language", choices=("zh", "en"))
    parser.add_argument("--configured", action="store_true")
    parser.add_argument("--report", type=Path, help="Save the native CLI validation evidence")
    args = parser.parse_args()
    if args.probe:
        probe(disabled=args.expect_disabled, language=args.language, configured=args.configured)
        return
    with tempfile.TemporaryDirectory(prefix="hermes-ux-native-") as raw:
        temp = Path(raw)
        home, source = temp / "home", temp / "source"
        home.mkdir()
        source.mkdir()
        env = dict(os.environ, HERMES_HOME=str(home))
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        # Set locally too, before the official validator/scanner can import tools.
        os.environ["HERMES_HOME"] = str(home)
        import yaml
        sys.path.insert(0, str(ROOT))
        from plugin.compat import verify_core
        compatibility = verify_core()
        from build_release import sources
        for path in sources():
            target = source / path.relative_to(ROOT)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
        (home / "config.yaml").write_text(yaml.safe_dump({
            "plugins": {"enabled": []}, "model": {"default": "native-fixture"}, "custom": {"keep": 7}}))
        for command in (["git", "init", "-q"], ["git", "add", "."],
                        ["git", "-c", "user.name=UX integration test", "-c", "user.email=fixture@example.invalid",
                         "-c", "commit.gpgsign=false", "commit", "-qm", "isolated native install fixture"]):
            run(command, cwd=source, env=env)
        revision = run(["git", "rev-parse", "HEAD"], cwd=source, env=env).strip()
        cli = [sys.executable, "-m", "hermes_cli.main", "plugins"]
        from importlib.util import find_spec
        has_validator = find_spec("hermes_cli.plugin_validate") is not None
        if args.require_validator and not has_validator:
            raise RuntimeError("This check requires the official admission validator")
        reports = {}
        if has_validator:
            reports["source"] = validate(cli, source, temp, env)
            reports["payload"] = validate(cli, source / "plugin", temp, env)
            # Prove the official probe reaches middleware registration, rather
            # than accepting a manifest without actually executing register().
            negative = temp / "missing-middleware"
            shutil.copytree(source, negative, ignore=shutil.ignore_patterns(".git"))
            manifest = yaml.safe_load((negative / "plugin.yaml").read_text())
            manifest["provides_middleware"].remove("tool_request")
            (negative / "plugin.yaml").write_text(yaml.safe_dump(manifest))
            rejected = json.loads(run(cli + ["validate", str(negative), "--json"],
                                      cwd=temp, env=env, expected=1))
            assert not rejected["ok"]
            assert any(not c["ok"] and "undeclared middleware" in c["detail"]
                       and "tool_request" in c["detail"] for c in rejected["checks"]), rejected
            reports["missing_middleware_rejected"] = rejected
        from tools.plugin_guard import scan_plugin
        scan = scan_plugin(source)
        assert scan.verdict != "dangerous", scan.findings
        # The official scanner reports documented sudo commands and subprocess
        # tests as caution. Keep scanning enabled and use its explicit trust flag
        # only for this locally constructed, reviewed fixture.
        run(cli + ["install", source.as_uri(), "--ref", revision, "--no-enable", "--force"], cwd=temp, env=env)
        target = home / "plugins" / "hermes-interaction"
        assert target.is_dir() and (target / ".git").exists()
        assert run(["git", "rev-parse", "HEAD"], cwd=target, env=env).strip() == revision
        assert "hermes-interaction" not in yaml.safe_load((home / "config.yaml").read_text())["plugins"]["enabled"]
        if has_validator:
            reports["installed"] = validate(cli, target, temp, env)
        probe_cli = [sys.executable, str(ROOT / "scripts/check_native_install.py"), "--probe"]
        run(probe_cli + ["--expect-disabled"], cwd=temp, env=env)
        run(cli + ["enable", "hermes-interaction", "--no-allow-tool-override"], cwd=temp, env=env)
        package_language = json.loads((target / "plugin/language.json").read_text())["language"]
        # No install.py/configure call has occurred at this point.
        run(probe_cli + ["--language", package_language], cwd=temp, env=env)
        baseline = yaml.safe_load((home / "config.yaml").read_text())
        before = tree_hashes(home / "plugins")
        setup = [sys.executable, str(target / "install.py")]
        run(setup + ["configure", "--language", "en", "--dry-run"], cwd=temp, env=env)
        assert yaml.safe_load((home / "config.yaml").read_text()) == baseline
        run(setup + ["configure", "--language", "en"], cwd=temp, env=env)
        run(probe_cli + ["--language", "en", "--configured"], cwd=temp, env=env)
        run(setup + ["configure", "--language", "en"], cwd=temp, env=env)
        run(setup + ["restore-config"], cwd=temp, env=env)
        restored = yaml.safe_load((home / "config.yaml").read_text())
        assert restored == baseline, "Native configuration did not restore its baseline"
        assert tree_hashes(home / "plugins") == before, "Native checkout or metadata changed"
        run(cli + ["disable", "hermes-interaction"], cwd=temp, env=env)
        run(probe_cli + ["--expect-disabled"], cwd=temp, env=env)
        run(cli + ["remove", "hermes-interaction"], cwd=temp, env=env)
        assert not target.exists()
        summary = {"core": compatibility, "fixture_commit": revision,
                          "official_validator": has_validator, "native_git_install": True,
                          "unconfigured_enable_discovery": True, "disabled_discovery": True,
                          "configure_enable_restore_remove": True, "metadata_preserved": True,
                          "plugin_scan": scan.verdict}
        if args.report:
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(json.dumps(dict(summary, validation=reports), indent=2) + "\n")
        print(json.dumps(summary))


if __name__ == "__main__":
    main()
