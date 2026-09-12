"""Require one tested baseline; allow only formatting/comment differences.

No gateway imports here: discovery can run on a worker while gateway.run imports.
"""
from __future__ import annotations

import hashlib
import ast
import importlib.util
import json
from pathlib import Path
import subprocess


class CompatibilityError(RuntimeError):
    pass


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
    contract = json.loads(Path(__file__).with_name("compatibility.json").read_text())
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
    matched = next((profile for profile, missing in differences if not missing), None)
    if matched is None:
        closest, missing = min(differences, key=lambda item: len(item[1]))
        raise CompatibilityError(
            "Unsupported or modified Hermes core. Closest tested commit: " + closest["core_commit"]
            + ". Mismatched interfaces: " + ", ".join(missing)
            + ". No UX hooks were installed. See docs/COMPATIBILITY.md."
        )
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
            "hermes_version": matched["hermes_version"], "interface_files": len(matched["files"]),
            "format_only_files": [name for name, expected in matched["files"].items() if actual[name] != expected]}
