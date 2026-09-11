#!/usr/bin/env python3
"""Hermes Telegram UX lifecycle; run as the account that owns HERMES_HOME.

The gateway must be stopped for mutations. No services, credentials, conversations,
SOUL files, or model settings are managed by this installer.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile

import yaml
from plugin.compat import verify_core

PLUGIN_ID = "hermes-interaction"  # Stable id preserves upgrades from the private 1.5 release.
STATE_DIR = "telegram-ux-installer"
SETTINGS = {"soft_wait": False, "status_delay_seconds": 0.6,
            "status_min_edit_seconds": 2.5, "slow_notice_seconds": 45.0,
            "text_batch_seconds": 0.8}
DISPLAY = {"streaming": False, "tool_progress": "off", "cleanup_progress": True,
           "interim_assistant_messages": False, "thinking_progress": False,
           "long_running_notifications": True, "busy_ack_enabled": True,
           "busy_steer_ack_enabled": True, "busy_ack_detail": False, "live_status": "off"}


def stamp():
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


def atomic_write(path, data, mode=0o600):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, raw = tempfile.mkstemp(prefix=".ux-", dir=path.parent)
    staged = Path(raw)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        staged.chmod(mode)
        os.replace(staged, path)
    finally:
        staged.unlink(missing_ok=True)


def json_bytes(data):
    return (json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode()


def yaml_bytes(data):
    return yaml.safe_dump(data, allow_unicode=True, sort_keys=False).encode()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read_config(home):
    path = home / "config.yaml"
    if path.is_symlink() or not path.is_file():
        raise ValueError("HERMES_HOME/config.yaml must be an ordinary file; initialize Hermes first.")
    if path.stat().st_uid != os.geteuid():
        raise ValueError("Run the installer as the account that owns config.yaml.")
    config = yaml.safe_load(path.read_text())
    if not isinstance(config, dict):
        raise ValueError("config.yaml must contain a YAML mapping.")
    return config


def get_value(config, path):
    node = config
    for key in path:
        if not isinstance(node, dict):
            raise ValueError("Expected a mapping at " + ".".join(path))
        if key not in node:
            return {"exists": False}
        node = node[key]
    return {"exists": True, "value": deepcopy(node)}


def put_value(config, path, value):
    node = config
    parents = []
    for key in path[:-1]:
        parents.append((node, key))
        node = node.setdefault(key, {})
        if not isinstance(node, dict):
            raise ValueError("Expected a mapping at " + ".".join(path))
    if value["exists"]:
        node[path[-1]] = deepcopy(value["value"])
    else:
        node.pop(path[-1], None)
        for parent, key in reversed(parents):
            if parent[key] == {}:
                del parent[key]
            else:
                break


def desired_values(preset):
    entry = ("plugins", "entries", PLUGIN_ID)
    values = {entry + ("allow_gateway_injection",): True}
    values.update({entry + ("settings", key): value for key, value in SETTINGS.items()})
    if preset == "recommended":
        values.update({("agent", "gateway_notify_interval"): 1,
                       ("display", "busy_input_mode"): "steer",
                       ("display", "busy_ack_enabled"): True,
                       ("display", "busy_steer_ack_enabled"): True,
                       ("platforms", "telegram", "reactions"): True,
                       ("platforms", "telegram", "extra", "disable_link_previews"): True,
                       ("display", "platforms", "telegram", "runtime_footer", "enabled"): False})
        values.update({("display", "platforms", "telegram", key): value
                       for key, value in DISPLAY.items()})
    return values


def plan_install(config, previous, preset):
    changed = deepcopy(config)
    records = deepcopy(previous.get("records", [])) if previous else []
    existing = {tuple(r["path"]): r for r in records}
    for path, value in desired_values(preset).items():
        current = get_value(changed, path)
        record = existing.get(path)
        after = {"exists": True, "value": value}
        if record:
            # Preserve preferences changed since installation, including plugin settings.
            if current != record["after"]:
                continue
            record["after"] = after
        else:
            record = {"path": list(path), "before": current, "after": after, "kind": "value"}
            records.append(record)
        put_value(changed, path, after)
    for name, wanted in (("enabled", True), ("disabled", False)):
        path = ("plugins", name)
        current = get_value(changed, path)
        members = current.get("value", [])
        if not isinstance(members, list) or not all(isinstance(x, str) for x in members):
            raise ValueError("plugins." + name + " must be a list of plugin ids.")
        record = existing.get(path)
        present = PLUGIN_ID in members
        if record and present != record["after_member"]:
            continue
        if not record:
            record = {"path": list(path), "kind": "member", "before_exists": current["exists"],
                      "before_member": present, "after_member": wanted}
            records.append(record)
        if present != wanted:
            result = [*members, PLUGIN_ID] if wanted else [x for x in members if x != PLUGIN_ID]
            put_value(changed, path, {"exists": True, "value": result})
    return changed, records


def plan_restore(config, records):
    changed = deepcopy(config)
    conflicts = []
    for record in reversed(records):
        path = record["path"]
        try:
            current = get_value(changed, path)
        except ValueError:
            # A later user edit may replace an entire mapping, not just a leaf.
            conflicts.append(".".join(path))
            continue
        if record["kind"] == "member":
            members = current.get("value", [])
            if not isinstance(members, list):
                conflicts.append(".".join(path))
                continue
            if (PLUGIN_ID in members) == record["after_member"]:
                members = [x for x in members if x != PLUGIN_ID]
                if record["before_member"]:
                    members.append(PLUGIN_ID)
                put_value(changed, path, {"exists": bool(members) or record["before_exists"], "value": members})
        elif current == record["after"]:
            put_value(changed, path, record["before"])
        elif current != record["before"]:
            conflicts.append(".".join(path))
    return changed, conflicts


def copy_plugin(source, destination):
    # Do not follow symlinks into credentials or files outside a reviewed release.
    if source.is_symlink() or any(p.is_symlink() for p in source.rglob("*")):
        raise ValueError("Plugin source must not contain symlinks.")
    shutil.copytree(source, destination,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "._*", ".DS_Store"))


@contextmanager
def locked(home):
    directory = home / STATE_DIR
    if directory.is_symlink():
        raise ValueError("Installer state must not be a symlink.")
    directory.mkdir(mode=0o700, exist_ok=True)
    directory.chmod(0o700)
    with (directory / "lock").open("a") as stream:
        os.chmod(stream.name, 0o600)
        try:
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError("Another UX installer is running.") from None
        try:
            for name in ("state.json", "transaction.json"):
                if (directory / name).is_symlink():
                    raise ValueError("Installer state files must not be symlinks.")
            yield directory
        finally:
            fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def recover(home, directory):
    journal_path = directory / "transaction.json"
    if not journal_path.exists():
        return False
    journal = json.loads(journal_path.read_text())
    backup = Path(journal["backup"])
    path = home / "config.yaml"
    if digest(path.read_bytes()) not in journal["config_hashes"]:
        raise RuntimeError("Configuration changed after an interrupted install. Preserve your edits and inspect " + str(backup))
    destination = home / "plugins" / PLUGIN_ID
    rollback = destination.with_name("." + PLUGIN_ID + "-recover")
    if rollback.exists():
        shutil.rmtree(rollback)
    if (backup / "plugin").exists():
        copy_plugin(backup / "plugin", rollback)
    if destination.exists():
        shutil.rmtree(destination)
    if rollback.exists():
        os.replace(rollback, destination)
    atomic_write(path, (backup / "config.yaml").read_bytes(), journal["config_mode"])
    state_path = directory / "state.json"
    if (backup / "state.json").exists():
        atomic_write(state_path, (backup / "state.json").read_bytes())
    else:
        state_path.unlink(missing_ok=True)
    for name in journal.get("temporary", []):
        temporary = destination.parent / name
        if temporary.exists():
            shutil.rmtree(temporary)
    journal_path.unlink()
    return True


def transact(home, directory, config, next_state, source):
    """Journal first; on any exception restore the exact pre-operation snapshot."""
    path = home / "config.yaml"
    destination = home / "plugins" / PLUGIN_ID
    state_path = directory / "state.json"
    backup = home / "backups" / "hermes-telegram-ux" / stamp()
    backup.mkdir(parents=True, mode=0o700)
    backup.chmod(0o700)
    atomic_write(backup / "config.yaml", path.read_bytes())
    if destination.exists():
        copy_plugin(destination, backup / "plugin")
    if state_path.exists():
        atomic_write(backup / "state.json", state_path.read_bytes())
    if next_state and "baseline_backup" not in next_state:
        next_state["baseline_backup"] = str(backup)
    destination.parent.mkdir(exist_ok=True)
    staged = destination.with_name("." + PLUGIN_ID + "-" + backup.name)
    old = destination.with_name(staged.name + "-old")
    if source:
        copy_plugin(source, staged)
    after = yaml_bytes(config)
    mode = path.stat().st_mode & 0o777
    journal = {"backup": str(backup), "config_hashes": [digest(path.read_bytes()), digest(after)],
               "config_mode": mode, "temporary": [staged.name, old.name]}
    atomic_write(directory / "transaction.json", json_bytes(journal))
    try:
        if destination.exists():
            os.replace(destination, old)
        if source:
            os.replace(staged, destination)
        atomic_write(path, after, mode)
        if next_state:
            atomic_write(state_path, json_bytes(next_state))
        else:
            state_path.unlink(missing_ok=True)
        # Removing the journal is the commit point; leftover old copies are harmless.
        (directory / "transaction.json").unlink()
    except BaseException:
        recover(home, directory)
        raise
    if old.exists():
        shutil.rmtree(old)
    return str(backup)


def install(home, source=None, *, core=None, preset="recommended", dry_run=False):
    home = Path(home).expanduser().resolve()
    read_config(home)
    compatibility = verify_core(core)
    source = Path(source or Path(__file__).with_name("plugin")).resolve()
    manifest = yaml.safe_load((source / "plugin.yaml").read_text())
    if manifest.get("name") != PLUGIN_ID or not (source / "__init__.py").is_file():
        raise ValueError("Invalid plugin source.")
    destination = home / "plugins" / PLUGIN_ID
    if destination.is_symlink() or (home / "plugins").is_symlink():
        raise ValueError("Plugin destination must not be a symlink.")
    with locked(home) as directory:
        config = read_config(home)
        if (directory / "transaction.json").exists():
            raise RuntimeError("An interrupted transaction exists. Stop the gateway and run recover first.")
        state_path = directory / "state.json"
        previous = json.loads(state_path.read_text()) if state_path.exists() else None
        selected = previous["preset"] if previous else preset
        changed, records = plan_install(config, previous, selected)
        result = {"action": "install", "version": manifest["version"], "preset": selected,
                  "compatibility": compatibility, "changed_paths": [".".join(r["path"]) for r in records
                    if get_value(config, r["path"]) != get_value(changed, r["path"])]}
        if dry_run:
            result["dry_run"] = True
            return result
        state = dict(previous or {}, schema=1, version=manifest["version"], preset=selected, records=records)
        result["backup"] = transact(home, directory, changed, state, source)
        return result


def uninstall(home, *, dry_run=False):
    home = Path(home).expanduser().resolve()
    read_config(home)
    if (home / "plugins").is_symlink() or (home / "plugins" / PLUGIN_ID).is_symlink():
        raise ValueError("Plugin destination must not be a symlink.")
    with locked(home) as directory:
        config = read_config(home)
        if (directory / "transaction.json").exists():
            raise RuntimeError("Run recover before uninstalling an interrupted transaction.")
        state_path = directory / "state.json"
        if not state_path.exists():
            return {"action": "uninstall", "changed": False, "reason": "No managed installation."}
        state = json.loads(state_path.read_text())
        changed, conflicts = plan_restore(config, state["records"])
        if not (Path(state["baseline_backup"]) / "config.yaml").is_file():
            raise RuntimeError("Baseline backup is missing; restore it before uninstalling.")
        baseline = Path(state["baseline_backup"]) / "plugin"
        result = {"action": "uninstall", "changed": True, "preserved_user_changes": conflicts,
                  "restores_previous_plugin": baseline.exists()}
        if not dry_run:
            result["backup"] = transact(home, directory, changed, None, baseline if baseline.exists() else None)
        else:
            result["dry_run"] = True
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["check", "install", "uninstall", "recover"])
    parser.add_argument("--hermes-home", type=Path, default=Path(os.environ.get("HERMES_HOME", "~/.hermes")))
    parser.add_argument("--hermes-core", type=Path)
    parser.add_argument("--preset", choices=["recommended", "keep-display"], default="recommended")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    try:
        if args.action == "check":
            result = verify_core(args.hermes_core)
        elif args.action == "install":
            result = install(args.hermes_home, core=args.hermes_core, preset=args.preset, dry_run=args.dry_run)
        elif args.action == "uninstall":
            result = uninstall(args.hermes_home, dry_run=args.dry_run)
        else:
            if args.dry_run:
                parser.error("recover cannot use --dry-run")
            home = args.hermes_home.expanduser().resolve()
            read_config(home)
            with locked(home) as directory:
                result = {"recovered": recover(home, directory)}
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (ValueError, RuntimeError, OSError, yaml.YAMLError) as error:
        # YAML parser errors can include credential values. Never print raw configuration snippets.
        message = "Invalid YAML. Validate config.yaml privately." if isinstance(error, yaml.YAMLError) else str(error)
        print("Hermes Telegram UX: " + message, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
