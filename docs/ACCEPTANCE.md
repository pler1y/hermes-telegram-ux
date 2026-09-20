# Temporary progress acceptance

Use an isolated Telegram test bot and fixed official Hermes core. Record exact source/artifact hashes and distinguish actual Telegram observations from synthetic hook tests. These are criteria, not a claim that the current candidate has passed or been deployed.

## Product scenarios

| Scenario | Request | Check |
|---|---|---|
| A: fast answer | `1+1等于多少` | Schedule initial feedback at the first reliably correlated public turn hook. A turn finishing before the worker sends must not leave a late bubble. Preserve the native answer. |
| B: weather search | `帮我查一下上海未来7天天气` | Status includes actual query/task when available. Recognized results support only observed counts/fields. Never claim missing humidity data. Edit the same message, then clean it up. |
| C: investigation | `调查最近一周 OpenAI 有什么重要新闻` | Relevant query/task labels appear when observable; an informative investigation does not remain a generic tool-name display throughout. |
| D: code inspection | `检查这个项目为什么 Telegram 状态消息没有删除` | File/search/test stages correspond to real operations. Safe filenames or recognized Telegram context identify the subject. Printing a test command is not running tests. |
| E: tool failure | A deliberately failing bounded search/tool fixture | No fabricated success, acquired data or retry. A retry requires a real subsequent attempt. Preserve the native explanation. |
| F: cleanup | Complete a normal task | Finalizing followed by deletion after a short cleanup window. No permanent “本轮处理已结束”, elapsed timer, details/settings/dismiss/continue buttons or count footer remains. |

Capture message IDs, edits, deletions and native answers. Do not demand exact example wording, invented waiting stages, an initial bubble for a turn completed before sending, or deletion precisely after successful Telegram delivery. `on_session_end` is not a delivery receipt. Record any residual message caused by a real deletion failure.

## Automated regression requirements

| Area | Checks |
|---|---|
| Lifecycle | One send per turn; same-ID edits; no replacement after edit failure; completion before/during send; late-event suppression; normal/reset/unload cleanup. |
| Task context | Generic feedback scheduled before extraction; safe user-task reduction; query/file/command target extraction; specific, partial and generic fallback. |
| Evidence | Structured search counts; actual numeric weather fields; missing-field negative controls; unknown/malformed results; failure precedence; test execution versus test success. |
| Public notes | Successful progress-tool handling; concise public action; intended next steps/model claims never promoted to verified success; no general answer-style guidance. |
| Ordering/volume | Identical text does not edit; rapid updates coalesce; old tool/request/interim events cannot rewind newer state; terminal state cannot reopen. |
| UI | No ordinary-status keyboard, timer, statistics or completion card. Independent `/tgux` has language/progress/emoji only. Old preferences cannot restore removed UI or final-answer annotation. |
| Isolation | Missing/expired/consumed/mismatched route skips output; user/topic/profile boundaries; no pre-auth send; unknown initial delivery never triggers another send. |
| Failures | Send/edit/delete error/timeout isolation; bounded cleanup; native final text/attachments unaffected; plugin expiry does not stop Hermes. |
| Boundary | Real PluginManager hook/manifest agreement; public transport signatures; official validate/doctor; no Hermes private runtime access or mutation. |

Automated transport/host tests do not prove live Telegram delivery, real model note quality, group behavior or compatibility beyond executed core versions. Follow [TESTING.md](TESTING.md); native packaging tests read committed source and cannot validate uncommitted changes.

## Native flow checks

Retain baseline checks for native file delivery with downloaded contents verified, approval/denial, bounded tool timeout, `/stop` followed by a new conversation, plugin-disabled native chat, independent `/tgux` navigation and scoped preferences. Group/topic and multi-profile live sessions require separate evidence if performed. Plugin status expiry must not be mistaken for task cancellation.

For reproducible approval cases, `tests/fixtures/approval_gate` is a separate test policy plugin requesting native approval for harmless marked `printf` commands. Remove it after testing; it is excluded from release archives. Automation may approve once only for an exactly matched, previously reviewed bounded fixture command, never arbitrary model output.

Historical acceptance used permanent completion cards and buttons. Its results remain in [VALIDATION.md](VALIDATION.md); the old `catalog_experience_acceptance.py` button expectations do not validate this revision. Record new results against current source only after execution.
