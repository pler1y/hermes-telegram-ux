#!/usr/bin/env python3
"""Live native discovery/middleware verification in a disposable Hermes home."""
import json
import os
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    # Set before importing any Hermes module, so global path caches stay isolated.
    with tempfile.TemporaryDirectory(prefix="hermes-ux-registration-") as raw:
        os.environ["HERMES_HOME"] = raw
        home = Path(raw)
        (home / "config.yaml").write_text("plugins:\n  enabled: []\n")
        from install import install
        install(home)
        from hermes_cli.plugins import discover_plugins, render_system_prompt_sections, has_middleware, get_plugin_manager
        from model_tools import get_tool_definitions
        discover_plugins()
        definitions = get_tool_definitions(enabled_toolsets=["interaction"], quiet_mode=True, skip_tool_search_assembly=True)
        names = [d["function"]["name"] for d in definitions]
        assert {"interaction_update", "interaction_actions"} <= set(names), names
        sections = render_system_prompt_sections({"platform": "telegram", "session_id": "ux-fixture"})
        from plugin.i18n import package_language
        language = package_language()
        expected = "先给结论" if language == "zh" else "Use English"
        assert any(s.id == "hermes_interaction.telegram" and expected in s.content for s in sections)
        assert has_middleware("llm_request") and has_middleware("tool_request")
        from hermes_cli.middleware import apply_llm_request_middleware
        from agent.codex_responses_adapter import _preflight_codex_api_kwargs
        from agent.codex_runtime import _bypass_sdk_request_transform
        from plugin.status import TurnState
        from plugin.progress import TaskProgress
        runtime = next(callback.__self__ for callback in get_plugin_manager()._middleware["llm_request"]
                       if getattr(callback, "__name__", "") == "narration_request")
        runtime.registry.bind(TurnState("ux-fixture", "key", None, None, 1, [None], [], None, None, progress=TaskProgress()))
        for provider in ("openai-codex", "xai-oauth"):
            request = {"model": "fixture", "instructions": "fixture", "input": [{"role": "user", "content": "fixture"}],
                       "tools": [{"type": "function", "name": "read_file", "parameters": {
                           "type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}}]}
            result = apply_llm_request_middleware(request, session_id="ux-fixture", platform="telegram", provider=provider)
            assert result.changed, provider
            wire = _bypass_sdk_request_transform(_preflight_codex_api_kwargs(result.payload)) if provider == "openai-codex" else result.payload
            tool = wire.get("tools", wire.get("extra_body", {}).get("tools"))[0]
            assert "_hermes_progress" in tool["parameters"]["required"], provider
            assert "Telegram delivery requirement" in wire["instructions"]
            assert ("brief Chinese" if language == "zh" else "brief English") in wire["instructions"]
        runtime.uninstall()
        print(json.dumps({"native_discovery": True, "registered_tools": names, "middleware_providers": ["openai-codex", "xai-oauth"]}))


if __name__ == "__main__":
    main()
