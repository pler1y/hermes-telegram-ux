#!/usr/bin/env python3
"""Prepare an upstream catalog entry from a committed release; never submit it automatically."""
import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import subprocess

import yaml

ROOT = Path(__file__).resolve().parents[1]
REPO = "https://github.com/pler1y/hermes-telegram-ux"


def git(*args):
    return subprocess.check_output(["git", "-C", str(ROOT), *args], text=True).strip()


def timestamp(value):
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("Release publication time must include a timezone")
    return result.astimezone(timezone.utc)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ref", required=True, help="Published release tag or full commit")
    parser.add_argument("--released-at", required=True, help="Verified GitHub release published_at (ISO-8601)")
    parser.add_argument("--output", type=Path, default=ROOT / "catalog-submission")
    parser.add_argument("--require-mature", action="store_true")
    args = parser.parse_args()
    sha = git("rev-parse", "--verify", "--end-of-options", args.ref + "^{commit}")
    manifest = yaml.safe_load(git("show", sha + ":plugin.yaml"))
    compat = json.loads(git("show", sha + ":plugin/compatibility.json"))
    released = timestamp(args.released_at)
    eligible = max(released, timestamp(git("show", "-s", "--format=%cI", sha))) + timedelta(days=14)
    now = datetime.now(timezone.utc)
    entry = {"name": "hermes-telegram-ux", "repo": REPO, "sha": sha,
             "description": "Immediate Telegram feedback, editable task progress, mid-task instructions and natural controls.",
             "maintainer": "pler1y", "tier": "community", "requires_hermes": ">=0.21.0,<0.22.0",
             "docs_url": REPO + "/blob/" + sha + "/docs/NATIVE-INSTALL.md", "platforms": ["linux", "macos"],
             "capabilities": {key: manifest.get(key, []) for key in (
                 "provides_tools", "provides_hooks", "provides_middleware", "requires_env")}}
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "hermes-telegram-ux.yaml").write_text(yaml.safe_dump(entry, sort_keys=False))
    readiness = {"sha": sha, "version": manifest["version"], "released_at": released.isoformat(),
                 "earliest_submission_at": eligible.isoformat(), "mature": now >= eligible,
                 "tested_core_commits": [p["core_commit"] for p in compat["profiles"]],
                 "requires_fresh_upstream_validation": True, "submitted": False}
    (args.output / "readiness.json").write_text(json.dumps(readiness, indent=2) + "\n")
    (args.output / "PR-DRAFT.md").write_text(f"""# feat(plugin-catalog): add Hermes Telegram UX

Add Hermes Telegram UX as a community plugin maintained by pler1y, the repository owner.
It gives Telegram users immediate intake feedback, a shared editable progress message,
mid-task instruction receipts, natural stop controls, and English/Chinese interface text.
The plugin stays in its own repository and is explicitly installed and enabled.

- Repository: {REPO}
- Candidate: `{manifest['version']}` / `{sha}`
- Published: {released.isoformat()}
- Earliest pin date under the two-week policy: **{eligible.isoformat()}**
- Installation and limits: {entry['docs_url']}

The catalog version range is an outer boundary. Runtime registration also checks every
guarded interface file against one complete tested baseline and refuses mismatches.
The plugin uses public tools/hooks/middleware plus documented internal gateway and
Telegram adapters; it does not claim compatibility with every commit in that range.

Validation commands and behavior coverage are documented in `docs/CATALOG.md` and
`docs/TESTING.md` at the pinned commit. Before submitting, attach the candidate CI URL,
rerun the official catalog structure/validate checks against the then-current upstream,
verify publication age, and record fresh Telegram live acceptance results.

This is a catalog-only submission. Related rolling-status work (#80262) and the
editable-status API proposal (#69885) are acknowledged; no core behavior change or
replacement of those proposals is requested here.
""")
    print(json.dumps(readiness, indent=2))
    if args.require_mature and not readiness["mature"]:
        raise SystemExit("Candidate is not mature yet; files are a draft, not a submission.")


if __name__ == "__main__":
    main()
