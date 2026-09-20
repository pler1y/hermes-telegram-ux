# Catalog-safe development

Goal: a separate, useful Telegram plugin using public Hermes extension points. Full remains on its original main checkout, including pre-existing untracked research.

- Channel: `catalog-safe` in the shared `pler1y/hermes-telegram-ux` repository; independent `catalog-v*` releases and Plugin-only packages. Full stays on `main`.
- Target: official Hermes 0.21.3 `3c3ab69abb9b08683b5eb15b4e2b8be1198c875f` (2026-09-16 main snapshot).
- Implementation: public hooks, adapter send/edit/delete, supervised cleanup, bounded per-turn state, native approvals/interim/final delivery, optional counts, Chinese/English help.
- Completed: 33 unit/transport/boundary tests; 4 real host contract tests; official validate (10 checks, zero warnings) and doctor; native Git and ZIP install/enable/disable/remove; unchanged core hashes; package allowlist and provenance.
- Completed live: 13 recorded cases covering pure replies, tools, attachment, interim, failure, tool/approval timeouts, approve/deny, native stop, recovery and plugin-disabled baseline. See `VALIDATION.md` for exact markers and limits.
- Runtime tested at `a4f8325f187df210bc7f0b1e583dbdc4b541a834`. The dedicated bot uses an isolated official current-core snapshot. The original Full installation/config remain available for rollback; the temporary approval fixture has been removed.
- Release ZIP includes only the Catalog runtime and its documentation. The final source SHA is recorded by the build in `PROVENANCE.json`; local delivery evidence and a PR draft are kept with the project development documents.
- GitHub releases use the independent `catalog-v*` channel; each release page records its source SHA, package checksums and remote CI. Remaining external work is official Catalog re-review and maintainer acceptance. GitHub distribution does not imply Catalog admission.
