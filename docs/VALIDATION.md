# Progress Intelligence — developed and live-validated 2026-09-20

## Final candidate and scope

Task-aware progress is deployed to the dedicated private `@hermes_ux_lab_bot`. This iteration completed local checkpoint, implementation, automated checks, live deployment, directly related corrections, retesting and restoration of the original test configuration. No push, tag, release, PR, Catalog publication or production-Bot change was performed.

- Baseline local checkpoint: `31b3a5fddc6e106eafe4240e58384c407c840b8d`, preserving the preceding real-validated temporary-message lifecycle. Branch: `codex/catalog-experience`.
- The final accepted runtime is the working-tree snapshot `round-4-final`, deployed at **2026-09-20 18:03:01 Asia/Shanghai**. The final local commit follows this record; `final-local-commit.json` in the evidence directory binds its exact commit to the same deployed runtime hashes.
- Runtime SHA256: `4998be75d2a6e6ce839795cf606c786a58f516ac6fd194cbda043172b0830395` (10 Python files plus plugin.yaml). Package source manifest SHA256: `6d5c5da99d92805611658fc06467134d0317929781793d54692a433c90b03921`. Snapshot ZIP SHA256: `4ec671d9987ae38203b4fa992160b95d2596201b735c5a5bb18dad3bc321edb0`.
- After acceptance, this record, `PROGRESS.md` and the API explanation were updated locally. The deployed documentation remains the pre-acceptance snapshot; deployed runtime files are unchanged and individually hash-verified. Manifest version remains `1.9.0-catalog.1`; no release/version bump is implied.
- Official Hermes 0.21.3, fixed core commit `3c3ab69abb9b08683b5eb15b4e2b8be1198c875f`. Local checks use Python3.12.13; live host uses Python3.11.16. All **13,490 tracked core files** retain their original hashes.
- Dedicated service: `hermes-gateway-catalog-safe-lab.service`. Installed plugin: `/home/hermes-ux-lab/catalog-safe-20260916/home/plugins/hermes-telegram-ux-catalog`. Full test service remains inactive; Full implementation and production installations were not modified.

Evidence root in the maintainer workspace:
`Telegram测试工具/reports/progress-intelligence-20260920-172143/`.
The final live evidence is in `round-4-final/`; earlier snapshots and observations remain in preceding round directories. `round-4` is an intermediate source snapshot, not another deployed candidate. Raw Telegram new/edit/delete events and final existence checks are retained, with per-turn public tool/answer rows and public hook observations. Hidden reasoning, system prompts and credentials are excluded from exported evidence. The independent audit copied below maps every visible state to concrete public evidence; it does not infer execution from a successful final answer alone.

## Final code and automated checks

- `catalog/intelligence.py`: conservative action/object classification from the public user task and actual tool arguments; raw queries, paths and code stay out of UI; bounded structural facts for counts, missing files, actual weather fields, success and failure. Python/shell inspection does not execute code or pretend that unexecuted/unknown branches ran.
- `catalog/model.py`: preserve specific results/errors across model events, correlate actual follow-up actions and API retries, and retain same-batch mixed source outcomes. Neither a successful date query nor an unrelated prior success hides a failed source.
- `catalog/presentation.py`: result/error priority, task-specific synthesis following an observed model request and short result hold, honest current-step completion scope, and failure-qualified partial summaries. Public progress-tool notes remain distinct from verified results.
- `catalog/adapter.py` and `catalog/telegram.py`: two-second render-only check for synthesis transitions; it does not refresh task execution TTL. One owned message, same-ID edits, native final reply and bounded automatic cleanup are retained.
- Added intelligence/priority regression suites; boundary allowlist includes only the new pure-stdlib module. The strict boundary rules were not relaxed.

| Check | Final result |
|---|---|
| All unit/UI/async/boundary unittest cases | **163 passed**, 4.738s |
| Official-host PluginManager contract tests | **6 passed**, 1.158s |
| Standalone Catalog boundary guard | **PASS** |
| Official `plugins validate --json` | **10/10**, `ok:true`, **0 warnings** |
| Official `plugins doctor --ci` | Discovery/import/registration **PASS**, 17 hooks / 1 tool |
| Remote staged official validate / doctor | **PASS** on the actual Python3.11 host |
| `git diff --check` | **PASS** |

