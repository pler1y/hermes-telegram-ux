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
| `pre_llm_call` | Turn starts; `session_id`, `turn_id`, `platform`, `sender_id`, `parent_session_id` | Per-turn context with display/conversation guidance after matching the execution identity; create bounded state | No live route or guidance without a matching ticket; skip subagents |
| `pre_tool_call` | Before execution; session/turn/tool-call IDs, tool name | Always `None` | No argument rewrite, block, approve, or ID guessing |
| `post_tool_call` | Tool settles, including blocked/cancelled; IDs, name, `status`; bounded arguments only for this plugin's successful progress tool | Always `None` | Other tool arguments/results are not retained; a blocked progress tool does not update public notes |
| `pre_api_request` | Each provider attempt; session/turn/request IDs and native retry count | Always `None` | Missing attempt ID not counted; retry labels describe the current request |
| `post_api_request` | Provider attempt returned | Always `None` | Does not mean the overall task completed |
| `api_request_error` | Provider attempt failed | Always `None` | Shows observed request failure; does not invent retry progress |
| `pre_approval_request` | Before prompted/smart approval; `turn_id`, `tool_call_id`, `surface` | Always `None`; prompted wait differs from smart evaluation | No ambiguous cross-session join; native approval remains authoritative |
| `post_approval_response` | Choice/timeout/withdrawal/notification failure; IDs, `choice` | Always `None` | Unknown choice never treated as approval |
| `on_interim_message` | Off-path observer, streaming or non-streaming; session/turn/iteration | Always `None`; generic stage acknowledgement | Never resends text, including already-streamed text |
| `transform_llm_output` | Before successful final delivery; text, session/platform and additive turn ID | Nonempty original text plus optional counts, or `None` | Empty/silent/media/code-fence-sensitive replies pass through; exceptions return `None` |
| `on_session_end` | Turn finalization; session/turn IDs, completed/failed/interrupted | Always `None`; finish panel and release turn state | Reduced legacy exit payload cannot assert precise outcome |
| `on_session_finalize` / `on_session_reset` | Session teardown/reset; outgoing session ID | Always `None`; discard only matching state/panels | No cross-session cleanup from absent IDs |
| `ctx.register_platform_handler("telegram", factory)` | Connect-time `(native, adapter)` | Public adapter send/edit/delete plus scoped `tgux2:` SDK callbacks; import only four reviewed SDK types inside the factory | Reconnect cancels old panels, invalidates old tickets |
| `ctx.get_config` | Plugin-relative settings on registration | Read own namespace only | Invalid values use bounded defaults |
| `ctx.register_command("tgux", handler)` | Native command dispatch, raw args | Owned menu after a same-ticket authorized `pre_command`; localized text fallback | No private conversation lookup or native handler dispatch |
| `ctx.spawn_task` / `ctx.on_unload` | Supervised async work / reverse cleanup | Nonblocking panel worker; stop and clear on unload | Missing event loop fails only the isolated factory; native Telegram continues |

All registered callbacks accept additive keyword fields. Event processing is in-memory and bounded (128 concurrent turns, 512 counted events per turn, idle expiry); at most 256 live UI cards with one-hour expiry. Personal preferences use quota-bounded public `ctx.state`. Counts use opaque IDs; session keys are never parsed. Only intentional public notes from the plugin's own successful progress tool are retained; other tool arguments/results, raw child summaries and approval commands are never copied to the panel.

## Middleware

**None registered or required.** The [official middleware contract](https://github.com/NousResearch/hermes-agent/blob/3c3ab69abb9b08683b5eb15b4e2b8be1198c875f/website/docs/developer-guide/middleware.md) supports request dictionaries and `next_call` execution wrappers, with fail-open exceptions. None is necessary for observational UX; the implementation does not touch requests, guardrails, tool execution or approvals. `provides_middleware` is empty. The single declared `telegram_ux_update` tool accepts bounded public milestones and optional follow-up suggestions; it cannot execute requests or change routing. The official probe checks both declarations.

## Routing and transport boundary

The public ingress hook supplies normalized message fields. The platform registrar supplies the read-only adapter handle; only its public `send(chat_id, content, reply_to, metadata)`, `edit_message(chat_id, message_id, content)` and `delete_message(chat_id, message_id)` methods are called. The supplied native Telegram SDK Application registers one prefix-scoped callback handler and its Bot sends/edits plugin-owned cards and reply keyboards. The hook documentation explicitly permits side-channel replies through public adapter sends. No gateway object, session store, bot token, private transport field or Hermes import is used.

Python ContextVar propagation is an **optional optimization, not a promised Hermes lifecycle contract**. A single-use ticket is shared only through the actual execution context; it expires after 60 seconds and is consumed atomically. Matching public sender/profile fields and active transport generation are required before sending. Absent propagation disables live display. The actual host dispatcher/context behavior is covered by a contract test on the pinned core and current-main CI. This approach cannot guarantee a rolling panel for delayed/reconstructed queue turns; restoring that guarantee requires an explicit public route/turn hook.

Only calls for a known `(session_id, turn_id)` affect state. Approval events lacking session ID require a unique matching turn ID. Unknown events are ignored. No lookup into gateway/session databases or internal runtime state fills gaps. The original final reply remains owned by Hermes even after transport failure.


## Additional public surfaces in 1.9.0-catalog.1

- `pre_command`: observes only authorized gateway `/tgux` dispatch. The ingress ticket must still match the command text, profile, transport generation and expiry. No directive is returned, and no menu is sent from the pre-auth hook.
- `subagent_start` / `subagent_stop`: require exact parent session/turn and child session IDs. Only observed status counts are shown. Child goals, summaries and tool histories are not copied; late starts cannot resurrect ended children.
- `register_tool`: one schema-bounded public progress tool, handled through its successful `post_tool_call` event. No tool overrides or execution middleware.
- `ctx.state.get/set`: hashed user/chat/topic keys store only display preferences. No global settings writes, credentials, conversation text or private session database access.
- Telegram SDK factory imports: `InlineKeyboardButton`, `InlineKeyboardMarkup`, `ReplyKeyboardMarkup`, `CallbackQueryHandler`. Each card uses an opaque token and validates its original user, chat, topic, message and expiry. Unload/reconnect removes the exact SDK handler. SDK use remains optional when the native object is unavailable.
- Follow-ups and native command shortcuts use selective, one-time reply keyboards. The user sends the request through native ingress; no `inject_message`, private command dispatcher or guessed session key is required. Command permissions stay with Hermes.

## Omitted lifecycle coverage

No intake acknowledgement, busy interception, natural-language stop matching, custom stop implementation, completion-group renderer, session/database polling or Full adapter import. Public `agent_loop_stopped` currently exists as an observer, but its routing key does not provide this adapter's turn correlation; it is deliberately unused. Interruption labels come only from correlated `on_session_end(interrupted=True)`.

The original [PR #108887](https://github.com/NousResearch/hermes-agent/pull/108887) was OPEN when checked on 2026-09-16. Its [maintainer follow-up](https://github.com/NousResearch/hermes-agent/pull/108887#issuecomment-5674969935) requires eliminating private rebinds and using public extensions. Official Catalog admission is separate from this repository's independent releases. Admission remains subject to review; passing validation alone does not establish acceptance.
