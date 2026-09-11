# 来源与范围

本项目从先前独立开发的 `hermes-interaction` 1.5.0 整理而来，1.6.0 增加通用安装、卸载、恢复、兼容检测、发布文档与独立环境验收。

本仓库不包含 Hermes 核心源码、模型 SDK 或 Telegram SDK 的副本。这些外部依赖按各自许可证分发；核心基线来自 [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent)，Telegram Python 依赖为 [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot)。

进度说明、停止、文件传输和单气泡显示并非本项目独有发明。本项目的范围是将这些交互与 Hermes 当前任务状态、途中补充和所属后台工作衔接起来。

仓库中的库存及活动通知数据为合成验收样本，不包含真实业务资料。

1.7.0 的内部上下文整理提示参考了 [Hermes PR #80262](https://github.com/NousResearch/hermes-agent/pull/80262) 所关注的使用场景。本项目独立实现插件适配，没有复制该 PR 的核心源码。
