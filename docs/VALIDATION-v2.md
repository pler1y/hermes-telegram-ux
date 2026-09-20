# v2.0.0 release candidate validation

This record belongs to the v2 release-preparation line. The accepted implementation is `c5b8aef94d1f096fbad9ad782b2ad312e9254d33`. Release preparation does not change `catalog/` or `__init__.py`; `plugin.yaml` changes only version `1.9.0-catalog.1 → 2.0.0`.

## Historical preservation and runtime equivalence

Integration commit `6103f23f65d15d1a0f125b13be817eb7a4e1de90` has parents `c5b8aef94d1f096fbad9ad782b2ad312e9254d33` and `3b2175199d8d9dbafaa39e13c1f5dafd4bf0cfcb`. Its entire tree equals the accepted candidate. Both histories remain ancestors; no rebase, squash or forced main update is used.

Remote `legacy/full-1.8.3` preserves `3b2175199d8d9dbafaa39e13c1f5dafd4bf0cfcb`; `v1.8.3` remains `1ed97bfbe9071a179e1a2b8fcc260a573ecc6364`. Their trees match. Candidate branch `codex/catalog-experience` remains exactly `c5b8aef…`.

The release allowlist contains only the nine accepted Python payload files, manifest, license and reviewed documentation. No legacy `plugin/`, `catalog/interface.py` or `catalog/preferences.py` is restored. Version and provenance are derived from committed `plugin.yaml`, not a duplicated runtime version constant.

## Exact-commit automated verification

The local receipt lives in `Telegram测试工具/reports/v2-release-prep-20260920-191159/`, outside the distributable plugin. GitHub [Actions](https://github.com/pler1y/hermes-telegram-ux/actions/workflows/catalog-safe.yml) attaches `native.json`, `upgrade.json`, the ZIP, checksums and provenance to each tested revision. The report records the tested source SHA and core SHA; use the final PR head's run, not an older candidate run.

Local release validation uses Python 3.12.13 and official Hermes `3c3ab69abb9b08683b5eb15b4e2b8be1198c875f` (0.21.3). The complete suite is rerun after the final documentation/test commit; `final/summary.json`, `final/native.json`, `final/upgrade.json` and `final/tree-and-package-proof.json` bind the results to that exact HEAD.

| Check | Result |
|---|---|
| Full unit suite | 161 passed |
| Real PluginManager contracts | 7 passed |
| Standalone boundary guard | PASS |
| Official `plugins validate --json` | 10/10, zero warnings |
| Official `plugins doctor --ci` | PASS; 16 hooks / 1 tool / 0 commands / 0 middleware |
| Native Git install/enable/disable/remove | PASS |
| Verified ZIP extraction/native lifecycle | PASS |
| Negative undeclared-hook control | Correctly rejected for both installation paths |
| Historical Git → same-ID v2 Git | PASS |
| Historical ZIP → same-ID v2 Git | PASS |
| Reproducible allowlisted ZIP/provenance | PASS; exact committed source |
| Runtime byte comparison | All nine Python files match accepted candidate |
| Hermes tracked-core comparison | 13,490 files unchanged |
| `git diff --check` | PASS |

The GitHub `Hermes Telegram UX` workflow runs the full checks against both the fixed core and current core main on Python 3.11 and 3.12. The final PR is delivered only after all four push jobs and subsequent PR jobs pass. Current-main core revisions are recorded in each native/upgrade artifact; a branch label alone is not an immutable compatibility claim. See the PR checks and commit-specific Actions links for final remote status.

## Upgrade scope

The internal ID stays `hermes-telegram-ux-catalog`. Disposable homes start from actual historical menu-bearing `1.9.0-catalog.1` at `93ff48a`, retaining configuration and external preferences. Git and ZIP origins are replaced by the same-ID exact v2 Git commit. The tests inspect one enabled plugin, no commands/menus, preserved configuration/state and a synthetic public-hook progress lifecycle (one send, at least one same-ID edit and one deletion). The historical configuration says progress=true while its persisted preference says false: old loading suppresses progress, proving the state fixture is active; v2 ignores that state and shows progress. One route preserves enabled configuration with the old process already unloaded; the ZIP route explicitly disables before replacement, remains disabled with --no-enable, then enables. Native disable writes its deny-list as expected, while all unrelated values and external data remain intact. This is an install/upgrade contract test, not a live Telegram test. Native ZIP lifecycle means verified extraction plus native validate/enable/disable/remove; Hermes has no direct ZIP install command.

## Live Telegram evidence and limits

The real A–F, supplementary recovery, language and cleanup acceptance belongs to `c5b8aef…` under its original `1.9.0-catalog.1` version. See [the unaltered historical record](VALIDATION.md). Runtime byte identity carries that implementation evidence into v2; it does not turn the old run into a fresh v2 deployment. This release-preparation round does not redeploy the test Bot or modify real Full installations.

Known P3 wording limitations and public lifecycle limits remain as recorded: compound-target repetition, conservative English task objects, coalesced short stages, bounded best-effort deletion and no public final-delivery receipt. No redesign or new UX feature is part of release preparation.

## Publication boundary

The intended delivery is an open, unmerged `release/v2.0.0 → main` review PR after local validation and GitHub CI. No v2 tag, GitHub Release, default-branch change, Catalog publication, Catalog PR #108887 update or historical branch deletion is authorized in this stage.

## Historical branch CI

Saving the unchanged Full commit to `legacy/full-1.8.3` triggered its historical `Tests` workflow: [run 35507112053](https://github.com/pler1y/hermes-telegram-ux/actions/runs/35507112053). All five fixed-core regression jobs passed; two Python variants of the mutable-upstream fingerprint check rejected changed private interfaces. This is an existing Full compatibility boundary, not a v2 workflow result. The legacy commit/tag and workflow were preserved without modification. The uploaded accepted public-plugin baseline also passed its [push CI](https://github.com/pler1y/hermes-telegram-ux/actions/runs/35507076196) and [existing-PR CI](https://github.com/pler1y/hermes-telegram-ux/actions/runs/35507078262).
