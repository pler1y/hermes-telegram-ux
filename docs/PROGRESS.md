# v2.1.0 release handoff

The dynamic progress implementation is complete. It combines real tool activity/results with voluntary public milestones, preserves specific stages through ordinary API activity, and keeps native answers and task control unchanged. Registration remains 1 tool / 16 hooks / 0 middleware / 0 commands.

Development acceptance and its limits are summarized in [LIVE-MILESTONE-ACCEPTANCE.md](LIVE-MILESTONE-ACCEPTANCE.md). The remaining nonblocking P2 is TTL cleanup after abnormal host termination without an end hook. No further feature iteration is planned for this release.

Release preparation sets version 2.1.0 and the public API minimum Hermes 0.21.0, restores temporary test observation configuration, and uses the existing gate followed by one complex and one simple final-commit smoke. Exact publication, CI, package and smoke identities belong in the [Release notes](https://github.com/pler1y/hermes-telegram-ux/releases/tag/v2.1.0). The existing Catalog PR #108887 must pin that same final commit. See [RELEASE.md](RELEASE.md) for integrity and migration instructions.
