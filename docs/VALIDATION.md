# Current temporary-progress live Telegram acceptance — 2026-09-20

## Scope and source proof

Executed real Telegram acceptance only: deployment, observation, evidence capture and this validation record. No runtime code or test assertions were changed; no commit, push, tag, release, PR, Catalog publication or production Bot operation was performed. The uncommitted temporary-progress working tree was deployed, not the older `d0ff0a8` completion-card runtime. Version text remains `1.9.0-catalog.1`; this is not a new release.

- Source directory: `Catalog-safe源码`; branch `codex/catalog-experience`.
- HEAD: `93ff48a0a3a5ec956cbf424f29b23c8b8ec01fc3`; dirty at capture, with 18 tracked changed files (966 insertions / 587 deletions) plus two untracked test files. The full binary Git diff and both untracked tests were saved before deployment.
- Snapshot: 2026-09-20 16:21:44 Asia/Shanghai. Deployment: 16:26:50.
- Source manifest SHA256 (18 package files): `6c5d75f6012eb17e0a01655499ebc79a149d1c06dc527b216c065a2bdcc39315`.
- Runtime manifest SHA256 (9 Python files plus plugin.yaml): `24fe7c536ec146006eef9f9efd8499a08db10c9308be958d27b06a3a1f8a258d`.
- ZIP SHA256: `9fa4a84d7739962e29d6aeee1fecd39069a6239b1b7378564edfb9869771fca4`.
- Manifest aggregates use SHA256 of the UTF-8 JSON filename→SHA256 mapping, with sorted keys and separators `(',', ':')`. ZIP includes the 18 files and `WORKING-TREE-PROVENANCE.json`.
- All 18 installed file hashes matched the captured working tree at deployment and after acceptance. This validation section was added locally afterward; the installed package retains the pre-acceptance documentation snapshot. Runtime hashes remain identical.
- Dedicated private Bot: `@hermes_ux_lab_bot`; account `hermes-ux-lab`; service `hermes-gateway-catalog-safe-lab.service`; installed plugin `/home/hermes-ux-lab/catalog-safe-20260916/home/plugins/hermes-telegram-ux-catalog`.
- Official Hermes 0.21.3, core `3c3ab69abb9b08683b5eb15b4e2b8be1198c875f`, Python 3.11.16. Native token streaming was off; native interim messages were on. This is one private-chat environment, not a compatibility matrix.
- Previous plugin, previous installation and exact config are backed up under `/home/hermes-ux-lab/catalog-safe-20260916/temporary-progress-live-20260920-162144`. Earlier Full backups were preserved. Full test service remained inactive; no dual Full/Catalog Gateway.
- Official validate: 10 checks, 0 warnings; doctor: 17 hooks and 1 tool. Final restored discovery: enabled, 17 hooks / 1 tool / 1 command / 0 middleware, no plugin error.
- Final service: active/running, PID 615341, NRestarts 0 (no automatic restarts; planned baseline restarts occurred), Telegram connected, 0 active agents. All 13,490 tracked core files unchanged. Exact original config restored after disabled baseline; SHA256 `9cd8e61b3b43eb00aa1ddf6fcdaf449a5717b81073d1927c840b983b850add26`.

Evidence directory in the maintainer workspace:
`Telegram测试工具/reports/temporary-progress-live-20260920-162144/`.
It contains Git status/HEAD/diff, source snapshot/manifest/ZIP, deployment and health receipts, raw `events.jsonl`, final message-existence checks, per-turn public tool/answer transcript rows, native checks and Telegram screenshots. Transcript extraction excludes hidden reasoning and system prompts. The capture utility's initial SQL quoting error was corrected only in `/tmp`, and A's already-completed turn evidence was retrieved read-only; A was not resent and no plugin code was changed.

## A–F results

Times below are client-observed seconds from the start of sending each prompt, not server-side request timestamps. NewMessage/MessageEdited/MessageDeleted events and a final `get_messages` check provide the timeline. Distinct statuses are printed exactly as observed. Immediate finalization can bypass the ordinary edit interval; one short final-stage edit pair is not sustained flooding.

