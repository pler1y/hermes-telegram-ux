# Hermes Telegram UX

**Hermes Telegram 交互增强**，让 Hermes 的 Telegram 对话更适合日常使用：简短可见的任务进度、途中追加要求、自然语言停止，以及完整发送的结果。

项目名为 `hermes-telegram-ux`；内部插件 ID 保留 `hermes-interaction`，用于兼容原有安装。当前版本 **1.6.0**。这是社区插件，依赖 Hermes，本身不提供模型额度或 Telegram 账号。

[下载安装包](https://github.com/pler1y/hermes-telegram-ux/releases/tag/v1.6.0) · [自动测试](https://github.com/pler1y/hermes-telegram-ux/actions/workflows/tests.yml) · [反馈问题](https://github.com/pler1y/hermes-telegram-ux/issues)

## 使用体验

- 开始任务后给出可见反馈，后续进度编辑同一个气泡。
- 进度来自真实工具事件和当前模型回复中的公开行动说明；不另开模型请求生成进度，不展示隐藏推理或虚构百分比。
- 执行中可以补充要求。收到补充和实际应用补充是两种状态。
- 私聊发送“停一下”进入 Hermes 原生停止流程；已完成的外部操作不会自动撤销。
- 最终正文准备完整后发送，不逐字输出；超长内容仍受 Telegram 分条限制。
- `/start`、`/hello` 或“开始使用”打开首页，日常入口和进阶设置分层。
- 支持所属后台任务的进度与停止、文件交付规范，以及绑定当前用户和消息的可选后续按钮。

公开说明的措辞、资料理解和执行结果仍受模型与工具能力影响。这个插件优化交互，不承诺加快模型响应。

## 支持范围

当前经过验证的基线：**Hermes 0.21.0，提交 `b499ab11fe8b081470e269f2fb27abae03000da5`**，Linux ARM64、Python 3.11、Telegram，xAI OAuth / Grok 4.6。此前的内部版本使用同一核心提交在 Linux x86_64 / OpenAI Codex 环境运行；它不等同于本发行包的全套跨平台验收。

插件适配了部分 Hermes 内部接口，安装及加载前会检查核心版本和接口文件。未验证的新版本会拒绝加载。详见 [兼容边界](docs/COMPATIBILITY.md)。不要为了安装插件直接降级正在使用的 Hermes；请先在独立环境验证。

## 安装

前提：已有可正常收发 Telegram 消息的 Hermes，并完成模型登录。先按 [Hermes 官方安装说明](https://hermes-agent.nousresearch.com/docs/getting-started/installation/)安装 Hermes。模型凭据和 Bot token 由 Hermes 管理；不要放进本仓库。

如果机器尚未安装 Hermes，或现有版本不在支持范围，使用 [从零建立独立测试环境](docs/FRESH-INSTALL.md) 中的固定提交步骤；官方默认安装入口可能已更新到其他版本。

从 [v1.6.0 发行页](https://github.com/pler1y/hermes-telegram-ux/releases/tag/v1.6.0)下载 `hermes-telegram-ux-1.6.0.zip` 和对应 `.sha256` 文件，校验后解压，在项目目录执行。以下变量按自己的安装位置填写；命令必须由拥有 Hermes 配置的账号执行：

```bash
HERMES_HOME="$HOME/.hermes"
HERMES_CORE="$HERMES_HOME/hermes-agent"
HERMES_PYTHON="$HERMES_CORE/venv/bin/python"
export PYTHONPATH="$HERMES_CORE"

"$HERMES_PYTHON" install.py check --hermes-core "$HERMES_CORE"
"$HERMES_PYTHON" install.py install --hermes-home "$HERMES_HOME" --hermes-core "$HERMES_CORE" --dry-run
```

确认当前对话及后台任务都已结束，**停止自己的 Gateway 服务**，然后安装：

```bash
"$HERMES_PYTHON" install.py install --hermes-home "$HERMES_HOME" --hermes-core "$HERMES_CORE"
```

启动同一个 Gateway 服务，在 Telegram 发送 `/new`，再发送 `/start`。新会话可避免旧会话中冻结的系统提示沿用旧交互规则。

安装器不猜测服务名称，也不自动停止或重启服务。例如，用户级 systemd 服务用 `systemctl --user stop/start 你的服务名`；系统级服务用 `sudo systemctl stop/start 你的服务名`。不要把其他人的服务名称直接套用到自己的机器。

默认 `recommended` 预设关闭逐字输出和重复工具日志，启用本插件的状态气泡、补充反馈、反应及简洁链接。若要自行配置显示行为，在首次安装时增加 `--preset keep-display`；完整体验仍需避免原生流式和进度与插件重复。所有配置键见 [配置说明](docs/CONFIGURATION.md)。

该版本使用项目安装器来管理显示预设、备份和恢复。源码根目录也有原生 `plugin.yaml` / `register(ctx)` 入口，但仅执行原生插件下载/启用不会完成这些配置和生命周期记录；本文安装流程是受支持的完整路径。

## 更新、卸载和故障恢复

先结束前后台任务、停止 Gateway，再运行相应操作，完成后重新启动服务。

```bash
# 从新发行包的目录重复安装：更新代码，保留最初安装基线和后来手动修改的配置。
"$HERMES_PYTHON" install.py install --hermes-home "$HERMES_HOME" --hermes-core "$HERMES_CORE"

# 先查看，再卸载。
"$HERMES_PYTHON" install.py uninstall --hermes-home "$HERMES_HOME" --dry-run
"$HERMES_PYTHON" install.py uninstall --hermes-home "$HERMES_HOME"

# 仅在安装被断电/强制结束、提示存在未完成事务时运行。
"$HERMES_PYTHON" install.py recover --hermes-home "$HERMES_HOME"
```

卸载只还原仍等于插件所写值的配置项，保留用户之后修改的值和其他插件。若首次安装前已有旧版插件，会恢复该旧版；若没有则删除本插件。模型、登录、聊天数据库和 SOUL 文件不属于安装器的管理范围。

备份保存在 `$HERMES_HOME/backups/hermes-telegram-ux/`，管理记录在 `$HERMES_HOME/telegram-ux-installer/`，权限受限。备份可能包含私人配置，不可上传 GitHub。安装异常会自动恢复；若异常后配置又被外部修改，恢复命令会停止并给出备份位置，避免覆盖这些修改。详见 [恢复说明](docs/RECOVERY.md)。

## 验证与开发

[测试方法](docs/TESTING.md)说明纯安装器测试、真实 Hermes 回归、原生注册检查和 Telegram 人工验收。实机结果见 [验收记录](docs/ACCEPTANCE.md)。这些结果只代表记录的环境和场景。

提交问题时附 Hermes 提交、插件版本、复现步骤和脱敏日志。不要提交 Bot token、OAuth 文件、聊天数据库或完整配置。详见 [安全说明](SECURITY.md)。

许可证与公开发布状态见 [发布清单](docs/RELEASE.md)。
