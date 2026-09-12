# Installation

## Before you start

Use Hermes 0.21.0 at commit `b499ab11fe8b081470e269f2fb27abae03000da5`. Confirm your model login and Telegram bot work before adding this plugin. The installer checks the core revision and the interfaces it uses; see [compatibility](COMPATIBILITY.md).

Download an edition and its matching `.zip.sha256` from [Releases](https://github.com/pler1y/hermes-telegram-ux/releases/latest):

- `hermes-telegram-ux-1.7.1-en.zip` for English.
- `hermes-telegram-ux-1.7.1-zh.zip` for Chinese.

On Linux, verify with `sha256sum -c <archive>.sha256`; on macOS, use `shasum -a 256 -c <archive>.sha256`. Extract the ZIP and open its directory. Run the following as the account that owns your Hermes installation, adjusting the paths:

```bash
HERMES_HOME="$HOME/.hermes"
HERMES_CORE="$HERMES_HOME/hermes-agent"
HERMES_PYTHON="$HERMES_CORE/venv/bin/python"
export PYTHONPATH="$HERMES_CORE"

"$HERMES_PYTHON" install.py check --hermes-core "$HERMES_CORE"
"$HERMES_PYTHON" install.py install --hermes-home "$HERMES_HOME" --hermes-core "$HERMES_CORE" --dry-run
```

## Install

Finish foreground and background tasks, and stop your Gateway using its usual service or container manager. Then run:

```bash
"$HERMES_PYTHON" install.py install --hermes-home "$HERMES_HOME" --hermes-core "$HERMES_CORE"
```

Restart the same Gateway. Send `/new` to start a fresh conversation and `/start` to open the menu.

The installer manages plugin files and configuration; it does not manage your Gateway service. Its default `recommended` preset enables progress and mid-task feedback while disabling duplicate tool logs and partial answer streaming. To keep existing display settings, use `--preset keep-display` on first installation. Review the dry-run on Gateways shared with other platforms, since a few busy-input settings apply globally.

Use this installer for managed upgrades and removal. The internal plugin ID remains `hermes-interaction` for existing installations.

## Language and emoji

Each edition has a fixed language. The English package uses English for acknowledgements, menus, buttons and built-in progress, and asks the model to write its public updates in English. Model-generated text still follows the task and model behavior. There is no language detection or translation service.

To switch editions, stop the idle Gateway and install the other archive over the existing installation. Then restart and send `/new`. If you previously edited the language setting manually, that choice is preserved; change it to `en` or `zh` in the plugin settings:

```yaml
plugins:
  entries:
    hermes-interaction:
      settings:
        language: en
        status_emoji: true
```

This is a fragment to merge into your existing configuration. `status_emoji` controls automatic decoration of progress text; the edition's greeting and menu copy can still contain emoji. The source checkout defaults to Chinese.

By default, immediate acknowledgement happens at Telegram intake. `status_delay_seconds` only controls fallback bubble creation if intake feedback was unavailable; it does not postpone the acknowledgement. Set `soft_wait: true` in the plugin settings to omit that acknowledgement and ordinary model-waiting text. Substantive tool activity, explicit progress, message receipts, long waits, compression, approvals and terminal states can still appear.

Ordinary progress edits remain rate limited. Failed sends and edits progressively back off. When Telegram requests a wait, status bubbles, intake acknowledgements and typing indicators on the same bot honor it; the next successful edit shows the latest status.

## Upgrade or remove

Finish tasks and stop Gateway first. To upgrade, extract the new release and run the same installation command from that directory. Restart Gateway and send `/new` afterward.

To remove:

```bash
"$HERMES_PYTHON" install.py uninstall --hermes-home "$HERMES_HOME" --dry-run
"$HERMES_PYTHON" install.py uninstall --hermes-home "$HERMES_HOME"
```

Restart Gateway after removal. The installer restores the settings it managed while retaining subsequent user changes. If a plugin existed before the first managed installation, it restores that version. Model credentials, conversation history and SOUL files are not replaced.

## Interrupted installation

Keep Gateway stopped and run:

```bash
"$HERMES_PYTHON" install.py recover --hermes-home "$HERMES_HOME"
```

Retain `$HERMES_HOME/backups/hermes-telegram-ux/` and `$HERMES_HOME/telegram-ux-installer/` for recovery. Backups can contain private configuration. See [recovery details](RECOVERY.md).
