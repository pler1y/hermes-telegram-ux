#!/usr/bin/env python3
"""AST guard for the executable payload; a supplement to official validation/review."""
import argparse
import ast
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
PAYLOAD = ("__init__.py", "catalog/__init__.py", "catalog/adapter.py", "catalog/model.py",
           "catalog/presentation.py", "catalog/telegram.py", "catalog/preferences.py",
           "catalog/experience.py", "catalog/interface.py")
FORBIDDEN_CALLS = {"setattr", "delattr", "eval", "exec", "compile", "__import__", "globals", "locals", "vars"}
FORBIDDEN_IMPORTS = {"sys", "importlib", "inspect", "ctypes", "subprocess", "marshal", "pickle"}


def scan(source, filename):
    errors = []
    tree = ast.parse(source, filename=filename)
    sdk_imports = set()
    if filename == "catalog/adapter.py":
        for function in ast.walk(tree):
            if isinstance(function, ast.FunctionDef) and function.name == "wire_telegram":
                sdk_imports.update(id(node) for node in ast.walk(function) if isinstance(node, ast.ImportFrom))
    public_sdk = {"telegram": {"InlineKeyboardButton", "InlineKeyboardMarkup", "ReplyKeyboardMarkup"},
                  "telegram.ext": {"CallbackQueryHandler"}}
    for node in ast.walk(tree):
        issue = None
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = [alias.name for alias in node.names] if isinstance(node, ast.Import) else [node.module or ""]
            relative = isinstance(node, ast.ImportFrom) and node.level > 0
            sdk = (id(node) in sdk_imports and node.module in public_sdk and
                   all(alias.name in public_sdk[node.module] and alias.asname is None for alias in node.names))
            for name in names:
                root = name.split(".")[0]
                if not relative and not sdk and (root not in sys.stdlib_module_names or root in FORBIDDEN_IMPORTS):
                    issue = f"non-allowlisted import: {name}"
        builtin_type_name = (isinstance(node, ast.Attribute) and node.attr == "__name__"
                             and isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name)
                             and node.value.func.id == "type")
        if isinstance(node, ast.Attribute) and node.attr.startswith("_") and not builtin_type_name:
            issue = f"private attribute: {node.attr}"
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id in FORBIDDEN_CALLS:
                issue = f"dynamic execution/mutation: {node.func.id}"
            if node.func.id in {"getattr", "hasattr"} and len(node.args) > 1:
                arg = node.args[1]
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str) and arg.value.startswith("_"):
                    issue = f"private dynamic attribute: {arg.value}"
                elif not isinstance(arg, ast.Constant) and not (isinstance(node.args[0], ast.Name) and node.args[0].id == "self"):
                    issue = "unbounded dynamic host lookup"
        if isinstance(node, ast.Attribute) and isinstance(node.ctx, (ast.Store, ast.Del)):
            # Assign only direct fields on plugin-owned objects, never self.host.method.
            if not isinstance(node.value, ast.Name) or node.value.id not in {"self", "turn", "panel", "ticket", "card", "menu"}:
                issue = "foreign object attribute mutation"
        if issue:
            errors.append(f"{filename}:{node.lineno}: {issue}")
    return errors


def check(root=ROOT):
    errors = []
    actual = {p.relative_to(root).as_posix() for p in (root / "catalog").rglob("*.py")} | {"__init__.py"}
    if actual != set(PAYLOAD):
        errors.append("Executable payload differs from reviewed allowlist")
    for relative in PAYLOAD:
        errors.extend(scan((root / relative).read_text(), relative))
    for forbidden in ("plugin", "install.py", "migrate_prompts.py", "release-manifest.json"):
        if (root / forbidden).exists():
            errors.append(f"Full distribution file present: {forbidden}")
    return errors


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", type=Path, default=ROOT)
    errors = check(parser.parse_args().path)
    print("\n".join(errors) if errors else "Catalog boundary: PASS (public Telegram factory imports; no Hermes imports, private access or host mutation)")
    raise SystemExit(bool(errors))
