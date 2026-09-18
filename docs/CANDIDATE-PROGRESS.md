# Catalog candidate — 2026-09-14

Goal completed locally: prepare 1.8.2 behavior as the new **1.8.3-rc.1** candidate,
without publishing a release or creating/updating an upstream PR.

- Both middleware declarations match real registration; root/payload/installed
  sources pass the official probe and a missing middleware declaration is rejected.
- Preserve all five prior baselines and add reviewed official 0.21.3 core
  `debfc7420b61a96ad97fc03b18cca74d7e72697d`. Full-file/AST matching, complete profile
  metadata and exact core versions are required before runtime import/registration.
- Preserve native platform observation for UX-consumed Telegram updates; current
  core ingress counters no longer miss natural stop/menu messages.
- The newest two cores passed 182 plugin tests; the four historical cores retain
  their recorded 180-test runs. All six passed with no skips, compatibility/runtime
  checks, native lifecycle and both ZIP edition lifecycles. Five newer cores also
  pass official validation; the newest surfaces a non-fatal security-scan caution.
  The oldest core has no validator command.
- Current-core upstream regressions: 101 passed. Python 3.11 and 3.12 source
  fingerprint checks passed on all six cores; full runtime checks used Python 3.11 on macOS.
- Details and reproducible commands: [validation](VALIDATION-1.8.3-rc.1.md),
  [release](RELEASE.md), [catalog preparation](CATALOG.md).
- Existing untracked `docs/research/` remains untouched and outside the candidate.

Next, only after a later release/submission request: publish the selected candidate,
verify its public SHA/release timestamp, wait for pin maturity, rerun validation on
the then-current upstream, and submit for maintainer review. New live Telegram/model
acceptance is separate from the automated evidence. No maturity date is invented.
