# Hermes Telegram UX · Hermes Plugin

**1.9.0-catalog.1** · Public-API Telegram experience · [中文说明](README.zh-CN.md)

Natural task progress in one edited message, a `/tgux` home menu, user-sent follow-up requests and personal display preferences. Hermes owns steering, queues, `/stop`, approvals, final answers and files.

## Experience

- Progress uses public tool/model/approval events, elapsed time and observed retries. The `telegram_ux_update` tool supplies intentional public milestones; explicitly correlated subagents have a status summary.
- `/tgux` opens home, examples, native command shortcuts, help and settings. Scoped callbacks are bound to the initiating user, chat, topic and message; cards expire after one hour and after restart.
- Finished status cards offer details, dismiss and follow-up requests. Reply keyboards let users send requests through normal Hermes routing; no automatic injection or private command dispatch.
- Language, detail level, progress, reply statistics, status emoji, elapsed hints, conversation guidance and follow-ups are saved for each user/chat/topic through public plugin state. Changes apply from the next turn and never modify global settings.
- Final replies are unchanged by default. Optional statistics count only observed events, not billing. Closing a card does not cancel a task. Native reactions have separate Hermes settings.

## Install and upgrade

Requires a Telegram-enabled Hermes 0.21.3+ installation with the official messaging dependencies. The verified core revision is in [PUBLIC-API.md](docs/PUBLIC-API.md); compatibility with later versions is established by validation, not assumed.

Use an independently versioned `catalog-v*` release from [GitHub releases](https://github.com/pler1y/hermes-telegram-ux/releases). A development candidate may exist before its release page. The repository default `main` distributes Full, so always pin the Plugin release ref when using native Git installation. Follow the complete [installation and rollback instructions](README.zh-CN.md#安装发布包).

Do not enable Full and Plugin in the same Gateway. Stop the Gateway, back up the previous plugin, verify the release ZIP checksum, install it, then run `hermes plugins validate <plugin-directory>` and `hermes plugins enable hermes-telegram-ux-catalog`. Restart the Gateway and send `/tgux`.

To disable/remove, use `hermes plugins disable hermes-telegram-ux-catalog`, restart and check native chat, then use `hermes plugins remove hermes-telegram-ux-catalog`. Runtime callbacks/tasks are removed; personal preferences use the plugin-owned state directory. The plugin never writes the Hermes session database.

## Defaults and boundaries

Defaults live at `plugins.entries.hermes-telegram-ux-catalog.settings`: `language: zh`, `display: brief`, `progress: true`, `final_summary: false`, `emoji: true`, `wait_hint: true`, `conversation_style: true`, `followups: true`, `update_interval: 1.5`, `status_ttl: 600`. Users override display preferences through their own `/tgux` settings, from the next turn.

No network reply occurs at the pre-auth ingress hook. Status routing requires a single-use context ticket and matching execution identity; menu routing also requires the public authorized command path. Missing or reconstructed context falls back to native behavior. Cards summarize observed execution, not final delivery confirmation. Native streaming, interim messages and compression feedback remain native. Progress guidance depends on the model following instructions; no reasoning deltas or arbitrary tool results are copied.

Runtime uses public hooks, plugin state/tool registration and the Telegram SDK supplied by the official platform factory. No Hermes runtime imports, private access, host mutation, queue takeover or automatic continuation. Distribution is independent from official Catalog admission.

See [validation](docs/VALIDATION.md), [testing](docs/TESTING.md), [public API inventory](docs/PUBLIC-API.md), and [development progress](docs/PROGRESS.md).

MIT License.
