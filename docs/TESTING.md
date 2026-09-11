# 测试方法

## 安装器单元测试

只需 Python 3.11+ 和 PyYAML，不读取真实凭据或配置：

```bash
python -m pip install -r requirements-dev.txt
python -m unittest test_install -v
```

测试覆盖首次安装、重复安装、升级恢复旧插件、卸载、用户新配置保留、两个预设、dry-run、版本拒绝、错误 YAML、符号链接、并发锁、写入失败回滚和中断事务恢复。故障通过测试层注入，不需要破坏真实系统。

## 真实 Hermes 环境回归

在受支持的 Hermes Python 环境中，从项目目录执行：

```bash
export PYTHONPATH="$HERMES_CORE"
"$HERMES_PYTHON" scripts/run_tests.py
"$HERMES_PYTHON" scripts/check_runtime.py
```

两个脚本都会在导入 Hermes 前创建临时 `HERMES_HOME`，结束后删除。完整回归若存在跳过测试，会以失败状态退出；因此不会把缺少核心或 Telegram SDK 的跳过误报成验收通过。

`check_runtime.py` 经原生插件发现、工具与 prompt 注册、中间件分发，另验证 Codex 请求发送转换以及 xAI 请求中的状态字段。它不调用付费模型，也不发送 Telegram 消息；真实模型/平台验收另行完成。

## Telegram 实机验收

使用独立测试 Bot、模型登录和运行账号。不要对正在工作的生产会话进行停止试验。将 `acceptance/` 中的合成样本复制到临时目录，确保 `material-b.txt` 不存在。

1. `/new` 开始新会话；若 Hermes 要求原生确认，选本次确认。`/start` 打开首页，点击“更多设置”和“返回”，再关闭。
2. 请模型运行 `slow_inventory.py` 读取库存，生成未来 7 天补货 CSV；执行期间追加“改为 10 天，计入在途、缺口降序、文件名 ten-day.csv”。观察收到补充的反馈与后续实际应用，最终应只交付修订版。
3. 独立读取 CSV，验证封箱胶 14、打印纸 14、收纳袋 10、墨盒 7、信封 2，降序排列，标签纸不列入。
4. 请模型读取 material-a.txt 与缺失的 material-b.txt，生成 notice.txt。应保留日期和人数，将地点、报名截止标为待补充；核对文件实际送达和内容。
5. 启动一个合成前台任务，先写 started 标记，等待 45 秒后写 done 标记。确认开始后发送“停一下”。检查任务停止、无迟到状态、等待超过原定完成时点后没有 done 标记。
6. 明确要求后台委派，做独立可控任务。期间继续询问和补充，观察所属进度；再停止，独立核对后台账本/进程、完成事件被消费、没有再次唤醒。
7. 停止 Gateway，重复安装、卸载还原、再次安装；重新启动后重复收发与首页检查。将配置语义与原版基线比较，确认模型、权限与其他服务保持正常。

首次气泡延迟用状态日志中 `age` 测量，起点是状态生命周期，不是用户按下发送。日志中的同一 message id 对应同气泡更新。还必须查看实际 Telegram 客户端，不能只凭日志或模型自述判定界面通过。

CI 执行自动回归和原生注册检查，不使用任何模型或 Telegram 凭据。真实 Telegram 验收需要维护者在隔离测试账号中执行，结果写入 ACCEPTANCE.md。

完整实机流程结束后可运行 `python acceptance/verify_artifacts.py --root 你的测试目录` 独立核对生成产物。测试中的等待时长仅用于观察取消行为，不是性能测试或默认延迟设置。