| Case | Result | Observation |
|---|---|---|
| A — 1+1 | PASS | One status, native answer `2`, status deleted. Initial feedback 2.616 s is noticeable but does not establish a plugin-specific latency cause. |
| B — Shanghai weather | PARTIAL | One status and clean deletion; task title appears, but most visible updates alternate generic processing/organizing text without showing actual recovery or retrieved-data progress. |
| C — installed code reading | PARTIAL | Actual safe source reads and normal final answer; status reuses the prompt fragment rather than exposing the cleanup-inspection stage. |
| D — missing file | PARTIAL | Real file-not-found result, accurate native explanation, no fabricated success or fallback; failure was not visible in the progress bubble. |
| E — public news | PARTIAL | Real search/read/result stages and supported result counts; raw truncated English query strings leak into the status and the final query-result wording persists for 51.445 s. |
| F — cleanup across A–E | PASS | Every status deleted 0.846–1.131 s after its native answer. No feedback gap, late new status, residual completion card or inline keyboard. |

| Case | Start (Asia/Shanghai) | Status ID | First status | Final answer | Status deleted | Delete minus answer |
|---|---|---:|---:|---:|---:|---:|
| A | 16:29:57.499 | 7325 | +2.616s | +9.024s (ID 7326) | +10.155s | +1.131s |
| B | 16:33:37.206 | 7328 | +1.212s | +67.889s (ID 7329) | +68.799s | +0.910s |
| C | 16:35:17.744 | 7331 | +1.155s | +35.346s (ID 7332) | +36.307s | +0.961s |
| D | 16:36:50.014 | 7334 | +1.212s | +7.230s (ID 7335) | +8.076s | +0.846s |
| E | 16:38:06.702 | 7337 | +1.367s | +114.028s (ID 7338) | +114.880s | +0.852s |

## Exact visible timelines

Each case created one ordinary main status; all edits targeted its same message ID. No ordinary-task inline keyboard was present in any message/edit or final existence check.

### A — status 7325

Prompt: 1+1等于多少？

```text
+002.616s  🤔 正在思考中…
+007.386s  🤔 正在组织回复内容…
+008.968s  ✍️ 正在整理最终回答…
+009.024s  Hermes native final answer arrived (message 7326)
+010.155s  Status deleted (message 7325)
```

### B — status 7328

Prompt: 帮我搜索一下上海未来7天的天气，重点看看每天的温度、湿度和风速，并简单总结一下变化。

```text
+001.212s  🤔 正在思考中…
+002.836s  🤔 正在处理上海未来 7 天的天气…
+009.722s  🤔 正在组织回复内容…
+011.372s  📖 正在阅读上海未来 7 天的天气相关资料…
+013.038s  🤔 正在处理上海未来 7 天的天气…
+019.567s  🤔 正在组织回复内容…
+021.222s  🤔 正在处理上海未来 7 天的天气…
+030.005s  🤔 正在组织回复内容…
+031.611s  🤔 正在处理上海未来 7 天的天气…
+037.361s  🤔 正在组织回复内容…
+039.020s  🤔 正在处理上海未来 7 天的天气…
+041.113s  🤔 正在组织回复内容…
+042.799s  🤔 正在处理上海未来 7 天的天气…
+067.559s  🤔 正在组织回复内容…
+067.699s  ✍️ 正在整理最终回答…
+067.889s  Hermes native final answer arrived (message 7329)
+068.799s  Status deleted (message 7328)
```

### C — status 7331

Prompt: 请只读取当前安装的 Hermes Telegram UX 插件代码，检查 Telegram 状态消息在正常任务结束后是怎样清理的，不要修改任何文件。
已确认的源码文件：/home/hermes-ux-lab/catalog-safe-20260916/home/plugins/hermes-telegram-ux-catalog/catalog/telegram.py 和 /home/hermes-ux-lab/catalog-safe-20260916/home/plugins/hermes-telegram-ux-catalog/catalog/adapter.py。

```text
+001.155s  🤔 正在思考中…
+002.856s  🤔 正在处理只读取当前安装的 Hermes Telegram UX 插件代码…
+004.604s  🤔 正在组织回复内容…
+006.274s  🤔 正在处理只读取当前安装的 Hermes Telegram UX 插件代码…
+008.482s  🤔 正在组织回复内容…
+010.168s  🤔 正在处理只读取当前安装的 Hermes Telegram UX 插件代码…
+034.997s  🤔 正在组织回复内容…
+035.156s  ✍️ 正在整理最终回答…
+035.346s  Hermes native final answer arrived (message 7332)
+036.307s  Status deleted (message 7331)
```

### D — status 7334

