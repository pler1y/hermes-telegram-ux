"""Local catalog drafts must not invent publication or maturity evidence."""
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import yaml

from scripts import prepare_catalog

ROOT = Path(__file__).resolve().parent


class CatalogPreparation(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="ux-catalog-draft-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for name in ("plugin.yaml", "plugin/plugin.yaml", "plugin/compatibility.json"):
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, target)
        for command in (["git", "init", "-q"], ["git", "add", "."],
                        ["git", "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
                         "-c", "commit.gpgsign=false", "commit", "-qm", "candidate"]):
            subprocess.run(command, cwd=self.root, check=True, capture_output=True)
        self.output = self.root / "draft"

    def prepare(self, *extra):
        with patch.object(prepare_catalog, "ROOT", self.root), patch("sys.argv", [
            "prepare_catalog", "--ref", "HEAD", "--output", str(self.output), *extra
        ]), redirect_stdout(io.StringIO()):
            prepare_catalog.main()

    def test_unpublished_candidate_uses_exact_commit_and_declared_capabilities(self):
        self.prepare()
        readiness = json.loads((self.output / "readiness.json").read_text())
        self.assertIsNone(readiness["released_at"])
        self.assertIsNone(readiness["earliest_pin_at"])
        self.assertFalse(readiness["mature"])
        self.assertFalse(readiness["submitted"])
        self.assertFalse(readiness["public_sha_reachability_verified"])
        entry = yaml.safe_load((self.output / "hermes-telegram-ux.yaml").read_text())
        sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=self.root, text=True).strip()
        self.assertEqual(entry["sha"], sha)
        self.assertEqual(entry["capabilities"]["provides_middleware"], ["llm_request", "tool_request"])
        self.assertIn(sha, entry["docs_url"])

    def test_unpublished_candidate_cannot_pass_maturity_gate(self):
        with self.assertRaisesRegex(SystemExit, "unpublished"):
            self.prepare("--require-mature")

    def test_old_release_timestamp_cannot_make_new_commit_mature(self):
        with self.assertRaisesRegex(SystemExit, "two-week"):
            self.prepare("--released-at", "2000-01-01T00:00:00Z", "--require-mature")
        self.assertFalse(json.loads((self.output / "readiness.json").read_text())["mature"])


if __name__ == "__main__":
    unittest.main()
