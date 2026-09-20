#!/usr/bin/env python3
"""Upgrade real historical Git/ZIP installs in disposable homes, without network.

Uses native `plugins install --force --ref <SHA>` for both upgrades. A pinned
Git install cannot advance with `plugins update`; a ZIP has no Git checkout.
The hook/transport smoke is synthetic, not live Telegram acceptance.
"""
import argparse
import asyncio
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import zipfile

from build_release import ROOT, build, git
from check_native import NAME, run, source_hashes

OLD_REF = "93ff48a0a3a5ec956cbf424f29b23c8b8ec01fc3"
TOOL = "telegram_ux_update"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def manifest_at(commit):
    import yaml
    return yaml.safe_load(git("show", f"{commit}:plugin.yaml"))


async def probe(mode, version):
    from hermes_cli.plugins import PluginManager, PluginState
    from tools.registry import registry

    if mode == "seed":
        # Exact historical Preferences.key scope and host-owned storage format.
        scope = ["10", "42", "10"]
        key = "prefs:" + digest(json.dumps(scope).encode())
        state = PluginState(NAME)
        state.set(key, {"language": "en", "progress": False, "emoji": False,
                        "final_summary": True, "followups": True, "display": "detail"})
        state.set("unknown_future_key", {"preserve": [1, "untouched"]})
        print("UPGRADE_PROBE=" + json.dumps({"path": str(state.path), "sha256": digest(state.path.read_bytes())}))
        return

    manager = PluginManager()
    manager.discover_and_load()
    installed = [p for p in manager.list_plugins() if p["name"] == NAME]
    try:
        if mode == "removed":
            assert installed == [], installed
        else:
            assert len(installed) == 1, installed
            info = installed[0]
            assert info["version"] == version, info
            if mode == "disabled":
                assert not info["enabled"] and info["hooks"] == 0 and info["tools"] == 0, info
            else:
                assert info["enabled"] and info["error"] is None, info
                expected = {"hooks": 17, "commands": 1} if mode == "old" else {"hooks": 16, "commands": 0}
                assert all(info[key] == value for key, value in expected.items()), info
                assert info["tools"] == 1 and info["middleware"] == 0, info
                assert manager.has_hook("transform_llm_output") is (mode == "old")
                assert manager.has_hook("pre_command") is (mode == "old")

        if mode in ("disabled", "removed"):
            assert not manager.has_hook("pre_llm_call")
            assert not manager.get_platform_handler_factories("telegram")
            assert registry.get_entry(TOOL, scope=manager.scope_key) is None
            print("UPGRADE_PROBE=" + json.dumps({"mode": mode, "single_or_absent_registration": True}))
            return

        sent, edits, deleted = [], [], []

        async def send(**kwargs):
            sent.append(kwargs)
            return SimpleNamespace(success=True, message_id="77")

        async def edit_message(**kwargs):
            edits.append(kwargs)
            return SimpleNamespace(success=True)

        async def delete_message(**kwargs):
            deleted.append(kwargs)
            return True

        factories = manager.get_platform_handler_factories("telegram")
        assert len(factories) == 1
        factories[0][0](None, SimpleNamespace(send=send, edit_message=edit_message, delete_message=delete_message))
        source = SimpleNamespace(platform="telegram", chat_id="10", user_id="10", thread_id="42")
        event = SimpleNamespace(source=source, message_id="3", internal=False)
        assert manager.invoke_hook("pre_gateway_dispatch", event=event) == []
        assert sent == [], "Unauthenticated ingress must not display progress"
        await asyncio.to_thread(manager.invoke_hook, "pre_llm_call", session_id="upgrade", turn_id="turn",
                                platform="telegram", sender_id="10", user_message="检查指定文件")
        for _ in range(100):
            await asyncio.sleep(.03)
            if mode == "old" or sent:
                break
        if mode == "old":
            assert not sent, "Old disabled preference fixture must be effective before upgrade"
        else:
            assert len(sent) == 1, sent
            assert "正在" in sent[0]["content"] and sent[0]["content"].startswith("🤔"), sent
            assert sent[0]["metadata"] == {"thread_id": "42"}
            assert manager.invoke_hook("pre_tool_call", session_id="upgrade", turn_id="turn",
                                       tool_call_id="read", tool_name="read_file", args={"path": "/tmp/missing"}) == []
            assert manager.invoke_hook("post_tool_call", session_id="upgrade", turn_id="turn",
                                       tool_call_id="read", tool_name="read_file", status="error",
                                       result="File not found") == []
            assert manager.invoke_hook("transform_llm_output", session_id="upgrade", turn_id="turn",
                                       platform="telegram", response_text="Native final reply") == []
            assert manager.invoke_hook("post_llm_call", session_id="upgrade", turn_id="turn",
                                       platform="telegram", assistant_response="Native final reply") == []
        manager.invoke_hook("on_session_end", session_id="upgrade", turn_id="turn", completed=True)
        for _ in range(100):
            if mode == "old" or deleted:
                break
            await asyncio.sleep(.03)
        if mode == "new":
            assert deleted == [{"chat_id": "10", "message_id": "77"}], deleted
            assert len(sent) == 1 and edits and all(item["message_id"] == "77" for item in edits)
            assert all("reply_markup" not in item for item in sent + edits)
            assert "Native final reply" not in repr(sent + edits)
            result = json.loads(registry.dispatch(TOOL, {"goal": "Check file", "action": "Reading"}, scope=manager.scope_key))
            assert result["ok"], result
        print("UPGRADE_PROBE=" + json.dumps({"mode": mode, "version": version,
            "hooks": info["hooks"], "tools": info["tools"], "commands": info["commands"],
            "single_registration": True, "synthetic_public_hook_smoke": "pass",
            "sent": len(sent), "edited": len(edits), "deleted": len(deleted),
            "old_preferences_ignored": mode == "new"}))
    finally:
        manager.unload()
        await asyncio.sleep(.05)
        assert not manager.has_hook("pre_llm_call")
        assert registry.get_entry(TOOL, scope=manager.scope_key) is None