Prompt: 请读取 /tmp/TGUX_DOES_NOT_EXIST_20260920_A7F91.txt，并告诉我里面是什么内容。

```text
+001.212s  🤔 正在思考中…
+004.595s  🤔 正在组织回复内容…
+006.333s  🤔 正在思考中…
+006.889s  ✍️ 正在整理最终回答…
+007.230s  Hermes native final answer arrived (message 7335)
+008.076s  Status deleted (message 7334)
```

### E — status 7337

Prompt: 调查最近7天 OpenAI 的重要公开新闻，找出几件主要事件，并分别说明发生了什么。只进行公开网页搜索，不要修改任何文件或外部数据。

```text
+001.367s  🤔 正在思考中…
+003.055s  🤔 正在处理最近 7 天 OpenAI 的重要公开新闻…
+007.412s  🤔 正在组织回复内容…
+009.075s  🤔 正在处理最近 7 天 OpenAI 的重要公开新闻…
+017.278s  🤔 正在组织回复内容…
+018.973s  📊 已找到 10 条搜索结果，正在整理OpenAI latest news past week September 2…
+027.810s  🔎 正在搜索最近 7 天 OpenAI 的重要公开新闻…
+029.480s  🔎 正在搜索site:openai.com "Sep 18…
+031.330s  📊 已找到 8 条搜索结果，正在整理site:openai.com "Sep 18…
+043.510s  📖 正在阅读最近 7 天 OpenAI 的重要公开新闻相关资料…
+052.359s  📊 正在整理这一步的结果…
+054.108s  🤔 正在处理最近 7 天 OpenAI 的重要公开新闻…
+060.653s  🤔 正在组织回复内容…
+062.291s  📊 已找到 8 条搜索结果，正在整理September 19 2026 OpenAI antitrust lawsui…
+113.736s  ✍️ 正在整理最终回答…
+114.028s  Hermes native final answer arrived (message 7338)
+114.880s  Status deleted (message 7337)
```

## Tool-result grounding and task specificity

- **A:** actual `execute_code` ran `print(1+1)` and returned success/output `2`/exit 0. The very short tool execution did not produce a visible calculation stage; no invented result was displayed.
- **B:** `web_extract` actually attempted the weather API and the central meteorological Shanghai page, so the visible weather-reading status has a real basis. API extraction returned a service error, and `browser_exec` failed because Chromium was missing. A later `execute_code → terminal curl` returned seven-day temperature/humidity/wind data; `search_files` and `read_file` then inspected a weather cache. The status did not express those failures, successful data retrieval or recovery. It never claimed unsupported humidity, wind or result counts. Of 15 status versions, 12 are the two repeated processing/organizing phrases. This is task-label awareness, not rich progress awareness.
- **C:** tools were `skill_view("hermes-agent")` and `read_file` on the installed `catalog/telegram.py` and `catalog/adapter.py`. No write command occurred. Both reads were brief; the following roughly 25 s still used generic processing text. The native final explanation of `on_session_end → finalizing → cleanup delay → delete_owned` agrees with the source. The status itself never visibly localized message-cleanup logic.
- **D:** one `read_file` returned `{"content":"","error":"File not found: /tmp/TGUX_DOES_NOT_EXIST_20260920_A7F91.txt"}`. The path was verified absent before the test and remained absent afterward. There was no fallback call and no invented fallback/success wording. Native final text correctly says the file does not exist; the bubble only returned to thinking/finalizing, without displaying the tool error.
- **E:** actual tools were `skill_view`, 14 `web_search` calls and 3 `web_extract` calls; no mutation tools were used. The three visible counts 10/8/8 match the respective returned `data.web` array lengths (captured database rows 221/228/235), not merely requested limits. Search result counts were not presented as unique event counts. Some extract calls returned HTTP 429/HTTP errors and later sources supplied material; no visible recovery wording appeared. The last query-result status stayed unchanged from +62.291 to +113.736 s (51.445 s), with no additional tool call during that interval. No persistent hang or fabricated progress is established, but the truncated query poorly communicates report synthesis.
- No A–E turn called `telegram_ux_update`. The observed task wording came from fallback inference and actual tool arguments/results; optional model-authored progress was not exercised.
- No A–E turn sent an additional native interim body. Each left its user prompt and one native final answer; the sole plugin status was absent on final lookup. Native Telegram reactions and older chat history are separate from plugin progress UI. Historical old-version cards were not deleted by this acceptance task.

