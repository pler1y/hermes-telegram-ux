<div align="center">

# Hermes Telegram UX

**消息即刻回应，进度随时可见，任务途中也能改变方向。**

为 [Hermes Agent](https://github.com/NousResearch/hermes-agent) 提供更自然的 Telegram 交互。

[![Release](https://img.shields.io/github/v/release/pler1y/hermes-telegram-ux)](https://github.com/pler1y/hermes-telegram-ux/releases/latest)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

[快速开始](#快速开始) · [使用](#使用) · [文档](#文档) · [English](README.md)

</div>

---

给 Hermes 发消息后，不必猜它有没有收到。立即获得回应，在同一条消息里查看任务进度，执行中也能补充要求。完成的答案和文件，直接交付到当前聊天。

## 功能

- **即时回应**：普通请求到达时立即显示「🤔 思考中…」，不等待模型生成。
- **同一气泡更新进度**：任务状态持续更新，减少重复消息。
- **途中补充要求**：添加细节或调整方向；回执会区分补充要求和排队请求。
- **自然表达停止**：单独说“等一下”“等下”“等等”“停”或“暂停”，即可请求停止。
- **答案与文件交付**：在 Telegram 中接收完整回复、生成文件和后续操作入口。
- **中英双语界面**：安装时选择中文或英文。

## 对话示例

以下展示交互流程；具体进度措辞由模型根据任务生成。

> **你** · 帮我按未来 7 天的需求生成补货表。<br>
> **Hermes** · 🤔 思考中…<br>
> **进度** · 📄 我先核对库存和日均用量。<br>
> **你** · 改为 10 天，把在途库存也算进去。<br>
> **Hermes** · 收到，补充已记下。<br>
> **进度** · 🧮 接下来按 10 天计算，同时扣除在途库存。<br>
> **结果** · 完整回复和生成的补货 CSV 文件。

进度行更新同一条临时消息，答案交付后清理。已验证场景见[实机验收记录](docs/ACCEPTANCE-1.7.0.md)。

## 快速开始

### 环境要求

- Linux 或 macOS 上已安装 Hermes，完成模型登录，并接入可正常回复的 Telegram Bot。
- 使用[支持的 Hermes 核心](docs/COMPATIBILITY.md)。目前验证了 0.21.0 和 0.21.2 的部分修订，并非所有修订都兼容；安装器会在启用前检查。
- Hermes 的 Python 环境中已具备 PyYAML 6.x 和 `python-telegram-bot` 22.x。

### 使用 Hermes 命令安装

以下适用于**首次安装**。先结束正在执行的任务并停止 Gateway，再由运行 Hermes 的账号执行。将 `HERMES_CORE` 改成实际核心目录，下方为常见路径。

```bash
export HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
HERMES_CORE="$HERMES_HOME/hermes-agent"
HERMES_PYTHON="$HERMES_CORE/venv/bin/python"
export PYTHONPATH="$HERMES_CORE"

# 安装已验证的 v1.8.2 发行版。
"$HERMES_PYTHON" -m hermes_cli.main plugins install \
  https://github.com/pler1y/hermes-telegram-ux \
  --ref 6197d30a994a195c37611e29f26803ac1db2d6ff --no-enable
```

检查兼容性、配置中文界面并启用插件：

```bash
UX_DIR="$HERMES_HOME/plugins/hermes-interaction"
"$HERMES_PYTHON" "$UX_DIR/install.py" check --hermes-core "$HERMES_CORE" && \
"$HERMES_PYTHON" "$UX_DIR/install.py" configure --hermes-core "$HERMES_CORE" --language zh && \
"$HERMES_PYTHON" -m hermes_cli.main plugins enable hermes-interaction
```

配置成功后，重新启动同一个 Gateway。在 Telegram 发送 `/new`，再发送 `/start`。需要英文界面时，将 `--language zh` 改为 `--language en`。

已有安装请看[升级与卸载](docs/NATIVE-INSTALL.md#upgrade-and-remove)。通过 ZIP 安装的用户继续使用 [ZIP 安装指南](docs/INSTALLATION.md)，不要混用两种安装方式。自定义路径、依赖及共享 Gateway 设置见[原生安装指南](docs/NATIVE-INSTALL.md)。

## 使用

照常发送消息、链接或文件即可，不需要用特殊命令启动任务。

| 想做什么 | 发送什么 |
|---|---|
| 补充要求 | “把在途库存也算进去。” |
| 请求停止 | “等一下”“等下”“等等”“停”或“暂停” |
| 打开菜单 | `/start` |
| 开始新会话 | `/new` |

停止短句按整条消息匹配，“不要停”“等一下再部署”等完整要求不会直接变成停止指令。停止不会撤销已经执行的操作，也不是可以从原位置恢复的暂停。界面语言由配置决定，不随每条消息的语言自动切换。

## 文档

| 指南 | 内容 |
|---|---|
| [原生安装](docs/NATIVE-INSTALL.md) | 通过 Hermes 安装、更新和移除 |
| [ZIP 安装](docs/INSTALLATION.md) | 下载版本与手动安装 |
| [从零开始](docs/FRESH-INSTALL.md) | 新环境准备 |
| [配置说明](docs/CONFIGURATION.md) | 语言、显示预设和进度设置 |
| [兼容说明](docs/COMPATIBILITY.md) | 支持的核心与升级检查 |
| [故障恢复](docs/RECOVERY.md) | 备份与中断恢复 |
| [更新日志](CHANGELOG.md) | 各版本变化 |

## 参与贡献

欢迎提交问题反馈和范围明确的 Pull Request。开发流程与反馈所需信息见 [CONTRIBUTING.md](CONTRIBUTING.md)。回归测试和上游兼容检查结果见 [GitHub Actions](https://github.com/pler1y/hermes-telegram-ux/actions)。

敏感问题请按 [SECURITY.md](SECURITY.md) 处理。官方插件目录申请单独记录在[收录状态](docs/CATALOG.md)中。

## 许可证

采用 [MIT](LICENSE) 许可证。依赖与来源说明见 [NOTICE.md](NOTICE.md)。