Full stdout/stderr are in `checks/`; unittest summaries are on stderr. These runs validate the uncommitted candidate runtime that was actually deployed. Native Git/ZIP release harnesses read committed objects and were not used to claim dirty-tree validation. They are not a published release or a cross-version compatibility matrix.

Directly related live findings were corrected and retested before the final acceptance: actual Python `-c` arithmetic recognition; whole fenced JSON weather-field evidence; current-step success scope; and mixed parallel source success/failure preservation. Final A–E and supplemental cases below all use the same final runtime. Earlier partial runs are not reused as final PASS evidence.

## Final live outcome and cleanup

A–E all pass their exercised task-awareness and lifecycle criteria. Supplemental double-success, mixed-failure, and sequential recovery cases also pass their respective observed behavior. Across those eight cases, each ordinary task owns exactly one status message; every edit targets that message; all eight are absent in the final message-existence check; all native final answers remain. No ordinary completion card, elapsed footer, Details/Settings/Continue/Close keyboard or raw query was observed. Native command approvals remain native and are not counted as plugin status cards.

After export, the temporary public observer plugin was removed from the active plugins directory and retained under the backup directory. Exact original config bytes, mode and ownership were restored; SHA256 `9cd8e61b3b43eb00aa1ddf6fcdaf449a5717b81073d1927c840b983b850add26`. Runtime manifest and all core hashes were reverified. Backup and receipt: `/home/hermes-ux-lab/catalog-safe-20260916/progress-intelligence-20260920-172143/acceptance-cleanup.json`.

The post-restoration A smoke (`case-A-after-cleanup`) passes independently of the observer: status7458 appears+2.169s, becomes calculating+7.059s, current calculation completed+9.102s, task-specific synthesis+11.112s; native final7460 `2。` arrives+11.245s; status is deleted+12.259s (**1.014s after final**). Native once-only approval7459 was preserved. Zero new observer events is expected after observer removal, not newly hook-correlated evidence. This is the ninth clean lifecycle check on the final runtime.

Final service receipt: active/running, PID626588, NRestarts0, Telegram connected, zero active agents. Fresh official discovery confirms enabled, **17 hooks / 1 tool / 1 command / 0 middleware**, error:null, observer absent. See `acceptance-cleanup.stdout`, `health-final.stdout`, `discovery-final.stdout` and the post-cleanup case in the final round directory.

## API boundary and remaining limits

The runtime still registers only public hooks, the public progress tool, `/tgux`, and the public Telegram platform-handler factory. Owned-message I/O uses the supplied adapter's `send`, `edit_message`, `delete_message`. No Hermes internal import/private access, monkey patch, middleware, stream observer, final-answer transformer or final-answer sender has been added. Final answer and native task/approval control remain Hermes responsibilities. Catalog-safe compliance here means the checked public-API boundary on the fixed official core, not Catalog admission.

No confirmed P1/P2 remains on the exercised paths. The following limited observations remain:

- One supplemental compound task produces the P3 wording repetition “两篇资料资料”; facts and lifecycle are unaffected.
- Complex mixed scripts can use brief conservative task-related action/step labels; classification is deliberately incomplete and does not claim to know each internal statement. Arbitrary prose/task extraction is not a semantic guarantee.
- The longest unchanged final A–E state is **48.561s** in E, inclusive of cleanup wait (47.908s until the native answer), displaying task-related news synthesis. The public model request actually lasted through that interval; no fictional stages were inserted. There was no stale raw search-query state.
- Exact native final-delivery ordering and deletion under every network error cannot be guaranteed: public turn completion is not a Telegram delivery receipt. Bounded deletion retry remains unchanged; all final exercised cases actually deleted successfully.
- Only this private chat, fixed core and deployed settings were live-tested. Final-round native stop/media/disabled cases were not newly rerun; their prior temporary-progress acceptance is historical evidence only. External forecast/news accuracy was not independently researched.

# Final live state timelines and evidence

