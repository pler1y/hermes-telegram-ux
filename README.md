# Hermes Telegram UX · Catalog-safe

**1.8.3-catalog.1 — local, unpublished candidate.** [中文使用说明](README.zh-CN.md)

See tool execution, model requests and approval status in Telegram through public Hermes plugin events. A separate status message is edited as events arrive. Hermes continues to deliver interim messages, approvals, final answers and files. Text answers that used tools can include a short record of observed calls.

## Scope versus Full

| Feature | Catalog-safe | Full 1.8.3-rc.1 |
|---|---|---|
| Tool / API / approval events | Public-hook status panel | Integrated progress |
| Interim messages | Native; panel shows that an update arrived | Integrated narration |
| Final output | Original text plus optional counts | Integrated delivery |
| Immediate intake receipt | Starts at execution, not ingress | Supported |
| Busy acknowledgement / steering | Native Hermes | Custom UX |
| Stop | Native `/stop`; observe actual turn end | Custom lifecycle / phrases |
| Background completion groups | Native Hermes | Custom rendering |
| One bubble across the whole lifecycle | Not promised | Supported |
| Custom menu / action buttons | `/tgux` help only | Supported |
| Private imports / method replacement | None | Guarded integration |

Live display requires a single-use, 60-second ingress ticket propagated through Python context plus matching public sender/profile identity. Missing/lost context, ambiguous identity, reconnects, subagents and background starts fall back to native behavior. Queue restarts may lose the ticket. No session-key parsing, internal polling or gateway mutation is used. Thread metadata and reply anchors are preserved. See the [public API inventory](docs/PUBLIC-API.md).

The plugin stores bounded IDs, counts and status categories in memory. It does not copy prompts, tool results, approval commands or interim text to status messages. Counts describe observed events, not billing. Turn-end status is not a delivery receipt. Finished panels remain visible.

## Install the delivered artifact

Requires a working Hermes 0.21.3+ Telegram setup and Python 3.11–3.13. Stop active work and the target Gateway first. Use one edition per Gateway; do not enable Full alongside this edition.

In the delivery directory, verify the SHA256 file against trusted delivery evidence:

```bash
shasum -a 256 -c hermes-telegram-ux-catalog-1.8.3-catalog.1.zip.sha256
CATALOG_HOME="${HERMES_HOME:-$HOME/.hermes}"
CATALOG_DIR="$CATALOG_HOME/plugins/hermes-telegram-ux-catalog"
test ! -e "$CATALOG_DIR" && mkdir -p "$CATALOG_DIR" && \
  unzip -q hermes-telegram-ux-catalog-1.8.3-catalog.1.zip -d "$CATALOG_DIR"
hermes plugins validate "$CATALOG_DIR"
hermes plugins enable hermes-telegram-ux-catalog
```

Restart the same Gateway, then send `/tgux`. `PROVENANCE.json` records the complete source SHA and per-file hashes. No additional Python packages, custom installer or core edits are required.

Native Git installation is also supported: `hermes plugins install file:///absolute/path/to/catalog-safe-checkout --ref FULL_40_CHARACTER_REVIEWED_COMMIT --no-enable`, followed by validation and enablement. Substitute the reviewed local source path and full commit from the delivery report. The candidate is not published: do not install the repository's default branch, which remains Full. Do not run an unpinned `plugins update` against that branch.

## Configuration and removal

Merge settings into `plugins.entries.hermes-telegram-ux-catalog.settings` and restart the Gateway:

| Key | Default | Meaning |
|---|---|---|
| `language` | `zh` | `zh` or `en` |
| `progress` | `true` | Show correlated live panels |
| `final_summary` | `true` | Append counts to text replies with tool activity |
| `update_interval` | `1.5` | Minimum edit interval, 1–30 seconds |
| `status_ttl` | `600` | Idle status expiry, 30–3600 seconds |

Expiry retires the status panel; it does not cancel the task. Initial send failures are not retried, avoiding duplicate messages after ambiguous network failures. Native progress/streaming settings remain operator-controlled. Streamed final annotation visibility depends on the native delivery path; no streaming messages are intercepted.

Run `hermes plugins disable hermes-telegram-ux-catalog` and restart to use native Telegram behavior. Run `hermes plugins remove hermes-telegram-ux-catalog` to remove the directory. For upgrades, stop the Gateway, back up the installed directory, verify the new artifact checksum and replace the directory before validating and enabling it. Restore the backup to roll back.

## Development

[Testing](docs/TESTING.md) · [Acceptance scenarios](docs/ACCEPTANCE.md) · [Progress](docs/PROGRESS.md) · [API contract and fallback rules](docs/PUBLIC-API.md)

CI validates the official contract and clean installation on the fixed baseline and current main. Runtime has no source fingerprint gate. This is not yet an accepted Catalog listing; maintainer review and release maturity remain separate requirements.

MIT License.
