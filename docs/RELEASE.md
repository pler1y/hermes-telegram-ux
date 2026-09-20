# Hermes完整版发布

当前发布线为 `main`，版本 **1.8.3**，标签 `v1.8.3`。本版将已完成验收的 rc.2 修复交付给用户。Hermes插件版在 `catalog-safe` 分支、`catalog-v*` 标签下独立发布，规则见 [EDITIONS.md](EDITIONS.md)。

## 发布检查

对五套受支持核心执行 `scripts/run_tests.py`、`check_compatibility.py`、`check_runtime.py`、`check_native_install.py` 与 `check_editions.py`。旧 0.21.0 无官方 validator，其余核心使用 `--require-validator`。保留严格兼容保护，未知核心探测失败不等于已支持核心的回归失败，也不能据此宣称新增兼容。

`scripts/build_release.py` 从允许列表生成确定性的中英文 ZIP、SHA256 与源码清单；修改源码或文档后重建，并用 `--check` 校验。安装生命周期必须针对最终打包内容通过。仅上传发行包、校验文件和不含本机信息的来源记录。

合并主线后核对精确提交，创建轻量 `v*` 标签并发布 Release。原生安装说明从该固定标签解析完整 SHA；标签发布后不移动。GitHub Latest 保留给完整版稳定版，插件版发行不得覆盖此入口。

## 实机证据

运行时修复的 Telegram 验收来自 2026-09-18，见 [FULL-PROGRESS.md](FULL-PROGRESS.md)。发布整理不改变运行逻辑，不把历史验收描述为重新执行。新版核心、群组和其他模型的支持仍需要独立验证。

GitHub 发布与官方插件目录申请是两项工作；本页不执行或暗示目录收录。旧目录候选资料见 [CATALOG.md](CATALOG.md)。