## Native behavior smoke checks

| Check | Result and evidence |
|---|---|
| Native `/usage` | PASS: native usage receipt at +1.527 s; no plugin status/buttons. The command does not enter model transcript, so no matching user row is expected. |
| Native active `/stop` | PASS: real `terminal("sleep 20", timeout=30)` began around +4.150 s. Before `/stop`, `active_agents=1`; stop sent +11.678 s, native `Stopped` at +11.866 s. Tool returned `[Command interrupted]`, exit 130, followed by `Operation interrupted.` Status 7342 changed to interrupted and was deleted +13.542 s. Later bounded chat-history lookup after the original sleep deadline found no late `TEMP_STOP_SHOULD_NOT_FINISH` answer. |
| Native attachment | PASS: existing public plugin `LICENSE` was read and delivered as message 7347, 1,088 bytes. Downloaded SHA256 `dbf878b4d6fbf3dfec6a2195081a37cfc185a537a47a1a5dbcc9b061dd7690a0` matches deployed source. No server-side file creation/copy/modification requested. Status deleted +9.113 s; attachment arrived +9.984 s, a 0.871 s gap. |
| Disabled baseline | PASS: official CLI disabled only this plugin; a fresh PluginManager reported enabled=false, 0 hooks/tools/commands, `disabled via config`. Exact `TEMP_NATIVE_DISABLED_OK` native reply arrived +5.812 s with no plugin status or buttons. Config original bytes/permissions were restored and final enabled discovery/Telegram connection verified. |
| Final integrity and logs | PASS for executed checks: all installed source hashes match, 13,490 tracked core files unchanged, original config restored, Full inactive, 0 active agents. The service journal window from 08:26:45 UTC contained 54 lines; targeted traceback/plugin-delivery/delete/media/connection-error patterns all counted zero. This is a targeted journal scan, not a claim that every external tool succeeded. |

Service restarts emitted Hermes native shutdown notices; these are operational messages, not ordinary task completion cards. No production Bot was touched.

## Issues recorded — no fixes applied

- **P0:** none observed in this environment.
- **P1:** none observed. No broken answers, routing errors, duplicate main status, cleanup failure or severe fabricated progress.
- **P2:** B/C mostly repeat task-name processing and reply-organization wording rather than specific work stages; D tool failure is absent from the bubble; B/E tool-error/recovery transitions were not expressed; E exposes truncated English query strings and leaves the last one visible for 51.445 s. Initial status latency was 1.147–2.616 s across ordinary probes (A–E: 1.155–2.616 s); A's 2.616 s is an initial-feedback observation, with no isolated causal attribution to the plugin.
- **P3:** C's `正在处理只读取…` and missing spacing in E's query concatenation are awkward. B and C each had a single terminal-stage edit pair 140/159 ms apart (D 556 ms), producing a possible brief wording flash; ordinary B intervals were otherwise 1.606–24.760 s. This is not sustained high-frequency refresh. In the native Stop probe, `这一步没有成功，等待后续处理` briefly preceded `本轮运行已中断` by 152 ms. The attachment task also reused an awkward literal request fragment; delivery itself passed.
- **Environment/tool limitations:** B's missing Chromium and external extraction errors, and E's HTTP 429/HTTP errors were observed; no evidence attributes them to this UX revision. Native execution recovered and produced answers. No environment packages or tools were repaired.

## Coverage limits and final state

This run does not establish live group/topic isolation, concurrency, SDK unload, reconnect/rate-limit behavior, injected delete failure, native streaming-on behavior, a broader Python/core matrix, model-authored `telegram_ux_update`, or image/audio/video delivery. A real document attachment was checked. Stop proves the foreground terminal interruption and session recovery, not termination of every possible background process (no process-tree probe was performed). The factual accuracy of every weather/news statement was not independently researched; result grounding checks concern the progress statements, tool outcomes and preserved native delivery. All timings are client observations with network/scheduling delay.

All A–E captures are complete; B–E remain PARTIAL for the UX reasons above and were not silently reclassified as PASS. Findings were recorded without runtime fixes or reruns to improve wording. The deployed temporary-progress candidate is enabled on the dedicated test Bot, with original config restored and Telegram connected. Awaiting the maintainer's next instruction.

# Current working-tree verification — 2026-09-20

