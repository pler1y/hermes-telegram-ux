# Hermes Telegram UX

让 Hermes 在 Telegram 里及时回应、清楚汇报、随时接受新要求。

消息到达即接话，任务进度在同一条消息中更新；执行途中可以补充要求或请求停止，完成后直接收到答案和文件。

[English](README.md) · [下载安装包](https://github.com/pler1y/hermes-telegram-ux/releases/latest) · [安装指南](docs/INSTALLATION.md) · [反馈问题](https://github.com/pler1y/hermes-telegram-ux/issues)

**官方目录准备候选版：1.8.0-rc.1。** 本分支补充原生安装和新核心验证，尚未被官方目录收录。[原生安装](docs/NATIVE-INSTALL.md) · [收录准备状态](docs/CATALOG.md)。默认下载链接仍指向稳定版。

## 用起来是什么样

下面是交互流程示例；进度行会更新同一个气泡。模型生成的具体措辞随任务而变化。

| 时刻 | Telegram 中的对话 |
|---|---|
| 你发送任务 | 帮我按未来 7 天的需求生成补货表。 |
| 立即接话 | 好，我看一下 👀 |
| 开始处理 | 📄 我先核对库存和日均用量，找出需要补货的商品。 |
| 你补充要求 | 改为 10 天，把在途库存也算进去。 |
| 收到补充 | 收到，补充已记下。 |
| 实际调整 | 🧮 接下来按 10 天计算，同时扣除在途库存。 |
| 完成交付 | 完整回复和生成的补货 CSV 文件。 |

如果新消息需要排队，回执会说明“这条会在当前任务后处理”。发送“停一下”可以请求停止；已完成的操作不会自动撤销。

通过 `/start` 打开首页，可以选择查资料、读链接或文件、写几句话；任务、历史对话和用量入口放在“更多设置”中。[1.7.0 实机验收记录](docs/ACCEPTANCE-1.7.0.md)包含已验证的场景和测试边界。

## 功能

- **即时接话**：收到消息就给出简短回应，随后自然接上任务进度。
- **内部状态**：整理聊天上下文时，也能看到 Hermes 正在做什么。
- **中英双版**：选择中文或英文安装包，接话、进度提示与菜单保持同一种语言。
- **任务进度**：在同一条消息中持续更新，减少重复通知。
- **途中补充**：任务进行时，可以继续添加要求、调整方向。
- **随时停止**：发送“停一下”，停止当前任务，也支持后台任务。
- **结果交付**：完整发送回复，将生成的文件直接交付到对话中。
- **快捷入口**：通过首页菜单和后续按钮，继续操作或调整设置。

## 安装

需要已接入 Telegram、完成模型登录的 Hermes。本候选版验证了 **0.21.0（`b499ab11fe8b`）和 0.21.2（`a84a2223f82c`）** 两套核心；其他提交只有在受保护的接口文件完整匹配某套基线时才允许加载，详见[兼容边界](docs/COMPATIBILITY.md)。通过 Hermes 管理插件代码请看[原生安装](docs/NATIVE-INSTALL.md)。

ZIP 安装从[全部发行版](https://github.com/pler1y/hermes-telegram-ux/releases)选择对应版本的 `-zh.zip` 中文版及校验和文件，校验后解压；本候选版标记为预发行。

在解压目录中，由 Hermes 所属账号先执行只读兼容检查，路径按实际安装位置填写：

```bash
HERMES_HOME="$HOME/.hermes"
HERMES_CORE="$HERMES_HOME/hermes-agent"
HERMES_PYTHON="$HERMES_CORE/venv/bin/python"
export PYTHONPATH="$HERMES_CORE"

"$HERMES_PYTHON" install.py check --hermes-core "$HERMES_CORE"
```

检查通过后，结束正在运行的任务并停止 Gateway，再安装：

```bash
"$HERMES_PYTHON" install.py install --hermes-home "$HERMES_HOME" --hermes-core "$HERMES_CORE"
```

重新启动 Gateway，在 Telegram 发送 `/new`，再发送 `/start`。

安装选项、配置预览及服务管理方式见 [安装指南](docs/INSTALLATION.md)。

## 使用

照常给 Hermes 发送任务即可。运行期间可以继续补充要求，也可以直接停止：

| 操作 | 示例 |
|---|---|
| 补充要求 | “改按 10 天计算，把在途库存也算进去。” |
| 停止任务 | “停一下” |
| 打开首页 | `/start` 或“开始使用” |

## 文档

- [配置说明](docs/CONFIGURATION.md)：显示预设和进度设置
- [升级与卸载](docs/INSTALLATION.md#升级与卸载) · [故障恢复](docs/RECOVERY.md)
- [开发与测试](docs/TESTING.md) · [发布构建](docs/RELEASE.md)
- [安全与隐私](SECURITY.md)

## 许可证

[MIT](LICENSE)。依赖与来源说明见 [NOTICE.md](NOTICE.md)。
