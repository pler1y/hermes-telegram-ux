# Milestone guidance and host verification

`telegram_ux_update` is optional. Guidance asks for a concrete new comparison, verification or synthesis phase when real tool activity cannot express it, and asks simple tasks to omit calls. There is no quota, forced tool choice or periodic schedule. Goal-only filler, question echoes, duplicate text and unsupported findings are suppressed; accepting a tool input does not promise that it was displayed or verified.

The host probe uses the real PluginManager, tool registry, message composition and deferred Tool Search / `tool_call` bridge. Only transport is synthetic; no model runs. It verifies discovery, schema, per-turn guidance, underlying tool dispatch, visible milestone integration and unload. It passed on Python 3.11 and 3.12 against the verified host baseline.

```bash
python scripts/probe_progress_host.py --core "$HERMES_CORE" --output artifacts/host-probe.json
```

Host availability does not establish voluntary model use. Actual model calls, visibility, omissions and limits are recorded in [real acceptance](LIVE-MILESTONE-ACCEPTANCE.md). Authored [event timelines](MILESTONE-TIMELINES.md) separately exercise ordering and cleanup. The plugin reads no hidden reasoning and cannot guarantee that every model emits useful notes.
