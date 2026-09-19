# Full candidate releases

当前开发版本为 **1.8.3-rc.2 Full**，用于停止、会话归属、进度证据与安装配置修复。完整测试和专用 Bot 结果记录在 [Full 维护进度](FULL-PROGRESS.md)。正式发布前须完成受支持核心回归、原生/ZIP 安装生命周期、源码清单与真实 Telegram 验证；保留精确兼容检查。当前候选没有发布到远端。

以下为上一候选的历史记录，目录收录流程不再代表 Full 的发布路线。

# 发布与目录候选

上一开发版本为 **1.8.3-rc.1**，保留 1.8.2 的界面和停止语句行为，增加目录验证及当前核心适配。已发布的 1.8.2 标签和附件保持不变。本次只准备本地候选，不发布 release、不创建或更新上游 PR。

## 候选检查与构建

使用已支持 Hermes 的 Python 环境（设置 `PYTHONPATH` 指向 core），运行：

```bash
python scripts/run_tests.py
python scripts/check_compatibility.py --hermes-core "$HERMES_CORE"
python scripts/check_runtime.py
python scripts/check_native_install.py --require-validator --report native-report.json
python scripts/build_release.py
python scripts/build_release.py --check
python scripts/check_editions.py
```

对全部五套支持基线检查回归和原生生命周期；0.21.0 没有官方 validator，明确记录为不可用，不作为 admission 成功。新核心对应的上游批处理、审批、任务租约和后台持久化回归也要完成。详见 [候选验证](VALIDATION-1.8.3-rc.1.md)。

构建器只读取允许列表，检查敏感内容和 Python 语法，生成确定性的中英文 ZIP、SHA-256 校验文件及 `release-manifest.json`。新增或修改代码/文档后必须重建；不要修改已发布 ZIP。提交候选时不包含忽略的 `dist/`、`catalog-submission/` 或本地测试报告，也不带入既有未跟踪研究资料。

## 发布说明

- 支持新增官方 core `5eb99eb2844b22ebb723711b8e6a0bbb80bb5f04`，保留原四套基线。
- 完整源码/AST 检查外，再核对核心版本与基线清单完整性；未知代码在注册前拒绝。
- 两处 middleware 声明与真实注册一致；官方验证器验证根目录、payload 和原生安装后的目录，并有漏声明失败样本。
- 原生 enable 即可加载；配置助手仍用于语言、显示和按钮权限配置，并保留配置恢复功能。
- 自然停止和首页菜单被插件消费时，补齐原生事件观察，避免新核心把已处理消息误报为分发停滞。
- 目录草案可以从未发布的本地提交生成，但不会伪造发布时间、两周成熟状态或公开可克隆性。

自动验证未发送真实 Telegram 消息或调用模型，不代表完成新版实机验收。历史记录仍见 ACCEPTANCE-1.7.0.md。

## 之后正式发行时

确认候选、提交新版本并完成 CI，再创建新标签和 release，附两种 ZIP 与校验和。原生用户以该发布对应的完整 SHA 安装；不要让 README 的旧 SHA 冒充新候选。按实际 GitHub 发布时间运行 `prepare_catalog.py` 生成目录条目与成熟时间。

只有用户后续明确要求时才向上游提交或更新 PR。候选提交的公开可达性、官方 CI、成熟期与维护者审查仍需逐项满足；[目录说明](CATALOG.md)给出准确边界。
