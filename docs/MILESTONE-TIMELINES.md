# 动态任务进度：四类公开事件回放

> 本页保留本地实现阶段的验证范围与历史结果；后续真实模型、Telegram 验收及最终回归见 [LIVE-MILESTONE-ACCEPTANCE.md](LIVE-MILESTONE-ACCEPTANCE.md)。

由 `python scripts/check_milestones.py --write-doc` 生成。以下输入均为人工编写的公开事件、工具参数和结果夹具；没有运行模型、访问 Telegram、执行所列命令或查询真实网站。Grok 与 Aurora 的输入用于检验通用状态机制，不构成产品发布或项目动态事实。

状态文本直接记录自已注册的公开 hook → `HermesCatalogAdapter` → `TelegramPanels` → 测试 transport 的 send/edit/delete 调用，未手写预期时间线。每步留出显示窗口，因此展示的是可见阶段回放；真实运行中的快速事件可能按现有节流规则合并。静默步骤只推进测试时钟并调用显示刷新，不冒充经过等量墙钟时间。

本回放验证状态协同与消息生命周期，不能验证 Hermes 是否主动选择调用该工具、真实调用频率、模型是否忠实理解来源、真实 Telegram 延迟或原生最终回答送达。Milestone 均由脚本明确调用已注册的工具 handler；finding 的事实支持另由专项回归检查。

## 发布信息调查

模拟用户请求：Grok 4.6 什么时候发布？

主动 milestone：3 次。1 次 send，10 次 edit，1 次 delete。

| 顺序 | 公开事件 / 测试步骤 | transport 可见变化 |
| --- | --- | --- |
| 1 | 已授权的 pre_llm_call：建立本轮临时气泡 | send：🤔 思考中… |
| 2 | 普通模型请求及返回 / pre | 无 send/edit/delete |
| 3 | 普通模型请求及返回 / post | 无 send/edit/delete |
| 4 | 静默 45 秒（推进测试时钟并调用显示刷新） | 无 send/edit/delete |
| 5 | 搜索官方发布信息 / pre | edit：🔎 搜索 Grok 4.6 的官方发布信息… |
| 6 | 搜索官方发布信息 / post | edit：📊 找到 8 条结果，继续核对… |
| 7 | 普通模型请求及返回 / pre | 无 send/edit/delete |
| 8 | 普通模型请求及返回 / post | 无 send/edit/delete |
| 9 | 静默 45 秒（推进测试时钟并调用显示刷新） | 无 send/edit/delete |
| 10 | 公开 milestone：跨来源比较 / pre | 无 send/edit/delete |
| 11 | 公开 milestone：跨来源比较 / post | edit：🕒 核对不同来源中的发布日期… |
| 12 | 普通模型请求及返回 / pre | 无 send/edit/delete |
| 13 | 普通模型请求及返回 / post | 无 send/edit/delete |
| 14 | 静默 45 秒（推进测试时钟并调用显示刷新） | 无 send/edit/delete |
| 15 | 读取公告来源 / pre | edit：📖 阅读 x.ai… |
| 16 | 读取公告来源 / post | edit：📖 已读取 x.ai，继续核对… |
| 17 | 公开 milestone：比较资料 / pre | 无 send/edit/delete |
| 18 | 公开 milestone：比较资料 / post | edit：🕒 比较官方资料与其他来源的日期… |
| 19 | 补充查找来源 / pre | edit：🔎 搜索 Grok 4.6 官方更新记录… |
| 20 | 补充查找来源 / post | edit：📊 找到 1 条结果，继续核对… |
| 21 | 公开 milestone：整理结果 / pre | 无 send/edit/delete |
| 22 | 公开 milestone：整理结果 / post | edit：✍️ 整理发布时间线… |
| 23 | post_llm_call：模拟原生回答已生成（内容不复制） | edit：✍️ 整理回答… |
| 24 | on_session_end(completed=True)：清理临时气泡 | delete：删除 owned-status |
| 25 | 等待本轮 transport 工作任务结束 | 无 send/edit/delete |
| 26 | 迟到的工具事件（已结束的轮次） | 无 send/edit/delete |

## 代码清理问题检查

模拟用户请求：检查这个项目为什么状态消息没有被删除

主动 milestone：3 次。1 次 send，10 次 edit，1 次 delete。

| 顺序 | 公开事件 / 测试步骤 | transport 可见变化 |
| --- | --- | --- |
| 1 | 已授权的 pre_llm_call：建立本轮临时气泡 | send：🤔 思考中… |
| 2 | 普通模型请求及返回 / pre | 无 send/edit/delete |
| 3 | 普通模型请求及返回 / post | 无 send/edit/delete |
| 4 | 静默 45 秒（推进测试时钟并调用显示刷新） | 无 send/edit/delete |
| 5 | 定位清理入口 / pre | edit：🔍 定位… |
| 6 | 定位清理入口 / post | edit：📊 当前步骤已完成，核对结果… |
| 7 | 公开 milestone：检查生命周期 / pre | 无 send/edit/delete |
| 8 | 公开 milestone：检查生命周期 / post | edit：📝 检查状态气泡的清理入口… |
| 9 | 读取消息清理代码 / pre | edit：📖 检查 telegram.py… |
| 10 | 读取消息清理代码 / post | edit：📖 已读取 telegram.py，继续核对… |
| 11 | 普通模型请求及返回 / pre | 无 send/edit/delete |
| 12 | 普通模型请求及返回 / post | 无 send/edit/delete |
| 13 | 静默 45 秒（推进测试时钟并调用显示刷新） | 无 send/edit/delete |
| 14 | 公开 milestone：检查触发条件 / pre | 无 send/edit/delete |
| 15 | 公开 milestone：检查触发条件 / post | edit：📝 核对消息删除的触发条件… |
| 16 | 运行清理测试 / pre | edit：🧪 运行相关测试… |
| 17 | 运行清理测试 / post | edit：🧪 测试命令已执行完，核对结果… |
| 18 | 公开 milestone：整理原因 / pre | 无 send/edit/delete |
| 19 | 公开 milestone：整理原因 / post | edit：✍️ 整理状态消息未删除的原因… |
| 20 | post_llm_call：模拟原生回答已生成（内容不复制） | edit：✍️ 整理回答… |
| 21 | on_session_end(completed=True)：清理临时气泡 | delete：删除 owned-status |
| 22 | 等待本轮 transport 工作任务结束 | 无 send/edit/delete |
| 23 | 迟到的工具事件（已结束的轮次） | 无 send/edit/delete |

