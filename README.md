<div align="center">

# Hermes Telegram UX

**Instant feedback. Live progress. A conversation you can steer.**

A Telegram interaction plugin for [Hermes Agent](https://github.com/NousResearch/hermes-agent).

[![Release](https://img.shields.io/github/v/release/pler1y/hermes-telegram-ux)](https://github.com/pler1y/hermes-telegram-ux/releases/latest)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

[Quick start](#quick-start) · [Usage](#usage) · [Documentation](#documentation) · [简体中文](README.zh-CN.md)

</div>

---

Local development candidate: **1.8.3-rc.1** (based on 1.8.2). See [candidate validation](docs/VALIDATION-1.8.3-rc.1.md) and [catalog readiness](docs/CATALOG.md). The commands below still pin the published 1.8.2 release.

Keep working with Hermes without wondering whether your message arrived. Get an immediate acknowledgement, follow progress in a single message, and add instructions while the task is running. Answers and generated files arrive in the same chat.

## Features

- **Immediate feedback** — “🤔 Thinking…” appears as an ordinary request arrives, without waiting for the model.
- **One progress message** — task updates share a bubble instead of filling the chat with status messages.
- **Mid-task instructions** — add a requirement or change direction; receipts distinguish updates from queued requests.
- **Natural stop requests** — say “stop the task” or “stop please” to enter Hermes' stop flow.
- **Answers and files** — receive complete replies, generated files and follow-up actions in Telegram.
- **Two interface languages** — choose English or Chinese during setup.

## In conversation

An illustrative flow; progress wording is generated for each task.

> **You** · Make a restocking sheet for the next 7 days.<br>
> **Hermes** · 🤔 Thinking…<br>
> **Progress** · 📄 I'll check stock and daily usage.<br>
> **You** · Make it 10 days and include incoming stock.<br>
> **Hermes** · Got it — thanks for the update.<br>
> **Progress** · 🧮 I'll calculate 10 days of demand, including incoming stock.<br>
> **Result** · Your answer and restocking CSV.

Progress lines update the same temporary message, which is cleaned up when the answer is delivered. See the [live acceptance record](docs/ACCEPTANCE-1.7.0.md) for previously verified scenarios.

## Quick start

### Requirements

- Hermes with a working model login and Telegram bot, on Linux or macOS.
- A [supported Hermes core](docs/COMPATIBILITY.md). Selected 0.21.0 and 0.21.2 revisions are tested; not every revision is compatible. The installer checks before enabling the plugin.
- Hermes' Python environment with PyYAML 6.x and `python-telegram-bot` 22.x.

### Install with Hermes

For a **new installation**, finish active tasks and stop your Gateway. Run the following as the account that runs Hermes. Set `HERMES_CORE` to your actual core directory; the path below is a common layout.

```bash
export HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
HERMES_CORE="$HERMES_HOME/hermes-agent"
HERMES_PYTHON="$HERMES_CORE/venv/bin/python"
export PYTHONPATH="$HERMES_CORE"

# Install the reviewed v1.8.2 release.
"$HERMES_PYTHON" -m hermes_cli.main plugins install \
  https://github.com/pler1y/hermes-telegram-ux \
  --ref 6197d30a994a195c37611e29f26803ac1db2d6ff --no-enable
```

Check compatibility, configure the English interface and enable the plugin:

```bash
UX_DIR="$HERMES_HOME/plugins/hermes-interaction"
"$HERMES_PYTHON" "$UX_DIR/install.py" check --hermes-core "$HERMES_CORE" && \
"$HERMES_PYTHON" "$UX_DIR/install.py" configure --hermes-core "$HERMES_CORE" --language en && \
"$HERMES_PYTHON" -m hermes_cli.main plugins enable hermes-interaction
```

After successful setup, restart the same Gateway. Send `/new`, then `/start` in Telegram. Change `--language en` to `--language zh` for Chinese.

Already installed? Follow [upgrade and removal](docs/NATIVE-INSTALL.md#upgrade-and-remove). ZIP users should continue with the [ZIP installation guide](docs/INSTALLATION.en.md); the two installation methods must not be mixed. See [native installation](docs/NATIVE-INSTALL.md) for custom paths, dependencies and shared Gateway settings.

## Usage

Send messages, links and files as usual. No special command is needed to start a task.

| To… | Send… |
|---|---|
| Add a requirement | “Include incoming stock in the calculation.” |
| Request a stop | “Stop the task.” or “Stop please.” |
| Open the menu | `/start` |
| Start a new conversation | `/new` |

Stop phrases are matched as whole messages. A request to stop does not undo completed actions or create a resumable pause. Interface language follows your configuration, not the language of each incoming message.

## Documentation

| Guide | What's inside |
|---|---|
| [Native installation](docs/NATIVE-INSTALL.md) | Install, update and remove through Hermes |
| [ZIP installation](docs/INSTALLATION.en.md) | Downloadable editions and manual setup |
| [Configuration](docs/CONFIGURATION.md) | Language, display presets and progress settings |
| [Compatibility](docs/COMPATIBILITY.md) | Supported cores and upgrade checks |
| [Recovery](docs/RECOVERY.md) | Backups and interrupted installations |
| [Changelog](CHANGELOG.md) | Changes by release |

Some detailed guides are currently in Chinese. Both README pages cover installation and everyday use.

## Contributing

Bug reports and focused pull requests are welcome. Read [CONTRIBUTING.md](CONTRIBUTING.md) for the development workflow and what to include in a report. Check [GitHub Actions](https://github.com/pler1y/hermes-telegram-ux/actions) for regression and upstream compatibility results.

For sensitive reports, follow [SECURITY.md](SECURITY.md). Official directory submission is tracked separately in [catalog status](docs/CATALOG.md).

## License

[MIT](LICENSE). Dependency and source acknowledgements are in [NOTICE.md](NOTICE.md).
