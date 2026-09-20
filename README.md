# Hermes Telegram UX · Hermes Plugin

**1.9.0-catalog.1** · Public-API Telegram experience · [中文说明](README.zh-CN.md)

Task-aware progress in one temporary Telegram message. The message follows the work and is cleaned up when the turn ends. Hermes owns steering, queues, `/stop`, approvals, streaming, final answers and files.

This checkout contains an unreleased revision of the candidate. Earlier deployment and validation records describe their recorded source commits, not the current working tree.

## Experience

- Initial feedback is scheduled at the earliest reliably correlated public turn hook, before task-label processing. Later updates edit the same message and are deduplicated and throttled.
- Public tool names and selected arguments identify the actual action and its subject. Recognized structured results can add verified facts, such as a search-result count or available weather fields. Unknown formats use a safe fallback.
- `telegram_ux_update` accepts short, explicitly public progress notes. A model-supplied note is not independent proof that a tool succeeded. Hidden reasoning and raw tool output are not displayed.
- Status stays concise, normally one line. Ordinary status messages have no elapsed timer, statistics, completion card or inline controls.
- At normal completion the bubble enters finalizing, waits a short configurable cleanup window, and is deleted through the public adapter. Cleanup failure never changes the native answer; a failed deletion can leave a message behind.
- `/tgux` remains an independent menu for help, examples, native command shortcuts and three preferences: language, progress and emoji. User/chat/topic preferences apply from the next turn. There is no per-task settings, details, dismiss or follow-up button.

## Install and upgrade

Requires a Telegram-enabled Hermes 0.21.3+ installation with the official messaging dependencies. The verified core revision is in [PUBLIC-API.md](docs/PUBLIC-API.md); compatibility with later versions is established by validation, not assumed.

Use an independently versioned `catalog-v*` release from [GitHub releases](https://github.com/pler1y/hermes-telegram-ux/releases). A development candidate may exist before its release page. The repository default `main` distributes Full, so always pin the Plugin release ref when using native Git installation. Follow the complete [installation and rollback instructions](README.zh-CN.md#安装发布包).

Do not enable Full and Plugin in the same Gateway. Stop the Gateway, back up the previous plugin, verify the release ZIP checksum, install it, then run `hermes plugins validate <plugin-directory>` and `hermes plugins enable hermes-telegram-ux-catalog`. Restart the Gateway and send `/tgux`.

To disable/remove, use `hermes plugins disable hermes-telegram-ux-catalog`, restart and check native chat, then use `hermes plugins remove hermes-telegram-ux-catalog`. Runtime callbacks/tasks are removed; personal preferences use the plugin-owned state directory. The plugin never writes the Hermes session database.

## Defaults and boundaries

Defaults live at `plugins.entries.hermes-telegram-ux-catalog.settings`: `language: zh`, `progress: true`, `emoji: true`, `update_interval: 1.5`, `status_ttl: 600`, `cleanup_delay: 1.0`. `cleanup_delay` is clamped to 0–5 seconds. Legacy detail, reply-statistics, elapsed-hint, conversation-style and follow-up preferences are ignored. Final answers are never rewritten or annotated.

No network reply occurs at the pre-auth ingress hook. The checked public API has no ordinary-message hook that combines post-authentication timing with a reliable route before `pre_llm_call`. Initial-feedback delay therefore remains a public-lifecycle limitation. Status routing requires a single-use context ticket and matching execution identity; menu routing also requires the public authorized command path. Missing or reconstructed context falls back to native behavior.

`on_session_end` is an Agent completion event, not confirmation that Telegram received the final answer. The short cleanup window is best-effort presentation timing; a slow native delivery can finish after the bubble disappears. Unknown initial-send outcomes are never retried, and failed edits never create a replacement bubble. Cleanup attempts are bounded. Native streaming, interim messages and compression feedback remain native and can have their own visible messages.

Runtime uses public hooks, plugin state/tool registration and the Telegram SDK supplied by the official platform factory. No Hermes runtime imports, private access, host mutation, queue takeover or automatic continuation. Distribution is independent from official Catalog admission.

See [historical validation](docs/VALIDATION.md), [testing](docs/TESTING.md), [public API inventory](docs/PUBLIC-API.md), [acceptance criteria](docs/ACCEPTANCE.md), and [development progress](docs/PROGRESS.md).

MIT License.
