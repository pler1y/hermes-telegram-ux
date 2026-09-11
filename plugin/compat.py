"""Fail closed before registering hooks on an untested Hermes core.

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
    mismatched = []
    for name, expected in contract["files"].items():
        path = root / name
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            mismatched.append(name)
    if mismatched:
        raise CompatibilityError(
            "Unsupported or modified Hermes core. Tested commit: " + contract["core_commit"]
            + ". Mismatched interfaces: " + ", ".join(mismatched)
            + ". No UX hooks were installed. See docs/COMPATIBILITY.md."
        )
    # Source archives have no .git; the interface hashes remain mandatory there.
    if (root / ".git").exists():
        result = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"],
                                capture_output=True, text=True, timeout=10)
        if result.returncode or result.stdout.strip() != contract["core_commit"]:
            raise CompatibilityError("Hermes revision is not the tested commit " + contract["core_commit"])
    return {"core_commit": contract["core_commit"], "interface_files": len(contract["files"])}
