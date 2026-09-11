# 从零建立独立测试环境

以下面向 Linux，使用独立目录，固定到本发行包实际验证的 Hermes 提交。已有正常工作的 Hermes 不应原地降级；可以用新系统账号隔离，也可以用下面独立的 HERMES_HOME。使用独立 Telegram Bot，避免同一 token 被多个 polling 进程占用。

## 1. 安装指定核心和依赖

需要 Git 和 uv。uv 可按其 [官方安装文档](https://docs.astral.sh/uv/getting-started/installation/)安装；下面由 uv 管理 Python 3.11 和独立虚拟环境。

```bash
set -e
umask 077
export HERMES_HOME="$HOME/.hermes-telegram-ux-lab"
HERMES_CORE="$HERMES_HOME/hermes-agent"
HERMES_PYTHON="$HERMES_CORE/venv/bin/python"
export PYTHONPATH="$HERMES_CORE"

# 首次安装要求新目录，避免覆盖已有实例。
test ! -e "$HERMES_HOME"
mkdir -m 700 "$HERMES_HOME"
git init "$HERMES_CORE"
git -C "$HERMES_CORE" remote add origin https://github.com/NousResearch/hermes-agent.git
git -C "$HERMES_CORE" fetch --depth 1 origin b499ab11fe8b081470e269f2fb27abae03000da5
git -C "$HERMES_CORE" checkout --detach FETCH_HEAD

UV_PROJECT_ENVIRONMENT="$HERMES_CORE/venv" uv sync --project "$HERMES_CORE" \
  --frozen --no-dev --no-install-project --python 3.11
uv pip install --python "$HERMES_PYTHON" 'python-telegram-bot==22.8'
"$HERMES_PYTHON" -m hermes_cli.main --version
```

`--no-install-project` 只省略构建 Hermes 分发包；依赖仍由官方锁文件安装。这里通过 PYTHONPATH 和 `python -m hermes_cli.main` 使用固定源码，不依赖全局命令入口。

## 2. 配置模型与测试 Bot

```bash
cd "$HERMES_HOME"
"$HERMES_PYTHON" -m hermes_cli.main setup
"$HERMES_PYTHON" -m hermes_cli.main gateway setup
"$HERMES_PYTHON" -m hermes_cli.main gateway run
```

按照 Hermes 原生交互完成模型登录、Telegram Bot token 及允许用户配置。模型授权和 Bot token 不应放进 shell 命令行、Git 配置或本项目文件。本次实机使用独立的 xAI OAuth 授权；不要复用其他应用会轮换的 refresh token。

先从 Telegram 发一条普通消息，再要求做一次简单工具计算，确认原版双向收发正常。停止此处前台运行的 gateway 后，再安装 UX 包。

## 3. 安装 UX

回到解压后的 Hermes Telegram UX 项目目录，沿用同一终端里的变量：

```bash
"$HERMES_PYTHON" install.py check --hermes-core "$HERMES_CORE"
"$HERMES_PYTHON" install.py install --hermes-home "$HERMES_HOME" --hermes-core "$HERMES_CORE"
cd "$HERMES_HOME"
"$HERMES_PYTHON" -m hermes_cli.main gateway run
```

Telegram 中开始新会话并打开 `/start`，再按 [测试方法](TESTING.md)验收。需要开机常驻时，可根据 Hermes 官方服务文档配置自己的独立服务；其执行账号、HOME、HERMES_HOME、Python 路径和工作目录必须与这里一致。

GitHub/PyPI 暂时不可达属于依赖获取问题，不应绕过 TLS 或删除版本校验。可在另一台可信机器下载同一官方提交后传输，再用 `install.py check` 核对核心接口；不要复制别人的整个 Hermes home。
