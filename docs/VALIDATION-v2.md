# v2.0.0 release candidate validation

This record belongs to the v2 release-preparation line. The accepted implementation is `c5b8aef94d1f096fbad9ad782b2ad312e9254d33`. Release preparation does not change `catalog/` or `__init__.py`; `plugin.yaml` changes only version `1.9.0-catalog.1 → 2.0.0`.

## Historical preservation and runtime equivalence

Integration commit `6103f23f65d15d1a0f125b13be817eb7a4e1de90` has parents `c5b8aef94d1f096fbad9ad782b2ad312e9254d33` and `3b2175199d8d9dbafaa39e13c1f5dafd4bf0cfcb`. Its entire tree equals the accepted candidate. Both histories remain ancestors; no rebase, squash or forced main update is used.

Remote `legacy/full-1.8.3` preserves `3b2175199d8d9dbafaa39e13c1f5dafd4bf0cfcb`; `v1.8.3` remains `1ed97bfbe9071a179e1a2b8fcc260a573ecc6364`. Their trees match. Candidate branch `codex/catalog-experience` remains exactly `c5b8aef…`.

The release allowlist contains only the nine accepted Python payload files, manifest, license and reviewed documentation. No legacy `plugin/`, `catalog/interface.py` or `catalog/preferences.py` is restored. Version and provenance are derived from committed `plugin.yaml`, not a duplicated runtime version constant.

## Exact-commit automated verification

The local receipt lives in `Telegram测试工具/reports/v2-release-prep-20260920-191159/`, outside the distributable plugin. GitHub [Actions](https://github.com/pler1y/hermes-telegram-ux/actions/workflows/catalog-safe.yml) attaches `native.json`, `upgrade.json`, the ZIP, checksums and provenance to each tested revision. The report records the tested source SHA and core SHA; use the final PR head's run, not an older candidate run.

Release validation is pending while this preparation record is being assembled. The required checks are full unit and contract suites, boundary guard, official validate/doctor, diff check, exact-ref native Git/ZIP lifecycle, negative undeclared-hook control, actual historical-install upgrade and tracked-core hash comparison. Results will be recorded before the final review PR is delivered.

## Upgrade scope

The internal ID stays `hermes-telegram-ux-catalog`. Disposable homes start from actual historical menu-bearing `1.9.0-catalog.1` at `93ff48a`, retaining configuration and external preferences. Git and ZIP origins are replaced by the same-ID exact v2 Git commit. The tests inspect one enabled plugin, no commands/menus, preserved configuration/state and a synthetic public-hook progress lifecycle. This is an install/upgrade contract test, not a live Telegram test. Native ZIP lifecycle means verified extraction plus native validate/enable/disable/remove; Hermes has no direct ZIP install command.

## Live Telegram evidence and limits

The real A–F, supplementary recovery, language and cleanup acceptance belongs to `c5b8aef…` under its original `1.9.0-catalog.1` version. See [the unaltered historical record](VALIDATION.md). Runtime byte identity carries that implementation evidence into v2; it does not turn the old run into a fresh v2 deployment. This release-preparation round does not redeploy the test Bot or modify real Full installations.

Known P3 wording limitations and public lifecycle limits remain as recorded: compound-target repetition, conservative English task objects, coalesced short stages, bounded best-effort deletion and no public final-delivery receipt. No redesign or new UX feature is part of release preparation.

## Publication boundary

The intended delivery is an open, unmerged `release/v2.0.0 → main` review PR after local validation and GitHub CI. No v2 tag, GitHub Release, default-branch change, Catalog publication, Catalog PR #108887 update or historical branch deletion is authorized in this stage.
