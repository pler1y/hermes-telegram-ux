# 发布清单

项目名称：中文 **Hermes Telegram 交互增强**；英文 **Hermes Telegram UX**；仓库名 **hermes-telegram-ux**。

当前交付是 1.6.0 源码与可复现 ZIP，已完成固定环境安装和实际 Telegram 验收。公开源码位于 [pler1y/hermes-telegram-ux](https://github.com/pler1y/hermes-telegram-ux)，安装包与校验和位于 [v1.6.0 发行页](https://github.com/pler1y/hermes-telegram-ux/releases/tag/v1.6.0)。仓库只包含独立项目文件。

- [x] 公共源码与原生插件元数据；内部 ID 保持升级兼容
- [x] 通用安装、选择预设、版本检查、卸载、事务恢复
- [x] README、配置、兼容、测试、恢复和安全文档
- [x] 112 项无跳过回归、原生注册检查与脱敏实机记录
- [x] GitHub Actions 工作流；相同测试命令已在新依赖环境运行
- [x] 合成验收样本与独立产物检查脚本
- [x] `.gitignore`、来源说明、MIT LICENSE 文件
- [x] 白名单归档、逐文件 SHA-256、归档 SHA-256、秘密格式扫描

本项目使用 MIT 许可证，版权行使用项目贡献者名称。外部依赖的来源与许可范围见 [NOTICE.md](../NOTICE.md)。

构建：

```bash
python scripts/build_release.py
python scripts/build_release.py --check
```

产物位于 `dist/`。同一源码重复构建生成同一 ZIP 校验和；`release-manifest.json` 记录所有公开文件的 SHA-256。修改任意公开文件后需重新构建，CI 会拒绝过期清单。

扫描覆盖 Bot token、常见私钥、GitHub/OpenAI token、具体用户目录和长认证令牌赋值等格式；另人工检查了发行文件列表。扫描不能数学上证明不存在任何秘密，所以仍禁止将真实配置、备份、OAuth、聊天记录或运维交接加入公开目录。

新核心支持必须先重新完成兼容及实机检查，再更新 compatibility.json；不要删除版本检查来使未知环境“看起来能装”。
