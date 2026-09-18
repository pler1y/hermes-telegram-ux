# Official catalog candidate

**1.8.3-rc.1** is an unpublished local candidate based on 1.8.2. This preparation
creates no upstream PR, updates no existing PR, and publishes no release. Earlier
release history references PR #108887; it is not submission evidence for this
candidate. The intended catalog tier is **community**, maintained by pler1y.

## Technical readiness

- Native Git install at an exact revision, installed-source validation, enable,
  discovery, Telegram wiring/unload, configuration/recovery and removal.
- Bare native enable/discovery works before running the optional configuration
  helper. Disabled discovery installs no UX tools or gateway wrappers.
- Both manifests declare exactly two tools, thirteen hooks and two middleware
  handlers. The official probe must run and report no declaration warnings.
  A fixture missing `tool_request` must fail official validation.
- Six complete source baselines; every guarded file must match one baseline by
  raw SHA-256 or complete Python AST, and the core version must match that baseline.
  Unknown executable changes, incomplete contracts and mixed baselines fail before
  runtime imports or registration, including under Python optimization.
- Current-core consumed controls/menu messages reach the native observer exactly
  once. This preserves ingress counters and original event identity.

See [validation evidence](VALIDATION-1.8.3-rc.1.md), [compatibility policy](COMPATIBILITY.md)
and [native installation](NATIVE-INSTALL.md). Internal gateway/Telegram interfaces
remain part of the integration; core source files are never patched on disk.

## Reproduce

Use each supported core's Python 3.11 environment and the declared Telegram SDK:

```bash
export PYTHONPATH="$HERMES_CORE"
"$HERMES_PYTHON" scripts/run_tests.py
"$HERMES_PYTHON" scripts/check_compatibility.py --hermes-core "$HERMES_CORE"
"$HERMES_PYTHON" scripts/check_runtime.py
"$HERMES_PYTHON" scripts/check_native_install.py --require-validator --report native-report.json
"$HERMES_PYTHON" scripts/build_release.py --check
"$HERMES_PYTHON" scripts/check_editions.py
```

The 0.21.0 baseline predates `plugins validate`; omit `--require-validator` only
there. The report explicitly says the validator was unavailable. All checks use
throwaway homes and synthetic messages, without model calls or Telegram delivery.
Native security scanning stays enabled; the harness explicitly trusts its own
reviewed local Git fixture after scanning (which reports caution for documented
service/subprocess operations).

The root layout is the catalog target (`subdir` omitted). The payload `plugin/`
manifest/entry are also validated because ZIP installations use that layout.
The manifest omits `requires_hermes` for older validator compatibility; the catalog
outer range and mandatory runtime version/source guard retain the support boundary.

## Prepare the exact pin locally

After committing the candidate, generate a draft from that immutable source:

```bash
python scripts/prepare_catalog.py --ref HEAD --output catalog-submission/candidate
```

This produces the entry, a PR text draft and readiness JSON. Without a verified
release timestamp, `released_at` / `earliest_pin_at` are null and `mature` is false.
Public SHA reachability is also marked unverified. The script reads Git objects,
not the current working tree, and checks root/payload metadata consistency.
No network mutation occurs.

After a real public release, verify its GitHub publication timestamp and rerun:

```bash
python scripts/prepare_catalog.py --ref RELEASE_TAG \
  --released-at VERIFIED_GITHUB_RELEASE_TIMESTAMP --require-mature
```

The [official admission policy](https://github.com/NousResearch/hermes-agent/blob/5eb99eb2844b22ebb723711b8e6a0bbb80bb5f04/plugin-catalog/README.md)
requires a public, owner/major-contributor submission, a full SHA, settled release
code (two weeks at pin time), validation and maintainer review. The helper takes
the later of commit/publication time plus 14 days; an old release date cannot make
new code mature. No maturity date is claimed for this unpublished candidate.

Before an eventual submission, verify that the selected SHA can be cloned from the
public repository, rerun the official structural validator and `hermes plugins
validate` against the then-current upstream, and attach that evidence. A compatible
main today does not guarantee a future PR's checkout is compatible. Unknown core
changes require review and another supported baseline, never a validator bypass.

A new full Telegram/model acceptance run is not part of this local validation;
[1.7.0 live evidence](ACCEPTANCE-1.7.0.md) remains historical. Catalog inclusion,
if approved, still requires users to install and enable the plugin themselves.
