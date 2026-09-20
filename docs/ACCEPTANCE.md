# Catalog-safe live acceptance

Use an isolated Telegram test bot and a fixed official Hermes core. Record exact source/artifact hashes and restore the previous service if setup or delivery fails. Never treat synthetic hook tests as real Telegram acceptance.

| # | Task | Check |
|---|---|---|
| 1 | Pure conversation with an exact marker | Model reply arrives; no unnecessary count footer |
| 2 | One terminal calculation | Natural tool/API status, correct answer, optional counts in details |
| 3 | Read two test files then summarize | Multiple tool transitions; original answer preserved |
| 4 | Generate a small CSV in the test directory | File delivered by native Hermes |
| 5 | Read a deliberately absent test file | Honest failure state; final explanation survives |
| 6 | A bounded foreground wait | Status remains visible during tool execution |
| 7 | Prompted approval on an isolated fixture | Native buttons; waiting status; approve once |
| 8 | Deny a fixture approval | Denial status; forbidden fixture action does not execute |
| 9 | Time-limited fixture task | Tool timeout/failure reflected without blocking later work |
| 10 | Native `/stop` during a wait, then recovery | Native interruption; next conversation works |
| 11 | Disable plugin and send a pure reply | Native baseline still works |

Additional automated cases cover rate-limits, transport errors, cross-topic concurrent routes, missing context, duplicate/late events, session reset and unload. Group/topic and multi-profile live tests must be recorded separately if performed. Human product acceptance (“worth installing”) remains the maintainer's judgment after trying the candidate.

Actual results belong in `VALIDATION.md` after execution. There are no Full screenshots or mislabeled mockups in this distribution.

For reproducible human-approval cases, the source checkout includes
`tests/fixtures/approval_gate`, a separate policy plugin that requests native
approval for harmless marked `printf` commands. This exercises the real Gateway,
approval buttons and outcome hooks without depending on shell-risk heuristics.
Remove the fixture after testing; it is excluded from the release archive.

## 1.9 experience scenarios

Open `/tgux`; test home/help/settings navigation, language switching, per-user display preferences, native command reply keyboards, optional final statistics, details and close. Run a bounded calculation and deliver a small CSV, then select a suggested follow-up request. Check that every edited status retains its controls, closing a live card does not stop work, and native `/stop` still allows a later conversation. Download the generated CSV and check its contents, not only the attachment name. Native approval automation in the maintainer harness may approve once only when the entire command exactly matches a previously reviewed bounded test fixture; never approve arbitrary model-generated commands.
