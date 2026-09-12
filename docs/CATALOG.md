# Official catalog preparation

Status: **candidate preparation; not submitted or accepted**. Target: the `community`
tier in NousResearch/hermes-agent's [Plugin Catalog](https://hermes-agent.nousresearch.com/docs/user-guide/features/plugin-catalog).
The plugin remains maintained by pler1y in this repository. Catalog inclusion would
not bundle it into Hermes or enable it by default.

## Candidate scope

1.8.0-rc.1 preserves the existing interaction design while adding:

- Complete tool/hook/middleware declarations and compatibility with the native Git installer.
- Two guarded core baselines, without rejecting unrelated commits whose guarded files match.
- Native configuration/recovery that preserves the installed checkout and provenance metadata.
- Official admission validation, native install/enable/discovery/wiring/removal, and regression CI.

The product covers the entire Telegram flow: intake acknowledgement, editable task progress,
mid-task requirement receipts, compression notices, foreground/background stop handling,
final file delivery, follow-up buttons, and Chinese/English interface text. Existing related
work does not by itself establish equivalent behavior or equivalent usability.

[PR #80262](https://github.com/NousResearch/hermes-agent/pull/80262) was still open on
2026-09-12; its latest commit was 2026-08-24. [Issue #69885](https://github.com/NousResearch/hermes-agent/issues/69885)
was still open and last updated 2026-07-23. The latter is an interface proposal, not
a released competing plugin. These dates describe public activity, not abandonment or
a quality ranking. This submission path does not request core changes or replacement of either proposal.

## Current upstream constraints

The examined upstream is `a84a2223f82c3d9906fd4a9d778a188774e7a08e`:

- `plugins_cmd.py` only accepts `manifest_version: 1`. The manifest's existing fields
  are additive and supported by the v1 loader, so the candidate uses that format.
- `plugin_validate.py` imports the version parser from its old location when a
  manifest declares `requires_hermes`; that import raises in this upstream checkout.
  The optional field is therefore omitted from the plugin manifest. The actual
  19-file runtime compatibility gate remains mandatory. The catalog entry has an
  outer `>=0.21.0,<0.22.0` boundary and explicitly documents the additional hash gate.
- The validator supplies a registration-only context; optional state is used only
  when the host supplies a real get/set facade. No validator-specific core bypass exists.
- The official security scan classifies documented service commands and subprocess
  checks as caution. Native CI keeps scanning on and explicitly trusts its own local
  fixture. Users review any native installer confirmation; no scan-disable preset is supplied.

## Reproduce checks

Use each supported core's isolated locked environment with its Telegram dependency,
set `PYTHONPATH` to that checkout, then run the project's checks:

```bash
python scripts/run_tests.py
python scripts/check_runtime.py
python scripts/check_native_install.py --require-validator
python scripts/build_release.py --check
python scripts/check_editions.py
```

The old 0.21.0 baseline predates `plugins validate`; omit `--require-validator` there.
All checks use disposable homes. They do not call a model or send Telegram messages.
CI tests both exact baselines and separately checks the current upstream main interfaces
on push, pull request or manual dispatch. A green admission check is not a live acceptance result.

## Prepare the upstream PR

Publish a tested candidate and read its actual `published_at` from GitHub. Generate
the entry and English PR draft from the exact published commit:

```bash
python scripts/prepare_catalog.py --ref v1.8.0-rc.1 \
  --released-at VERIFIED_GITHUB_RELEASE_TIMESTAMP
```

Output goes to the ignored `catalog-submission/` directory: `hermes-telegram-ux.yaml`,
`PR-DRAFT.md`, and `readiness.json`. The entry's capabilities come from that commit's
manifest, not uncommitted source. No GitHub write or PR submission occurs.
Use `--require-mature` at actual submission time; it exits nonzero before the later
of commit/release time plus 14 days. The timestamp must be independently verified;
the script cannot verify a user-provided publication date itself.

Before submitting:

1. Complete fresh Telegram live acceptance for the candidate on the new core using
   [TESTING.md](TESTING.md); attach the record and a representative demo. The older
   1.7.0 record is historical evidence, not candidate acceptance.
2. Confirm the pinned release has matured for at least two weeks under the official
   policy. New candidate code starts a new window; an earlier draft does not satisfy it.
3. Recheck official policy and current main. Run the official structure checker on
   the generated YAML and validate/install the exact candidate against that current
   checkout. Changed protected interfaces require a reviewed compatibility update,
   not removal of the guard.
4. Submit only `plugin-catalog/hermes-telegram-ux.yaml` to the upstream repository,
   using the actual candidate CI and live acceptance evidence in the PR description.

Maintainer review determines acceptance and timing. The remaining compatibility
coupling is disclosed so reviewers can judge whether the candidate is suitable for
the directory; it is not presented as a solved public-API-only integration.
