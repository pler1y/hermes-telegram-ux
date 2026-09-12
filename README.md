# Hermes Telegram UX

Timely replies, clear progress and room for new instructions — Hermes on Telegram.

Get a quick acknowledgement, follow live task progress, add instructions along the way, and receive complete answers and files in your chat.

[简体中文](README.zh-CN.md) · [Download](https://github.com/pler1y/hermes-telegram-ux/releases/latest) · [Installation guide](docs/INSTALLATION.en.md) · [Report an issue](https://github.com/pler1y/hermes-telegram-ux/issues)

**Version 1.8.1** adds safer plugin loading/unloading, bot-specific follow-up buttons and formatting-tolerant core checks. [Official catalog PR #108887](https://github.com/NousResearch/hermes-agent/pull/108887) is submitted; inclusion is pending maintainer review and release maturity. See [native installation](docs/NATIVE-INSTALL.md) and [submission status](docs/CATALOG.md).

## What it feels like

This example illustrates the conversation flow. Progress rows update the same bubble; model-generated wording varies with the task.

| Moment | In your Telegram chat |
|---|---|
| Your request | Make a restocking sheet for the next 7 days. |
| Immediate reply | Let me take a look 👀 |
| Work begins | 📄 I'll check stock and daily usage to find what needs restocking. |
| Your update | Make it 10 days and include incoming stock. |
| Receipt | Got it — thanks for the update. |
| Adjustment | 🧮 I'll calculate 10 days of demand and subtract incoming stock. |
| Delivery | A complete answer and the generated restocking CSV. |

If a new message must wait, its receipt says it will be handled after the current task. Say “stop the task” to request a stop; earlier actions are not undone.

Send `/start` to find information, read a link or file, or write something. Running tasks, conversations and usage are under “More options”. The [1.7.0 live acceptance record](docs/ACCEPTANCE-1.7.0.md) lists verified scenarios and their limits.

## Features

- **Quick feedback** — a short, natural acknowledgement as your message arrives.
- **Live progress** — updates in one message, with fitting emoji and less notification clutter.
- **Visible internal work** — see when Hermes is tidying up the conversation context.
- **Change direction** — add details while a task is running.
- **Stop naturally** — say “stop the task” to stop current or associated background work.
- **Complete delivery** — receive full answers, generated files and useful follow-up buttons.
- **Chinese and English editions** — choose your interface language when installing.

## Install

You'll need a working Telegram bot and model login. This release checks the interfaces of **Hermes 0.21.0 (`b499ab11fe8b`) or 0.21.2 (`a84a2223f82c`, `436ec489854b`)**. Other commits are accepted only when all guarded files match one baseline by bytes or complete Python syntax; see [compatibility](docs/COMPATIBILITY.md). For installation through `hermes plugins install`, follow [native installation](docs/NATIVE-INSTALL.md).

For ZIP installation, choose the English `-en.zip` or Chinese `-zh.zip` and its checksum from the matching [release](https://github.com/pler1y/hermes-telegram-ux/releases). Verify and extract the archive. Run this read-only compatibility check from the extracted directory as the account that owns Hermes, adjusting the paths for your installation:

```bash
HERMES_HOME="$HOME/.hermes"
HERMES_CORE="$HERMES_HOME/hermes-agent"
HERMES_PYTHON="$HERMES_CORE/venv/bin/python"
export PYTHONPATH="$HERMES_CORE"

"$HERMES_PYTHON" install.py check --hermes-core "$HERMES_CORE"
```

After the check passes, finish active tasks and stop your Gateway. Then install:

```bash
"$HERMES_PYTHON" install.py install --hermes-home "$HERMES_HOME" --hermes-core "$HERMES_CORE"
```

Restart the same Gateway, then send `/new` and `/start` in Telegram. See the [installation guide](docs/INSTALLATION.en.md) for upgrades, language settings and removal.

## Use it

Send a question, link or file as usual. During a task, keep typing to add a detail or change the request.

| Action | Example |
|---|---|
| Add a requirement | “Use a 10-day forecast and include incoming stock.” |
| Stop a task | “Stop the task.” |
| Open the menu | `/start` or “show menu” |

## Documentation

- [Install, upgrade and uninstall](docs/INSTALLATION.en.md)
- [中文安装指南](docs/INSTALLATION.md) · [从零安装](docs/FRESH-INSTALL.md)
- [Configuration](docs/CONFIGURATION.md) · [Compatibility](docs/COMPATIBILITY.md)
- [Development and testing](docs/TESTING.md) · [Release builds](docs/RELEASE.md)
- [Security](SECURITY.md)

## License

[MIT](LICENSE). See [NOTICE.md](NOTICE.md) for dependency and source information.
