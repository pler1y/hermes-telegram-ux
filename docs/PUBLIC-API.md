# Catalog-safe public capability inventory

Checked 2026-09-16 against official main **`3c3ab69abb9b08683b5eb15b4e2b8be1198c875f`**, Hermes **0.21.3**. The Full baseline is `8e38243614c1ecc37e0cdcbd4e6e223f920ec895` (1.8.3-rc.1). Its private integration is absent from this branch and every Catalog payload.

Primary references at the exact checked revision:

- [Public hook catalog and payloads](https://github.com/NousResearch/hermes-agent/blob/3c3ab69abb9b08683b5eb15b4e2b8be1198c875f/website/docs/user-guide/features/hooks.md)
- [Native plugin API and platform handler factory](https://github.com/NousResearch/hermes-agent/blob/3c3ab69abb9b08683b5eb15b4e2b8be1198c875f/website/docs/developer-guide/plugins/index.md)
- [PluginContext and VALID_HOOKS public definitions](https://github.com/NousResearch/hermes-agent/blob/3c3ab69abb9b08683b5eb15b4e2b8be1198c875f/hermes_cli/plugins.py)
- [Public BasePlatformAdapter send/edit/delete signatures and SendResult](https://github.com/NousResearch/hermes-agent/blob/3c3ab69abb9b08683b5eb15b4e2b8be1198c875f/gateway/platforms/base.py)
- [Observer ID/status contract](https://github.com/NousResearch/hermes-agent/blob/3c3ab69abb9b08683b5eb15b4e2b8be1198c875f/website/docs/developer-guide/observer-hooks.md)
- [Official admission validator](https://github.com/NousResearch/hermes-agent/blob/3c3ab69abb9b08683b5eb15b4e2b8be1198c875f/hermes_cli/plugin_validate.py)

## Feature → hook → fallback

| Hook / capability | Timing and fields consumed | Return / behavior | Missing-data fallback |
|---|---|---|---|
| `pre_gateway_dispatch` | Before authorization; `event.source` (platform/chat/user/thread/profile), `event.message_id`, `event.internal` | Always `None`; capture a plugin-owned ticket only | No network before authorization; skip invalid ingress |
| `pre_llm_call` | Turn starts; `session_id`, `turn_id`, `platform`, `sender_id`, `parent_session_id` | Always `None`; create bounded state, optionally claim ticket | No text injection; no live route without a matching ticket; skip subagents |
| `pre_tool_call` | Before execution; session/turn/tool-call IDs, tool name | Always `None` | No argument rewrite, block, approve, or ID guessing |
| `post_tool_call` | Tool settles, including blocked/cancelled; IDs, name, `status` | Always `None` | Missing status means returned, not success; no result inspection |
| `pre_api_request` | Each provider attempt; session/turn/request IDs | Always `None` | Missing attempt ID not counted |
| `post_api_request` | Provider attempt returned | Always `None` | Does not mean the overall task completed |
| `api_request_error` | Provider attempt failed | Always `None` | Shows observed request failure; does not invent retry progress |
| `pre_approval_request` | Before prompted/smart approval; `turn_id`, `tool_call_id`, `surface` | Always `None`; prompted wait differs from smart evaluation | No ambiguous cross-session join; native approval remains authoritative |
| `post_approval_response` | Choice/timeout/withdrawal/notification failure; IDs, `choice` | Always `None` | Unknown choice never treated as approval |
| `on_interim_message` | Off-path observer, streaming or non-streaming; session/turn/iteration | Always `None`; generic stage acknowledgement | Never resends text, including already-streamed text |
| `transform_llm_output` | Before successful final delivery; text, session/platform and additive turn ID | Nonempty original text plus optional counts, or `None` | Empty/silent/media/code-fence-sensitive replies pass through; exceptions return `None` |
| `on_session_end` | Turn finalization; session/turn IDs, completed/failed/interrupted | Always `None`; finish panel and release turn state | Reduced legacy exit payload cannot assert precise outcome |
| `on_session_finalize` / `on_session_reset` | Session teardown/reset; outgoing session ID | Always `None`; discard only matching state/panels | No cross-session cleanup from absent IDs |
| `ctx.register_platform_handler("telegram", factory)` | Connect-time `(native, adapter)` | Retain supplied adapter for public send/edit/delete; no SDK handler interception | Reconnect cancels old panels, invalidates old tickets |
| `ctx.get_config` | Plugin-relative settings on registration | Read own namespace only | Invalid values use bounded defaults |
| `ctx.register_command("tgux", handler)` | Native command dispatch, raw args | Static localized help string | No conversation lookup needed |
| `ctx.spawn_task` / `ctx.on_unload` | Supervised async work / reverse cleanup | Nonblocking panel worker; stop and clear on unload | Missing event loop fails only the isolated factory; native Telegram continues |

All registered callbacks accept additive keyword fields. All event processing is in-memory and bounded (128 concurrent turns, 512 counted events per turn, idle expiry). Counts use opaque IDs; session keys are never parsed. Tool arguments/results and approval commands are never retained or copied to the panel.

## Middleware

**None registered or required.** The [official middleware contract](https://github.com/NousResearch/hermes-agent/blob/3c3ab69abb9b08683b5eb15b4e2b8be1198c875f/website/docs/developer-guide/middleware.md) supports request dictionaries and `next_call` execution wrappers, with fail-open exceptions. None is necessary for observational UX; the implementation does not touch requests, guardrails, tool execution or approvals. `provides_middleware` and `provides_tools` are empty and checked by the official probe. There is no artificial plugin tool solely to inflate the feature list.

## Routing and transport boundary

The public ingress hook supplies normalized message fields. The platform registrar supplies the read-only adapter handle; only its public `send(chat_id, content, reply_to, metadata)`, `edit_message(chat_id, message_id, content)` and `delete_message(chat_id, message_id)` methods are called. The hook documentation explicitly permits side-channel replies through public adapter sends. No gateway object, session store, bot token, private transport field or Hermes import is used.

Python ContextVar propagation is an **optional optimization, not a promised Hermes lifecycle contract**. A single-use ticket is shared only through the actual execution context; it expires after 60 seconds and is consumed atomically. Matching public sender/profile fields and active transport generation are required before sending. Absent propagation disables live display. The actual host dispatcher/context behavior is covered by a contract test on the pinned core and current-main CI. This approach cannot guarantee a rolling panel for delayed/reconstructed queue turns; restoring that guarantee requires an explicit public route/turn hook.

Only calls for a known `(session_id, turn_id)` affect state. Approval events lacking session ID require a unique matching turn ID. Unknown events are ignored. No lookup into gateway/session databases or internal runtime state fills gaps. The original final reply remains owned by Hermes even after transport failure.

## Omitted lifecycle coverage

No intake acknowledgement, busy interception, natural-language stop matching, custom stop implementation, completion-group renderer, session/database polling or Full adapter import. Public `agent_loop_stopped` currently exists as an observer, but its routing key does not provide this adapter's turn correlation; it is deliberately unused. Interruption labels come only from correlated `on_session_end(interrupted=True)`.

The original [PR #108887](https://github.com/NousResearch/hermes-agent/pull/108887) was OPEN when checked on 2026-09-16. Its [maintainer follow-up](https://github.com/NousResearch/hermes-agent/pull/108887#issuecomment-5674969935) requires eliminating private rebinds and using public extensions. No PR update or remote publication is part of this local candidate. Admission remains subject to review; passing validation alone does not establish acceptance.
