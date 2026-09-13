# Contributing

Thanks for helping improve Hermes Telegram UX. Small, focused changes are easier to review and validate across supported Hermes versions.

## Report a problem

Open an [issue](https://github.com/pler1y/hermes-telegram-ux/issues) with:

- The plugin version, Hermes version and core commit, and operating system.
- Whether you installed through Hermes or a release ZIP, and the interface language.
- Steps to reproduce, the expected result and what actually happened.
- Relevant error messages or a screenshot with private information removed.

Do not include Bot tokens, OAuth credentials, private conversations or full configuration files. Follow [SECURITY.md](SECURITY.md) for sensitive reports.

反馈问题时，请附插件与 Hermes 版本、安装方式、复现步骤及实际结果。日志和截图请先去除凭据、个人信息与聊天内容。

## Develop and verify

Use a separate Hermes environment and a supported core from [COMPATIBILITY.md](docs/COMPATIBILITY.md). Do not use a production conversation for stop or interruption tests.

From the repository root, set `HERMES_CORE` and `HERMES_PYTHON` to the core and Python interpreter in your development environment:

```bash
export PYTHONPATH="$HERMES_CORE"
"$HERMES_PYTHON" scripts/run_tests.py
"$HERMES_PYTHON" scripts/check_runtime.py
"$HERMES_PYTHON" scripts/build_release.py
"$HERMES_PYTHON" scripts/check_editions.py
```

The regression runner uses a temporary Hermes home and fails if tests are skipped. Release builds update `release-manifest.json`; include that updated manifest when changing files in the release allowlist. Full instructions, native installation checks and Telegram acceptance scenarios are in [TESTING.md](docs/TESTING.md).

## Send a pull request

Explain the problem, the resulting behavior and how you verified it. Add regression coverage when fixing a behavioral bug. Keep unrelated changes separate, and include both interface languages when changing user-facing copy.

Supported-core regression tests and checks against upstream `main` serve different purposes. An upstream compatibility failure means the current development core does not match a supported baseline; it does not alone prove a regression on a supported core. Do not bypass compatibility checks just to make CI pass. Interface changes need review and appropriate regression coverage.

Documentation improvements are welcome. Keep examples executable, distinguish illustrative conversations from real acceptance evidence, and avoid claiming support beyond what has been verified.
