# Historical convergence record

This document preserves the preparation-stage history and decisions. The publication protocol and stable installation identity are described in [RELEASE.md](RELEASE.md); final release results belong to the tagged Release notes.

# v2.0.0 主线收敛准备 — 2026-09-20

已经验收的候选 `c5b8aef94d1f096fbad9ad782b2ad312e9254d33` 已原样上传 `codex/catalog-experience`。fetch 后确认远端旧 main 仍为 `3b2175199d8d9dbafaa39e13c1f5dafd4bf0cfcb`，并已将同一提交保存到 `legacy/full-1.8.3`。`v1.8.3` 保持 `1ed97bfbe9071a179e1a2b8fcc260a573ecc6364` 不动。

`release/v2.0.0` 从候选创建。历史整合提交 `6103f23f65d15d1a0f125b13be817eb7a4e1de90` 的两个父提交依次为上述候选与旧 Full main。采用 `git merge --no-ff -s ours origin/main` 的原因是已审核决定整体使用新插件文件树，同时保留旧 Full 的全部祖先；不是自动取舍未知的代码冲突。整合前后整个文件树经 `git diff --exit-code c5b8aef 6103f23` 验证无差异，两个父提交均为后续发布线祖先。

发布准备只更新版本、安装/兼容/迁移文档和发布验证。`catalog/` 与 `__init__.py` 保持候选字节不变，manifest 仅版本改为 `2.0.0`。不引入 Full `plugin/` runtime、不恢复 interface/preferences，不修改真实测试 Bot 或 Hermes core。

内部 ID 保留 `hermes-telegram-ux-catalog`；原因见 [ID 调查](PLUGIN-ID.md)，旧用户步骤见 [迁移](MIGRATION-v2.md)，当前结果见 [v2 验证](VALIDATION-v2.md)。未来只维护 Hermes Telegram UX，Full 只作历史参考。

本阶段允许上传候选、保存 legacy、上传发布准备分支并创建 `release/v2.0.0 → main` PR。main 合并、v2 Tag/Release、默认分支调整、Catalog 更新与删除旧分支均留待下一次正式授权。旧阶段“不 push”等记录属于当时的范围，保留如下。

---

# Hermes Telegram UX 收敛说明

## 产品与验收边界

未来只维护一个 **Hermes Telegram UX**：当前通过 Hermes 官方公开插件 API 实现的临时进度插件。Full 1.8.3 停止开发及适配新 Hermes，仅作为历史和 UX 参考保留。

Progress Intelligence 的已验收基线是 `77c4a116166e10acf1681500cd51cadf851950f0`。本轮删除外围 UI 和持久化偏好，不重写 `catalog/intelligence.py`、状态优先级或气泡删除时序。本轮代码、自动检查与真实 A–F 回归是否完成，以 [VALIDATION.md](VALIDATION.md) 的最新记录为准；上一阶段验收不能代替本轮回归。

当前收敛内容：删除 `/tgux`、`catalog/interface.py`、`catalog/preferences.py`、Telegram SDK 菜单导入及 `ctx.state` 使用。完成卡、详情、Continue、Close、欢迎导航和普通任务按钮不属于正式产品。保留 **16 hooks、1 个 `telegram_ux_update` tool、0 commands、0 middleware**；只删去服务 `/tgux` 的 `pre_command`，仍观察 interim/subagent 活动以维护相关任务的活动期限，不保留其统计 UI 数据。

设置只剩配置层 `language: auto|zh|en`（默认 auto，按当前消息无状态判断；不明确时回退中文），以及原有 `update_interval=1.5`、`status_ttl=600`、`cleanup_delay=1.0`。后三项继续控制节流、无事件时的展示期限和结束清理延迟，不改变 Hermes 执行。没有 per-user/chat/topic 偏好面板或插件内进度开关；不需要进度时禁用插件。

## Full 1.8.3 的实际位置

两个源码目录是同一仓库 `https://github.com/pler1y/hermes-telegram-ux.git` 的 worktree，并非两个独立仓库。

| 对象 | 本地目录 / Git 身份 |
|---|---|
| Full | `../项目源码`；`main` 为 `3b2175199d8d9dbafaa39e13c1f5dafd4bf0cfcb` |
| Full 发布 Tag | `v1.8.3` 为 `1ed97bfbe9071a179e1a2b8fcc260a573ecc6364`；与上述 main 的代码树完全相同 |
| 当前公开 API 路线 | 本目录所属 `Catalog-safe源码` worktree；开发分支 `codex/catalog-experience` |
| 两线共同祖先 | `8e38243614c1ecc37e0cdcbd4e6e223f920ec895` |

