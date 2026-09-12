# 发布构建

发行版提供中文 `-zh.zip`、英文 `-en.zip` 两份源码 ZIP 和 SHA-256 校验和，可从 [Releases](https://github.com/pler1y/hermes-telegram-ux/releases)下载。

## 构建

```bash
python scripts/build_release.py
python scripts/build_release.py --check
```

产物输出到 `dist/`。两个版本只更换语言标记，均附中英文文档，每份 ZIP 有独立的完整性清单。

在支持的 Hermes Python 环境中运行 `python scripts/check_editions.py`，会分别验证两份 ZIP 的哈希、安装、重复安装、原生插件注册与卸载恢复。

构建脚本按文件清单打包，检查 Python 语法和常见凭据格式，并生成 `release-manifest.json`。相同源码会生成相同的 ZIP 校验和。

修改项目文件后重新构建，再提交更新后的清单；CI 会检查源码与清单是否一致。配置、凭据、会话及备份文件不属于发行内容。

## 发布

运行 [开发检查](TESTING.md)，为通过检查的提交创建版本标签，并上传对应的 ZIP 和校验和文件。

仓库文档可以持续更新；已发布版本的源码以标签为准。文档修订无需替换原版本的安装附件。

新增核心版本支持时，更新 `plugin/compatibility.json` 并完成兼容与实际使用验证。依赖来源和许可证见 [NOTICE.md](../NOTICE.md)。

## 官方目录发行版

`1.8.1` 是发布到主分支的正式版本。构建清单中的 `tested_core_commits` 列出四套受支持基线，替代此前单一的 `core_commit` 字段。

发布前运行四套核心的回归、原生安装及当前核心官方验证，再发布中英文源码包。新核心上的 Telegram 实机验收结果单独记录，不以自动检查代替。根据 GitHub 实际发布时间运行 `scripts/prepare_catalog.py` 生成精确 SHA 目录条目及两周成熟时间，再更新已提交的官方 PR。可审查、已合并及已上架是不同状态，详见 [CATALOG.md](CATALOG.md)。
