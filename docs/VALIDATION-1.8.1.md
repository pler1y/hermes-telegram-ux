# Version 1.8.1 validation — 2026-09-12

Eight additional regression cases bring the plugin suite to **164 tests, zero
failures/errors/skips**, on each supported environment:

| Environment | Plugin suite | Native lifecycle | Admission validator | English/Chinese ZIP lifecycle |
|---|---|---|---|---|
| 0.21.0 `b499ab11fe8b` | 164 passed | Passed | Not available in this core | Passed |
| 0.21.2 `a84a2223f82c` | 164 passed | Passed | Passed | Passed |
| 0.21.2 `436ec489854b` | 164 passed | Passed | Passed | Passed |
| 0.21.2 `044a77b3b6af` | 164 passed | Passed | Passed | Passed |

Before the fixes, tests reproduced wrong-bot button delivery, handlers left behind
after partial wiring, replacement of a later plugin wrapper during unload,
formatting-only core rejection and global notification settings being overwritten.
Additional coverage checks unloaded wrappers forwarding to native behavior,
re-wiring without duplicate handlers, stream consumer collection, cross-bot
callback rejection without consuming the valid menu, and retiring older settings
without overwriting a user's later edits. Upgrade dry-runs list those restored paths before any write.

The real-core compatibility check copies guarded files into a disposable directory:
comment-only changes pass; adding executable syntax fails. The full Python syntax
tree remains guarded, including scope, literal values, defaults, decorators and
docstrings. CI runs this check on Python 3.11 and 3.12. No checked module is imported
or executed by the compatibility check.

Native validation exercises Git install, enable, discovery, actual Telegram
handler wiring/unwiring, configure/restore and removal. Git/catalog metadata is
preserved. Native scanning stays enabled and reports caution for documented
service/subprocess operations. No model call or Telegram network request is made.

Internal gateway interfaces are still used. These changes do not claim arbitrary
future-core compatibility, compatibility with every third-party plugin, or a new
full Telegram/model acceptance run. Historical live evidence remains in
[ACCEPTANCE-1.7.0.md](ACCEPTANCE-1.7.0.md).
