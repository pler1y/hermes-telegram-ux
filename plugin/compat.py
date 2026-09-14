"""Require one tested baseline; allow only formatting/comment differences.

No gateway imports here: discovery can run on a worker while gateway.run imports.
"""
from __future__ import annotations

import hashlib
import ast
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import tomllib


class CompatibilityError(RuntimeError):
    pass


def load_contract() -> dict:
    """Reject incomplete baselines instead of letting an empty file set match."""
    def require(condition):
        if not condition:
            raise ValueError("Incomplete or malformed baseline")

    try:
        contract = json.loads(Path(__file__).with_name("compatibility.json").read_text())
        require(contract["schema"] == 4)
        require(contract["policy"] == "reviewed-source")
        required = contract["guarded_files"]
        require(isinstance(required, list) and required and len(set(required)) == len(required))
        require(all(isinstance(name, str) and not Path(name).is_absolute()
                   and ".." not in Path(name).parts and name.endswith(".py") for name in required))
        profiles = contract["profiles"]
        require(isinstance(profiles, list) and profiles)
        commits = set()
        for profile in profiles:
            commit = profile["core_commit"]
            require(re.fullmatch(r"[0-9a-f]{40}", commit) and commit not in commits)
            commits.add(commit)
            require(re.fullmatch(r"\d+\.\d+\.\d+", profile["hermes_version"]))
            for key in ("files", "python_ast_v1"):
                hashes = profile[key]
                require(isinstance(hashes, dict) and set(hashes) == set(required))
                require(all(re.fullmatch(r"[0-9a-f]{64}", digest) for digest in hashes.values()))
    except (OSError, ValueError, KeyError, TypeError, AssertionError) as exc:
        raise CompatibilityError("Invalid compatibility contract; no UX hooks were installed.") from exc
    return contract


def python_ast_v1(data: bytes) -> str:
    """Hash the complete Python syntax tree without importing or executing it.

    Statements, scope, literal values, defaults, decorators and docstrings remain
    guarded. Comments, source positions and formatting do not affect the tree.
    This is not a signature-only compatibility check.
    """
    tree = compile(data, "<compatibility-check>", "exec", flags=ast.PyCF_ONLY_AST, dont_inherit=True)
    for node in ast.walk(tree):
        # Python 3.12 added this empty field to pre-existing def/class syntax.
        # Nonempty type parameters remain guarded as executable syntax.
        if getattr(node, "type_params", None) == []:
            del node.type_params
    return hashlib.sha256(ast.dump(tree, include_attributes=False).encode()).hexdigest()


def verify_core(root: Path | None = None) -> dict:
    spec = None if root else importlib.util.find_spec("hermes_cli")
    if root is None:
        if spec is None or not spec.origin:
            raise CompatibilityError("Run with Hermes' Python or pass --hermes-core /path/to/hermes-agent.")
        root = Path(spec.origin).resolve().parent.parent
    root = root.expanduser().resolve()
    contract = load_contract()
    profiles = contract["profiles"]
    actual, contents, syntax = {}, {}, {}
    for name in {name for profile in profiles for name in profile["files"]}:
        path = root / name
        contents[name] = path.read_bytes() if path.is_file() else None
        actual[name] = hashlib.sha256(contents[name]).hexdigest() if contents[name] is not None else None

    def matches(profile, name, expected):
        if actual[name] == expected:
            return True
        allowed = profile.get("python_ast_v1", {}).get(name)
        if not allowed or contents[name] is None:
            return False
        if name not in syntax:
            try:
                syntax[name] = python_ast_v1(contents[name])
            except (SyntaxError, ValueError, UnicodeError):
                syntax[name] = None
        return syntax[name] == allowed

    differences = [(profile, [name for name, expected in profile["files"].items()
                             if not matches(profile, name, expected)]) for profile in profiles]
    candidates = [profile for profile, missing in differences if not missing]
    if not candidates:
        closest, missing = min(differences, key=lambda item: len(item[1]))
        raise CompatibilityError(
            "Unsupported or modified Hermes core. Closest tested commit: " + closest["core_commit"]
            + ". Mismatched interfaces: " + ", ".join(missing)
            + ". No UX hooks were installed. See docs/COMPATIBILITY.md."
        )
    # Version is an additional boundary, not a substitute for source review.
    # Parse metadata without importing the core (including its version module).
    try:
        version = tomllib.loads((root / "pyproject.toml").read_text())["project"]["version"]
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise CompatibilityError("Cannot read Hermes core version; no UX hooks were installed.") from exc
    matched = next((profile for profile in candidates if profile["hermes_version"] == version), None)
    if matched is None:
        versions = ", ".join(sorted({profile["hermes_version"] for profile in candidates}))
        raise CompatibilityError(
            f"Unsupported Hermes version {version!r}; matching source baselines require "
            f"{versions}. No UX hooks were installed. See docs/COMPATIBILITY.md.")
    # Git HEAD is diagnostic, never a bypass for changed executable syntax.
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
            "hermes_version": version, "policy": contract["policy"],
            "interface_files": len(matched["files"]),
            "format_only_files": [name for name, expected in matched["files"].items() if actual[name] != expected]}