路径相对于 `Catalog-safe源码` 根目录。旧 Full main 是发布合并提交，不应把共同祖先误称为 Full 1.8.3 最终实现。本轮不改 Full 目录、分支或 Tag；其既存未跟踪 `docs/research/` 也不属于清理范围。

## 最后一次 Full 纯 UX 差异审计

审计范围只包括展示、证据、去重与展示可靠性；任务停止、后台取消、迟到最终结果过滤、菜单和私有生命周期接入不属于迁移目标。

| 能力 | Full 1.8.3 实际实现 | 当前路线与取舍 |
|---|---|---|
| 状态分类 | `plugin/progress.py::shell_stage/stage_for_tool` 另分 deploy、verify、recall、复合命令 | 已有任务相关分类；无法可靠细分时保持通用执行提示。额外分类不构成本轮核心缺口 |
| 结果证据 | `TaskProgress.finish` 使用宽松列表计数，部分测试提示由 exit 0 推出“通过” | `catalog/intelligence.py::result_facts` 验证实际搜索条目、读取、数值字段与失败；命令执行结束不等于测试全通过，不迁移旧判定 |
| 并行与慢等待 | `TaskProgress.render` 显示同时运行的步骤数和较久无更新提示 | 当前保留最新实际动作及同批部分失败，真实后续模型请求后进入任务相关汇总；不恢复额外统计、多行等待提示 |
| 去重与归属 | `TaskProgress.start/finish`、`InteractionRuntime._deliver_status` 维护 attempt/owner、发送锁和文本去重 | `catalog/model.py`、`catalog/telegram.py` 已有 turn/message ownership、节流合并、终态保护、路由隔离及有界清理，继续保留 |
| 暂时发送失败 | `InteractionRuntime._defer_status` 指数退避并尊重 `retry_after` | 当前不重试结果不明的初始发送，编辑失败后清理已知消息，删除有两次有界尝试。限流恢复属于未来可选可靠性评估，本轮不改变已冻结 transport |

