# 版本与更新渠道 / Edition channels

| 名称 | 分支 | 插件 ID | 标签 | 安装包 |
| --- | --- | --- | --- | --- |
| Hermes完整版 / Full | `main` | `hermes-interaction` | `v*` | `hermes-telegram-ux-<version>-zh/en.zip` |
| Hermes插件版 / Plugin | `catalog-safe` | `hermes-telegram-ux-catalog` | `catalog-v*` | `hermes-telegram-ux-catalog-<version>.zip` |

两条线共用仓库、Issues 和 Releases 列表，各自维护源码、功能、兼容范围和版本号。插件版发行包不含完整版；不把两条分支互相整体合并。共享修复应分别适配和验证。

完整版从 [main](https://github.com/pler1y/hermes-telegram-ux) 开始；插件版从 [catalog-safe](https://github.com/pler1y/hermes-telegram-ux/tree/catalog-safe) 开始。当前插件版下载为 [catalog-v1.8.3-catalog.1](https://github.com/pler1y/hermes-telegram-ux/releases/tag/catalog-v1.8.3-catalog.1)。仓库的 Latest 入口保留给完整版稳定版；插件版页面始终链接自己的标签，不依赖仓库的通用 Latest。

安装和升级固定到所选版本的完整提交 SHA 或校验后的 ZIP。分支承载后续开发，不自动将未发布提交安装到用户环境。插件版不要使用无固定 ref 的默认分支更新。

切换版本需先停止空闲 Gateway、备份并卸载原版本。完整版先恢复它管理的配置，再安装另一版；两种插件不要在同一 Gateway 同时启用。

Each edition has its own branch, plugin ID, tag family and package. Install and upgrade from that edition's pinned release. The repository-wide Latest release belongs to stable Full; Plugin releases use explicit links from their branch. One edition per Gateway. GitHub distribution is separate from admission to the official Hermes Plugin Catalog.
