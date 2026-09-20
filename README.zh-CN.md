# Hermes Telegram UX · Hermes插件版

**1.8.3-catalog.1 · 公开插件版** · [下载安装包](https://github.com/pler1y/hermes-telegram-ux/releases/tag/catalog-v1.8.3-catalog.1)

在 Telegram 中查看 Hermes 当前正在调用工具、请求模型或等待审批。状态独立显示在一条消息中；最终回复仍由 Hermes 发送，使用工具的文字回复可附简短统计。默认中文，也支持英文。

此发行物仅使用公开插件接口，与 Full 独立维护。目标基线是 Hermes 0.21.3，完整提交见 [公开能力清单](docs/PUBLIC-API.md)。源码在同仓库 `catalog-safe` 分支独立更新，发行标签使用 `catalog-v*`；尚未进入官方 Plugin Catalog。

## 实际能力

| 体验 | Catalog-safe | Full 1.8.3 |
|---|---|---|
| 工具、模型请求反馈 | 根据公开事件更新，合并频繁编辑 | 支持 |
| 审批等待、拒绝、超时、撤回 | 观察并显示；使用原生审批按钮 | 支持 |
| 中途说明 | 保留原生消息，状态显示收到阶段说明 | 可纳入统一进度 |
| 最终文字回复 | 保留原文，工具任务可附调用统计 | 支持整合展示 |
| 收到消息立即响应 | 从执行开始事件出现状态 | 支持 intake 响应 |
| 忙碌时追加消息 | Hermes 原生行为 | 自定义确认 |
| 停止 | 使用原生 `/stop`；只观察实际结束结果 | 自然语言停止和自定义回执 |
| 后台完成组 | Hermes 原生行为 | 自定义渲染 |
| 单气泡覆盖完整生命周期 | 不承诺；独立状态消息和最终回复 | 支持 |
| 自定义首页、后续操作按钮 | 不提供；`/tgux` 显示本版说明 | 支持 |
| 核心源码指纹、私有方法重绑 | 无 | 有严格兼容保护 |

状态消息依赖可靠的入站消息与执行事件关联：插件使用单次、60 秒有效的 Python 上下文票据，并检查公开 sender/profile 字段。没有上下文传播、缺少身份、过期、重连、子代理或后台启动时，不发送额外状态。排队后重建的执行上下文可能只显示 Hermes 原生进度。这一降级不影响最终回复。群组和话题保留原始回复锚点；应在自己的环境完成验收。

统计仅代表插件实际观察到的带 ID 事件，不是计费记录。模型请求结束不等于任务完成；本轮结束不等于 Telegram 已确认收到最终消息。状态消息不会复制命令、工具结果、审批命令或模型的中途正文。结束后的状态消息保留供回看。

## 安装发布包

需要已能正常使用 Telegram 的 Hermes 0.21.3+、Python 3.11–3.13。先结束活动任务并停止该测试 Gateway。不要在同一 Gateway 同时启用 Full 和 Catalog-safe。

从[本版发行页](https://github.com/pler1y/hermes-telegram-ux/releases/tag/catalog-v1.8.3-catalog.1)下载 ZIP 和同名 `.zip.sha256` 文件，在下载目录校验后安装：

```bash
cd /absolute/path/to/delivery
shasum -a 256 -c hermes-telegram-ux-catalog-1.8.3-catalog.1.zip.sha256
CATALOG_HOME="${HERMES_HOME:-$HOME/.hermes}"
CATALOG_DIR="$CATALOG_HOME/plugins/hermes-telegram-ux-catalog"
test ! -e "$CATALOG_DIR" && mkdir -p "$CATALOG_DIR" && \
  unzip -q hermes-telegram-ux-catalog-1.8.3-catalog.1.zip -d "$CATALOG_DIR"
hermes plugins validate "$CATALOG_DIR"
hermes plugins enable hermes-telegram-ux-catalog
```

重启同一 Gateway，在 Telegram 发送 `/tgux`，然后发一条普通请求。ZIP 内的 `PROVENANCE.json` 记录完整源码提交及逐文件摘要。无额外 Python 依赖，不需要运行自定义安装脚本或修改 Hermes core。

也可通过原生 Git 安装固定发布版本：

```bash
CATALOG_COMMIT="$(git ls-remote --refs https://github.com/pler1y/hermes-telegram-ux.git refs/tags/catalog-v1.8.3-catalog.1 | cut -f1)"
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
        final_summary: true
        update_interval: 1.5
        status_ttl: 600
```

设置在 Gateway 启动时读取。`update_interval` 限制在 1–30 秒，`status_ttl` 在 30–3600 秒。长时间没有新事件时显示“状态更新已超时”，只停止插件状态更新，不取消模型或工具。关闭 `final_summary` 可保持最终回复逐字不变。

安装不会修改 Hermes 的逐字流式输出、工具进度或中途消息开关。已有原生进度可能与插件状态同时显示；按个人喜好配置 Hermes。流式显示是否采用最终文字变换取决于宿主的原生交付路径，本版不接管流式消息。

## 关闭、移除和升级

```bash
hermes plugins disable hermes-telegram-ux-catalog
# 重启 Gateway，确认原生收发正常后：
hermes plugins remove hermes-telegram-ux-catalog
```

升级时先停 Gateway、备份插件目录，验证新包 SHA256，再安装新目录并验证、启用。回退使用备份的旧目录和原配置。插件的状态仅保存在内存中，卸载清除注册及活动状态任务，不读写会话数据库。

## 开发与验证

已完成 33 项单元/边界测试和 4 项真实宿主契约测试，以及官方验证、两种干净安装流程和真实 Telegram 验收。具体结果与未覆盖范围见 [VALIDATION.md](docs/VALIDATION.md)。

以 [TESTING.md](docs/TESTING.md) 复现开发验证；当前进度见 [PROGRESS.md](docs/PROGRESS.md)，真实体验场景见 [ACCEPTANCE.md](docs/ACCEPTANCE.md)。自动化测试与真实 Telegram 结果分别记录。

MIT License。Full 版本请使用独立的 Full 主线及其说明。
