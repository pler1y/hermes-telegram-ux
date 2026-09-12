# 安装指南

## 准备

使用 [支持的 Hermes 核心版本](COMPATIBILITY.md)，完成模型登录和 Telegram 接入，确认机器人可以正常回复消息。新环境可按 [从零安装指南](FRESH-INSTALL.md)配置。

本文适用于 ZIP 安装；通过 Hermes 插件命令管理代码请看[原生安装](NATIVE-INSTALL.md)。从 [发行页](https://github.com/pler1y/hermes-telegram-ux/releases)下载对应版本的 `-zh.zip` 中文版或 `-en.zip` 英文版和 `.sha256` 文件，校验后解压。1.8.0-rc.1 标记为候选版，尚未收录官方目录。以下命令在解压目录运行，由拥有 Hermes 配置的账号执行。

```bash
HERMES_HOME="$HOME/.hermes"
HERMES_CORE="$HERMES_HOME/hermes-agent"
HERMES_PYTHON="$HERMES_CORE/venv/bin/python"
export PYTHONPATH="$HERMES_CORE"
```

路径按实际安装位置填写。可以先检查版本并预览配置变更：

```bash
"$HERMES_PYTHON" install.py check --hermes-core "$HERMES_CORE"
"$HERMES_PYTHON" install.py install --hermes-home "$HERMES_HOME" --hermes-core "$HERMES_CORE" --dry-run
```

## 安装插件

结束前台和后台任务，停止对应的 Gateway 服务，然后安装：

```bash
"$HERMES_PYTHON" install.py install --hermes-home "$HERMES_HOME" --hermes-core "$HERMES_CORE"
```

完成后启动同一个 Gateway 服务。在 Telegram 发送 `/new` 开始新会话，再发送 `/start` 打开首页。

Gateway 的启停沿用自己的部署方式。用户级 systemd 服务使用 `systemctl --user stop/start 服务名`，系统级服务使用 `sudo systemctl stop/start 服务名`；容器环境使用对应的容器管理命令。安装器只负责插件及配置。

## 显示预设

默认 `recommended` 预设启用任务进度和补充反馈，关闭逐字输出及重复工具日志。

需要保留原有显示设置时，在首次安装命令末尾添加 `--preset keep-display`，再按 [配置说明](CONFIGURATION.md)手动调整。重复安装会保留首次选择以及后续手动修改的配置。

ZIP 安装使用本项目的 `install.py install/uninstall` 管理代码、显示预设和备份。原生安装使用独立的 `configure/restore-config` 配置入口，保留 Hermes 管理的代码与版本信息。两种管理记录不能混用。内部插件 ID 仍为 `hermes-interaction`。

## 升级与卸载

先结束前后台任务并停止 Gateway。升级时，在新版本的解压目录重新运行安装命令：

```bash
"$HERMES_PYTHON" install.py install --hermes-home "$HERMES_HOME" --hermes-core "$HERMES_CORE"
```

卸载可先预览变更，再执行：

```bash
"$HERMES_PYTHON" install.py uninstall --hermes-home "$HERMES_HOME" --dry-run
"$HERMES_PYTHON" install.py uninstall --hermes-home "$HERMES_HOME"
```

操作完成后重新启动 Gateway。升级后使用 `/new` 开始新会话。

卸载恢复插件管理的配置，保留用户后续修改。如果首次安装前已有旧版插件，会恢复该版本。模型登录、聊天记录和 SOUL 文件不受影响。

## 故障恢复

如果安装因断电或进程中断而未完成，保持 Gateway 停止，执行：

```bash
"$HERMES_PYTHON" install.py recover --hermes-home "$HERMES_HOME"
```

备份位于 `$HERMES_HOME/backups/hermes-telegram-ux/`，管理记录位于 `$HERMES_HOME/telegram-ux-installer/`。保留这些文件以便恢复；备份可能包含私人配置。

恢复规则和配置冲突处理见 [故障恢复](RECOVERY.md)。

## 交互说明

任务进度根据工具事件和本轮回复更新。执行中追加要求后，会先显示收到补充的反馈，再由 Hermes 在后续执行中应用。发送“停一下”会请求停止前台或所属后台任务，已完成的外部操作不会自动撤销。

最终回复以完整消息发送，长文仍按 Telegram 的长度限制分条。更详细的接口说明见 [兼容说明](COMPATIBILITY.md)。

## 语言版本

两个安装包使用同一套功能，界面语言固定。中文版使用中文，英文版的接话、菜单、内置状态和模型公开进度提示使用英文。不会检测用户所在地或自动识别消息语言，也没有翻译请求。

切换版本时，结束任务并停止 Gateway，安装另一语言的 ZIP，重启后发送 `/new`。安装器会保留手动修改过的 `plugins.entries.hermes-interaction.settings.language`；若曾手动修改，可把它设为 `zh` 或 `en`。从源码安装默认中文。

消息到达 Telegram 入口后立即发送简短接话，再由同一气泡承接任务进度；不等待模型生成。正常网络延迟仍会影响实际显示时间。
