# Hermes Telegram UX

[English](README.md)

在 Telegram 等待 Hermes 工作时，用一条临时气泡显示当前任务进度。状态随真实工具动作和结果更新，任务结束后自动清理。安装、启用，然后正常聊天即可。

**v2.0.0 已在 [release/v2.0.0](https://github.com/pler1y/hermes-telegram-ux/tree/release/v2.0.0) 准备审查，尚未合入 main、打 Tag 或发布 Release。** 从 v2 开始，只维护这一套官方公开 Plugin API 实现。

## 使用体验

下列状态都在同一个消息上编辑，并结合当前任务生成：

```text
🤔 正在思考中…
🔎 正在搜索最近 7 天 OpenAI 的重要公开新闻…
📊 已找到 10 条搜索结果，正在整理最近 7 天 OpenAI 的重要公开新闻…
✍️ 正在汇总最近 7 天 OpenAI 的重要公开新闻…
Hermes 原生最终回答 → 临时状态自动清理
```

- 工具实际开始后，显示对应动作与任务对象。
- 有可靠结果才展示搜索数量、天气数据字段、文件不存在或工具失败。
- 真正发生后续调用才显示恢复；部分失败不会被说成全部成功。
- 长时间模型汇总显示任务相关总结，不让旧搜索 Query 一直停留。
- 单一消息、编辑节流、去重、归属隔离和有限清理。
- 按本轮消息自动使用中文或英文。

没有完成卡、按钮、欢迎页、个人设置面板或 `/tgux`。不需要进度时，直接通过 Hermes 禁用插件。

## 安装已审查的候选

需要已经正常使用 Telegram 的 Hermes。已验证基线为 **Hermes 0.21.3**，commit `3c3ab69abb9b08683b5eb15b4e2b8be1198c875f`。CI 也检查 Hermes 当前 main 的 Python 3.11／3.12；请查看要安装的具体候选结果。

原生安装器的 `--ref` 接受 **40 位 commit SHA**，不接受分支名。先取得候选提交，在 GitHub 审阅后按该准确 SHA 安装：

```bash
TGUX_COMMIT="$(git ls-remote https://github.com/pler1y/hermes-telegram-ux.git refs/heads/release/v2.0.0 | cut -f1)"
printf '%s\n' "$TGUX_COMMIT"
hermes plugins install https://github.com/pler1y/hermes-telegram-ux.git --ref "$TGUX_COMMIT" --no-enable
hermes plugins validate "${HERMES_HOME:-$HOME/.hermes}/plugins/hermes-telegram-ux-catalog" --json
hermes plugins doctor "${HERMES_HOME:-$HOME/.hermes}/plugins/hermes-telegram-ux-catalog" --ci
hermes plugins enable hermes-telegram-ux-catalog
```

重启对应 Gateway，发送普通任务即可。原生扫描器有提示时，先审阅再决定安装。不要安装远端旧默认分支并期待得到 v2。已有安装先阅读 [迁移说明](docs/MIGRATION-v2.md)：固定 SHA 安装需要明确替换，`--no-enable` 不会禁用已经运行的旧插件。

内部 ID **`hermes-telegram-ux-catalog` 保持不变**，用于兼容安装、配置和状态身份；它不再代表第二个产品版本。详见 [ID 决策与源码依据](docs/PLUGIN-ID.md)。

也可用 `scripts/build_release.py --ref <40位SHA>` 从已审阅提交构建可复现 ZIP，包内有文件哈希和 `PROVENANCE.json`。Hermes 原生安装器不直接接收 ZIP；验证后手工部署和完整替换方法见迁移说明。本轮尚未发布 v2 Release 附件。

## 配置

默认无需设置。可选参数位于 `plugins.entries.hermes-telegram-ux-catalog.settings`：

```yaml
language: auto
update_interval: 1.5
status_ttl: 600
cleanup_delay: 1.0
```

- `language`：`auto / zh / en`。自动读取当前消息，忽略代码、URL 和路径；纯数字或仅媒体输入回退中文。升级保留原先明确指定的语言。
- `update_interval`：最小编辑间隔，1–30 秒。
- `status_ttl`：显示无活动超时，30–3600 秒，不取消 Hermes 任务。
- `cleanup_delay`：回合结束后的清理等待，0–5 秒。

修改配置后重启。没有用户／聊天／Topic 偏好系统或内部进度、表情开关。旧菜单偏好不再读取，无需删除用户旧文件。

## 职责与边界

执行、Session、Context、审批、`/stop`、中断、流式输出、最终回答、附件及原生投递恢复仍由 Hermes 负责。插件只观察公开事件，维护自己创建的进度消息，不替代 Hermes、不修改 core、不 monkey patch、不改写最终回答、不读取隐藏思维链。

运行代码只依赖标准库、官方公开插件接口及提供的公开 adapter。路由不确定时不输出状态，不猜测聊天归属、不读取私有任务状态补充信息。初始反馈发生在可安全关联的公开回合事件之后，鉴权前不发消息。

回合结束不是 Telegram 最终投递回执。清理采用有限尝试，删除失败可能留下状态，原生投递较慢时也可能晚于清理。长模型请求可以保持同一条真实汇总状态。官方验证通过不代表已进入官方 Catalog。

## Legacy Full 历史实现

v1.8.3 及以前的 Full 使用较深的 Hermes 内部接入，现已停止维护。历史保留在 [legacy/full-1.8.3](https://github.com/pler1y/hermes-telegram-ux/tree/legacy/full-1.8.3) 和 [v1.8.3](https://github.com/pler1y/hermes-telegram-ux/tree/v1.8.3)。它们只作历史参考，不是推荐安装选项。不要在同一 Gateway 同时启用 Full 和 v2。

[迁移](docs/MIGRATION-v2.md) · [更新记录](CHANGELOG.md) · [v2 验证](docs/VALIDATION-v2.md) · [历史真实验收](docs/VALIDATION.md) · [测试方法](docs/TESTING.md) · [公开 API](docs/PUBLIC-API.md)

MIT License。
