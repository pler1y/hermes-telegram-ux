#!/usr/bin/env python3
"""Validate both downloadable editions, including native installation and clean removal."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    with tempfile.TemporaryDirectory(prefix="hermes-ux-editions-") as temp:
        temp = Path(temp)
        subprocess.run([sys.executable, str(ROOT / "scripts/build_release.py"), "--output", str(temp / "dist")], check=True)
        import yaml
        version = yaml.safe_load((ROOT / "plugin.yaml").read_text())["version"]
        for language in ("zh", "en"):
            name = f"hermes-telegram-ux-{version}-{language}"
            archive = temp / "dist" / (name + ".zip")
            with zipfile.ZipFile(archive) as z:
                z.extractall(temp)
            edition = temp / name
            manifest = json.loads((edition / "release-manifest.json").read_text())
            assert manifest["language"] == language
            for relative, digest in manifest["sha256"].items():
                assert hashlib.sha256((edition / relative).read_bytes()).hexdigest() == digest, relative
            home = temp / ("home-" + language)
            home.mkdir()
            baseline = {"model": {"default": "fixture"}, "plugins": {"enabled": []}}
            (home / "config.yaml").write_text(yaml.safe_dump(baseline))
            env = dict(os.environ, HERMES_HOME=str(home))
            args = [sys.executable, "install.py", "install", "--hermes-home", str(home)]
            subprocess.run(args, cwd=edition, env=env, check=True, stdout=subprocess.DEVNULL)
            installed = yaml.safe_load((home / "config.yaml").read_text())
            assert installed["plugins"]["entries"]["hermes-interaction"]["settings"]["language"] == language
            subprocess.run(args, cwd=edition, env=env, check=True, stdout=subprocess.DEVNULL)
            subprocess.run([sys.executable, "scripts/check_runtime.py"], cwd=edition, env=env, check=True)
            subprocess.run([sys.executable, "install.py", "uninstall", "--hermes-home", str(home)],
                           cwd=edition, env=env, check=True, stdout=subprocess.DEVNULL)
            assert yaml.safe_load((home / "config.yaml").read_text()) == baseline
            assert not (home / "plugins/hermes-interaction").exists()
            print(json.dumps({"edition": language, "archive_integrity": True, "install_repeat_uninstall": True}))


if __name__ == "__main__":
    main()
