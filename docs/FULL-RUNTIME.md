# Full runtime boundaries

Full retains the complete Telegram interaction lifecycle through guarded Hermes runtime integration. Catalog-safe is maintained separately. The compatibility gate runs before runtime import/registration; runtime wrappers never rewrite Hermes source files.

## Current responsibilities

| Module | Responsibility |
| --- | --- |
| `compat.py`, `compatibility.json` | Exact reviewed source/AST profiles and core version checks |
| `bindings.py` | Transactional overrides, handler ownership and unload restoration |
| `full_adapter.py` | Native session-key resolution, originating worker context and serialized hook mutation |
| `runtime.py` | Registration, host lifecycle integration, background ownership and delivery coordination |
| `intake.py` | Early receipt ownership, native admission handoff and compression feedback |
| `status.py`, `progress.py` | Turn state, public progress and operation/attempt evidence |
| `actions.py`, `welcome.py`, `controls.py` | Telegram buttons, menu and native command forwarding |
| `install.py` | Reversible plugin/configuration installation and language selection |

The adapter introduced in 1.8.3-rc.2 narrows native identity handling. Existing private patch installation and delivery remain in runtime/intake; they have not all been moved behind a new interface. Future extraction should preserve these tested boundaries rather than introduce additional wrappers solely to reduce file size.

## Turn and conversation identity

A gateway generation and an agent hook `turn_id` are different identifiers. The synchronous notify wrapper binds the exact `TurnState` before Hermes creates the executor task; Hermes' existing copied context carries that owner into the worker. A late worker therefore still refers to its old state and cannot claim a replacement registered under the same session ID.

Hooks validate ownership and mutate state under the registry lock. Context-free callbacks must already identify the current agent turn. Background child sessions use an explicit child-to-state mapping; legitimate foreground handoff preserves ownership, while stop/child completion invalidates it. Native compression callbacks also compare the gateway generation.

Session routing follows the runner's native `_session_key_for_source`, including group-user isolation, shared topics and profile settings. Before that resolver is available, early feedback uses a conservative source identity plus adapter identity. A group send without an owner is not assigned to whichever group member happens to have the only active state.

## Private integration inventory

| Owner | Integration points | Contract / regression |
| --- | --- | --- |
| Runtime | `GatewayRunner._run_agent_notify_long_running`, `_compose_busy_ack_message`, `_send_busy_ack_reply`, `_busy_stop_command`, `_handle_stop_command`, `_deliver_async_delegation_group` | Lifecycle, busy routing, native stop delegation, cancellation completion filtering; `test_runtime`, `test_experience`, `test_turn_ownership`, `test_acceptance` |
| Intake | `GatewayRunner._handle_message_with_agent`, `_hmwa_hygiene_plan`, `_hmwa_run_session_hygiene`, `_hmwa_hygiene_notify`; `TurnRunner._status_callback_sync` | Early receipt admission/cleanup and native compression notices; `test_intake` |
| Identity adapter | Native adapter selection, `_session_key_for_source`, notify-before-executor order and `_run_in_executor_with_context` context propagation | No additional host method replacement; `test_turn_ownership` calls the real executor seam; `test_integration_safety` exercises native session routing |
| Telegram integration | Send/edit wrappers, batching attributes, stream display filtering, native authorization/command/observer entries | Adapter-scoped delivery, handler cleanup and forwarding; `test_controls`, `test_delivery`, `test_product`, `test_integration_safety` |
| Background integration | Subagent registry interruption; async completion claim/drop/release | Native foreground stop remains reachable if auxiliary cancellation fails; `test_turn_ownership`, `test_acceptance` |

Identity resolution and executor ordering are in files already covered by the 23-file compatibility contract. No extra unsupported core baseline is enabled by this change. The inventory is grouped by behavior; it does not claim that six runner methods represent the entire private dependency surface.

## Failure and evidence rules

- Child lookup, interruption or cancellation-record persistence cannot prevent the native foreground stop call. Successful in-memory cancellation records remain usable if durable storage fails; restarting before persistence recovers can still lose those records.
- Progress problems and results belong to an operation and attempt. Another operation's success does not resolve a failure; an older attempt finishing late does not override its successor. Display stage and foreground/background execution options do not define operation identity.
- Result history is bounded to 64 entries and precise failures to 128; older unresolved failures retain a conservative stage warning until the task ends.
- Native reconfiguration preserves the selected language unless explicitly changed. ZIP language editions retain their existing selection behavior.
- Configuration writes copy ancestors along the changed path so YAML aliases do not propagate Telegram settings into another platform. Restoration uses the same write boundary.

## Verification

Use `scripts/run_tests.py` in a pinned Hermes environment: skipped runtime cases fail the run. Continue `check_compatibility.py`, `check_runtime.py`, native install/discovery/unload and both ZIP edition lifecycles. Updated results and the independent Telegram test report are recorded in [FULL-PROGRESS.md](FULL-PROGRESS.md).
