# Catalog-safe development

Current goal: task-aware progress in one temporary Telegram bubble, followed by cleanup. Hermes retains execution, task control, approvals, final-answer and attachment delivery. Full remains on its original main checkout, including pre-existing untracked research.

## Progress Intelligence development — 2026-09-20

- Baseline checkpoint: `31b3a5f` preserves the temporary-bubble lifecycle that passed real Telegram cleanup acceptance. B–E task intelligence was only partial at that baseline.
- Current changes preserve the full task purpose, remove raw search syntax, interpret bounded structural result evidence, keep errors/results above generic model activity, and age completed results into task-specific synthesis only after a subsequent public model request.
- Normalized `assistant_tool_call_count` is used instead of assuming a dict response; same-ID API retries retain their attempt order. No stream observers, middleware, final transformers, private APIs or task control have been added.
- A two-second display check can update synthesis wording without refreshing execution TTL or calling Hermes. The normal one-message/edit/delete lifecycle and independent `/tgux` menu remain in place.
- Final automated checks: 163 unit + 6 host contract cases, boundary guard, official validate (10/10, zero warnings) and doctor passed. Final real Telegram A–E, same-batch mixed-result and sequential recovery acceptance passed; every ordinary status was edited in place and deleted after its native answer. Runtime SHA256: `4998be75d2a6e6ce839795cf606c786a58f516ac6fd194cbda043172b0830395`.
- The final runtime remains deployed to the dedicated test Bot. Temporary public observation was removed, exact original config restored, and post-restoration A smoke passed. All 13,490 tracked core files remain unchanged. Full timelines/evidence and the nonblocking wording limitation are recorded in `VALIDATION.md`. No publication is authorized.

## Temporary-progress implementation baseline — 2026-09-20

- Channel: `catalog-safe` in shared `pler1y/hermes-telegram-ux`; independent `catalog-v*` releases and Plugin-only packages. Work continues on the existing candidate branch. Manifest version remains `1.9.0-catalog.1`; these changes do not imply a new release.
- Target: official Hermes 0.21.3 `3c3ab69abb9b08683b5eb15b4e2b8be1198c875f`, the fixed 2026-09-16 main snapshot.
- Initial feedback: schedule in `pre_llm_call` immediately after safe route correlation, before task extraction. No earlier ordinary-message public hook combines authentication and required route data. Pre-auth ingress records only a one-use ticket.
- Progress: short action/subject labels from current public user message and observed tool arguments; narrowly recognized facts from structured results. Keep `telegram_ux_update` for public action notes, distinguish model claims from verified evidence, and use safe fallbacks.
- Lifecycle: one owned message, deduplicated/coalesced edits, terminal protection and bounded cleanup. Normal completion becomes finalizing then deletion. `cleanup_delay` defaults to 1 second, clamped to 0–5 seconds. Agent completion is not a Telegram-delivery receipt.
- UI: no permanent completion cards, elapsed hints, statistics or ordinary-task buttons. Independent `/tgux` keeps language/progress/emoji preferences and native command shortcuts. Legacy display/style/statistics/follow-up preferences are ignored.
- API boundary: retain 17 public hooks, replacing `transform_llm_output` with `post_llm_call`. No stream hooks or middleware: independently queued streams do not identify final delivery, and observational UI does not need request mutation. Guidance concerns progress, not general answer style.
- Verified locally on Python 3.12.13 against the fixed core: 109 unit/UI/async/boundary tests and six real PluginManager contract tests passed; official validate passed all ten checks with zero warnings; doctor and the standalone boundary guard passed. Current working-tree enabled/disabled discovery probes and `git diff --check` also passed. New dedicated suites cover 33 task/evidence/ordering cases and 20 temporary-message races; an integrated weather fixture verifies initial feedback, task-specific edits, missing-humidity protection and deletion of the same message.
- Verification limits: transport is synthetic, including the real-host contract suite. No new live Telegram/model acceptance, remote deployment, GitHub push, release packaging or multi-version CI was performed. Native Git/ZIP release harnesses read committed objects and were not used to claim validation of uncommitted changes. Remaining live scenarios and native file/approval/stop checks are listed in `ACCEPTANCE.md`.

## Historical evidence

- Earlier `1.9.0-catalog.1` runtime `d0ff0a83ab4136d4b5279237b296ba95ff9c6299`: 54 unit/boundary and six host contracts, official validate/doctor, Git/ZIP lifecycle, fixed/current-core Python 3.11/3.12 CI, and 14 private Telegram checks were recorded as passed. Saved records show this runtime installed on the test bot, with PR #5 targeting `catalog-safe` as a draft at that time. Its completion-card/button behavior is not current acceptance. This is saved evidence, not a fresh deployment check.
- Previous `1.8.3-catalog.1` runtime `a4f8325f187df210bc7f0b1e583dbdc4b541a834`: 33 unit/transport/boundary and four host contracts, official validate/doctor, native Git/ZIP lifecycle, unchanged core hashes and package provenance were recorded. Thirteen live cases covered pure replies, tools, attachments, interim text, failures, tool/approval timeouts, approve/deny, native stop, recovery and disabled baseline. See `VALIDATION.md` for markers/limits.
- The dedicated test installation used an isolated official core; Full installation/configuration were retained for rollback and the temporary approval fixture was removed according to the historical record.
- Release archives contain only Catalog runtime/documentation, with exact source SHA and per-file hashes in `PROVENANCE.json`. Independent GitHub distribution and validation do not imply official Plugin Catalog admission.
