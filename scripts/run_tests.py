#!/usr/bin/env python3
"""Isolated regression runner; skipped runtime tests make the run fail."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    with tempfile.TemporaryDirectory(prefix="hermes-ux-tests-") as raw:
        os.environ["HERMES_HOME"] = raw
        suite = unittest.defaultTestLoader.discover(str(ROOT), pattern="test_*.py")
        result = unittest.TextTestRunner(verbosity=2).run(suite)
        report = {"tests": result.testsRun, "failures": len(result.failures),
                  "errors": len(result.errors), "skipped": len(result.skipped)}
        print(json.dumps(report))
        return 0 if result.wasSuccessful() and not result.skipped else 1


if __name__ == "__main__":
    sys.exit(main())