Full 源码依据固定在 [v1.8.3 progress.py](https://github.com/pler1y/hermes-telegram-ux/blob/1ed97bfbe9071a179e1a2b8fcc260a573ecc6364/plugin/progress.py) 和 [runtime.py](https://github.com/pler1y/hermes-telegram-ux/blob/1ed97bfbe9071a179e1a2b8fcc260a573ecc6364/plugin/runtime.py)；当前对应 [intelligence.py](../catalog/intelligence.py)、[model.py](../catalog/model.py)、[telegram.py](../catalog/telegram.py)。

**审计结论：在最终产品职责内，没有发现必须继续搬迁的明显重要 UX 缺口，不再迁移 Full 功能。** 上述差异是真实取舍，不表示两者功能完全相同。

## 辅助气泡：本轮不实现

已检查官方 Hermes 0.21.3 `3c3ab69abb9b08683b5eb15b4e2b8be1198c875f`：

- `session:compress` 是官方 gateway `hooks/` 系统的**压缩完成**事件，不在 `PluginContext.register_hook` 的 `VALID_HOOKS` 中。普通 payload 只有 `platform/session_id/old_session_id/in_place/compression_count`，没有 Telegram chat/user/topic 或精确任务 turn 路由。
- Codex runtime 的附加 `thread_id/turn_id` 是运行时标识，不能视为 Telegram Topic。即使额外维护 session 到路由的关联，也没有配套的公开压缩开始事件满足本轮需求。
- 压缩开始走 `agent._emit_status`，gateway 通过 `TurnRunner._status_callback_sync` 投递原生状态。Full 的 `plugin/intake.py::patch_gateway` 修改 `_hmwa_hygiene_plan`、`_hmwa_run_session_hygiene`、`_hmwa_hygiene_notify` 及 `TurnRunner._status_callback_sync` 才接入这一体验；不迁移这些 patch。
- 因此不增加“正在整理上下文”辅助气泡，也不为独立后台工作建立第二套路由和生命周期。原生提示保持 Hermes 负责；以后出现可可靠关联用户/chat/topic/turn 的公开事件时再评估。

固定源码依据：[插件 hook 白名单](https://github.com/NousResearch/hermes-agent/blob/3c3ab69abb9b08683b5eb15b4e2b8be1198c875f/hermes_cli/plugins.py)、[压缩开始及完成事件](https://github.com/NousResearch/hermes-agent/blob/3c3ab69abb9b08683b5eb15b4e2b8be1198c875f/agent/conversation_compression.py)（`_announce_compression_start`、`session:compress` fire site）、[gateway 事件与原生状态转发](https://github.com/NousResearch/hermes-agent/blob/3c3ab69abb9b08683b5eb15b4e2b8be1198c875f/gateway/run_turn_runner.py)（`_event_callback_sync`、`_status_callback_sync`）、[Full intake.py](https://github.com/pler1y/hermes-telegram-ux/blob/1ed97bfbe9071a179e1a2b8fcc260a573ecc6364/plugin/intake.py)。这不是“公开压缩事件完全不存在”的结论。

## 以后升级 Hermes 时检查什么

| 公开接口 | 当前依赖 / 必须保持的语义 |
|---|---|
| `pre_gateway_dispatch`、`pre_llm_call` | ingress 的 source/chat/user/topic/profile/message 信息及 session/turn/sender 关联；前者在授权前，只记录票据，不能发送 |
| `pre_tool_call`、`post_tool_call` | call/session/turn IDs、工具名、参数、status/result；结构变化必须保守降级，不从任意正文猜成功 |
| `pre_api_request`、`post_api_request`、`api_request_error` | request ID、retry count、`assistant_tool_call_count`；请求结果不等于 Telegram 已投递 |
| `pre_approval_request`、`post_approval_response` | 明确关联的等待与结果；仅观察，不批准或拒绝 |
| `on_interim_message`、`subagent_start`、`subagent_stop` | 当前 turn / parent turn 的活动关联；不转发正文、不查询内部任务树 |
| `post_llm_call`、`on_session_end`、`on_session_finalize`、`on_session_reset` | 结束与释放自身状态；不把 Agent 完成当作最终消息投递回执 |
| `register_platform_handler("telegram", ...)` 与 adapter `send/edit_message/delete_message` | 工厂生命周期、chat/topic 参数、SendResult 的 success/message_id；只维护自己创建的消息 |
| `PluginContext.register_hook/register_tool/get_config/spawn_task/on_unload` | 注册、配置、异步任务托管和卸载；不重新依赖 Telegram SDK、`ctx.state`、私有 session 数据或宿主属性修改 |

完整接口解释见 [PUBLIC-API.md](PUBLIC-API.md)。入口仍为 `__init__.py → catalog/adapter.py`。`catalog/experience.py` 的指导只服务可选公开进度，不约束回答风格、委派、Memory、Session 或文件交付。没有 stream observer、middleware、final-answer transformer 或自定义最终答案发送器。

ContextVar 票据传播是可缺省的实现条件，不是 Hermes 保证的插件契约；传播或路由不确定时省略状态，不用内部查询补洞。删除失败可能留下自身消息；默认清理延迟不能保证与慢速原生最终发送的严格先后顺序。每次升级继续运行 unit、真实 PluginManager contract、boundary、官方 validate/doctor 和受影响的 Telegram 回归；单一固定版本的成功不证明未来版本兼容或官方 Catalog 已收录。

## 仓库统一准备方案（尚未执行）

1. 新 main 的内容应采用**本轮完成 A–F 后的最终本地提交，以 VALIDATION 为准**。`77c4a11` 是冻结基线，不提前作为瘦身后的最终提交。
2. 保留现有 `v1.8.3`；可增加 `legacy/full-1.8.3` 指向 `3b2175199d8d9dbafaa39e13c1f5dafd4bf0cfcb`，保存旧 main 的发布合并历史。Full 不再开发或跟随 Hermes 更新。
3. 当前 main 不是候选分支的祖先。未来整合可创建同时保留旧 main 与最终候选父提交、内容采用最终候选树的整合提交，再让 main 前进到该提交；不要求删除历史或强推。本轮只准备方案，不调整分支。
4. `catalog-safe`、`feat/catalog-safe`、`fix/catalog-integration-hardening`、`candidate/catalog-1.8.3-rc.1`、`feat/plugin-catalog-readiness` 已存在于候选历史中，统一后可以归档；不在本轮删除。`codex/catalog-experience` 在整合完成后也可作为已完成开发线保留。
5. README 统一为一个产品、一条安装/升级路径和一份职责边界；Full 只链接历史 Tag。未来发布时明确旧安装标识/渠道的迁移方式，避免同一用户同时启用两套实现。

本轮不 push、不 release、不改变远端默认分支。本说明依据本地 Git 与固定核心源码；没有 fetch，也不声称远端当前状态已经同步。
