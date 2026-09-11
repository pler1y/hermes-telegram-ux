#!/usr/bin/env python3
"""Build a deterministic source archive from an allowlist; never sweep a Hermes home."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PATTERNS = ["*.md", "LICENSE", ".gitignore", "requirements-dev.txt", "install.py", "migrate_prompts.py",
            "__init__.py", "plugin.yaml", "test_*.py", "plugin/*.py", "plugin/*.yaml", "plugin/*.json",
            "docs/*.md", "scripts/*.py", "acceptance/*.py", "acceptance/*.csv", "acceptance/*.txt",
            ".github/workflows/*.yml"]
SECRET_PATTERNS = [r"\b\d{6,15}:[A-Za-z0-9_-]{30,60}\b",
                   r"-----BEGIN (?:OPENSSH|RSA|EC|DSA) PRIVATE KEY-----",
                   r"\b(?:ghp_|github_pat_)[A-Za-z0-9_]{30,}\b",
                   r"\bsk-(?:proj-)?[A-Za-z0-9_-]{35,}\b",
                   r"/" + r"Users/[^/\s]+/", r"/" + r"home/[^/\s]+/\.hermes",
                   r"(?i)(?:refresh_token|access_token)\s*[=:]\s*[\"'][A-Za-z0-9._-]{20,}"]


def sources():
    paths = sorted({p for pattern in PATTERNS for p in ROOT.glob(pattern) if p.is_file()})
    if any(p.is_symlink() for p in paths):
        raise ValueError("Release allowlist contains a symlink")
    for path in paths:
        content = path.read_text(encoding="utf-8")
        for pattern in SECRET_PATTERNS:
            if re.search(pattern, content):
                raise ValueError("Potential private data in " + str(path.relative_to(ROOT)))
        if path.suffix == ".py":
            compile(content, str(path.relative_to(ROOT)), "exec")
    return paths


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Verify the committed manifest without rebuilding it")
    parser.add_argument("--output", type=Path, default=ROOT / "dist")
    args = parser.parse_args()
    import yaml
    metadata = yaml.safe_load((ROOT / "plugin.yaml").read_text())
    assert metadata == yaml.safe_load((ROOT / "plugin/plugin.yaml").read_text()), "Root/payload metadata differ"
    paths = sources()
    manifest = {"project": "hermes-telegram-ux", "version": metadata["version"],
                "language": json.loads((ROOT / "plugin/language.json").read_text())["language"],
                "core_commit": json.loads((ROOT / "plugin/compatibility.json").read_text())["core_commit"],
                "sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}}
    manifest_path = ROOT / "release-manifest.json"
    if args.check:
        assert json.loads(manifest_path.read_text()) == manifest, "Release manifest is stale; rebuild after changing files"
        print(json.dumps({"manifest_matches": True, "files": len(paths), "privacy_scan": "passed"}))
        return
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    args.output.mkdir(parents=True, exist_ok=True)
    for language in ("zh", "en"):
        payload = {str(p.relative_to(ROOT)): p.read_bytes() for p in paths}
        payload["plugin/language.json"] = (json.dumps({"language": language}) + "\n").encode()
        edition = dict(manifest, language=language,
                       sha256={name: hashlib.sha256(data).hexdigest() for name, data in sorted(payload.items())})
        payload["release-manifest.json"] = (json.dumps(edition, ensure_ascii=False, indent=2) + "\n").encode()
        name = "hermes-telegram-ux-" + str(metadata["version"]) + "-" + language
        archive = args.output / (name + ".zip")
        with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as out:
            for relative, data in sorted(payload.items()):
                info = zipfile.ZipInfo(name + "/" + relative, date_time=(2026, 9, 11, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                out.writestr(info, data)
        checksum = hashlib.sha256(archive.read_bytes()).hexdigest()
        archive.with_suffix(".zip.sha256").write_text(checksum + "  " + archive.name + "\n")
        print(json.dumps({"archive": str(archive), "language": language, "sha256": checksum, "files": len(payload)}, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, AssertionError, OSError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
