# 文档导航 · Documentation

项目概览：[中文](../README.zh-CN.md) · [English](../README.md)

**安装使用请选择稳定版 1.8.2。** 当前开发分支是尚未发布的 1.8.3-rc.1 候选；两者支持的核心基线不同。开始安装前，先确认 [1.8.2 的兼容范围](https://github.com/pler1y/hermes-telegram-ux/blob/v1.8.2/docs/COMPATIBILITY.md)。

**For installation, use stable release 1.8.2.** The development branch is the unpublished 1.8.3-rc.1 candidate, with an additional supported core. Check the stable release's compatibility before installing. Both README pages cover installation and everyday use; many detailed guides below are in Chinese.

## 安装与使用 · Installation and use

| 文档 / Guide | 内容 / Purpose |
| --- | --- |
| [原生安装 / Native installation](NATIVE-INSTALL.md) | 通过 Hermes 安装、升级和移除；Hermes-managed installation, upgrades, and removal |
| [ZIP 安装](INSTALLATION.md) · [English ZIP guide](INSTALLATION.en.md) | 下载包校验与手动安装；release archives and manual installation |
| [从零开始 / Fresh environment](FRESH-INSTALL.md) | 模型登录、Telegram 与环境准备 |
| [配置 / Configuration](CONFIGURATION.md) | 语言、显示预设和进度设置 |
| [稳定版兼容 / Stable compatibility](https://github.com/pler1y/hermes-telegram-ux/blob/v1.8.2/docs/COMPATIBILITY.md) | 1.8.2 支持的核心与接口边界 |
| [恢复 / Recovery](RECOVERY.md) | 备份、中断恢复和配置冲突 |
| [更新日志 / Changelog](../CHANGELOG.md) | 各版本的用户可见变化 |

## 开发与目录 · Development and repository map

从[贡献指南](../CONTRIBUTING.md)开始，按[测试说明](TESTING.md)准备独立环境。开发分支的核心支持与维护策略见[兼容表](COMPATIBILITY.md)，打包方式见[发布说明](RELEASE.md)。

Start with [Contributing](../CONTRIBUTING.md). The [testing guide](TESTING.md), [development compatibility table](COMPATIBILITY.md), and [release guide](RELEASE.md) document checks and packaging.

| 路径 / Path | 职责 / Responsibility |
| --- | --- |
| [plugin/](../plugin/) | 插件实现：接收输入、进度、控制、交付和界面文案；plugin behavior and presentation |
| [plugin/runtime.py](../plugin/runtime.py) | Hermes 运行期接线与适配；runtime integration |
| [plugin/compat.py](../plugin/compat.py) · [compatibility.json](../plugin/compatibility.json) | 核心兼容检查与已验证基线；core guard and supported baselines |
| [plugin.yaml](../plugin.yaml) · [__init__.py](../__init__.py) | Hermes 发现与加载入口；plugin manifest and entry point |
| [install.py](../install.py) | 配置、ZIP 安装和恢复；setup and recovery |
| [scripts/](../scripts/) | 测试、兼容检查、打包和目录准备；verification and release tooling |
| 根目录 `test_*.py` | 按功能拆分的回归测试；feature-focused regression tests |
| [acceptance/](../acceptance/) | 实机验收素材和结果检查；live acceptance fixtures |
| [docs/](./) | 使用、开发和发布记录；guides and release records |

## 版本与验证 · Releases and validation

- [已发布版本 / Published releases](https://github.com/pler1y/hermes-telegram-ux/releases)：安装包与校验文件。
- [1.7.0 实机验收](ACCEPTANCE-1.7.0.md)、[1.8.0 验证](VALIDATION-1.8.0.md)、[1.8.1 验证](VALIDATION-1.8.1.md)：对应版本的历史验证范围。
- [1.8.3-rc.1 候选验证](VALIDATION-1.8.3-rc.1.md)、[候选进度](CANDIDATE-PROGRESS.md)、[目录状态](CATALOG.md)：当前候选的开发与收录准备。
- [验收方法](ACCEPTANCE.md)：可复用的体验检查步骤。

自动化覆盖和历史实机记录分别说明验证范围；候选版本的新核心支持不代表已经完成新的 Telegram 全流程实机验收。Release records describe their own versions; automated checks and historical live acceptance are not interchangeable.

使用 OpenClaw 时，请选择独立的 [OpenClaw Telegram UX](https://github.com/pler1y/openclaw-telegram-ux)。For OpenClaw, use that plugin's installation and compatibility instructions.
