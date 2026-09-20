# Hermes Telegram UX

[中文说明](README.zh-CN.md)

One temporary Telegram message shows what Hermes is doing for your current task. It appears when work starts, follows actual tool activity and results, and is removed when the turn ends. Install, enable, then send your usual messages.

This public-plugin implementation is the project's only future maintained product. The former Full implementation is historical reference; its Git history and tags remain intact. This checkout is an unpublished convergence candidate. Repository/default-branch changes and a new release have not been performed. The existing plugin identifier `hermes-telegram-ux-catalog` is retained for installation compatibility, not a second edition.

## What it does

- Keeps one owned status message, editing the same message ID with throttling and deduplication.
- Shows the action and task object, such as searching news, inspecting cleanup code or reading weather data.
- Reports recognized evidence: actual search-result counts, returned data fields, missing files, failures and real subsequent attempts. Raw queries, paths, commands and hidden reasoning are not displayed.
- Changes completed tool results into task-related synthesis during a subsequent model request. It does not invent new stages to animate a long wait.
- Deletes its temporary status after completion, reset or unload. Hermes keeps control of execution, approvals, `/stop`, streaming, answers, attachments and native delivery recovery.

There are no completion cards, buttons, welcome pages, settings panels or `/tgux` command. Disabling the plugin uses Hermes' native plugin management. Optional public progress notes work alongside automatic tool observations; model participation is not required.

## Install and upgrade

Requires a Telegram-enabled Hermes installation. The verified official baseline is Hermes **0.21.3**, commit `3c3ab69abb9b08683b5eb15b4e2b8be1198c875f`; later-version compatibility requires validation. No extra runtime Python dependencies or Hermes core changes are needed.

Use a reviewed ZIP built from the intended commit, verify its SHA256 and `PROVENANCE.json`, then place its contents in `${HERMES_HOME:-$HOME/.hermes}/plugins/hermes-telegram-ux-catalog`. Stop the Gateway and back up an existing plugin directory before replacing it. Do not enable the historical Full plugin in the same Gateway.

```bash
hermes plugins validate /absolute/path/to/plugins/hermes-telegram-ux-catalog --json
hermes plugins doctor /absolute/path/to/plugins/hermes-telegram-ux-catalog --ci
hermes plugins enable hermes-telegram-ux-catalog
```

Restart the Gateway and send a normal task. There is no setup menu. This unpublished candidate is not available from a new release tag; do not install the repository's old default branch expecting this code. See [the repository transition plan](docs/CONVERGENCE.md).

For removal, run `hermes plugins disable hermes-telegram-ux-catalog`, restart and verify native chat, then `hermes plugins remove hermes-telegram-ux-catalog` if desired. This version does not read or write personal preference state. Old plugin-owned preference data may remain on disk but is ignored; no migration or destructive cleanup is required.

## Configuration

Defaults work without settings. Optional installation settings live under `plugins.entries.hermes-telegram-ux-catalog.settings`:

```yaml
language: auto
update_interval: 1.5
status_ttl: 600
cleanup_delay: 1.0
```

`language` accepts `auto`, `zh`, `en`. Auto selects Chinese for Chinese text and English for English text in the current request, ignoring code blocks, URLs and paths. Numeric/media-only input falls back to Chinese; this is a bounded two-language heuristic, not arbitrary language detection. A fixed override is useful for mixed-language tasks. There is no per-user/chat/topic preference store, progress switch or emoji switch.

The remaining settings are operator controls for edit throttling (1–30s), display inactivity expiry (30–3600s), and cleanup delay (0–5s). Defaults and behavior are unchanged. Expiry ends the plugin's display, never the Hermes task. Restart after changing settings.

## Boundaries

Routing requires a matching, single-use ingress ticket and public turn identity. Uncertain routing skips plugin output and preserves native behavior. Authentication, user/chat/topic isolation, late-event protection and owned-message cleanup remain essential infrastructure.

Agent completion is not a Telegram final-delivery receipt. Cleanup is bounded and best effort: failed deletion can leave a status, and slow native delivery can finish after cleanup. Uncertain initial sends are not retried; failed edits do not create replacement bubbles. Native messages may appear independently.

Runtime code uses Python's standard library, public plugin hooks/tool registration and the supplied public adapter. No Telegram SDK callbacks, Hermes private imports, monkey patches, final-answer transformers or execution takeover are used. Public-API validation does not imply official Catalog admission.

[Validation](docs/VALIDATION.md) · [Testing](docs/TESTING.md) · [Public API inventory](docs/PUBLIC-API.md) · [Acceptance](docs/ACCEPTANCE.md) · [Convergence and Full audit](docs/CONVERGENCE.md)

MIT License.
