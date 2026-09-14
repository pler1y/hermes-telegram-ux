# 1.8.3-rc.1 candidate validation — 2026-09-14

This is a **local, unpublished candidate based on 1.8.2**. No release/tag or upstream
PR was created or updated. The existing 1.8.2 artifacts are not replaced.

## Environments and results

Tests ran locally on macOS arm64 with Python 3.11.15, PyYAML 6.0.3 and
python-telegram-bot 22.8. The 0.21.2 environments use the official frozen lockfile;
`a84a`, `436e` and `044a` have identical dependency lockfiles. The historical 0.21.0
baseline uses its existing isolated test environment. The new core was checked out
at the exact official main SHA resolved for this run; its source and lockfile were
not modified.

| Hermes/core | Plugin regression | Compatibility + runtime | Native lifecycle | Official validation |
|---|---|---|---|---|
| 0.21.0 `b499ab11fe8b` | 180 passed, 0 skipped | Passed | Passed | Unavailable in this old core |
| 0.21.2 `a84a2223f82c` | 180 passed, 0 skipped | Passed | Passed | Passed, 0 warnings |
| 0.21.2 `436ec489854b` | 180 passed, 0 skipped | Passed | Passed | Passed, 0 warnings |
| 0.21.2 `044a77b3b6af` | 180 passed, 0 skipped | Passed | Passed | Passed, 0 warnings |
| 0.21.2 `5eb99eb2844b` | 180 passed, 0 skipped | Passed | Passed | Passed, 0 warnings |

The original 1.8.2 suite had 167 tests. Thirteen new cases cover manifest capability
agreement, incomplete contracts, exact-version selection, pre-registration refusal,
source archives, native dispatch observation, and unpublished catalog preparation.
Python 3.12.13 also passed the real-source formatting/change-rejection check on all five baselines; the
full runtime matrix above uses Python 3.11. Linux CI is configured but has not been
run remotely for this unpublished candidate.

## Native path exercised

`scripts/check_native_install.py` builds a disposable Git repository from the
release allowlist, fixes its full SHA, and invokes the unmodified official
`python -m hermes_cli.main plugins` CLI. No mock installer/validator is used.

1. `validate SOURCE --json` and `validate SOURCE/plugin --json`: the capability
   probe executes register; tools/hooks/middleware match with zero warnings.
2. Remove `tool_request` from a separate fixture manifest: official validation
   returns exit 1 specifically for undeclared middleware. This proves registration
   is reached; a guard failure cannot be mistaken for the expected rejection.
3. `install file://LOCAL_REPO --ref FULL_SHA --no-enable --force`: native scanning
   is active, installed Git HEAD is checked, and disabled state is checked. Force
   is only the explicit trust decision for our reviewed local fixture.
4. `validate INSTALLED --json`, then a fresh disabled discovery process: no UX
   tools, middleware or runner patches.
5. `enable hermes-interaction --no-allow-tool-override`, then discovery and real
   TelegramAdapter wiring/unload **before configure**: tools, prompt and defaults
   load; handlers and wrappers restore correctly.
6. Configure dry-run and actual English configuration, load again, repeat configure,
   restore settings and compare the semantic baseline. Git/source/install metadata
   stays unchanged. Disable, verify unloaded discovery, then remove.

Each report records the core SHA, fixture SHA, scanner verdict and all four official
JSON reports (source, payload, installed, rejected fixture). Scanner verdict is
`caution` for documented service/subprocess operations, not a scanner-free pass.
The script can reproduce the report with `--report native-report.json`.

## Core change review

Reviewed [044a77b3 → 5eb99eb2](https://github.com/NousResearch/hermes-agent/compare/044a77b3b6af4ce16138d42762f812a20b9f7a89...5eb99eb2844b22ebb723711b8e6a0bbb80bb5f04):
12 of 23 guarded files changed. Checks retain complete files/ASTs rather than
reducing protection to signatures.

- Telegram batching now delegates delay selection and retains cancellation/hold
  ownership checks. UX only adjusts delay attributes and forwards native commands;
  it does not replace the batch dispatch implementation.
- Approval prompt construction moved to the base adapter; native choices and
  authorization remain owned by Hermes. UX approval observers still only display.
- Follow-up processing acknowledgements, replay canonicalization, profile/media
  scope and async-delegation database helpers changed. The UX turn ownership and
  stop cleanup tests still pass; native wrappers continue to delegate these paths.
- Current Telegram ingress accounting assumes its group-99 observer sees each
  consumed update. UX's ApplicationHandlerStop previously skipped it. The candidate
  forwards the original update to that observer once before stopping propagation;
  default dispatch, deep links and unaddressed group input do not get a second call.
- The current admission validator fixes the old requires_hermes parser import.
  The field remains omitted in the plugin manifest to retain old validator support;
  a mandatory exact-version gate supplements the existing source guard instead.

In the new core, **101 upstream tests passed** across these files:

```text
tests/gateway/test_telegram_text_batching.py
tests/gateway/test_telegram_approval_buttons.py
tests/gateway/test_telegram_ingress_delivery_gap.py
tests/gateway/test_turn_lease.py
tests/tools/test_async_delegation.py
tests/tools/test_async_delegation_fd_leak.py
tests/agent/test_replay_cleanup.py
tests/hermes_cli/test_plugin_validate.py
```

## Artifact and admission limits

The two ZIP editions are built with SHA-256 manifests and exercise fresh install,
repeat install, discovery/middleware and uninstall in each supported environment.
The deterministic rebuild and privacy/source allowlist checks must pass before
committing the candidate. Commands are in [RELEASE.md](RELEASE.md).

The local catalog draft uses the candidate's full commit SHA. Structural validation
can check its YAML, but public reachability, publication, two-week maturity and the
upstream PR's CI cannot be claimed before the code is actually published and
submitted. The draft keeps those states explicit; see [CATALOG.md](CATALOG.md) and
[the official admission policy](https://github.com/NousResearch/hermes-agent/blob/5eb99eb2844b22ebb723711b8e6a0bbb80bb5f04/plugin-catalog/README.md).

No real Telegram message or model request was sent. This is not a fresh Telegram
client/live model acceptance run; [1.7.0 live evidence](ACCEPTANCE-1.7.0.md) is historical.
