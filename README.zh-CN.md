# Hermes Telegram UX

[English](README.md)

用一条临时 Telegram 气泡告诉你 Hermes 正在为当前任务做什么。开始工作时给出反馈，随后按真实工具动作和结果更新，任务结束后自动清理。安装、启用，然后正常聊天即可。

当前公开插件实现是今后唯一维护的正式产品。旧 Full 停止开发和跟随 Hermes 更新，仅作历史与 UX 参考，Git 历史和旧 Tag 保留。本目录是尚未发布的收敛候选，尚未改变远端默认分支或创建新版 Release。技术标识 `hermes-telegram-ux-catalog` 暂时保留，以兼容现有安装；它不再代表第二个产品版本。

## 使用体验

- **同一条状态持续更新**：保留消息归属、节流、去重和迟到事件保护。
- **动作与任务对应**：搜索新闻、检查清理代码、读取天气数据等状态来自实际工具活动。
- **有依据才展示结果**：搜索返回数量、确实取得的数据字段、文件不存在、失败和实际后续尝试。不展示原始 Query、路径、命令或隐藏推理。
- **长任务仍有明确对象**：工具阶段结束并进入后续模型请求后，转为相关任务的整理或汇总，不编造阶段制造更新。
- **结束后清理**：只删除插件自己的临时状态。执行、审批、`/stop`、流式输出、最终答案、附件及原生投递恢复由 Hermes 负责。

没有完成卡、按钮、欢迎页、详情、继续处理或设置面板，也没有 `/tgux` 命令。不需要进度提示时，通过 Hermes 禁用插件即可。模型可以使用公开进度工具补充必要的里程碑，但自动工具进度不依赖它。

## 安装与升级

需要已经能正常使用 Telegram 的 Hermes。已验证官方基线为 **Hermes 0.21.3**，commit `3c3ab69abb9b08683b5eb15b4e2b8be1198c875f`；后续版本需重新验证兼容性。无需额外运行时 Python 依赖，不修改 Hermes core。

使用从目标提交构建并审核过的 ZIP，核对 SHA256 和包内 `PROVENANCE.json`，将内容放入 `${HERMES_HOME:-$HOME/.hermes}/plugins/hermes-telegram-ux-catalog`。升级前先停止 Gateway 并备份原插件目录，不要在同一 Gateway 同时启用历史 Full。

```bash
hermes plugins validate /absolute/path/to/plugins/hermes-telegram-ux-catalog --json
hermes plugins doctor /absolute/path/to/plugins/hermes-telegram-ux-catalog --ci
hermes plugins enable hermes-telegram-ux-catalog
```

重启 Gateway，发送一条普通任务即可，没有额外设置菜单。当前候选尚未发布为新 Tag，不要直接安装远端旧默认分支并期待得到此实现。后续统一方式见 [仓库收敛说明](docs/CONVERGENCE.md)。

需要关闭时，运行 `hermes plugins disable hermes-telegram-ux-catalog` 并重启 Gateway；确认原生聊天正常后，可用 `hermes plugins remove hermes-telegram-ux-catalog` 移除。本版不再读写个人偏好数据。已有旧偏好文件即使留在插件专属目录，也不会再生效；无需数据迁移或破坏性删除。

## 配置

默认无需配置。确有需要时，可在 `plugins.entries.hermes-telegram-ux-catalog.settings` 下设置：

```yaml
language: auto
update_interval: 1.5
status_ttl: 600
cleanup_delay: 1.0
```

语言可选 `auto / zh / en`。`auto` 按本轮文本选择中英文，忽略代码块、URL 和路径；纯数字或仅媒体输入回退中文。它是有限的中英文判断，不是任意语言识别。混合语言任务可以由管理员固定语言，不需要维护用户、聊天、Topic 的偏好系统。

其余三项为部署层可靠性参数：编辑节流 1–30 秒，显示无活动超时 30–3600 秒，结束清理等待 0–5 秒；原默认值和时序不变。状态超时不会停止 Hermes 任务。修改配置后重启 Gateway。没有插件内部进度开关或表情开关。

## 边界

只有入站票据、执行身份、用户、聊天及话题能可靠关联时才显示进度；关联不明时沿用原生行为。鉴权前不发送消息，不查询私有会话或后台任务树补充路由。

公开回合结束事件不是 Telegram 最终答案投递回执。清理采用有限尝试，删除失败仍可能留下状态；原生投递较慢时，气泡也可能先删除。不确定首次发送是否成功时不重发，编辑失败不创建替代气泡。Hermes 原生消息仍可独立出现。

运行代码只使用 Python 标准库、公开插件接口及提供的公开 adapter。不再注册 Telegram SDK 按钮回调，不使用 Hermes 私有调用、monkey patch、最终回答变换或第二套任务执行。通过官方验证不等于已进入官方 Plugin Catalog。

[验收记录](docs/VALIDATION.md) · [测试方法](docs/TESTING.md) · [公开 API](docs/PUBLIC-API.md) · [验收标准](docs/ACCEPTANCE.md) · [Full 审计及仓库收敛](docs/CONVERGENCE.md)

MIT License。
