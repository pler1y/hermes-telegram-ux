# Catalog-safe live acceptance

Use an isolated Telegram test bot and a fixed official Hermes core. Record exact source/artifact hashes and restore the previous service if setup or delivery fails. Never treat synthetic hook tests as real Telegram acceptance.

| # | Task | Check |
|---|---|---|
| 1 | Pure conversation with an exact marker | Model reply arrives; no unnecessary count footer |
| 2 | One terminal calculation | Tool/API status, correct answer and count |
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
