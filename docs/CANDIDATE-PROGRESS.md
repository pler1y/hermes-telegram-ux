# Current Full development

Current Full work and validation are recorded in [FULL-PROGRESS.md](FULL-PROGRESS.md). The 2026-09-14 catalog preparation below is historical; it is not the release route for Full.

# Catalog candidate — 2026-09-14

Goal completed locally: prepare 1.8.2 behavior as the new **1.8.3-rc.1** candidate,
without publishing a release or creating/updating an upstream PR.

- Both middleware declarations match real registration; root/payload/installed
  sources pass the official probe and a missing middleware declaration is rejected.
- Preserve all four old baselines and add reviewed official core
  `5eb99eb2844b22ebb723711b8e6a0bbb80bb5f04`. Full-file/AST matching, complete profile
  metadata and exact core versions are required before runtime import/registration.
- Preserve native platform observation for UX-consumed Telegram updates; current
  core ingress counters no longer miss natural stop/menu messages.
- Five cores each passed 180 plugin tests with no skips, compatibility/runtime
  checks, native lifecycle and both ZIP edition lifecycles. Four newer cores also
  passed official validation; the oldest core has no validator command.
- Current-core upstream regressions: 101 passed. Python 3.12 source fingerprint
  checks passed on all five cores; full runtime checks used Python 3.11 on macOS.
- Details and reproducible commands: [validation](VALIDATION-1.8.3-rc.1.md),
  [release](RELEASE.md), [catalog preparation](CATALOG.md).
- Existing untracked `docs/research/` remains untouched and outside the candidate.

Next, only after a later release/submission request: publish the selected candidate,
verify its public SHA/release timestamp, wait for pin maturity, rerun validation on
the then-current upstream, and submit for maintainer review. New live Telegram/model
acceptance is separate from the automated evidence. No maturity date is invented.
