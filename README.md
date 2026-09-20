# Hermes Telegram UX

[中文说明](README.zh-CN.md)

Task-aware, temporary Telegram progress for Hermes. One status message explains what is happening while you wait, follows real tool actions and results, and is cleaned up when the turn ends. Install, enable, then chat normally.

**Hermes Telegram UX v2.1.0** uses the public Plugin API implementation as the only maintained product. Official version identity comes from the [v2.1.0 tag](https://github.com/pler1y/hermes-telegram-ux/tree/v2.1.0) and [GitHub Release](https://github.com/pler1y/hermes-telegram-ux/releases/tag/v2.1.0).

## What you see

The same message is edited as work advances. Real tool actions, results and voluntary public model milestones update the same message:

```text
🤔 Thinking…
🔎 Searching for official release information…
📊 Found 8 search results; reviewing the sources…
🕒 Comparing release dates across sources…
✍️ Preparing the final answer…
Hermes sends its native final answer → the temporary status is removed
```

- Actual tool events identify the action and task object.
- Recognized tool results supply search counts, returned weather fields, missing files and failures.
- Recovery appears only after a real subsequent attempt. Partial failures stay qualified.
- For substantial work, `telegram_ux_update` supplies concrete stages that tool events cannot express, such as comparing sources or checking anomalies.
- Ordinary model requests and elapsed time keep the last meaningful status unchanged. Simple answers need no milestone calls.
- One owned message, throttled edits, duplicate suppression and bounded cleanup.
- Automatic Chinese/English status language from the current message.

Specific milestones survive ordinary API activity; a new real tool action can replace them. No timer invents stages, and missing tool objects never fall back to repeating the full user request. See the [real model and Telegram acceptance summary](docs/LIVE-MILESTONE-ACCEPTANCE.md).

No completion cards, buttons, welcome pages, personal settings panels or `/tgux` command. Disable the plugin through Hermes when you do not need progress.

## Install v2.1.0

Requires **Hermes >= 0.21.0** with working Telegram. The minimum is based on the public Plugin API boundary; it is not a claim of full testing on every supported release. The verified baseline is **Hermes 0.21.3**, commit `3c3ab69abb9b08683b5eb15b4e2b8be1198c875f`. CI also checks current Hermes main on Python 3.11 and 3.12; see the result for the exact release commit you install.

The native installer accepts a **40-character commit SHA**, not a branch name, for `--ref`. Resolve the official tag to its commit (including annotated tags), compare that SHA with the Release notes, and install exactly that revision. If the tag is unavailable, stop; do not fall back to a moving branch:

```bash
TGUX_REPO="https://github.com/pler1y/hermes-telegram-ux.git"
TGUX_COMMIT="$(git ls-remote --exit-code "$TGUX_REPO" 'refs/tags/v2.1.0' 'refs/tags/v2.1.0^{}' | awk '$2 == "refs/tags/v2.1.0^{}" { peeled=$1 } $2 == "refs/tags/v2.1.0" { direct=$1 } END { print peeled ? peeled : direct }')"
test "${#TGUX_COMMIT}" -eq 40 || { echo "Release tag unavailable; stop here." >&2; exit 1; }
case "$TGUX_COMMIT" in *[!0-9a-fA-F]*) echo "Invalid release SHA; stop here." >&2; exit 1 ;; esac
printf '%s\n' "$TGUX_COMMIT"
hermes plugins install https://github.com/pler1y/hermes-telegram-ux.git --ref "$TGUX_COMMIT" --no-enable
hermes plugins validate "${HERMES_HOME:-$HOME/.hermes}/plugins/hermes-telegram-ux-catalog" --json
hermes plugins doctor "${HERMES_HOME:-$HOME/.hermes}/plugins/hermes-telegram-ux-catalog" --ci
hermes plugins enable hermes-telegram-ux-catalog
```

Restart your Gateway and send a normal task. Review any native scanner findings before accepting installation. Existing users should first follow [the migration guide](docs/MIGRATION-v2.md); an existing pinned installation requires an explicit replacement, and `--no-enable` does not disable an already-running plugin.

The internal ID **`hermes-telegram-ux-catalog` stays unchanged** to preserve installation/configuration identity. It is a historical compatibility identifier, not a separate product edition. [ID decision and source audit](docs/PLUGIN-ID.md).

A reproducible ZIP can also be built from the reviewed commit with `scripts/build_release.py --ref <40-character-SHA>`. It includes per-file hashes and `PROVENANCE.json`. Hermes does not directly install ZIP files; verified manual deployment and replacement are explained in the migration guide. Use the ZIP and checksums attached to the official v2.1.0 Release; see [release integrity](docs/RELEASE.md).

## Configuration

Default behavior requires no setup menu. Optional settings belong under `plugins.entries.hermes-telegram-ux-catalog.settings`:

```yaml
language: auto
update_interval: 1.5
status_ttl: 600
cleanup_delay: 1.0
```

- `language`: `auto`, `zh`, or `en`. Auto reads current message text, ignoring code, URLs and paths. Ambiguous numeric/media-only input falls back to Chinese. An existing explicit language setting is preserved on upgrade.
- `update_interval`: minimum edit interval, 1–30 seconds.
- `status_ttl`: display inactivity expiry, 30–3600 seconds; never cancels the Hermes task.
- `cleanup_delay`: cleanup window after turn completion, 0–5 seconds.

Restart after configuration changes. There is no per-user preference store or internal progress/emoji switch. Old menu preferences are ignored without deleting old user files.

## Responsibilities and boundaries

Hermes retains execution, sessions, context, approvals, `/stop`, interruptions, streaming, final answers, attachments and native delivery recovery. This plugin only observes public events and maintains its own progress message. It does not replace Hermes, modify core, monkey patch, transform final answers or consume hidden chain of thought.

Runtime code uses the standard library, official public plugin hooks/tool registration and the supplied public adapter. Routing uncertainty suppresses plugin output; it never guesses another user's chat or inspects private task state. Initial feedback follows a safely correlated public turn event, not pre-authentication ingress.

Agent lifecycle completion is not a Telegram delivery receipt, and some abnormal host termination paths may fall back to the configured status TTL for cleanup (default 600 seconds). Cleanup is bounded and best effort; deletion failure can leave a status, and slow native delivery can finish after cleanup. Long model requests retain the last public observation until new progress or display expiry. Public-API validation is not official Catalog admission.

## Legacy Full implementation

Full v1.8.3 and earlier used deep Hermes-internal integration and are no longer maintained. History is preserved at [legacy/full-1.8.3](https://github.com/pler1y/hermes-telegram-ux/tree/legacy/full-1.8.3) and [v1.8.3](https://github.com/pler1y/hermes-telegram-ux/tree/v1.8.3). These are historical references, not an alternative recommended installation. Do not enable Full and v2 in the same Gateway.

[Migration](docs/MIGRATION-v2.md) · [Changelog](CHANGELOG.md) · [v2 validation](https://github.com/pler1y/hermes-telegram-ux/blob/v2.0.0/docs/VALIDATION-v2.md) · [Historical live acceptance](https://github.com/pler1y/hermes-telegram-ux/blob/v2.0.0/docs/VALIDATION.md) · [Testing](https://github.com/pler1y/hermes-telegram-ux/blob/v2.1.0/docs/TESTING.md) · [Public API](docs/PUBLIC-API.md)

MIT License.
