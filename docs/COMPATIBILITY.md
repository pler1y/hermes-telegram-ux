# 兼容边界

本版本以 Hermes commit `b499ab11fe8b081470e269f2fb27abae03000da5` 为唯一测试基线。`plugin/compatibility.json` 固定所使用的 15 个核心接口文件 SHA-256；Git checkout 还需提交一致。源码归档没有 Git 元数据时仍需文件哈希一致。

兼容检查发生在安装前和 `register(ctx)` 注册前；失败不会先打上一半补丁。检查器不在插件发现线程导入 `gateway.run`，避免发现锁与网关导入相互等待。

公开接口包括 tools、hooks、middleware、系统提示区块和 Telegram platform handler。内部适配涉及消息入口、回合前及回合中的上下文压缩、长任务通知、忙碌输入回执、停止、后台完成消费、Telegram 发送与编辑、部分显示清理。内部接口没有跨任意版本的稳定保证。

运行期不修改 Hermes 源码文件。关闭插件并重启进程后，这些运行期适配消失。与修改同一入口的第三方插件同时使用尚未验证；重复安装进同一进程会明确报错。

Schema 中的 `_hermes_progress` 是展示元数据，在实际工具 hooks、审批和执行前移除。只对已支持的 OpenAI / Codex 简单参数结构启用 strict 转换；其他提供方保留原生结构并增加公开说明字段。可选参数的空占位会恢复为省略，原本合法的 null 保留。

提供固定中英文界面；模型生成内容通过所选语言的提示规范引导。群聊、话题与身份隔离有回归覆盖，本版完整实机流程以私人聊天为主。

上游参考：[原生插件开发文档](https://hermes-agent.nousresearch.com/docs/developer-guide/plugins/)。安装行为以这里固定的核心源码和本项目测试结果为准，不把上游未来变化当作已兼容。
