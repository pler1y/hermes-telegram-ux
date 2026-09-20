# Hermes Telegram UX public capability inventory

Source rechecked for product convergence on 2026-09-20 against official Hermes **`3c3ab69abb9b08683b5eb15b4e2b8be1198c875f`**, Hermes **0.21.3**. The v2.0.0 release candidate preserves the accepted runtime at `c5b8aef94d1f096fbad9ad782b2ad312e9254d33`; release preparation changes metadata and documentation, not these API interactions. Full 1.8.3 is preserved at `3b2175199d8d9dbafaa39e13c1f5dafd4bf0cfcb` (same tree as tag `v1.8.3`); `8e38243614c1ecc37e0cdcbd4e6e223f920ec895` is the two lines' common ancestor. Full private integration is absent from the v2 runtime.

Primary references at the checked revision:

- [Hook catalog](https://github.com/NousResearch/hermes-agent/blob/3c3ab69abb9b08683b5eb15b4e2b8be1198c875f/website/docs/user-guide/features/hooks.md)
- [PluginContext and public hook names](https://github.com/NousResearch/hermes-agent/blob/3c3ab69abb9b08683b5eb15b4e2b8be1198c875f/hermes_cli/plugins.py)
- [Public adapter transport](https://github.com/NousResearch/hermes-agent/blob/3c3ab69abb9b08683b5eb15b4e2b8be1198c875f/gateway/platforms/base.py)
- [Observer IDs and statuses](https://github.com/NousResearch/hermes-agent/blob/3c3ab69abb9b08683b5eb15b4e2b8be1198c875f/website/docs/developer-guide/observer-hooks.md)
- [Official admission validator](https://github.com/NousResearch/hermes-agent/blob/3c3ab69abb9b08683b5eb15b4e2b8be1198c875f/hermes_cli/plugin_validate.py)

## Registered hooks

The runtime declares 16 hooks. `post_llm_call` replaces `transform_llm_output`; the plugin does not transform final answers.

| Hook | Public inputs consumed | Current use and fallback |
|---|---|---|
| `pre_gateway_dispatch` | `event.source` platform/chat/user/thread/profile, message ID, internal flag | Capture a single-use ingress ticket; return `None`. Never send before authorization. |
| `pre_llm_call` | Session/turn/platform/sender/parent IDs, `user_message` | Match the ticket and schedule initial feedback before task extraction. Reduce the current public message to a task subject. Return narrowly scoped public-progress guidance. Missing route or subagent execution receives no live panel. |
| `pre_tool_call` | Session/turn/call IDs, `tool_name`, selected `args` | Identify the actual action and task object, with a safe filename or short natural query only as a fallback; raw query operators and long query strings are never display text. Return `None`; no rewrite, veto or approval. |
| `post_tool_call` | Same IDs, name, args, `status`, `result` | Observe outcome and recognized bounded result structures. Retain concise labels/facts, not raw arguments/results. Accept notes from this plugin's successful progress tool. |
| `pre_api_request` | Session/turn/request IDs, API iteration and retry count | Observe current model request without modifying it or inspecting private prompts. |
| `post_api_request` | Request identity and public tool-call shape/count | Observe returned request versus tool phase. It is not Telegram delivery; response/reasoning text is not copied. |
| `api_request_error` | Request identity | Show observed request failure; do not invent a retry. |
| `pre_approval_request` | Turn/tool-call identity, surface | Reflect prompted/smart waiting. Native approval remains authoritative. |
| `post_approval_response` | Identity and choice | Reflect observed outcome; unknown choice is not approval. |
| `on_interim_message` | Session/turn/iteration | Refresh correlated activity without storing/copying interim text or replacing a newer tool phase. |
| `post_llm_call` | Session/turn identity | Enter finalizing after the tool loop. Ignore answer text; no final-answer transform/send. |
| `on_session_end` | Session/turn identity, completed/failed/interrupted | Set terminal presentation, request cleanup, release turn state. Normal completion shows finalizing, not a permanent completion card. |
| `on_session_finalize` / `on_session_reset` | Outgoing session identity | Discard matching plugin state/messages; no absent-ID cross-session cleanup. |
| `subagent_start` / `subagent_stop` | Explicit parent session/turn and child session IDs | Refresh the explicitly correlated parent activity only; no child tree/storage, cancellation or raw child summaries. |

Callbacks accept additive keyword fields. State is bounded to 128 active turns and 512 observed event identities per turn. Only known `(session_id, turn_id)` pairs affect a turn. Approval events without a session ID require a unique matching turn ID. Terminal state prevents late events from reopening progress.

## Task context and evidence

`pre_llm_call` provides `user_message`, `conversation_history`, `is_first_turn`, `session_id`, `task_id`, `turn_id`, `model`, `platform`, `parent_session_id` and `sender_id` in `agent/turn_context.py`. This plugin uses the current public message, not hidden reasoning or private session history.

The reducer prefers a specific action/subject, falls back to a partial target such as a safe filename or short natural-language query, and finally uses a generic truthful action. A small grammatical reduction preserves the purpose in later clauses while removing request phrasing, paths and secondary advice. It makes no extra LLM call and does not guarantee a semantic summary of arbitrary prose.

Selected public tool arguments identify the action actually starting. Commands are classified without echoing shell text; mixed/unknown commands stay generic. Result parsing accepts recognized dictionary/JSON structures, not assertions in arbitrary prose: for example validated search-result lists and numeric temperature/humidity/wind fields. Missing humidity cannot become a humidity-data claim. A zero process exit supports “test command completed”, not “all tests passed”. Errors take precedence over success facts. Recognized whole JSON code blocks from successful page extracts can supply numeric weather fields; quoted search snippets, units, schemas and requested fields cannot. Shell/Python classification is syntactic only and skips uncalled function bodies and unproven branches. Unknown mixed scripts keep a truthful task-related execution fallback.

Concrete results and failures survive follow-up model requests; generic activity does not overwrite them. A successful result may become a task-related summary after a subsequent `pre_api_request`, a three-second minimum hold and the two-second display tick. That tick neither calls Hermes nor refreshes execution TTL. New tool events can replace the summary with a newly observed action. Successful source retrieval and failure within the same API batch and safe task object are summarized as partial failure in either completion order. Positive evidence requires a nonempty validated search result or completed content read; a clock query, ordinary process exit, empty search or earlier batch cannot erase a current source failure. The original per-tool error remains recorded, and partial failure stays qualified during synthesis and finalization. “Trying again/another method” requires a later related tool start after an observed failure, not merely another model request. Public `assistant_tool_call_count` supports normalized host response objects; retry counts distinguish attempts that share an API request ID.

`telegram_ux_update` is a registered public tool for bounded `goal`, `action`, `finding` and `next` notes. It does not execute work. An explicit model action note can supply concise wording when observed evidence is insufficient; claimed findings and intended next steps are not promoted to verified execution. The four fields are not dumped into the bubble. Guidance concerns public progress only, not general answer style.

Only safe labels and structural facts survive handling. Secret-like values, hidden-reasoning tags, delivery directives, full paths/URLs and raw code are excluded from displayed labels. This conservative filter is not a universal sanitizer for arbitrary untrusted input.

## Initial-feedback timing and routing

Initial status is scheduled immediately after route validation in `pre_llm_call`, before task extraction. The checked core has no reliable ordinary-message hook combining a route and post-authentication timing earlier than that:

- `pre_gateway_dispatch` precedes authentication in `gateway/run_inbound.py`.
- Authenticated `gateway_platform_event` currently covers Telegram reactions/edited messages, not ordinary new messages.
- `on_session_start` lacks a complete route and is not per user message.

Initial-feedback delay is therefore a public lifecycle limitation. No pre-auth reply, private auth helper or monkey patch is used.

ContextVar propagation is an **optional optimization, not a promised Hermes lifecycle contract**. A single-use ticket travels through the actual execution context, expires after 60 seconds, and requires matching sender/profile and transport generation. Missing propagation or reconstructed/delayed queue context disables live display. No session-key parsing or gateway/database lookup fills gaps.

## Transport and cleanup

`ctx.register_platform_handler("telegram", factory)` supplies a read-only adapter. Ordinary progress uses only public `send`, `edit_message` and `delete_message`. One acknowledged initial send establishes the message ID; later updates edit that ID. Duplicate text is skipped, updates coalesce, uncertain initial sends are not retried, and edit failure never creates a replacement bubble.

Normal `on_session_end` requests finalizing and cleanup. `cleanup_delay` defaults to 1 second, clamped to 0–5 seconds. The worker deletes its own known message with bounded attempts; deletion failure is isolated but can leave a message behind. A turn completed before its worker starts does not create a late bubble. An in-flight send uses its acknowledgement for cleanup when available; an unknown outcome cannot provide a deletable ID.

`on_session_end` reports Agent completion, not successful Telegram answer delivery. Neither it nor `post_llm_call` is a post-delivery receipt. A short cleanup window cannot establish ordering against a slow native send. There is no private cleanup-ID list, delivery callback or second answer-delivery mechanism.

Final answers, streaming, attachments, approvals, `/stop`, interruptions, task timeouts and recovery remain native. Plugin idle expiry ends its display, not the underlying task.

## Installation language and lifecycle services

No command, menu, callback handler, keyboard or per-user preference store is registered. `language` is the only presentation choice, configured as `auto`, `zh` or `en`. Auto reads bounded current public message text only, ignores paths/URLs/code blocks, chooses Chinese for Chinese text and English for English text, and falls back to Chinese for ambiguous input. No history, profile or state lookup is used.

`ctx.get_config` reads language and the existing edit-interval, idle-expiry and cleanup-delay controls. `ctx.spawn_task` supervises only owned display workers; `ctx.on_unload` cleans up their registrations and messages. The runtime no longer imports Telegram SDK types or uses `ctx.state`, `register_command`, native bot methods or callback registration.

## Evaluated public interfaces not used

| Interface | Reason |
|---|---|
| `on_stream_start` / `on_stream_delta` / `on_stream_end` | Individual provider attempts, not final delivery. Each hook/callback has an independent asynchronous queue; cross-hook order is not guaranteed. Token text is unnecessary for this event-based UI. No stream hooks are registered. |
| `llm_request` / `tool_request` middleware | Observing inputs/results does not require altering model requests, tool arguments or execution. No middleware is registered. |
| `transform_llm_output` | Removed from registration; final answer bytes stay native. |
| `agent_loop_stopped` | Its session-key payload does not provide this adapter's exact session/turn correlation. Use correlated `on_session_end`. |
| `gateway_platform_event` | Current Telegram types do not supply ordinary-message intake or final-delivery events. |
| Adapter processing callbacks / internal delivery coordination | Not public plugin completion registration with this plugin's correlation data. The plugin does not replace adapter methods or access private lifecycle state. |

Stream deltas can contain `kind="reasoning"` when the operator opts in. This plugin does not subscribe. `post_api_request` can expose assistant content before all scratchpad checks, so it is not used as progress prose. Interim text is public commentary but can arrive late, so it is not republished.

The [official middleware contract](https://github.com/NousResearch/hermes-agent/blob/3c3ab69abb9b08683b5eb15b4e2b8be1198c875f/website/docs/developer-guide/middleware.md) and stream APIs were evaluated; not using them is an implementation choice, not a claim that they are private or unavailable.

No Hermes runtime imports, monkey patches, task-manager replacement or global configuration writes are needed. Independent distribution and successful validation do not establish official Plugin Catalog admission.