def child_probe(mode, version, temp, env):
    out = run([sys.executable, str(Path(__file__).resolve()), "--probe", mode, "--version", version], temp, env)
    lines = [line.removeprefix("UPGRADE_PROBE=") for line in out.splitlines() if line.startswith("UPGRADE_PROBE=")]
    assert len(lines) == 1, out
    return json.loads(lines[0])


def historical_zip(commit, target):
    # Fixture contains the exact committed old runtime, not relabelled v2 code.
    archive = git("archive", "--format=zip", commit, "__init__.py", "plugin.yaml", "catalog")
    with zipfile.ZipFile(io.BytesIO(archive)) as bundle:
        bundle.extractall(target)
    return digest(archive)


def assert_single_directory(home):
    directories = sorted(path.name for path in (home / "plugins").iterdir() if path.is_dir())
    assert directories == [NAME], directories


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--core", type=Path)
    parser.add_argument("--ref", default="HEAD")
    parser.add_argument("--old-ref", default=OLD_REF)
    parser.add_argument("--report", type=Path, default=ROOT / "artifacts/upgrade.json")
    parser.add_argument("--probe", choices=("seed", "old", "new", "disabled", "removed"))
    parser.add_argument("--version", default="")
    args = parser.parse_args()
    if args.probe:
        asyncio.run(probe(args.probe, args.version))
        return
    if not args.core:
        parser.error("--core is required")
    import yaml
    core = args.core.resolve()
    baseline = source_hashes(core)
    old_commit = git("rev-parse", "--verify", args.old_ref + "^{commit}").decode().strip()
    new_commit = git("rev-parse", "--verify", args.ref + "^{commit}").decode().strip()
    old, new = manifest_at(old_commit), manifest_at(new_commit)
    assert old["name"] == new["name"] == NAME
    assert old["version"] == "1.9.0-catalog.1" and new["version"] == "2.0.0", (old, new)
    reports = {"old_commit": old_commit, "old_version": old["version"], "new_commit": new_commit,
               "new_version": new["version"], "plugin_id": NAME,
               "core_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=core, text=True).strip(),
               "live_telegram": False, "transport": "synthetic; real PluginManager and public hook dispatch",
               "lifecycles": {}}
    try:
        with tempfile.TemporaryDirectory(prefix="hermes-ux-upgrade-") as raw:
            temp = Path(raw)
            release = build(new_commit, temp / "release")
            reports["new_package_sha256"] = release["sha256"]
            bundled = temp / "empty-bundled"
            bundled.mkdir()
            env = dict(os.environ, PYTHONPATH=str(core), PYTHONDONTWRITEBYTECODE="1",
                       HERMES_BUNDLED_PLUGINS=str(bundled), GIT_ALLOW_PROTOCOL="file", GIT_TERMINAL_PROMPT="0")
            cli = [sys.executable, "-m", "hermes_cli.main", "plugins"]
            for edition in ("git", "zip"):
                home = temp / edition
                home.mkdir()
                env["HERMES_HOME"] = str(home)
                # Use the host's documented cache path for an offline fixture.
                # The checked-out core blocklist is still checked by the native
                # installer; no --allow-removed or security-scan bypass is used.
                removed_path = core / "plugin-catalog/removed.yaml"
                removed = yaml.safe_load(removed_path.read_text()) if removed_path.exists() else {}
                (home / "cache").mkdir()
                (home / "cache/plugin-catalog.json").write_text(json.dumps({
                    "entries": [], "removed": (removed or {}).get("removed", [])}))
                config = {"plugins": {"enabled": [], "entries": {NAME: {"settings": {
                    "language": "zh", "progress": True, "emoji": False, "final_summary": True,
                    "followups": True, "cleanup_delay": .01, "unknown_future_setting": {"keep": 7}}}},
                    "unknown_plugins_option": ["keep"]}, "custom_fixture": {"keep": True, "text": "保留"}}
                config_path = home / "config.yaml"
                config_path.write_text(yaml.safe_dump(config, allow_unicode=True))
                target = home / "plugins" / NAME
                row = {"upgrade_method": "native install --force --ref; exact local Git source"}
                if edition == "git":
                    run(cli + ["install", ROOT.as_uri(), "--ref", old_commit, "--no-enable", "--force"], temp, env)
                    assert run(["git", "rev-parse", "HEAD"], target, env).strip() == old_commit
                else:
                    target.mkdir(parents=True)
                    row["old_zip_sha256"] = historical_zip(old_commit, target)
                    row["old_zip_kind"] = "git archive of exact historical runtime; manually extracted install"
                    assert not (target / ".git").exists()
                row["old_validation"] = json.loads(run(cli + ["validate", str(target), "--json"], temp, env))
                assert row["old_validation"]["ok"], row["old_validation"]
                seeded = child_probe("seed", old["version"], temp, env)
                state_path = Path(seeded["path"])
                state_bytes = state_path.read_bytes()
                external = home / "plugin-data" / "unrelated-user-file.bin"
                external.write_bytes(b"\x00preserve-user-data\xff")
                external_bytes = external.read_bytes()
                run(cli + ["enable", NAME], temp, env)
                row["old_probe"] = child_probe("old", old["version"], temp, env)
                # Old state disables progress even though config enables it.
                # Each probe exits and unloads: no live Gateway is left running.
                if edition == "zip":
                    run(cli + ["disable", NAME], temp, env)
                    row["old_disabled_probe"] = child_probe("disabled", old["version"], temp, env)
                    row["activation_path"] = "old probe unloaded/exited; disable; reinstall --no-enable; verify disabled; enable"
                else:
                    row["activation_path"] = "old probe unloaded/exited; enabled config retained by reinstall --no-enable"
                before_config = config_path.read_bytes()
                before_yaml = yaml.safe_load(before_config)
                assert_single_directory(home)
                refusal = run(cli + ["update", NAME], temp, env, expected=1)
                assert ("pinned" if edition == "git" else "not installed from git") in refusal, refusal
                row["native_update_refuses_old_pin_or_zip"] = True

                run(cli + ["install", ROOT.as_uri(), "--ref", new_commit, "--no-enable", "--force"], temp, env)
                assert run(["git", "rev-parse", "HEAD"], target, env).strip() == new_commit
                assert config_path.read_bytes() == before_config, "Reinstall rewrote existing configuration"
                assert state_path.read_bytes() == state_bytes and external.read_bytes() == external_bytes
                assert_single_directory(home)
                assert not (target / "catalog/preferences.py").exists()
                assert not (target / "catalog/interface.py").exists()
                assert not (target / "plugin").exists()
                row["validation"] = json.loads(run(cli + ["validate", str(target), "--json"], temp, env))
                assert row["validation"]["ok"] and not row["validation"]["warnings"], row["validation"]
                run(cli + ["doctor", str(target), "--ci"], temp, env)
                if edition == "zip":
                    row["upgraded_disabled_probe"] = child_probe("disabled", new["version"], temp, env)
                    run(cli + ["enable", NAME], temp, env)
                row["new_probe"] = child_probe("new", new["version"], temp, env)
                run(cli + ["disable", NAME], temp, env)
                row["disabled_probe"] = child_probe("disabled", new["version"], temp, env)
                run(cli + ["enable", NAME], temp, env)
                row["reenabled_probe"] = child_probe("new", new["version"], temp, env)
                run(cli + ["disable", NAME], temp, env)
                run(cli + ["remove", NAME], temp, env)
                assert not target.exists()
                row["removed_probe"] = child_probe("removed", new["version"], temp, env)
                after_yaml = yaml.safe_load(config_path.read_text())
                # Native disable moves this ID from the allow-list into the
                # explicit deny-list; remove keeps that activation preference.
                before_yaml["plugins"]["enabled"] = sorted(set(before_yaml["plugins"]["enabled"]) - {NAME})
                before_yaml["plugins"]["disabled"] = sorted(set(before_yaml["plugins"].get("disabled", [])) | {NAME})
                assert after_yaml == before_yaml, (after_yaml, before_yaml)
                assert state_path.read_bytes() == state_bytes and external.read_bytes() == external_bytes
                row.update({"single_directory_and_registration": True, "configuration_bytes_preserved_on_upgrade": True,
                    "unknown_config_preserved_through_lifecycle": True, "state_bytes_preserved_through_remove": True,
                    "state_sha256": digest(state_bytes), "state_path_relative": str(state_path.relative_to(home)),
                    "unrelated_data_preserved": True, "doctor": "pass", "enable_disable_remove": "pass"})
                reports["lifecycles"][edition + "_to_git"] = row
    finally:
        assert source_hashes(core) == baseline, "Hermes tracked core files changed"
    reports["core_files_unchanged"] = True
    reports["tracked_core_files_checked"] = len(baseline)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(reports, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"old": old_commit, "new": new_commit, "git_to_git": "pass", "zip_to_git": "pass",
                      "core_files_unchanged": True, "live_telegram": False}))


if __name__ == "__main__":
    main()
