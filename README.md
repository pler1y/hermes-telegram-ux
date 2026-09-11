# Hermes Telegram UX

A Telegram interaction plugin for Hermes.

Get a quick acknowledgement, follow live task progress, add instructions along the way, and receive complete answers and files in your chat.

[简体中文](README.zh-CN.md) · [Download](https://github.com/pler1y/hermes-telegram-ux/releases/latest) · [Installation guide](docs/INSTALLATION.en.md) · [Report an issue](https://github.com/pler1y/hermes-telegram-ux/issues)

## Features

- **Quick feedback** — a short, natural acknowledgement as your message arrives.
- **Live progress** — updates in one message, with fitting emoji and less notification clutter.
- **Visible internal work** — see when Hermes is tidying up the conversation context.
- **Change direction** — add details while a task is running.
- **Stop naturally** — say “stop the task” to stop current or associated background work.
- **Complete delivery** — receive full answers, generated files and useful follow-up buttons.
- **Chinese and English editions** — choose your interface language when installing.

## Install

You'll need Hermes 0.21.0 on the [supported core revision](docs/COMPATIBILITY.md), with a working Telegram bot and model login.

Download the English `-en.zip` or Chinese `-zh.zip` and its checksum from [Releases](https://github.com/pler1y/hermes-telegram-ux/releases/latest). Verify and extract the archive, finish active tasks, and stop your Gateway. Run this from the extracted directory as the account that owns Hermes, adjusting the paths for your installation:

```bash
HERMES_HOME="$HOME/.hermes"
HERMES_CORE="$HERMES_HOME/hermes-agent"
HERMES_PYTHON="$HERMES_CORE/venv/bin/python"
export PYTHONPATH="$HERMES_CORE"

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
