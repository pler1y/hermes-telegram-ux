"""Fail closed unless all guarded files match one tested Hermes baseline.

No gateway imports here: discovery can run on a worker while gateway.run imports.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess


class CompatibilityError(RuntimeError):
    pass


def verify_core(root: Path | None = None) -> dict:
    spec = None if root else importlib.util.find_spec("hermes_cli")
    if root is None:
        if spec is None or not spec.origin:
            raise CompatibilityError("Run with Hermes' Python or pass --hermes-core /path/to/hermes-agent.")
        root = Path(spec.origin).resolve().parent.parent
    root = root.expanduser().resolve()
    contract = json.loads(Path(__file__).with_name("compatibility.json").read_text())
    profiles = contract["profiles"]
    actual = {}
    for name in {name for profile in profiles for name in profile["files"]}:
        path = root / name
        actual[name] = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
    differences = [(profile, [name for name, expected in profile["files"].items()
                             if actual[name] != expected]) for profile in profiles]
    matched = next((profile for profile, missing in differences if not missing), None)
    if matched is None:
        closest, missing = min(differences, key=lambda item: len(item[1]))
        raise CompatibilityError(
            "Unsupported or modified Hermes core. Closest tested commit: " + closest["core_commit"]
            + ". Mismatched interfaces: " + ", ".join(missing)
            + ". No UX hooks were installed. See docs/COMPATIBILITY.md."
        )
    # A catalog-only, documentation or unrelated platform commit must not invalidate
    # byte-identical guarded interfaces. Git HEAD is diagnostic, never a bypass.
    revision = None
    if (root / ".git").exists():
        try:
            result = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"],
                                    capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                revision = result.stdout.strip()
        except (OSError, subprocess.TimeoutExpired):
            pass
    return {"core_commit": matched["core_commit"], "source_commit": revision,
            "hermes_version": matched["hermes_version"], "interface_files": len(matched["files"])}
