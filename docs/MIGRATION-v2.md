# Migrating to Hermes Telegram UX v2

v2 uses the official public Plugin API implementation as the only maintained product. The v1.8.3 Full implementation is historical and no longer maintained; its history is preserved in [`legacy/full-1.8.3`](https://github.com/pler1y/hermes-telegram-ux/tree/legacy/full-1.8.3) and [`v1.8.3`](https://github.com/pler1y/hermes-telegram-ux/tree/v1.8.3).

The internal v2 ID remains **`hermes-telegram-ux-catalog`** for installation and configuration compatibility. Full's ID is **`hermes-interaction`**. They are not interchangeable, and installing v2 does not automatically disable or replace Full. Do not enable both in the same Gateway.

This document prepares migration to the `release/v2.0.0` candidate. There is no final `v2.0.0` tag, GitHub Release or Catalog publication at this stage. Review the candidate before installing it; do not install the repository's old default branch expecting v2.

## Before changing an existing installation

1. Finish foreground and background tasks, then stop the corresponding Gateway using its existing service/container management. The plugin installer does not stop services.
2. Use the same operating-system account, Hermes profile and Python environment as that Gateway. Back up its configuration, current plugin directory and relevant installation records outside the plugin directory.
3. Run `hermes plugins list` and identify the existing ID and management method. For Full, distinguish its native Git installation from its ZIP installer before choosing the removal procedure below.

Examples below use the active `HERMES_HOME`, or the ordinary single-profile default. If your Gateway uses a different profile directory, set `TGUX_HOME` to that verified directory before continuing and ensure the `hermes` CLI targets that same profile.

```bash
TGUX_HOME="${HERMES_HOME:-$HOME/.hermes}"
TGUX_DIR="$TGUX_HOME/plugins/hermes-telegram-ux-catalog"
```

Changing files or a disable setting does not unload code already running in another process. Keep the Gateway stopped throughout replacement and validation.

## Resolve and review the candidate SHA

The checked Hermes core accepts only a full 40-character commit in `--ref`. It does not accept a branch name. Resolve the candidate branch without changing your installation:

```bash
TGUX_REPO="https://github.com/pler1y/hermes-telegram-ux.git"
TGUX_COMMIT="$(git ls-remote --exit-code --heads "$TGUX_REPO" refs/heads/release/v2.0.0 | awk 'NR == 1 {print $1}')"
test "${#TGUX_COMMIT}" -eq 40 || { echo "Candidate branch unavailable; stop here." >&2; exit 1; }
case "$TGUX_COMMIT" in *[!0-9a-fA-F]*) echo "Invalid candidate SHA; stop here." >&2; exit 1 ;; esac
printf 'Review this exact commit before installing: https://github.com/pler1y/hermes-telegram-ux/commit/%s\n' "$TGUX_COMMIT"
```

Review that SHA against the candidate PR and [v2 validation record](VALIDATION-v2.md) before running the installation commands. If the branch has moved beyond the reviewed commit, use the reviewed 40-character SHA instead. Resolving a branch is not itself approval of a new revision.

## New users

After resolving and reviewing the SHA, install without activating first:

```bash
hermes plugins install "$TGUX_REPO" --ref "$TGUX_COMMIT" --no-enable
hermes plugins validate "$TGUX_DIR" --json
hermes plugins doctor "$TGUX_DIR" --ci
hermes plugins enable hermes-telegram-ux-catalog
```

Run each step only after the previous one succeeds. Keep Hermes' install scanner enabled and inspect its findings. Restart the same Gateway, start a fresh conversation with `/new`, and send a normal task. There is no `/tgux`, welcome menu or settings panel.

## Existing public-plugin users (`1.9.0-catalog.1`)

The ID, installation directory and external configuration namespace stay the same. This is a same-ID replacement, not a second installation.

With the Gateway stopped and backups saved, disable the existing copy before replacement. A fixed-SHA installation cannot be advanced using `hermes plugins update`; use an explicit new reviewed SHA:

```bash
hermes plugins disable hermes-telegram-ux-catalog
hermes plugins install "$TGUX_REPO" --force --ref "$TGUX_COMMIT" --no-enable
hermes plugins validate "$TGUX_DIR" --json
hermes plugins doctor "$TGUX_DIR" --ci
hermes plugins enable hermes-telegram-ux-catalog
```

`--force` authorizes replacing the existing plugin directory and acknowledges scanner caution for that already reviewed commit; it does not offer a second interactive caution confirmation. The scanner still runs and dangerous findings remain blocked. Review the exact SHA before this command. This is not a Git force push. `--no-enable` does not disable an already enabled plugin and does not replace the explicit stop/disable steps.

Restart the same Gateway, use `/new`, and verify that only one `hermes-telegram-ux-catalog` entry is enabled, the native answer arrives, and the one temporary status is removed. Full (`hermes-interaction`) must remain disabled or absent.

Configuration behavior:

- `language`, `update_interval`, `status_ttl`, and `cleanup_delay` remain in `plugins.entries.hermes-telegram-ux-catalog.settings`. The legacy same-ID `config` subtree remains a Hermes-supported fallback.
- Explicit `language: zh` / `en` remains fixed. Select `auto` yourself if desired; the upgrade does not overwrite it.
- Removed progress/emoji/menu settings are ignored. No deletion is required.
- Old personal-preference data remains under Hermes' plugin-data namespace but is no longer read. It cannot recreate menus, disable the new progress display or change the new language behavior.
- The replacement preserves external configuration and plugin-data; back up any custom files placed inside the plugin code directory before replacement.

### Existing ZIP copies

The checked Hermes installer accepts Git/Catalog sources, not ZIP files. A ZIP directory without `.git` cannot use native `plugins update`.

For the candidate, the same-ID Git replacement above is the single documented upgrade route from an existing public-plugin ZIP copy as well. It replaces that directory with a pinned Git installation; configuration and plugin-data outside it remain. It does not require deleting the old preferences file.

If deploying a locally built ZIP for testing, verify its checksum and `PROVENANCE.json`, keep the Gateway stopped, back up and completely replace the plugin code directory, then validate/doctor/enable through Hermes. Do not overlay an archive onto old code and assume removed modules disappeared. This is an operator-managed archive deployment, not a native ZIP install command or a published v2 release download.

Catalog installations use a separate Catalog sidecar and reviewed pin. This candidate has not updated that Catalog entry. Do not expect a Catalog update command to fetch this candidate, and do not rename an existing Catalog entry or manifest to force it. Details: [plugin identity audit](PLUGIN-ID.md).

## Full users (`hermes-interaction`)

v2 no longer requires Full's private-core fingerprint match. It still requires a compatible public Plugin API; the checked baseline is Hermes 0.21.3, commit `3c3ab69abb9b08683b5eb15b4e2b8be1198c875f`. Later cores require their own validation.

Full changed some native display settings during installation. Disable alone leaves those settings as configured; use the matching historical management procedure where its records exist. Do not copy Full's settings or runtime files into v2.

### Full installed with native Hermes Git commands

Keep its installed helper available until configuration has been restored. In the Python environment used by the old installation, with the Gateway stopped:

```bash
TGUX_FULL_DIR="$TGUX_HOME/plugins/hermes-interaction"
python "$TGUX_FULL_DIR/install.py" restore-config --hermes-home "$TGUX_HOME" --dry-run
```

Inspect the preview before continuing. If it reports a managed native installation with a valid baseline:

```bash
python "$TGUX_FULL_DIR/install.py" restore-config --hermes-home "$TGUX_HOME"
hermes plugins disable hermes-interaction
hermes plugins remove hermes-interaction
```

The order is configuration restore, native disable, native remove. Do not run Full's ZIP `uninstall` against its native installation. The old helper restores only settings still matching what it managed and preserves later user edits. Keep the old backups and installer records.

Afterward use the new-user v2 procedure above, then restart once and begin a fresh session.

### Full installed with its ZIP installer

Use `install.py` from the original extracted Full distribution, in its Python environment. Keep that distribution outside the installed plugin directory. With the Gateway stopped, run from that distribution directory:

```bash
python install.py uninstall --hermes-home "$TGUX_HOME" --dry-run
```

Inspect the preview, then run:

```bash
python install.py uninstall --hermes-home "$TGUX_HOME"
hermes plugins list
```

Do not use native `restore-config` for a ZIP-managed install. ZIP uninstall may restore the plugin and enablement that existed before the first managed installation. If `hermes-interaction` reappears, keep it disabled before enabling v2:

```bash
hermes plugins disable hermes-interaction
```

Run that last command only if the restored plugin is present. It can remain as disabled history; do not delete user backups to make the installation look empty. Once Full is absent or explicitly disabled, use the new-user v2 procedure and restart.

### Missing management records, manual installation, or interrupted operations

If the helper reports `No managed installation`, this is not proof that Full settings were restored. Do not fabricate a baseline, delete installer state, or repeatedly try the other management mode. Save the current configuration and old plugin, explicitly disable `hermes-interaction` while it is still discoverable, and review the former Full display settings against the user's own backup before installing v2.

An interrupted transaction must be recovered using the matching old Full helper while the Gateway stays stopped. Preserve its `telegram-ux-installer` records and `backups/hermes-telegram-ux` directories. If the backup or current configuration is inconsistent, stop the restore step rather than overwriting user edits. See the [historical recovery instructions](https://github.com/pler1y/hermes-telegram-ux/blob/v1.8.3/docs/RECOVERY.md).

These procedures are documented migration paths; this release-preparation work does not automatically modify any real Full user's environment.

## Removing v2 later

Finish tasks and stop the corresponding Gateway, then:

```bash
hermes plugins disable hermes-telegram-ux-catalog
hermes plugins remove hermes-telegram-ux-catalog
```

Restart the Gateway to continue using native Hermes. The checked core removes the plugin code and install-metadata record, but retains its external configuration entry and plugin-data. This project does not delete those old user files.

## Validation scope

[VALIDATION-v2.md](VALIDATION-v2.md) records tests against the final release-candidate commit, including clean Git/ZIP payload lifecycles, old-version upgrade behavior, native enable/disable/remove, configuration/state preservation, and unchanged Hermes core. [VALIDATION.md](VALIDATION.md) retains the original live Telegram evidence and its original versions; it is not relabeled as a new v2 deployment.
