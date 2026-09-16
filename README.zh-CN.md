# Hermes Telegram UX · Catalog-safe

**1.8.3-catalog.1 · 本地候选版**

在 Telegram 中查看 Hermes 当前正在调用工具、请求模型或等待审批。状态独立显示在一条消息中；最终回复仍由 Hermes 发送，使用工具的文字回复可附简短统计。默认中文，也支持英文。

此发行物仅使用公开插件接口，与 Full 独立维护。目标基线是 Hermes 0.21.3，完整提交见 [公开能力清单](docs/PUBLIC-API.md)。尚未发布到远端，也尚未进入 Plugin Catalog。

## 实际能力

| 体验 | Catalog-safe | Full 1.8.3-rc.1 |
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

## 安装本地交付包

需要已能正常使用 Telegram 的 Hermes 0.21.3+、Python 3.11–3.13。先结束活动任务并停止该测试 Gateway。不要在同一 Gateway 同时启用 Full 和 Catalog-safe。

下面使用交付目录中的固定版本 ZIP 和独立 SHA256 校验文件。先确认校验文件来自可信的交付记录，再执行：

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

如从本地 Git 源码安装，使用交付记录中的完整 40 位提交，不选择 `main`：

```bash
hermes plugins install file:///absolute/path/to/catalog-safe-checkout \
  --ref FULL_40_CHARACTER_REVIEWED_COMMIT --no-enable
hermes plugins validate "$CATALOG_HOME/plugins/hermes-telegram-ux-catalog"
hermes plugins enable hermes-telegram-ux-catalog
```

这里的路径和 commit 是操作者提供的本地交付位置；远端正式安装命令要等发布后才可使用。不要对本候选执行无固定 ref 的 `plugins update`，仓库默认分支仍是 Full。

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

以 [TESTING.md](docs/TESTING.md) 执行单元测试、真实 PluginManager 契约测试、官方 validate/doctor、干净安装生命周期与发行包检查。当前进度见 [PROGRESS.md](docs/PROGRESS.md)，真实体验场景见 [ACCEPTANCE.md](docs/ACCEPTANCE.md)。模拟测试与真实 Telegram 结果分别记录。

MIT License。Full 版本请使用独立的 Full 主线及其说明。
