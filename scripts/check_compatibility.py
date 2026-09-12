#!/usr/bin/env python3
"""Validate the current core, then test formatting and code changes in a disposable copy."""
import argparse
import json
from pathlib import Path
import shutil
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from plugin.compat import CompatibilityError, verify_core


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hermes-core", type=Path, required=True)
    args = parser.parse_args()
    core = args.hermes_core.resolve()
    result = verify_core(core)
    profiles = json.loads((ROOT / "plugin/compatibility.json").read_text())["profiles"]
    profile = next(p for p in profiles if p["core_commit"] == result["core_commit"])
    with tempfile.TemporaryDirectory(prefix="hermes-ux-compat-") as raw:
        copy = Path(raw)
        for name in profile["files"]:
            target = copy / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(core / name, target)
        target = copy / "gateway/run.py"
        original = target.read_bytes()
        target.write_bytes(b"# Non-executable formatting fixture\n" + original)
        formatted = verify_core(copy)
        assert "gateway/run.py" in formatted["format_only_files"]
        target.write_bytes(original + b"\nHERMES_UX_UNREVIEWED_CHANGE = True\n")
        try:
            verify_core(copy)
        except CompatibilityError:
            pass
        else:
            raise AssertionError("Changed executable code was accepted")
    print(json.dumps(dict(result, formatting_accepted=True, code_change_rejected=True)))


if __name__ == "__main__":
    main()
