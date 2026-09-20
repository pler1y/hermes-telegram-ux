# v2.1.0 real model and Telegram acceptance

The development acceptance used a dedicated Telegram Bot, the real Hermes model (gpt-5.6-sol, medium) and public tool events/results. Model tool calls were correlated with actual Telegram sends, edits and deletions. No script invoked progress notes on behalf of the model. Hidden reasoning was not collected. The verified host was Hermes 0.21.3 at `3c3ab69abb9b08683b5eb15b4e2b8be1198c875f`.

## Observed scope

Eight rounds contained **37 natural main-task attempts**, including 27 complex tasks. Twenty complex tasks voluntarily called `telegram_ux_update`: **37 real model calls**, of which **31 became visible statuses**. Five historical filter omissions were corrected with regression coverage; one completed-claim note was correctly omitted. Seven complex tasks made no calls. Ten simple/control tasks made no calls; complex tasks used at most three. These are aggregate development observations, not a guaranteed call rate for every model or a claim that every attempt passed.

Tasks covered release-date research, cleanup-code inspection, file/data analysis, multi-source news research, simple answers and real failure/recovery. Thirty-six main attempts completed with native answers. The last data follow-up exhausted provider HTTP 429 retries and did not produce a task answer. A separate restored-configuration smoke succeeded earlier. One long-running historical capture ended before its task; later absence was checked separately, without inventing a deletion timestamp.

Historical native-answer errors included a stale latest-release claim and ambiguous percentage denominators. Fresh-source and explicit-denominator follow-ups corrected those answers. The plugin does not rewrite or guarantee native answer accuracy. Hermes background skill learning was preserved; aggregate behavior cannot be attributed solely to plugin guidance.

## Representative real observations

Latest complex multi-source research: initial status → **real model milestone** “核对GitHub实时API的release、tag与发布时间” → real retrieval tools/results → **real model milestone** “对照最新tag、main分支与官方产品公告” → **real model milestone** “复核‘已发布／已公告／仅main’边界并整理时间线” → real file-write action → native answer → owned status deleted. All three model notes were visible; the native answer completed in about 555 seconds.

Last data follow-up: initial status → **real model milestone** “核验重复记录、缺失成本与异常值对月度和地区汇总影响” → **real read tool event** → **real model milestone** “整理原始与去重汇总，并将重复影响与数据质量影响分开表述” → actual provider failures/retries → native error message. Both notes were visible, but there was no normal completion hook or answer. A read-only Telegram watch later observed TTL expiry and deletion, with native error messages preserved.

Simple/control tasks did not force model milestones. Actual tool events and recognized results drove automatic progress where available; ordinary API activity did not invent comparison or synthesis. The [authored replay timelines](MILESTONE-TIMELINES.md) are explicitly synthetic and are not included in the model call counts.

## Known limitation

Agent lifecycle completion is not a Telegram delivery receipt, and some abnormal host termination paths may fall back to the configured status TTL for cleanup. The default is 600 seconds. This was observed on provider retry exhaustion; it is retained as a nonblocking P2 limitation without private API or core workarounds.

## Release verification

The accepted implementation passed 240 unit and 7 real-host contract tests on both Python 3.11 and 3.12, boundary checks, official validate/doctor, native Git/ZIP lifecycle, historical upgrade paths and reproducible packaging. Those development checks precede the formal version metadata. The final commit's CI, compat check, package identity and two-task release smoke are recorded separately in the official [v2.1.0 Release](https://github.com/pler1y/hermes-telegram-ux/releases/tag/v2.1.0).

Raw captures, credentials, temporary observers and machine-specific environment reports are excluded from Git and release archives. Test observation configuration is restored before final smoke; learned native skills and ordinary user data are not rewound.