This section concerns the uncommitted temporary-progress revision based on candidate HEAD `93ff48a0a3a5ec956cbf424f29b23c8b8ec01fc3`, not the earlier deployed completion-card implementation. Runtime version remains `1.9.0-catalog.1`; no release is implied.

- Environment: Python 3.12.13; official Hermes 0.21.3 checkout `3c3ab69abb9b08683b5eb15b4e2b8be1198c875f`; disposable Hermes homes.
- `unittest discover -s tests/unit`: **109 passed** (31 adapter/route, 22 UI/integration/preferences, 3 boundary, 33 task/evidence/ordering, 20 async temporary-transport cases).
- `unittest discover -s tests/contract`: **6 passed**, using the real PluginManager with synthetic Telegram transport.
- Official `plugins validate`: **10 checks passed, zero warnings**; `plugins doctor --ci`: passed, **17 hooks and 1 tool**.
- Current working-tree enabled/disabled discovery probes, `scripts/check_boundary.py`, and `git diff --check`: passed.
- Acceptance now asserts normal completion deletes the owned status, no ordinary-task keyboard or final-answer transformer exists, and task summaries cannot claim missing result fields. Injected send/delete/settings failures in test logs are expected failure-isolation cases.
- No failed tests remain in this run. No new live Telegram conversations, real-model wording checks, deployment, Git/ZIP release lifecycle, or Python/core-version matrix were run. Automated A–F fixtures do not establish live Telegram acceptance or delivery timing. Earlier results below apply only to their recorded revisions.

# 1.9.0-catalog.1 candidate validation

Baseline: official Hermes `3c3ab69abb9b08683b5eb15b4e2b8be1198c875f`, Python 3.12, official locked messaging dependencies.

