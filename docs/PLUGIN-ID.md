# Plugin identity and v2 compatibility

Hermes Telegram UX v2.0.0 retains the internal plugin ID **`hermes-telegram-ux-catalog`**. The product name is **Hermes Telegram UX**. The ID is an installation compatibility key, not a second product or a recommendation to run two implementations.

This decision is based on the actual Hermes installer and loader at **0.21.3**, commit **`3c3ab69abb9b08683b5eb15b4e2b8be1198c875f`**. Changing the ID cannot be treated as a seamless rename on that core. No ID migration system is added.

## What identifies the installed plugin

For a top-level native plugin, Hermes uses `plugin.yaml`'s `name` as its registry key. `version` describes the installed payload; it does not make two differently named plugins the same installation. Nested plugin directories can have a path-derived registry key, but this project's native installation is top-level.

| Operation | Actual identity behavior | Checked source |
|---|---|---|
| Discovery and runtime ID | `parse_manifest_file()` derives the key from `name` for a top-level plugin; `PluginContext.plugin_id` returns `manifest_key()` | [plugins_manifest.py:316](https://github.com/NousResearch/hermes-agent/blob/3c3ab69abb9b08683b5eb15b4e2b8be1198c875f/hermes_cli/plugins_manifest.py#L316), [plugins_manifest.py:458](https://github.com/NousResearch/hermes-agent/blob/3c3ab69abb9b08683b5eb15b4e2b8be1198c875f/hermes_cli/plugins_manifest.py#L458), [plugins.py:234](https://github.com/NousResearch/hermes-agent/blob/3c3ab69abb9b08683b5eb15b4e2b8be1198c875f/hermes_cli/plugins.py#L234) |
| Git install and reinstall | `_install_plugin_core()` reads the cloned manifest name, selects `plugins/<name>`, and keys `.install-metadata.json` by that name | [plugins_cmd.py:635](https://github.com/NousResearch/hermes-agent/blob/3c3ab69abb9b08683b5eb15b4e2b8be1198c875f/hermes_cli/plugins_cmd.py#L635) |
| Existing same-ID directory | A reviewed force reinstall atomically replaces the target and its source/revision metadata, with rollback on failure | [plugins_cmd.py:614](https://github.com/NousResearch/hermes-agent/blob/3c3ab69abb9b08683b5eb15b4e2b8be1198c875f/hermes_cli/plugins_cmd.py#L614) |
| Enable and disable | Commands resolve the real key and update `plugins.enabled` / `plugins.disabled`; an explicit disable takes precedence | [plugins_cmd.py:972](https://github.com/NousResearch/hermes-agent/blob/3c3ab69abb9b08683b5eb15b4e2b8be1198c875f/hermes_cli/plugins_cmd.py#L972), [plugins_discovery.py:180](https://github.com/NousResearch/hermes-agent/blob/3c3ab69abb9b08683b5eb15b4e2b8be1198c875f/hermes_cli/plugins_discovery.py#L180) |
| Configuration | `get_config()` reads `plugins.entries.<plugin_id>.settings`, then the same ID's legacy `config` subtree | [plugins.py:257](https://github.com/NousResearch/hermes-agent/blob/3c3ab69abb9b08683b5eb15b4e2b8be1198c875f/hermes_cli/plugins.py#L257) |
| Durable state | `PluginState` derives a separate namespace from the ID under `plugin-data/<namespace>/state.json` | [plugins_state.py:66](https://github.com/NousResearch/hermes-agent/blob/3c3ab69abb9b08683b5eb15b4e2b8be1198c875f/hermes_cli/plugins_state.py#L66), [plugins_state.py:110](https://github.com/NousResearch/hermes-agent/blob/3c3ab69abb9b08683b5eb15b4e2b8be1198c875f/hermes_cli/plugins_state.py#L110) |
| Git update | `cmd_update()` finds the named directory. `_pull_plugin_update()` refuses pinned installs and directories without `.git`; otherwise it pulls and records the new revision | [plugins_cmd.py:784](https://github.com/NousResearch/hermes-agent/blob/3c3ab69abb9b08683b5eb15b4e2b8be1198c875f/hermes_cli/plugins_cmd.py#L784) |
| Catalog identity and update | The Catalog entry name is independent of manifest name. `.hermes-catalog.json` stores `catalog_name`; updates look up that entry and reinstall its reviewed SHA | [plugins_cmd_catalog.py:62](https://github.com/NousResearch/hermes-agent/blob/3c3ab69abb9b08683b5eb15b4e2b8be1198c875f/hermes_cli/plugins_cmd_catalog.py#L62), [plugins_cmd_catalog.py:121](https://github.com/NousResearch/hermes-agent/blob/3c3ab69abb9b08683b5eb15b4e2b8be1198c875f/hermes_cli/plugins_cmd_catalog.py#L121) |
| Remove / uninstall | Removes the selected code directory and its install-metadata record. It does not remove the external configuration entry or `plugin-data` | [plugins_cmd.py:881](https://github.com/NousResearch/hermes-agent/blob/3c3ab69abb9b08683b5eb15b4e2b8be1198c875f/hermes_cli/plugins_cmd.py#L881) |
| ZIP payload | This core's native installer accepts Git/Catalog sources, not a ZIP file. A verified ZIP is extracted into the same-ID directory, then managed through native validation and activation | [plugins_cmd.py:204](https://github.com/NousResearch/hermes-agent/blob/3c3ab69abb9b08683b5eb15b4e2b8be1198c875f/hermes_cli/plugins_cmd.py#L204), [lifecycle harness](https://github.com/pler1y/hermes-telegram-ux/blob/v2.0.0/scripts/check_native.py) |

## Why the ID is not renamed

Changing `name` to `hermes-telegram-ux` and reinstalling would select a new directory and metadata key. That installation path has no operation that removes the old `hermes-telegram-ux-catalog` directory, migrates its configuration entry, or moves its state namespace. Both copies could be enabled independently.

Changing a manifest name through an unpinned `git pull` is also not a rename transaction: the original directory and its install record remain, while discovery sees the new name. That leaves installation and runtime identities inconsistent.

Keeping the same Catalog entry name would not solve this: Catalog re-pinning still delegates to the same manifest-name-based installer. Conversely, preserving this manifest ID does not prevent the public product from being named Hermes Telegram UX. These are separate identities.

## Preserved and ignored data

The current implementation reads only `language`, `update_interval`, `status_ttl`, and `cleanup_delay` from the existing namespace. Valid configured values remain effective. In particular, an explicit `language: zh` or `language: en` is not changed to `auto`; `auto` is the default only when a setting is absent or invalid.

Old `progress` / `emoji` settings and personal preferences are ignored. The runtime no longer accesses `ctx.state`, creates menus, or registers `/tgux`. Old state files do not need to be deleted. Hermes' schema checker iterates the current declared schema, so extra old settings do not themselves prevent loading; see [validate_config_schema()](https://github.com/NousResearch/hermes-agent/blob/3c3ab69abb9b08683b5eb15b4e2b8be1198c875f/hermes_cli/plugins_manifest.py#L170).

A same-ID Git replacement changes the plugin code directory. Configuration and plugin-owned durable state outside that directory remain. Files manually added inside the code directory must be backed up before replacement; they are not an external-data preservation contract.

## Upgrade and evidence

Follow [MIGRATION-v2.md](MIGRATION-v2.md). Pinned installs require an explicit **40-character commit SHA** and a reviewed force reinstall; a tag name is not accepted directly by the checked core. `--no-enable` suppresses enabling during installation but does not disable an already enabled plugin or stop a running Gateway.

Code-level findings in this document do not substitute for install tests. [Candidate validation history](https://github.com/pler1y/hermes-telegram-ux/blob/v2.0.0/docs/VALIDATION-v2.md) preserves the release-preparation evidence. The official Release notes identify the final merge commit and its validation/smoke results. Prior `1.9.0-catalog.1` live records remain historical evidence. Catalog admission is a separate maintainer decision.
