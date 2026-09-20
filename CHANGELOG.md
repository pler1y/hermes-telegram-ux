# Changelog

## 2.0.0

This is a product convergence: the public Plugin API implementation becomes the only maintained Hermes Telegram UX. The behaviors below describe the change from the legacy Full/earlier menu-based product lines. Task intelligence and temporary-message behavior were already accepted at `c5b8aef94d1f096fbad9ad782b2ad312e9254d33`; this release preparation does not rewrite them.

### Added

- Task-aware Telegram progress tied to actual actions and task objects.
- Tool-result-grounded counts, returned data fields and file/read outcomes.
- Real failure and subsequent recovery feedback, including partial failures.
- Stateless automatic Chinese/English status language.
- Temporary progress cleanup with one owned message per ordinary turn.
- Official public Plugin API implementation.

### Removed

- Full private-runtime integration and Hermes monkey patches.
- Permanent completion cards and elapsed/statistics footers.
- Continue, Details, Settings, Close, welcome pages and legacy menus.
- `/tgux` UI and persistent personal preference system.
- Natural-language stop overrides and custom background-task cancellation/delivery filtering.

### Changed

- Hermes remains responsible for execution, stop, sessions, context, approvals, streaming, native final answers and attachments.
- One maintained product and one installation path replace parallel Full/Catalog editions.
- The public Plugin API implementation is the v2 mainline.
- Preserve both Git histories through a two-parent integration commit whose tree matches the accepted candidate.

### Compatibility

- Keep internal ID `hermes-telegram-ux-catalog`; the user-visible name is Hermes Telegram UX.
- Existing same-ID configuration and external plugin state remain in place. Retired menu preferences/settings are ignored, not deleted.
- An explicit language override remains effective; only absent values adopt `auto`.
- Pinned Git installs require an explicit reviewed new SHA. ZIP installs need complete replacement or same-ID Git reinstall, not `plugins update`.
- Full users must stop and disable/remove `hermes-interaction` using the original installation method before enabling v2. No Full fingerprint matching is required by v2.
- Verified Hermes baseline:0.21.3,`3c3ab69abb9b08683b5eb15b4e2b8be1198c875f`. See [migration](docs/MIGRATION-v2.md), [ID audit](docs/PLUGIN-ID.md) and [candidate validation history](https://github.com/pler1y/hermes-telegram-ux/blob/v2.0.0/docs/VALIDATION-v2.md).

## Historical Full 1.8.3

Legacy Full implementation / historical release. No longer maintained. Existing tag `v1.8.3` is unchanged at `1ed97bfbe9071a179e1a2b8fcc260a573ecc6364`; `legacy/full-1.8.3` preserves the former main merge `3b2175199d8d9dbafaa39e13c1f5dafd4bf0cfcb`. Both trees match.

Earlier validation records retain their original versions and results in [VALIDATION.md](https://github.com/pler1y/hermes-telegram-ux/blob/v2.0.0/docs/VALIDATION.md).
