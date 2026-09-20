# Hermes Telegram UX · Hermes插件版

**1.9.0-catalog.1 · 公开插件版** · [下载安装包](https://github.com/pler1y/hermes-telegram-ux/releases/tag/catalog-v1.9.0-catalog.1)

让 Telegram 中的 Hermes 任务更容易跟进：自然的实时进度、操作菜单、后续请求入口和个人显示偏好。任务补充、排队、停止、审批以及答案和文件交付继续使用 Hermes 原生能力。

本版仅使用公开插件接口，目标基线为 Hermes 0.21.3。源码在同仓库 `catalog-safe` 分支独立更新，发行标签使用 `catalog-v*`；尚未进入官方 Plugin Catalog。开发候选的安装包以提交记录为准，发行链接在发布后可用。

## 使用体验

- **实时任务汇报**：同一条进度消息持续更新，自然描述读文件、检索资料等动作。多步任务可补充目标、当前动作、已确认发现和下一步；可关联子任务显示完成/运行/异常汇总。等待时显示耗时，原生审批和失败有明确提示。
- **操作面板**：发送 `/tgux` 打开首页、示例任务、常用命令、帮助和设置。按钮只允许打开该卡片的用户操作，一小时后过期，重启后重新打开即可。
- **结果与继续处理**：完整答案和文件由 Hermes 发送。状态卡结束后可查看详情、关闭或选择后续请求。后续请求由用户点选发送，沿用原生鉴权和排队；插件不会替用户自动执行。
- **个人偏好**：在当前聊天/话题内保存自己的语言、简洁/详细、进度、统计、表情、耗时提示、对话指引和后续操作偏好。不会改变其他用户或管理员的全局配置，从下一轮生效。
- **原生控制**：执行中直接补充要求；需要停止时使用 `/stop`。关闭进度提示仅隐藏插件消息。

默认最终答案保持原样，不追加调用统计；可通过设置开启。详情中的计数只代表实际观察到的事件，不是计费记录。插件表情设置不改变 Hermes 原生消息反应。

进度和菜单需要可靠的入站上下文。插件仅在执行身份匹配后或已授权的 `/tgux` 命令路径使用单次、60 秒有效的票据；鉴权前不发送消息。丢失上下文、重连或无法关联的排队/后台执行沿用原生显示。对话指引是模型指导，公开进度说明不代替实际执行证据。

状态卡显示回合结束，不声称 Telegram 已收到最终答案。卡片可保留或手动关闭；不修改原生答案、流式输出、中途消息或上下文整理流程。可观察的子任务仅在明确父会话/回合关联下汇总，不接管其他后台任务。

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
        display: brief    # brief / detail
        emoji: true
        wait_hint: true
        conversation_style: true
        followups: true
        final_summary: false
        update_interval: 1.5
        status_ttl: 600
```

管理员默认设置在 Gateway 启动时读取；用户可通过 `/tgux` 设置菜单保存自己的覆盖值。`update_interval` 限制在 1–30 秒，`status_ttl` 在 30–3600 秒。长时间没有新事件时显示“状态更新已超时”，只停止插件状态更新，不取消模型或工具。关闭 `final_summary` 可保持最终回复逐字不变。

安装不会修改 Hermes 的逐字流式输出、工具进度或中途消息开关。已有原生进度可能与插件状态同时显示；按个人喜好配置 Hermes。流式显示是否采用最终文字变换取决于宿主的原生交付路径，本版不接管流式消息。

## 关闭、移除和升级

```bash
hermes plugins disable hermes-telegram-ux-catalog
# 重启 Gateway，确认原生收发正常后：
hermes plugins remove hermes-telegram-ux-catalog
```

升级时先停 Gateway、备份插件目录，验证新包 SHA256，再安装新目录并验证、启用。回退使用备份的旧目录和原配置。活动状态和按钮票据保存在内存中；个人偏好使用公开 `ctx.state` 保存在插件专属数据目录。卸载清除注册、SDK 回调和活动任务，不读写会话数据库；原生 remove 对插件数据的保留策略见 Hermes 提示。

## 开发与验证

本版增加了菜单权限、个人设置、子任务关联、显示关闭和后续请求验证。各项实际验证结果与未覆盖范围见 [VALIDATION.md](docs/VALIDATION.md)。

以 [TESTING.md](docs/TESTING.md) 复现开发验证；当前进度见 [PROGRESS.md](docs/PROGRESS.md)，真实体验场景见 [ACCEPTANCE.md](docs/ACCEPTANCE.md)。自动化测试与真实 Telegram 结果分别记录。

MIT License。Full 版本请使用独立的 Full 主线及其说明。
