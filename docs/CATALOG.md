# Official catalog submission

[PR #108887](https://github.com/NousResearch/hermes-agent/pull/108887) requests a
**community** entry for Hermes Telegram UX. Version **1.8.0** supplies the completed
native installation work, current-core compatibility and task ownership fixes.
The entry is not accepted until a Hermes maintainer reviews and merges it.
The plugin remains maintained by pler1y; inclusion does not bundle or enable it by default.

## What is ready

- Native Git installation, configuration/recovery, enable, discovery, Telegram handler wiring and removal.
- Complete declarations of two tools, thirteen hooks and two middleware handlers.
- Three guarded core baselines: Hermes 0.21.0 `b499ab11fe8b` and 0.21.2
  `a84a2223f82c` / `436ec489854b`. All 23 guarded files must match one baseline.
- Regression coverage for a new turn arriving while an old turn stops or finishes:
  progress, cleanup and follow-up actions stay with the owning turn.
- Chinese/English packages and reproducible isolated checks.

The integration uses internal gateway interfaces as well as public plugin APIs.
It does not modify core source files, but unrelated future changes to guarded
files require review and another tested baseline. The guard is not disabled to
make validation pass. See [compatibility](COMPATIBILITY.md).

## What the official process still requires

The [official admission policy](https://github.com/NousResearch/hermes-agent/blob/main/plugin-catalog/README.md)
requires maintainer review, a complete commit SHA and a release at least two weeks
old at pin time. A PR being ready for review does not waive this maturity condition
or promise acceptance. A new release/pin starts its own window; the PR description
records the verified release timestamp and earliest maturity date.

The repository contains historical Telegram/model acceptance for 1.7.0. Version
1.8.0 has automated integration evidence; a fresh full Telegram/model acceptance
run on the new core has not been recorded. Reviewers can request further evidence.
Automatic validation is not presented as live platform acceptance.

Users can install the published release directly today using
[NATIVE-INSTALL.md](NATIVE-INSTALL.md). After the upstream entry is merged and its
catalog is published/refreshed, users can discover and install it by catalog name.
Future catalog pin updates require another reviewed PR.

## Reproduce the technical checks

In each supported core's locked Python environment with the Telegram dependency,
set `PYTHONPATH` to that checkout, then run:

```bash
python scripts/run_tests.py
python scripts/check_runtime.py
python scripts/check_native_install.py --require-validator
python scripts/build_release.py --check
python scripts/check_editions.py
```

The old 0.21.0 baseline predates `plugins validate`; omit `--require-validator` there.
All checks use disposable homes and do not call a model or send Telegram messages.
CI covers all three baselines and checks current upstream main on push, pull
request and manual dispatch.

The examined 0.21.2 native installer accepts `manifest_version: 1`. The optional
`requires_hermes` manifest field triggers an upstream validator import error, so
it is omitted; the catalog has an outer `>=0.21.0,<0.22.0` range and the mandatory
23-file gate provides the actual boundary. Optional durable state is used only
when the context supplies callable get/set methods. Native security scanning stays
on; the check explicitly trusts its own disposable local fixture after scanning.

To generate a pin update from an actual published release:

```bash
python scripts/prepare_catalog.py --ref v1.8.0 \
  --released-at VERIFIED_GITHUB_RELEASE_TIMESTAMP
```

The ignored `catalog-submission/` output is local preparation only. Use
`--require-mature` to check whether the later of commit/release time plus 14 days
has elapsed before asking maintainers to merge the pin. The timestamp must be
independently verified from GitHub. Only the catalog YAML is submitted upstream;
plugin source stays in this repository.
