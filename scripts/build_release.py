#!/usr/bin/env python3
"""Build reproducible ZIP and SHA256 from a committed, reviewed file allowlist."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import subprocess
import zipfile

from check_boundary import ROOT, PAYLOAD, scan

# Distribute user documentation; historical operator/acceptance records stay in Git.
FILES = (*PAYLOAD, "plugin.yaml", "LICENSE", "README.md", "README.zh-CN.md", "docs/PUBLIC-API.md",
         "CHANGELOG.md", "docs/MIGRATION-v2.md", "docs/PLUGIN-ID.md", "docs/RELEASE.md")


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)


def build(ref, output):
    commit = git("rev-parse", "--verify", ref + "^{commit}").decode().strip()
    files = {name: git("show", f"{commit}:{name}") for name in FILES}
    for name in PAYLOAD:
        errors = scan(files[name].decode(), name)
        if errors:
            raise ValueError("\n".join(errors))
    # Pure JSON is valid YAML; metadata comes from committed source via the Hermes-provided parser.
    import yaml
    manifest = yaml.safe_load(files["plugin.yaml"])
    provenance = {"plugin": manifest["name"], "version": manifest["version"], "source_commit": commit,
                  "files": {name: hashlib.sha256(data).hexdigest() for name, data in files.items()}}
    files["PROVENANCE.json"] = (json.dumps(provenance, indent=2) + "\n").encode()
    output.mkdir(parents=True, exist_ok=True)
    artifact = output / f"{manifest['name']}-{manifest['version']}.zip"
    with zipfile.ZipFile(artifact, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in sorted(files.items()):
            info = zipfile.ZipInfo(name, (2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)
    checksum = hashlib.sha256(artifact.read_bytes()).hexdigest()
    artifact.with_suffix(".zip.sha256").write_text(f"{checksum}  {artifact.name}\n")
    verify(artifact)
    return {"source_commit": commit, "artifact": str(artifact), "sha256": checksum, "files": len(files)}


def verify(path):
    with zipfile.ZipFile(path) as archive:
        if set(archive.namelist()) != set(FILES) | {"PROVENANCE.json"} or len(archive.namelist()) != len(FILES) + 1:
            raise ValueError("Unexpected release contents")
        provenance = json.loads(archive.read("PROVENANCE.json"))
        for name in FILES:
            if hashlib.sha256(archive.read(name)).hexdigest() != provenance["files"][name]:
                raise ValueError(f"Payload hash mismatch: {name}")
        for name in PAYLOAD:
            if errors := scan(archive.read(name).decode(), name):
                raise ValueError("\n".join(errors))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ref", default="HEAD")
    parser.add_argument("--output", type=Path, default=ROOT / "dist")
    parser.add_argument("--verify", type=Path)
    args = parser.parse_args()
    if args.verify:
        verify(args.verify)
        print("Release contents: PASS")
    else:
        print(json.dumps(build(args.ref, args.output), indent=2))