Runtime source manifest SHA256: `4998be75d2a6e6ce839795cf606c786a58f516ac6fd194cbda043172b0830395` (verified against this directory's immutable manifest).

Only saved Telegram user-client events, public hook records, native tool/answer transcript rows, and this deployment's immutable source are audited. The auditor does not connect to Telegram/SSH, alter product code, or inspect hidden reasoning. Hook sequence and matched argument hashes support the stated evidence; a heartbeat and adjacent callbacks can render the same text, so this is not a claim of unique render-callback causality. Server/client subsecond clock differences are not treated as proof of false progress. Native approval receipts/interim replies are distinguished from the plugin's owned bubble. No missing case is a PASS.

## Coverage

- A: PASS; continuous capture and native single-use approval included.
- B: PASS; real three-field retrieval and two distinct executed follow-up steps.
- C: PASS; requested code really read, cleanup-purpose status retained.
- D: PASS; explicit missing-file state preserved through native explanation and cleanup.
- E: PASS for observed search/synthesis flow; does not naturally exercise mixed failures.
- Mixed same-batch sources: PASS, live case-mixed-failure genuinely exercises the fixed branch.
- Sequential failure/recovery: PASS, real failed read followed by a new successful source read.

## A — arithmetic — PASS

Trace seq1–10 is contiguous, observer drops zero. Main execute_code argument hashes and user-message hash match. Seq5 is its nested terminal pre-hook with no scoped IDs; outer code/result establish its relation, rather than pretending it is an independently identified turn.

| Client time | Visible plugin state | Actual public evidence |
|---|---|---|
| +1.979s | 🤔 正在思考中… | seq1 pre_llm_call +1.881s for this exact user request |
| +5.554s | 🧮 正在计算1+1… | seq4 pre_tool_call execute_code `call_OFpV1Qy3XJKhwwduCquRodOY`; exact code calls terminal `python3 -c 'print(1+1)'`; nested pre-hook seq5 |
| +7.214s | 🧮 已完成1+1计算，正在核对结果… | seq6 successful execute_code; DB414 output `2\n`, exit_code0, one nested tool call |
| +8.535s | ✍️ 正在整理1+1… | seq7 subsequent API, seq8 no-tool response, seq9/10 normal completion; native final DB415 is `2。` |

The native approval7432 appears +5.749s and its approved-once receipt +7.176s. No separate plugin approval state was captured in this brief nested-tool approval; the original native approval is visible and the tool only succeeds after explicit approval. Do not claim the plugin approved it or that this run showed a separate approval label. Approval callbacks are outside the seven-hook observer fixture.

One owned status7431; all its buttons empty. Native final7433 arrives +8.555s; status is deleted +9.627s (1.072s after final). Final snapshot: status absent, answer present, approved-once native receipt present without buttons. Maximum unchanged plugin status is 3.575s (+1.979→+5.554). There is no persistent completion card or duplicate status. The terminal transition appears 20ms before final delivery; this is one completion transition, not an edit flood.


## B — weather — PASS

Trace seq11–28 contiguous, zero drops; all six main pre/post argument hashes match. No web_search is called in this run: the model directly retrieves public API data through execute_code→web_extract, and the plugin does not invent a search stage.

| Client time | Visible plugin state | Actual public evidence |
|---|---|---|
| +1.122s | 🤔 正在思考中… | seq11 pre_llm_call for exact prompt |
| +2.778s | 🤔 正在分析上海未来 7 天的天气… | seq12 pre_api_request；仅分析任务，不虚构搜索 |
| +11.007s | 📖 正在读取上海未来 7 天的天气数据… | seq14 execute_code call_I3h4V9bblIHvNSyzxi4bigZ9，实际嵌套web_extract（seq15）请求Open-Meteo天气API |
| +13.015s | 📊 已获取温度、湿度、风速数据，正在整理上海未来 7 天的天气… | seq16成功，DB419嵌套results.content为完整fenced JSON；温度min/max各7值、风速7值、湿度168小时值 |
| +15.187s | ✍️ 正在整理上海未来 7 天的天气变化… | seq17后续API+结果hold后的天气变化整理 |
| +25.651s | ⚙️ 正在执行上海未来 7 天的天气的相关步骤… | seq19 execute_code call_cQBrcdkt0g4UJR7Uv3k5pjCg：解析既有结果并循环统计/打印，保守相关步骤标签 |
| +27.339s | 📊 当前步骤已完成，正在核对上海未来 7 天的天气的结果… | seq20成功，DB421实际输出7天温度/湿度均值/风速；只称当前步骤完成 |
| +29.162s | ✍️ 正在整理上海未来 7 天的天气变化… | seq21后续模型周期，已完成结果转整理；随后的seq23/24工具在5ms内完成 |
| +30.829s | 📊 当前步骤已完成，正在核对上海未来 7 天的天气的结果… | seq24另一execute_code call_2XOWUSfKXre4TNSuwdRCIoLs 成功，DB423实际7日期对应星期；不是无事件重复 |
| +32.995s | ✍️ 正在整理上海未来 7 天的天气变化… | seq25后续API+3秒结果hold后的天气变化整理 |

The explicit temperature/humidity/wind receipt is supported by real numeric arrays, not URL parameter names or requested fields. Both later “当前步骤已完成” labels map to **distinct calls of the same execute_code tool**: first data formatting/statistics, then weekday lookup. Loops and mixed operations use a conservative generic action; this does not assert which internal statement is executing. No result says the whole weather task has completed prematurely. No approval or native interim occurred.

One status7435 with empty buttons. Native final7436 +41.616s; deletion+42.507s (0.891s after final). Final snapshot confirms status absent and answer present. Longest unchanged status10.464s (+15.187→+25.651), an actual model cycle reviewing retrieved weather data. The later final-summary hold is9.512s. No raw query/code/API URL leakage, duplicate bubble or permanent completion card. Forecast truth is not independently re-researched; this acceptance verifies that visible progress claims follow retrieved data and native execution.


## C — PASS

| Client time | Visible plugin state | Actual public evidence |
|---|---|---|
| +1.888s | 🤔 正在思考中… | seq29 pre_llm_call |
| +3.444s | 🤔 正在分析Telegram 状态消息的清理代码… | seq30 pre_api_request；保留用户要检查的清理目的 |
| +6.100s | 📖 正在查阅hermes-agent 使用说明… | seq32 skill_view call_71qoj95wzniV0w630DSf63tL，name=hermes-agent |
| +7.762s | 📖 已读取hermes-agent 使用说明，正在梳理内容… | seq33成功，DB427非空指南正文 |
| +9.923s | ✍️ 正在总结Telegram 状态消息的清理逻辑… | seq34后续模型调用及guide-result hold；并非声称已经读过源码 |
| +11.716s | 📖 正在检查Telegram 状态消息的清理代码… | seq36/37 read_file：指定telegram.py/adapter.py，offset1/limit2000 |
| +13.384s | 📖 已读取Telegram 状态消息的清理代码，正在梳理内容… | seq38/39成功，DB429/430非空源码且未截断 |
| +15.618s | ✍️ 正在总结Telegram 状态消息的清理逻辑… | seq40后续API请求，真实源码信息总结阶段 |

Trace seq29–43 contiguous, zero drops; all six main pre/post tool argument hashes and initial user hash match. Actual operations are exactly one skill_view and two read_file calls; no mutation tool. Both requested installed files return their full content (`truncated=false`). The guide-read status is distinct from the code-read status. The earlier guide-summary label revisits summary before code reading, but makes no unsupported assertion about unseen code. The short “正在检查” can arrive just after server-side reads finish due transport throttling; cross-machine tens of milliseconds are not treated as fabricated activity.

One status7438, empty buttons. Native final7439 +37.318s; deletion+38.202s (0.884s later). Status absent/answer present in final snapshot. Longest unchanged state22.584s (+15.618→+38.202), a source-grounded code-summary phase with one public model cycle; no tool ran during that wait. No native interim, new buttons, completion card, or file write.


## D — PASS

| Client time | Visible plugin state | Actual public evidence |
|---|---|---|
| +1.118s | 🤔 正在思考中… | seq44 pre_llm_call |
| +2.775s | 🤔 正在分析指定文件… | seq45 pre_api_request；分析指定文件 |
| +4.455s | ⚠️ 未找到指定文件，正在整理说明… | seq47 read_file call_e7jzSDjDStmUApiIfVYhEUyZ，seq48 error；DB434 content空且明确File not found。seq49模型继续并不抹去错误 |

Trace seq44–52 contiguous, zero drops; both argument hashes and user hash match. Exactly one read_file attempts the given nonexistent path. There is no successful source peer or retry. The missing-file error is visible in the plugin state before the native explanation, confirming the mixed-batch fix does not soften the wholly failed D case.

One status7441, empty buttons. Native final7442 +5.881s; deletion+6.819s (0.938s later). Final snapshot confirms status absent and answer present. Maximum unchanged state2.364s (+4.455→+6.819), correctly preserving the missing-file result. No success claim, fallback claim, duplicate bubble, or permanent completion card.


## E — news — PASS for observed flow

| Client time | Visible plugin state | Actual public evidence |
|---|---|---|
| +1.467s | 🤔 正在思考中… | seq53 pre_llm_call，匹配本轮prompt hash |
| +3.074s | 🤔 正在分析最近 7 天 OpenAI 的重要公开新闻… | seq54 pre_api_request，只表示分析 |
| +6.010s | 📖 正在查阅company-news-research 使用说明… | seq56/59 skill_view company-news-research 成功（另一指南57/58成功），DB438非空正文 |
| +7.678s | 📊 当前步骤已完成，正在核对最近 7 天 OpenAI 的重要公开新闻的结果… | seq60/61 terminal date -Iseconds exit0、DB440真实日期；保守当前步骤成功，不表示新闻任务完成 |
| +9.836s | ✍️ 正在汇总最近 7 天 OpenAI 的重要公开新闻… | seq62后续API+结果hold结束 |
| +15.010s | 🔎 正在搜索最近 7 天 OpenAI 的重要公开新闻… | seq64–69六个真实web_search启动 |
| +16.725s | 📊 已找到 10 条搜索结果，正在整理最近 7 天 OpenAI 的重要公开新闻… | seq74当前call_nJlBIp2bEQUS29yE4jP7kSmA/DB447真实data.web长度10；其他同批也均10 |
| +20.938s | ✍️ 正在汇总最近 7 天 OpenAI 的重要公开新闻… | seq76下一API及result hold，整理现有搜索结果 |
| +26.613s | 🔎 正在搜索最近 7 天 OpenAI 的重要公开新闻… | seq78–85八个真实web_search启动 |
| +28.290s | 📊 已找到 8 条搜索结果，正在整理最近 7 天 OpenAI 的重要公开新闻… | seq86当前call_bWxJMY8afpPbVwAc7XzQ6YrX/DB456真实data.web长度8；其他同批也均8 |
| +32.464s | ✍️ 正在汇总最近 7 天 OpenAI 的重要公开新闻… | seq94后续API真实开始+27.803，seq95到+79.871返回无工具响应，已有搜索证据支持汇总 |

The file contains50 hook rows; this exact E turn is **seq53–97, 45 rows**, all contiguous and zero drops. Seq98–102 belong to a different turn_id after E completed and are not used to justify E's state. All34 main-tool pre/post argument hashes match. Actual E tools are two skill_view, one read-only date command and fourteen web_search. There is no web_extract, mutation, native interim or tool failure in E. Thus this run does not claim mixed-source/recovery coverage. Search snippets/results supply the native answer; this audit does not conduct independent external fact checking of news.

Two visible result counts10/8 match the selected returned arrays, not merely request limits or unique news counts. No raw search syntax, URLs or long query fragments appear in the owned status. The `date -Iseconds` form falls back to conservative “current step completed”; unlike round2 it no longer says the whole news task succeeded. No `telegram_ux_update` call is needed or observed.

One status7444, empty buttons. Native final7445 +80.372s; deletion+81.025s (0.653s later). Final snapshot confirms status absent and final present. Longest unchanged state is **48.561s** (+32.464→+81.025), accurately labelled news synthesis, with no intervening tool operation. A long real model cycle is not evidence of a stuck status or fictional progress; no invented stages were inserted. No permanent completion card.


## Additional mixed candidate — two successful pages, NOT mixed-failure coverage

Trace seq108–118, zero drops; four tool-argument hashes match. Both requested public pages actually succeeded this time. The earlier AP extraction failure is not fabricated into this run. AP content is partial/truncated but nonempty; the native answer explicitly notes this. No retry or mutation occurs.

| Client time | Visible plugin state | Actual public evidence |
|---|---|---|
| +0.962s | 🤔 正在思考中… | seq108 pre_llm_call |
| +2.741s | 🤔 正在分析最近 7 天 OpenAI 公开新闻中的两篇资料… | seq109 pre_api_request |
| +6.418s | 📖 正在阅读最近 7 天 OpenAI 公开新闻中的两篇资料相关资料… | seq111/112两独立web_extract同一API批次，真实并行请求两页 |
| +8.075s | 📖 已读取最近 7 天 OpenAI 公开新闻中的两篇资料，正在梳理内容… | seq113/114均statusok，DB460/461各有11088/15328字符正文、error:null |
| +10.271s | ✍️ 正在汇总最近 7 天 OpenAI 公开新闻中的两篇资料… | seq115下一模型请求及result hold，整理两篇已获得内容 |

One status7448, empty buttons; native final7449 +28.450s, delete+29.380s (0.930s later). Longest unchanged summary19.109s. Final snapshot confirms owned status absent/answer present. Lifecycle and truthful double-success flow PASS; required mixed-failure branch remains untested by this case.


## Additional mixed-failure — real same-batch success + failure — PASS

| Client time | Visible plugin state | Actual public evidence |
|---|---|---|
| +1.253s | 🤔 正在思考中… | seq119 pre_llm_call |
| +2.996s | 🤔 正在分析最近 7 天 OpenAI 公开新闻中的两篇资料… | seq120 pre_api_request |
| +7.418s | 📖 正在阅读最近 7 天 OpenAI 公开新闻中的两篇资料相关资料… | seq122/123同API:1两次真实web_extract启动；时钟差不足以用8ms判定倒序 |
| +9.097s | ⚠️ 部分最近 7 天 OpenAI 公开新闻中的两篇资料资料读取失败，正在整理已有结果… | seq124当前调用error+seq125同批另一读取ok+seq126真实下一模型请求；合并的是已观测同批混合结果 |
| +11.265s | ⚠️ 部分资料读取失败，正在汇总最近 7 天 OpenAI 公开新闻中的两篇资料… | seq126后续API已持续超过3秒，带失败限定地汇总成功资料；seq127–129最终阶段继续保留限定 |

Trace seq119–129 contiguous, zero drops; four main-tool argument hashes and prompt hash match. The two direct web_extract calls share the exact API:1 request ID and are both started before either completes:

- seq122 `call_ZSyutWLtv2ofQd58sHw1PLmN`: official OpenAI page; seq125 succeeds, DB465 contains8838 characters of正文 and `error:null`.
- seq123 `call_OSMLCMJAYvBW97nWHE25hD4z`: example.invalid URL; seq124 fails, DB466 has empty content and `Blocked: URL targets a private or internal network address`. This is an actual tool URL-guard rejection, not a fabricated body or an asserted remote HTTP/DNS outage. No bypass was attempted.

The failed call is the last-started/current call; success arrives afterward from the other call. At seq126 next model request, the merged presentation correctly keeps both facts. Partial-failure wording persists through task synthesis and terminal display. This directly exercises the previously missing inverse case, rather than relying only on unit tests or an unrelated successful date command. No retry, script, file mutation or `telegram_ux_update` call occurs. Native final accurately distinguishes the received official article from the rejected empty result.

One status7451, empty buttons. Native final7452 +15.347s; deletion+16.254s (0.907s later). Final snapshot confirms status absent/answer present. Longest unchanged interval4.989s (+11.265→+16.254), partial-failure-qualified synthesis. No whole-task failure overwrites available results. P3-only wording observation: concatenating a task ending with “两篇资料” creates “两篇资料资料” in one status; it does not change the factual scope or lifecycle result.


## Additional sequential recovery — PASS

| Client time | Visible plugin state | Actual public evidence |
|---|---|---|
| +1.163s | 🤔 正在思考中… | seq130 pre_llm_call |
| +2.860s | 🤔 正在分析核实 OpenAI 法律产品的公开资料… | seq131 pre_api_request，仅分析任务 |
| +4.508s | ⚠️ 这次读取核实 OpenAI 法律产品的公开资料没有成功 | seq133/134首次web_extract的真实URL guard rejection，DB470正文空；seq135不抹掉失败 |
| +7.699s | ↪️ 再次尝试，正在阅读核实 OpenAI 法律产品的公开资料相关资料… | seq137真实新web_extract已启动；相同工具、同一用户任务、不同公开来源URL，故任务层面再次尝试，不是再次请求被拒绝URL |
| +9.361s | 📖 已读取核实 OpenAI 法律产品的公开资料，正在梳理内容… | seq138 statusok，DB472官方页3083字符非空正文、error:null |
| +11.530s | ✍️ 正在整理核实 OpenAI 法律产品的公开资料… | seq139后续API+结果hold，seq140–142正常响应/结束，成功读取后整理真实内容 |

Trace seq130–142 contiguous, zero drops; four tool-argument hashes and prompt hash match. API:1 starts/finishes the invalid-URL extraction with actual guard rejection. Only after the subsequent model result does API:2 start the official-page extraction; this is sequential, not a parallel batch. The native final honestly records the first failure and the later successful public material. No bypass, retry of the rejected URL, script or mutation occurs.

“再次尝试” is supported as another attempt to read material for the same task; both calls use web_extract but point to different URLs. The current source selects `retry` for the same tool name and `alternative` for a different tool. The label does not assert that the failing URL itself recovered or that the failure was a remote HTTP error. A model request alone did not invent recovery: a real new pre_tool event preceded the recovery state.

One status7454, empty buttons; final7455 +11.746s, delete+12.683s (0.937s later). Final snapshot confirms status absent/answer present. Longest unchanged state3.191s (+4.508→+7.699), the first explicit failure pending the real follow-up action. No permanent completion card or late owned status appears.

## Consolidated final-version metrics and bounded conclusion

| Case | First status (s) | Visible versions | Longest unchanged (s) | Native final (s) | Delete (s) | Delete after final (s) |
|---|---:|---:|---:|---:|---:|---:|
| A-final | 1.979 | 4 | 3.575 | 8.555 | 9.627 | 1.072 |
| B-final | 1.122 | 10 | 10.464 | 41.616 | 42.507 | 0.891 |
| C | 1.888 | 8 | 22.584 | 37.318 | 38.202 | 0.884 |
| D | 1.118 | 3 | 2.364 | 5.881 | 6.819 | 0.938 |
| E | 1.467 | 11 | 48.561 | 80.372 | 81.025 | 0.653 |
| mixed | 0.962 | 5 | 19.109 | 28.450 | 29.380 | 0.930 |
| mixed-failure | 1.253 | 5 | 4.989 | 15.347 | 16.254 | 0.907 |
| recovery | 1.163 | 6 | 3.191 | 11.746 | 12.683 | 0.937 |

A–E numeric metrics match `calculated-metrics.json`. The additional cases were independently derived from their raw events. These eight completed live cases show **eight owned status messages, all deleted**, with every native final preserved in its final snapshot and no ordinary inline keyboard or permanent completion card. Primary A–E first status latency is1.118–1.979s; deletion follows the native final by0.653–1.072s across all eight cases.

No additional confirmed P1/P2 remains in this audited final runtime on the exercised paths. Both prior confirmed P2 issues have concrete final evidence: “current step” success scope in B/E, and real same-batch mixed outcome preserved into synthesis in mixed-failure. D retains an unambiguous wholly failed missing-file result. Query strings are not exposed; source/task-specific facts, real failures and real follow-up actions drive the observed states.

Limits: this is finite live UX evidence, not a guarantee of every provider/network failure, every arbitrary script classification, or Telegram native delivery ordering. The candidate still conservatively labels unsupported mixed scripts; long genuine model calls can leave truthful synthesis text unchanged. There is a nonblocking P3 duplicated-word observation in the two-page supplemental task. External news/weather correctness was not independently researched. Native approval is evidenced in A; this run does not claim a separately rendered plugin approval label for its brief nested approval. Different-turn background hook rows are explicitly excluded. The later smoke after removal of the test observer is outside this seven-hook audit and must not be represented as newly hook-correlated. Native usage/stop/media and disabled-baseline checks are owned by the root acceptance workflow, not independently re-certified by this report.


# Historical temporary-progress live Telegram acceptance — 2026-09-20

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
