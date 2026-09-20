# Native Hermes installation · 原生安装

**Hermes Full 1.8.3 / Hermes完整版** uses the five reviewed cores in the [compatibility table](COMPATIBILITY.md). A Hermes version number alone is insufficient. Linux and macOS are supported by the setup helper; use the Python environment that runs your working Hermes Telegram bot.

This page installs Full. For the public-API Plugin edition, use its [independent channel](https://github.com/pler1y/hermes-telegram-ux/tree/catalog-safe). Do not install both editions into the same Gateway.

原生安装由 Hermes 管理代码和固定版本，本项目的 `configure` 只管理交互配置及其备份。
已经通过 ZIP 安装的实例继续使用对应的安装器；迁移前先卸载受管理的 ZIP 版本，并确认没有恢复出的旧插件占用同名目录。

## Install a reviewed commit

Finish running tasks and stop the relevant Gateway. Set these paths for your installation:

```bash
export HERMES_HOME="$HOME/.hermes"
HERMES_CORE="$HERMES_HOME/hermes-agent"
HERMES_PYTHON="$HERMES_CORE/venv/bin/python"
export PYTHONPATH="$HERMES_CORE"
```

The command resolves the fixed `v1.8.3` release tag to its full commit SHA, then pins installation to that SHA. A missing tag stops installation. Future upgrades must resolve a reviewed Full `v*` tag; do not use the Plugin edition’s `catalog-v*` tags.

```bash
UX_COMMIT="$(git ls-remote --refs https://github.com/pler1y/hermes-telegram-ux.git refs/tags/v1.8.3 | cut -f1)"
test "${#UX_COMMIT}" -eq 40 || { echo "Release tag unavailable" >&2; exit 1; }
"$HERMES_PYTHON" -m hermes_cli.main plugins install \
  https://github.com/pler1y/hermes-telegram-ux --ref "$UX_COMMIT" --no-enable
UX_DIR="$HERMES_HOME/plugins/hermes-interaction"

"$HERMES_PYTHON" "$UX_DIR/install.py" check --hermes-core "$HERMES_CORE"
# On the supported 0.21.2 cores, validate before configure/enable.
"$HERMES_PYTHON" -m hermes_cli.main plugins validate "$UX_DIR"
"$HERMES_PYTHON" "$UX_DIR/install.py" configure --hermes-core "$HERMES_CORE" --language en --dry-run
"$HERMES_PYTHON" "$UX_DIR/install.py" configure --hermes-core "$HERMES_CORE" --language en
"$HERMES_PYTHON" -m hermes_cli.main plugins enable hermes-interaction
```

中文界面将 `--language en` 改为 `--language zh`。先查看 dry-run，再执行 configure。
旧 0.21.0 核心没有 validate 命令，只运行兼容检查；候选验证不会把缺少该命令记作通过。
`configure` 会启用插件、设置显示预设，并允许用户点击后续按钮时注入新消息；不会替换模型登录。
共享多平台 Gateway 可在首次 configure 时加 `--preset keep-display`，参见 [配置说明](CONFIGURATION.md)。

Hermes' scan remains enabled. It may request confirmation for this repository's
documented service commands and subprocess-based checks; inspect its report before
accepting. The manifest lists Python dependencies, but Hermes does not install them
automatically. A working Telegram environment normally already has PyYAML and
python-telegram-bot 22.x; install missing dependencies into that same environment.

On Hermes versions with catalog validation, run:

```bash
"$HERMES_PYTHON" -m hermes_cli.main plugins validate "$UX_DIR"
```

Restart the same Gateway, then send `/new` and `/start`. Confirm a normal reply,
progress updates, a mid-task instruction, and stop behavior before wider use.
通过校验不等于实机体验已验收，仍需实际检查 Telegram 收发、补充和停止。

## Upgrade and remove

For upgrades, stop the idle Gateway, review the new release and use the same
install command with `--force --ref NEW_FULL_SHA`. Rerun `configure` from the updated
checkout. It preserves settings changed after the first configuration and leaves
Git/catalog/install metadata under Hermes' ownership. Pinned installs do not follow
the branch automatically.

To remove, stop the idle Gateway, restore the UX settings while the helper still exists,
then disable and remove the plugin through Hermes:

```bash
"$HERMES_PYTHON" "$UX_DIR/install.py" restore-config --dry-run
"$HERMES_PYTHON" "$UX_DIR/install.py" restore-config
"$HERMES_PYTHON" -m hermes_cli.main plugins disable hermes-interaction
"$HERMES_PYTHON" -m hermes_cli.main plugins remove hermes-interaction
```

Restart Gateway afterward. If configuration is interrupted, keep Gateway stopped and
run `"$HERMES_PYTHON" "$UX_DIR/install.py" recover`. Configuration-only recovery preserves
the current native checkout even if Hermes updated it after the interruption.

卸载顺序是：恢复配置 → 原生禁用 → 原生移除 → 重启。不要对原生安装运行 ZIP 的 `install` 或 `uninstall`。
目前尚不能使用 `hermes plugins install hermes-telegram-ux` 这种目录短名称；收录后才会提供。
