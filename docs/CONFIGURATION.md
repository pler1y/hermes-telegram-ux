# 配置选择

首次安装默认为 `recommended`，也可以使用 `--preset keep-display`。重复安装保留首次选择；如需切换预设，先卸载再按新预设安装。可以随时手动修改各项设置，重复安装不会覆盖安装之后的修改。

两个预设都会启用 `plugins.enabled` 中的 `hermes-interaction`，移除 `plugins.disabled` 中同名项，并写入 `plugins.entries.hermes-interaction.allow_gateway_injection=true`。该授权用于插件声明的网关交互能力，详见固定核心的 PluginContext 实现。

两个预设的插件 settings：

| 键 | 初始值 | 用途 |
|---|---:|---|
| `soft_wait` | false | 模型等待阶段也有简短反馈 |
| `status_delay_seconds` | 0.6 | 创建状态气泡前等待 |
| `status_min_edit_seconds` | 2.5 | 常规状态最小编辑间隔 |
| `slow_notice_seconds` | 45 | 长时间无事件的等待提示 |
| `text_batch_seconds` | 0.8 | 连续文字消息的合并静默窗口 |

`recommended` 另写入：

- `agent.gateway_notify_interval=1`
- `display.busy_input_mode=steer`，`display.busy_ack_enabled=true`，`display.busy_steer_ack_enabled=true`
- `display.platforms.telegram` 下：`streaming=false`、`tool_progress=off`、`cleanup_progress=true`、`interim_assistant_messages=false`、`thinking_progress=false`、`long_running_notifications=true`、`busy_ack_enabled=true`、`busy_steer_ack_enabled=true`、`busy_ack_detail=false`、`live_status=off`、`runtime_footer.enabled=false`
- `platforms.telegram.reactions=true`、`platforms.telegram.extra.disable_link_previews=true`

`display` 中的三个全局忙碌输入键以及 `agent.gateway_notify_interval` 也可能影响同一 Gateway 的其他平台。多平台用户应先查看 dry-run，或选择 `keep-display` 并自行配置。

不删除原有 `status_phrases`，也不替换整个 `runtime_footer` 映射，只修改所需叶子配置。对其他值的语义保持不变；使用 PyYAML 写入后，原有注释和 YAML 排版不会保留，原始字节保存在备份中。

卸载按叶子和插件列表成员恢复。若当前值不同于安装器最后一次写入的值，会将其视为用户的新选择予以保留，并在结果的 `preserved_user_changes` 中列出路径。