- Official plugin validate: all 10 checks passed, zero warnings.
- Official doctor: discovery/import/registration passed; 17 hooks, one tool, no middleware.
- Real-host contracts: six passed, including the registered progress tool, authenticated command-context menu path, SDK callback cleanup, native reply preservation and disabled/unloaded behavior.
- Unit/boundary: 54 tests passed, including cross-user/topic isolation, expired/mismatched callbacks, preference persistence/failure, native command keyboards, live-card dismiss, subagent correlation and SDK import boundaries and atomic text/button edits.
- Native Git and ZIP install/enable/disable/remove passed at runtime source `d0ff0a83ab4136d4b5279237b296ba95ff9c6299`; official validators passed, an undeclared hook was rejected, unrelated config was preserved, and tracked core file hashes stayed unchanged.
- Remote CI passed on the fixed core and current upstream main, Python 3.11 and 3.12, for both push and PR runs: [PR run](https://github.com/pler1y/hermes-telegram-ux/actions/runs/35494525972), [push run](https://github.com/pler1y/hermes-telegram-ux/actions/runs/35494524454).
- Live Telegram on 2026-09-20: all 14 checks passed on the existing private test bot. Home, language toggle, statistics off, native usage command, a one-time native approval for the exact bounded test command, answer and CSV delivery, clean final answer, natural progress notes, details, user-sent follow-up, dismiss without cancellation, native stop/recovery, downloaded CSV contents and persistent buttons during updates.
- Installed source `d0ff0a83ab4136d4b5279237b296ba95ff9c6299`; ZIP SHA256 `56a07fea08891155e0b564634c2f6c2ab148a1afef2017858c00ff5963eb7105`. Service enabled/running with Telegram connected, zero active agents and installed file hashes matching provenance after acceptance.
- Live coverage is a private chat on the fixed core. Group/topic isolation, SDK unload and subagent correlation were verified automatically, not claimed as live group or real-model delegation acceptance. Model guidance is not a deterministic guarantee. Follow-up controls are offered on status cards; disabling progress suppresses those cards.

Local maintainer evidence is retained in `Telegram测试工具/reports/catalog-experience-20260920.json` and `catalog-experience-deployment-20260920.json` in the parent workspace. Reports are not bundled with user packages.

## Prior release validation (1.8.3-catalog.1)

# Catalog-safe validation — 2026-09-16

Candidate: **1.8.3-catalog.1**. Runtime tested at
`a4f8325f187df210bc7f0b1e583dbdc4b541a834` against official Hermes **0.21.3**,
`3c3ab69abb9b08683b5eb15b4e2b8be1198c875f` (main snapshot on 2026-09-16).
The final archive's `PROVENANCE.json` identifies its exact source commit and
per-file hashes. Subsequent documentation commits do not change this runtime.

## Automated checks

| Check | Executed result |
|---|---|
| Unit/state/transport/guard tests | 33 passed, Python 3.11.15 on macOS ARM64 |
| Real official PluginManager contract tests | 4 passed; transport synthetic |
| Official `plugins validate --json` | All 10 checks passed; zero warnings |
| Official `plugins doctor --ci` | Passed locally and on Linux ARM64 |
| Pinned native Git lifecycle | Install, enable, disabled discovery, disable and remove passed |
| ZIP lifecycle using README steps | Same lifecycle passed |
| Validator negative control | Undeclared hook rejected by the official validator |
| Private-API boundary | Zero Hermes runtime imports; AST checks passed |
| Archive allowlist and hashes | Passed; Full runtime and test fixtures excluded |
| Hermes tracked source files | Identical before and after native lifecycle checks |

`artifacts/native.json` is the machine-readable lifecycle report generated by
`scripts/check_native.py`. No test skips or validator bypass were used. GitHub
Actions has been configured for the baseline/main × Python 3.11/3.12 matrix;
remote CI had not run at the time of this 2026-09-16 record. For publication-time checks, use the linked GitHub Release and Actions results.

## Real Telegram acceptance

Executed in the existing dedicated test bot, with a separate home/core under its
existing unprivileged account, Linux ARM64, Python 3.11.16, python-telegram-bot
22.8 and the configured `openai-codex` provider. Native token streaming was off;
native interim messages were on. Full and Catalog were never simultaneously
enabled in one Gateway. The original Full installation/config were preserved.

These are actual chat interactions observed in Telegram Lite, not synthetic hook
invocations. Times below are Asia/Shanghai on 2026-09-16.

| Marker | Time | Observed result |
|---|---|---|
| CAT916-R01 | 13:15 | Exact `CAT916_PURE_OK`; no appended footer; status ended |
| CAT916-R02 | 13:15 | Actual terminal result 437; 1 tool / 2 model requests; status ended |
| CAT916-R03 | 13:16 | Two file reads plus calculation; apples 10 / pears 7; 3 tools / 4 requests |
| CAT916-R04 | 13:22 | Native CSV attachment delivered, 26 bytes; media directive remained native |
| CAT916-R05 | 13:22–13:23 | Missing-file error preserved; 1 tool issue; no fabricated success |
| CAT916-R06 | 13:23 | Interim sentence arrived once, live terminal status during 12-second wait, final marker arrived |
| CAT916-R09 | 13:25 | Real 2-second foreground timeout, exit 124; 1 tool issue; final reply arrived |
| CAT916-R07B | 13:29–13:31 | Live approval wait; expiry after 60 seconds; native notice said command did not run |
| CAT916-R07C | 13:32 | Native `/approve` resumed a marked printf command; exact output and ended status |
| CAT916-R08B | 13:34–13:35 | Native `/deny` rejected the write; target file confirmed absent over SSH; final explanation and tool issue preserved |
| CAT916-R10 | 13:36–13:37 | Native `/stop` during a running terminal wait; status changed to interrupted; native stopped receipt arrived |
| CAT916-R10-RECOVER | 13:37 | Exact recovery marker on the next ordinary turn; ended status |
| CAT916-R11 | 13:39–13:40 | Plugin disabled and Gateway restarted; exact native reply with no Catalog panel or footer |

Approval cases use the separately installed public `pre_tool_call` policy
fixture in `tests/fixtures/approval_gate`. It requests an actual native approval;
the Catalog plugin only observes it. Approval/denial choices use native slash
commands; Telegram inline-button taps are not claimed as tested here.

## Scope and product decision

Private-chat progress, ordinary final replies, attachments and the cases above
were exercised live. Cross-topic/profile routing, reconnects, rate limits,
missing/duplicate events, uncertain delivery, unload and concurrent routes were
tested automatically. Group/topic live sessions and native streaming mode were
not live-tested. Python versions beyond the executed environments are covered
by the proposed CI matrix only, not a completed CI result.

The 13 cases above completed against the fixed runtime. The approval fixture was
then removed. This candidate is ready for maintainer trial. The
maintainer's personal “worth installing” judgment and Catalog re-review remain
pending. Nothing has been pushed, tagged, published or posted to PR #108887.
