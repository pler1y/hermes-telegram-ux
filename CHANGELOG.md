# Changelog

## 1.8.0 — 2026-09-12

- Ship native Git installation and configuration from the catalog candidate.
- Fix displaced progress loops and finalizers: old turns cannot consume successor actions or reuse bubbles still owned by native cleanup.
- Retire foreground/background stop state before native stop yields, preserving a successor admitted during cleanup.
- Add the reviewed Hermes 0.21.2 `436ec489854b` baseline and guard 23 integration files, including session state and turn leases. Test all three supported baselines.
- Track the actual official catalog PR #108887. Catalog acceptance and its two-week release maturity requirement remain external; fresh full Telegram/model acceptance on the new core is not claimed.

## 1.8.0-rc.1 — Catalog preparation candidate

- Add native Git installation, configuration and configuration-only recovery that preserve Hermes-managed source and provenance metadata.
- Validate Hermes 0.21.0 and 0.21.2 baselines using complete 19-file interface sets; allow unrelated commits with matching interfaces and reject mixed or modified sets.
- Declare both middleware registrations and use the manifest format supported by the native installer. Handle registration contexts without optional durable state.
- Add official admission checks, native install/enable/Telegram wiring/remove checks, two-baseline CI, current-main compatibility checks, and catalog submission draft generation.
- Preserve the existing Telegram interaction design. New-core live acceptance and the official two-week maturity period remain required before catalog submission.

## 1.7.1 — 2026-09-12

- Respect Telegram's retry delay across status bubbles on the same bot; progressively back off after transport failures and resume with the latest status.
- Preserve native queue, steer and redirect receipts in the progress bubble. Early busy feedback only acknowledges receipt while routing is pending.
- Apply `soft_wait` to the active task progress and intake paths, while keeping substantive work, important notices and long waits visible.
- Add bilingual conversation examples and a read-only compatibility check to the README installation flow.

## 1.7.0

- Telegram 收到消息后立即接话，再在同一条气泡中更新任务进度。问候、致谢和任务请求使用自然的短回应。
- 新增上下文整理提示，覆盖回合开始前及执行中的压缩。停止、异常和审批继续优先显示。
- 提供固定中文、英文安装包，包含对应的菜单、按钮、状态文案和模型公开进度提示；仓库增加英文首页和安装指南。
- 按实际任务阶段搭配 emoji，尊重模型已经使用的表情，避免重复装饰与无意义轮播。
- 扩展接话交接、授权隔离、语言一致性及两种发行包安装/卸载检查。

## 1.6.0 — 2026-09-11

首个公开发行版。

- 提供独立安装包，支持安装、升级、卸载和故障恢复。
- 增加显示预设，保留用户后续修改的配置。
- 增加 Hermes 核心版本检查。
- 修复卸载后菜单与按钮处理器未清理的问题。
- 修复权限检查提示覆盖任务进度的问题。
- 修复修改显示配置后无法卸载的问题。
- 补充安装、配置及开发文档。

## 1.5.0

增加任务进度、途中补充、前后台任务衔接和自然语言停止。
