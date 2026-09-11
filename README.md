# Hermes Telegram UX

Hermes 的 Telegram 交互增强插件。

在 Telegram 中查看任务进度，随时补充要求或停止任务，并接收完整的回复和文件。

[下载安装包](https://github.com/pler1y/hermes-telegram-ux/releases/latest) · [安装指南](docs/INSTALLATION.md) · [反馈问题](https://github.com/pler1y/hermes-telegram-ux/issues)

## 功能

- **任务进度**：在同一条消息中持续更新，减少重复通知。
- **途中补充**：任务进行时，可以继续添加要求、调整方向。
- **随时停止**：发送“停一下”，停止当前任务，也支持后台任务。
- **结果交付**：完整发送回复，将生成的文件直接交付到对话中。
- **快捷入口**：通过首页菜单和后续按钮，继续操作或调整设置。

## 安装

需要已接入 Telegram 的 Hermes 0.21.0（[支持的核心版本](docs/COMPATIBILITY.md)），并完成模型登录。尚未安装 Hermes，可参考 [从零安装指南](docs/FRESH-INSTALL.md)。

从 [发行页](https://github.com/pler1y/hermes-telegram-ux/releases/latest)下载 ZIP 和校验和文件，校验后解压。

结束正在运行的任务并停止 Gateway。在解压目录中，由 Hermes 所属账号执行以下命令，路径按实际安装位置填写：

```bash
HERMES_HOME="$HOME/.hermes"
HERMES_CORE="$HERMES_HOME/hermes-agent"
HERMES_PYTHON="$HERMES_CORE/venv/bin/python"
export PYTHONPATH="$HERMES_CORE"

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
