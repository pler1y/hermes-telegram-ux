# Catalog-safe development

Goal: a separate, useful Telegram plugin using public Hermes extension points. Full remains on its original main checkout, including pre-existing untracked research.

- Branch: `feat/catalog-safe`, isolated checkout based on Full `8e38243614c1ecc37e0cdcbd4e6e223f920ec895`.
- Target: official Hermes 0.21.3 `3c3ab69abb9b08683b5eb15b4e2b8be1198c875f` (2026-09-16 main snapshot).
- Implementation: public hooks, adapter send/edit/delete, supervised cleanup, bounded per-turn state, native approvals/interim/final delivery, optional counts, Chinese/English help.
- Local checks completed so far: 29 unit/transport tests; 4 real host contract tests; official validate passes with zero warnings; AST boundary check passes.
- User authorized use of the existing dedicated Telegram test bot. Its existing Full environment is on an older core, so live acceptance requires an isolated current-core installation and reversible test-service switch.
- Remaining: packaging/clean lifecycle and CI, live Telegram cases, final evidence and local review commits. No remote publication or PR updates authorized.
