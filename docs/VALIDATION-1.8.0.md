# Version 1.8.0 validation — 2026-09-12

The task ownership regressions were reproduced before the runtime change:
old finalization consumed successor actions, displaced polling kept sending,
a new foreground turn adopted a message still owned by old cleanup, and the
native stop wrapper marked a successor interrupted after an asynchronous yield.
The fixes and five ownership regressions are in this release.

| Hermes core | Full plugin suite | Runtime/native install | Official validator | Both ZIP lifecycles |
|---|---|---|---|---|
| `b499ab11fe8b081470e269f2fb27abae03000da5` | 156 passed, 0 skipped | Passed | Unavailable in this core | Passed |
| `a84a2223f82c3d9906fd4a9d778a188774e7a08e` | 156 passed, 0 skipped | Passed | Passed | Passed |
| `436ec489854b7110b4c5506b1f52c514fa4c3ace` | 156 passed, 0 skipped | Passed | Passed | Passed |

Native checks use the actual Hermes Git installer, enable/discover/register,
Telegram adapter handler wiring, configure/restore and remove commands in a
disposable home. They verify Git and catalog metadata remain intact. Both
language archives pass install/reinstall/uninstall and source hash/privacy checks.

On `436ec489854b`, Hermes' canonical `scripts/run_tests.sh` also passed all 13 tests
in `test_reaped_eviction_interrupts_run.py`, `test_moa_one_shot_restore.py` and
`test_reaped_session_recovery.py`. This covers the reviewed upstream lease,
interruption and session replacement changes; it is not the full Hermes suite.

These are automated tests with controlled platform/model boundaries. No new
Telegram/model end-to-end acceptance is claimed here. Historical client
acceptance is recorded in [ACCEPTANCE-1.7.0.md](ACCEPTANCE-1.7.0.md).

Reproduction commands and remaining integration limits are documented in
[TESTING.md](TESTING.md), [COMPATIBILITY.md](COMPATIBILITY.md) and
[CATALOG.md](CATALOG.md). The official catalog PR is an application, not evidence
of maintainer acceptance.
