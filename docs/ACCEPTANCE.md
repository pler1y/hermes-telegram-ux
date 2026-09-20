# Hermes Telegram UX acceptance

Use only the dedicated test Bot and the fixed official core. Record exact source/runtime hashes; synthetic tests do not prove live Telegram behavior. The Progress Intelligence baseline is `77c4a11`; convergence must preserve its task inference, evidence rules and transport timing.

## Real task regression

| Case | Task | Required observation |
|---|---|---|
| A | `1+1等于多少？` | Prompt initial feedback, actual calculation if a calculation tool is used, native answer, one owned message deleted. |
| B | Shanghai seven-day weather, temperature/humidity/wind | Task-specific retrieval; fields only when actual values exist; current-step success scope; task-related synthesis; deletion. |
| C | Read installed telegram.py/adapter.py cleanup code, no writes | Actual read/inspect stages and the cleanup purpose; native answer and deletion. |
| D | Read a confirmed nonexistent file | Real missing-file failure remains visible through explanation; no invented success/retry. |
| E | OpenAI public news from the last seven days | Real search stage, actual returned counts when available, no raw query leakage, task-related long synthesis, deletion. |
| F | Failed public extraction followed sequentially by another actual source read | Failure appears first; recovery requires the later real pre_tool_call; success only after actual nonempty content. |

Capture every NewMessage/MessageEdited/MessageDeleted event from before sending the prompt and verify final message existence. Record one owned status ID per task, exact visible versions, native answer time, deletion time and longest unchanged state. Correlate tools with the correct public session/turn/call IDs. Exclude different-turn background events and hidden reasoning.

A long genuine model request can keep truthful synthesis text unchanged. Do not invent stages or require a fixed example string. Public turn completion is not a Telegram delivery receipt. Short states may be coalesced; a task finishing before the send worker starts must not leave a late bubble.

## Product removal checks

- No ordinary completion cards, elapsed/count footers, inline controls, details, continue, close, welcome/navigation/settings pages.
- `/tgux` is not registered, does not appear in the Bot's current command inventory, and invoking it produces no plugin menu. A native unknown-command reply is not a plugin error.
- Zero plugin commands, middleware or Telegram SDK callbacks. No persisted preference read/write. Old preferences cannot restore removed UI or disable ordinary progress.
- Per-turn language auto selection and fixed zh/en overrides; no cross-user/topic language cache. Chinese/English are the supported output labels; ambiguous text defaults to Chinese.
- Restoring the test configuration/removing temporary observers does not break native replies or owned-message cleanup.

## Automated protections

Preserve Progress Intelligence and all transport race/error tests: early/late completion, reset/unload, send acknowledgement ownership, edit failure without replacement, bounded deletion retry, throttle/coalescing, expired/mismatched/consumed route tickets, user/chat/topic/profile isolation, unknown route fallback, event identity limits, final-answer preservation and official enable/disable lifecycle.

Correlated interim/child events remain activity signals so display TTL does not regress; their raw text and unused statistics are not retained. Unregistered stream hooks cannot affect state. No native task cancellation or background-result filtering is implemented.

Run every unit and contract suite, boundary guard, official validate and doctor, and `git diff --check`. Native Git/ZIP packaging checks use committed objects and must identify the tested commit. Keep packaging output out of the source tree.

Native approval/stop/file behavior remains Hermes-owned. Do not count native approvals as plugin buttons. Additional native stop/file/group/topic testing requires its own evidence; do not silently inherit old tests as new live acceptance. The separate `tests/fixtures/approval_gate` may be used only for its reviewed harmless fixture and removed afterward; it never ships in the package.