## 文件与数据分析

模拟用户请求：分析销售数据文件中的关键指标与异常记录

主动 milestone：3 次。1 次 send，10 次 edit，1 次 delete。

| 顺序 | 公开事件 / 测试步骤 | transport 可见变化 |
| --- | --- | --- |
| 1 | 已授权的 pre_llm_call：建立本轮临时气泡 | send：🤔 思考中… |
| 2 | 普通模型请求及返回 / pre | 无 send/edit/delete |
| 3 | 普通模型请求及返回 / post | 无 send/edit/delete |
| 4 | 静默 45 秒（推进测试时钟并调用显示刷新） | 无 send/edit/delete |
| 5 | 读取数据文件 / pre | edit：📖 读取 sales.csv… |
| 6 | 读取数据文件 / post | edit：📖 已读取 sales.csv，继续核对… |
| 7 | 公开 milestone：检查字段 / pre | 无 send/edit/delete |
| 8 | 公开 milestone：检查字段 / post | edit：📝 检查月份与收入字段… |
| 9 | 普通模型请求及返回 / pre | 无 send/edit/delete |
| 10 | 普通模型请求及返回 / post | 无 send/edit/delete |
| 11 | 静默 45 秒（推进测试时钟并调用显示刷新） | 无 send/edit/delete |
| 12 | 计算关键指标 / pre | edit：🧮 计算… |
| 13 | 计算关键指标 / post | edit：🧮 计算已完成，核对结果… |
| 14 | 公开 milestone：核对数据 / pre | 无 send/edit/delete |
| 15 | 公开 milestone：核对数据 / post | edit：📝 核对收入为零的记录… |
| 16 | 补充读取数据 / pre | edit：📖 读取 adjustments.csv… |
| 17 | 补充读取数据 / post | edit：📖 已读取 adjustments.csv，继续核对… |
| 18 | 公开 milestone：整理结果 / pre | 无 send/edit/delete |
| 19 | 公开 milestone：整理结果 / post | edit：✍️ 整理关键指标与数据说明… |
| 20 | post_llm_call：模拟原生回答已生成（内容不复制） | edit：✍️ 整理回答… |
| 21 | on_session_end(completed=True)：清理临时气泡 | delete：删除 owned-status |
| 22 | 等待本轮 transport 工作任务结束 | 无 send/edit/delete |
| 23 | 迟到的工具事件（已结束的轮次） | 无 send/edit/delete |

## 多来源调查

模拟用户请求：调查最近一周 Aurora 项目发生了什么

主动 milestone：3 次。1 次 send，10 次 edit，1 次 delete。

| 顺序 | 公开事件 / 测试步骤 | transport 可见变化 |
| --- | --- | --- |
| 1 | 已授权的 pre_llm_call：建立本轮临时气泡 | send：🤔 思考中… |
| 2 | 普通模型请求及返回 / pre | 无 send/edit/delete |
| 3 | 普通模型请求及返回 / post | 无 send/edit/delete |
| 4 | 静默 45 秒（推进测试时钟并调用显示刷新） | 无 send/edit/delete |
| 5 | 搜索近期公开事件 / pre | edit：🔎 搜索 Aurora 项目 最近一周 公开信息… |
| 6 | 搜索近期公开事件 / post | edit：📊 找到 5 条结果，继续核对… |
| 7 | 公开 milestone：筛选来源 / pre | 无 send/edit/delete |
| 8 | 公开 milestone：筛选来源 / post | edit：📝 筛选最近一周的主要来源… |
| 9 | 读取公告 / pre | edit：📖 阅读 example.org… |
| 10 | 读取公告 / post | edit：📖 已读取 example.org，继续核对… |
| 11 | 公开 milestone：对比事件 / pre | 无 send/edit/delete |
| 12 | 公开 milestone：对比事件 / post | edit：📝 对比不同来源中的事件信息… |
| 13 | 普通模型请求及返回 / pre | 无 send/edit/delete |
| 14 | 普通模型请求及返回 / post | 无 send/edit/delete |
| 15 | 静默 45 秒（推进测试时钟并调用显示刷新） | 无 send/edit/delete |
| 16 | 补充核对事件 / pre | edit：🔎 搜索 Aurora 项目 事件日期 官方记录… |
| 17 | 补充核对事件 / post | edit：📊 找到 2 条结果，继续核对… |
| 18 | 公开 milestone：整理时间线 / pre | 无 send/edit/delete |
| 19 | 公开 milestone：整理时间线 / post | edit：✍️ 整理最近一周的事件时间线… |
| 20 | post_llm_call：模拟原生回答已生成（内容不复制） | edit：✍️ 整理回答… |
| 21 | on_session_end(completed=True)：清理临时气泡 | delete：删除 owned-status |
| 22 | 等待本轮 transport 工作任务结束 | 无 send/edit/delete |
| 23 | 迟到的工具事件（已结束的轮次） | 无 send/edit/delete |
