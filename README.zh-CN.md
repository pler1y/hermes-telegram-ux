# Hermes Telegram UX · Hermes插件版

**1.9.0-catalog.1 · 公开插件版** · [发行记录](https://github.com/pler1y/hermes-telegram-ux/releases)

用一条临时气泡显示 Hermes 正在为当前任务做什么：先给出反馈，再随实际工作更新，回合结束后清理。任务补充、排队、停止、审批、流式输出以及答案和文件交付继续使用 Hermes 原生能力。

本版仅使用公开插件接口，目标基线为 Hermes 0.21.3。源码在同仓库 `catalog-safe` 分支独立更新，发行标签使用 `catalog-v*`；尚未进入官方 Plugin Catalog。开发候选的安装包以提交记录为准，发行链接在发布后可用。

当前工作区正在修订此候选，尚未因此产生新发行。已有测试和部署记录仅对应其中注明的源码提交，不代表当前工作区已经部署。

## 使用体验

- **尽早反馈**：在能够可靠关联执行身份的公开回合阶段，先安排“正在思考中…”，再处理任务摘要。后续状态编辑同一条消息，并保留节流和去重。
- **任务相关进度**：从用户任务、实际工具名称和有限的公开参数中提取任务对象。例如搜索 query 可以成为“正在搜索上海未来 7 天的天气…”。已识别的结构化结果可提供搜索结果数量、实际包含的天气字段等事实；信息不足时安全降级。
- **公开进度说明**：保留 `telegram_ux_update`，供模型给出简短的目标、当前动作、发现和下一步。公开模型说明与工具结果证据分开处理，不展示隐藏思考、原始命令或工具全文。
- **临时、简洁的气泡**：通常一行，最多两行。不显示耗时、调用统计或普通任务按钮；正常结束进入最终整理阶段，经过短暂清理窗口后删除。
- **独立设置入口**：`/tgux` 保留首页、示例、原生命令、帮助和设置。只保存当前用户/聊天/话题的语言、进度和表情偏好，从下一轮生效。菜单不附在每轮状态下面。
- **原生控制与交付**：执行中补充要求、使用 `/stop`、审批以及最终答案和附件都由 Hermes 处理。插件不修改最终正文。

普通状态不再保留“✓ 本轮处理已结束”卡片，也不附带“继续处理 / 详情 / 设置 / 关闭提示”。旧的详细显示、答案统计、耗时、对话指引和后续操作偏好不再生效。插件表情设置不改变 Hermes 原生消息反应。

进度和菜单需要可靠的入站上下文。插件仅在执行身份匹配后或已授权的 `/tgux` 命令路径使用单次、60 秒有效的票据；鉴权前不发送消息。检查过的公开 API 没有普通消息“鉴权后、`pre_llm_call` 前且具有可靠路由”的通知，因此第一条气泡仍在 `pre_llm_call` 安排，之前的延迟属于公开插件生命周期限制。丢失上下文、重连或无法关联的排队/后台执行沿用原生显示。

`on_session_end` 代表 Agent 回合结束，不代表 Telegram 已经收到答案。清理窗口只是短暂等待，无法保证气泡一定在最终答案成功投递之后才删除；网络较慢时气泡可能先消失。首次发送结果不明时不重发，编辑失败不另发一条气泡。删除采用有限尝试，失败只影响临时状态，可能留下未删除的消息，不影响 Hermes 最终回答。

## 安装发布包

需要已能正常使用 Telegram 的 Hermes 0.21.3+、Python 3.11–3.13。先结束活动任务并停止该测试 Gateway。不要在同一 Gateway 同时启用 Full 和 Catalog-safe。

从[本版发行页](https://github.com/pler1y/hermes-telegram-ux/releases/tag/catalog-v1.9.0-catalog.1)下载 ZIP 和同名 `.zip.sha256` 文件，在下载目录校验后安装：

```bash
cd /absolute/path/to/delivery
shasum -a 256 -c hermes-telegram-ux-catalog-1.9.0-catalog.1.zip.sha256
CATALOG_HOME="${HERMES_HOME:-$HOME/.hermes}"
CATALOG_DIR="$CATALOG_HOME/plugins/hermes-telegram-ux-catalog"
test ! -e "$CATALOG_DIR" && mkdir -p "$CATALOG_DIR" && \
  unzip -q hermes-telegram-ux-catalog-1.9.0-catalog.1.zip -d "$CATALOG_DIR"
hermes plugins validate "$CATALOG_DIR"
hermes plugins enable hermes-telegram-ux-catalog
```

重启同一 Gateway，在 Telegram 发送 `/tgux`，然后发一条普通请求。ZIP 内的 `PROVENANCE.json` 记录完整源码提交及逐文件摘要。无额外 Python 依赖，不需要运行自定义安装脚本或修改 Hermes core。

也可通过原生 Git 安装固定发布版本：

```bash
CATALOG_COMMIT="$(git ls-remote --refs https://github.com/pler1y/hermes-telegram-ux.git refs/tags/catalog-v1.9.0-catalog.1 | cut -f1)"
test "${#CATALOG_COMMIT}" -eq 40 || { echo "Release tag unavailable" >&2; exit 1; }
hermes plugins install https://github.com/pler1y/hermes-telegram-ux --ref "$CATALOG_COMMIT" --no-enable
hermes plugins validate "${HERMES_HOME:-$HOME/.hermes}/plugins/hermes-telegram-ux-catalog"
hermes plugins enable hermes-telegram-ux-catalog
```

升级继续选择 `catalog-v*` 发布，核对版本后用新 SHA 重装（原生安装加 `--force`），然后验证和启用。不要省略 `--ref`；仓库默认 `main` 提供完整版。两版安装包互不包含，版本号和兼容范围分别维护。

## 设置

只在 Hermes `config.yaml` 中合并本插件命名空间，保留其余配置：

```yaml
plugins:
  entries:
    hermes-telegram-ux-catalog:
      settings:
        language: zh       # zh / en
        progress: true
        emoji: true
        update_interval: 1.5
        status_ttl: 600
        cleanup_delay: 1.0
```

管理员默认设置在 Gateway 启动时读取；用户可通过 `/tgux` 保存语言、进度和表情的覆盖值。`update_interval` 限制在 1–30 秒，`status_ttl` 在 30–3600 秒，`cleanup_delay` 在 0–5 秒，默认 1 秒。长时间没有新事件时，插件状态可短暂提示更新超时，然后进入清理；不会取消模型或工具。

安装不会修改 Hermes 的逐字流式输出、工具进度或中途消息开关。已有原生提示可能与插件状态同时显示。插件不注册最终文字变换，也不接管流式消息。

## 关闭、移除和升级

```bash
hermes plugins disable hermes-telegram-ux-catalog
# 重启 Gateway，确认原生收发正常后：
hermes plugins remove hermes-telegram-ux-catalog
```

升级时先停 Gateway、备份插件目录，验证新包 SHA256，再安装新目录并验证、启用。回退使用备份的旧目录和原配置。活动状态和按钮票据保存在内存中；个人偏好使用公开 `ctx.state` 保存在插件专属数据目录。卸载清除注册、SDK 回调和活动任务，不读写会话数据库；原生 remove 对插件数据的保留策略见 Hermes 提示。

## 开发与验证

此次修订的验收重点是任务相关状态、同消息更新、正确事实边界以及回合结束清理。此前候选的历史结果见 [VALIDATION.md](docs/VALIDATION.md)，其中完成卡和按钮场景不能替代新版临时气泡验收。

以 [TESTING.md](docs/TESTING.md) 复现开发验证；当前进度见 [PROGRESS.md](docs/PROGRESS.md)，真实体验场景见 [ACCEPTANCE.md](docs/ACCEPTANCE.md)。自动化测试与真实 Telegram 结果分别记录。

MIT License。Full 版本请使用独立的 Full 主线及其说明。
