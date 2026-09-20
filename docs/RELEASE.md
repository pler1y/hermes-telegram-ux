# Release identity and verification

Hermes Telegram UX v2.0.0 is identified by the commit behind the official [v2.0.0 tag](https://github.com/pler1y/hermes-telegram-ux/tree/v2.0.0) and [Release](https://github.com/pler1y/hermes-telegram-ux/releases/tag/v2.0.0). Release notes state the full 40-character commit. The internal plugin ID is `hermes-telegram-ux-catalog`.

## Pin the commit, not a moving branch

Use the tag-resolution command in [the migration guide](MIGRATION-v2.md). It prefers the peeled commit for annotated tags and accepts lightweight tags. A missing tag or malformed SHA stops the procedure. Hermes' `--ref` expects the full commit, not `v2.0.0` itself. Compare the result with the official Release notes before installing.

## Assets and provenance

The official assets are:

- `hermes-telegram-ux-catalog-2.0.0.zip`
- `hermes-telegram-ux-catalog-2.0.0.zip.sha256`
- `PROVENANCE.json`, also present inside the ZIP
- `RUNTIME-MANIFEST.json`, identifying the accepted Python payload by hash

Verify the downloaded ZIP against its checksum file, then inspect `PROVENANCE.json`. Its `source_commit` must match the resolved tag commit, `plugin` must be `hermes-telegram-ux-catalog`, and `version` must be `2.0.0`. It lists SHA256 hashes for every distributed file. The Release notes record the final checksum; do not substitute a candidate ZIP built from another commit.

The archive contains only runtime files, manifest, license and user documentation. Historical validation records, operator progress notes, test fixtures and private acceptance evidence are not distributed. The published [validation history](https://github.com/pler1y/hermes-telegram-ux/blob/v2.0.0/docs/VALIDATION.md) remains in Git with its original version labels.

Hermes' installer handles Git/Catalog sources, not ZIP input. Follow [migration](MIGRATION-v2.md) for same-ID replacement or verified manual archive deployment. Keep existing user configuration, plugin-data and backups.

## Reproduce a release archive

In a source checkout at the tag's commit, using the verified Hermes Python environment:

```bash
python scripts/build_release.py --ref "$TGUX_COMMIT"
python scripts/build_release.py --verify dist/hermes-telegram-ux-catalog-2.0.0.zip
```

The builder reads committed Git objects through a reviewed allowlist, uses fixed archive metadata, verifies payload hashes and records the exact source commit. `$TGUX_COMMIT` must be the previously verified tag commit. Historical reports remain unchanged; they are linked rather than copied into the installation archive.

## Validation scope

Release notes link the final main-commit CI and report its unit, contract, boundary, official validate/doctor, native install and package checks. The short Telegram smoke is run on that exact merge-commit payload before tagging. Earlier detailed A–F runs are historical evidence, not renamed release-time tests. All nine Python runtime files must match the accepted `c5b8aef94d1f096fbad9ad782b2ad312e9254d33` implementation.

Full history remains at `legacy/full-1.8.3` and `v1.8.3`. Project publication does not itself imply Hermes Catalog admission; Catalog review and its exact SHA pin are maintained separately.
