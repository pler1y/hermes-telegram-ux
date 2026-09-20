#!/usr/bin/env python3
"""Probe real Hermes tool discovery and per-turn guidance without a model or Telegram.

Run with a Hermes environment's Python and --core pointing at its checkout.
Only a temporary HERMES_HOME is populated; neither core nor user configuration
is changed. Scripted host calls establish wiring, not model compliance.
"""
import argparse
import asyncio
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = "hermes-telegram-ux-catalog"
CASES = (
    ("release_research", "Grok 4.6 什么时候发布？"),
    ("code_inspection", "检查这个项目为什么状态消息没有被删除"),
    ("data_analysis", "分析数据文件，计算关键指标并核对异常记录"),
    ("multi_source", "调查最近一周某个项目发生了什么，对比官方公告与其他来源"),
    ("simple_control", "1 加 1 等于几？"),
)


async def probe(core):
    import yaml

    sys.path[:0] = [str(ROOT), str(core)]
    # Import only after the isolated home is selected; Hermes scopes plugin
    # registry entries and configuration by the active profile/home.
    from catalog.adapter import HOOKS
    from catalog.experience import SCHEMA, TOOL, turn_guidance
    from agent.turn_context import compose_user_api_content
    from hermes_cli.plugins import get_plugin_manager
    from model_tools import get_tool_definitions, handle_function_call
    from tools.registry import registry

    manager = get_plugin_manager()
    manager.discover_and_load()
    sent, edits, deleted = [], [], []

    async def send(**kwargs):
        sent.append(kwargs)
        return SimpleNamespace(success=True, message_id=str(len(sent)))

    async def edit_message(**kwargs):
        edits.append(kwargs)
        return SimpleNamespace(success=True)

    async def delete_message(**kwargs):
        deleted.append(kwargs)
        return True

    try:
        manifest = yaml.safe_load((ROOT / "plugin.yaml").read_text())
        assert len(HOOKS) == 16 and all(manager.has_hook(hook) for hook in HOOKS)
        assert manifest["provides_tools"] == [TOOL]
        assert manifest["provides_middleware"] == []
        assert not manager.has_hook("pre_command")
        assert not manager.has_hook("transform_llm_output")

        definitions = registry.get_definitions({TOOL}, quiet=True)
        assert definitions == [{"type": "function", "function": SCHEMA}]
        entry = registry.get_entry(TOOL, scope=manager.scope_key)
        assert entry is not None and entry.toolset == "telegram_ux"
        model_definitions = get_tool_definitions(enabled_toolsets=["telegram_ux"], quiet_mode=True)
        model_tool_names = [item["function"]["name"] for item in model_definitions]
        assert "tool_search" in model_tool_names and "tool_call" in model_tool_names
        assert TOOL not in model_tool_names  # Hermes' default auto defers plugin tools.
        search = json.loads(handle_function_call("tool_search", {"queries": [TOOL]},
                                                enabled_toolsets=["telegram_ux"]))
        assert TOOL in search["tools"]
        describe = json.loads(handle_function_call("tool_describe", {"names": [TOOL]},
                                                  enabled_toolsets=["telegram_ux"]))
        assert describe["tools"][TOOL]["parameters"] == SCHEMA["parameters"]

        factories = manager.get_platform_handler_factories("telegram")
        assert len(factories) == 1
        factories[0][0](None, SimpleNamespace(send=send, edit_message=edit_message,
                                            delete_message=delete_message))
        cases = []
        for index, (name, user_message) in enumerate(CASES, 1):
            incoming = SimpleNamespace(
                source=SimpleNamespace(platform="telegram", chat_id="10", user_id="10", thread_id=None),
                message_id=str(index), internal=False,
            )
            manager.invoke_hook("pre_gateway_dispatch", event=incoming)
            result = await asyncio.to_thread(
                manager.invoke_hook, "pre_llm_call", session_id="probe", turn_id=str(index),
                platform="telegram", sender_id="10", parent_session_id="", user_message=user_message,
            )
            assert result == [turn_guidance()]
            # Exercise the checked host's API-message composer without an
            # AIAgent, provider request, or change to any host implementation.
            wire_content = compose_user_api_content(user_message, "", result[0]["context"])
            assert wire_content == user_message + "\n\n" + turn_guidance()["context"]
            # pre_llm_call is per turn; ordinary provider iterations do not
            # request another copy of progress guidance.
            again = manager.invoke_hook("pre_llm_call", session_id="probe", turn_id=str(index),
                                        platform="telegram", sender_id="10", user_message=user_message)
            assert again == []
            cases.append({"case": name, "guidance_received": True, "api_content_composed": True, "duplicate_guidance": False,
                          "model_invoked": False})
            await asyncio.sleep(.02)
            manager.invoke_hook("on_session_end", session_id="probe", turn_id=str(index), completed=True)
            await asyncio.sleep(.03)

        no_route = manager.invoke_hook("pre_llm_call", session_id="unrouted", turn_id="1",
                                       platform="telegram", sender_id="20", user_message="检查数据")
        other_platform = manager.invoke_hook("pre_llm_call", session_id="cli", turn_id="1",
                                             platform="cli", sender_id="10", user_message="检查数据")
        assert no_route == [] and other_platform == []
        manager.invoke_hook("pre_gateway_dispatch", event=SimpleNamespace(
            source=SimpleNamespace(platform="telegram", chat_id="10", user_id="10", thread_id=None),
            message_id="6", internal=False,
        ))
        await asyncio.to_thread(manager.invoke_hook, "pre_llm_call", session_id="bridge", turn_id="1",
                                platform="telegram", sender_id="10", user_message="对比资料中的日期")
        await asyncio.sleep(.02)
        bridged = json.loads(await asyncio.to_thread(
            handle_function_call, "tool_call", {"calls": [{"name": TOOL, "arguments": {"action": "比较不同来源中的日期"}}]},
            session_id="bridge", turn_id="1", tool_call_id="bridge-note", enabled_toolsets=["telegram_ux"],
        ))
        assert bridged["ok"]
        await asyncio.sleep(1.6)
        assert any("比较不同来源中的日期" in edit["content"] for edit in edits)
        manager.invoke_hook("on_session_end", session_id="bridge", turn_id="1", completed=True)
        await asyncio.sleep(.03)
        feedback = json.loads(registry.dispatch(
            TOOL, {"action": "比较不同来源中的日期"}, scope=manager.scope_key,
        ))
        assert feedback["ok"] and "does not confirm display" in feedback["message"]

        manager.unload()
        assert registry.get_entry(TOOL, scope=manager.scope_key) is None
        return {
            "core_revision": subprocess.check_output(["git", "-C", str(core), "rev-parse", "HEAD"], text=True).strip(),
            "runtime": sys.version.split()[0],
            "host_probe": "passed",
            "tool_schema_discovered": True,
            "default_model_tool_names": model_tool_names,
            "deferred_tool_search_found_progress": True,
            "deferred_tool_describe_preserved_schema": True,
            "real_tool_call_bridge_reached_progress_observer": True,
            "public_hooks": len(HOOKS),
            "declared_tools": len(manifest["provides_tools"]),
            "declared_middleware": len(manifest["provides_middleware"]),
            "command_hook": False,
            "unsupported_routes_receive_guidance": False,
            "schema_description": definitions[0]["function"]["description"],
            "turn_guidance": turn_guidance()["context"],
            "scripted_tool_feedback": feedback,
            "cases": cases,
            "synthetic_transport": {"sent": len(sent), "deleted": len(deleted), "bridge_milestone_displayed": True},
            "unload_removed_tool": True,
            "model_evaluation": "not_run",
            "model_evaluation_limitation": "This deterministic host probe does not measure model invocation frequency, milestone quality, or tool choice.",
        }
    finally:
        manager.unload()
        await asyncio.sleep(.03)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--core", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    core = args.core.resolve()
    if not (core / "hermes_cli/plugins.py").is_file():
        parser.error("--core must name a Hermes checkout with the public plugin API")
    prior = {key: os.environ.get(key) for key in ("HERMES_HOME", "HERMES_BUNDLED_PLUGINS")}
    try:
        with tempfile.TemporaryDirectory(prefix="tgux-host-probe-") as scratch:
            home = Path(scratch)
            plugin = home / "plugins" / PLUGIN
            plugin.mkdir(parents=True)
            for name in ("__init__.py", "plugin.yaml"):
                shutil.copy2(ROOT / name, plugin / name)
            shutil.copytree(ROOT / "catalog", plugin / "catalog", ignore=shutil.ignore_patterns("__pycache__"))
            (home / "bundled").mkdir()
            (home / "config.yaml").write_text(json.dumps({
                "plugins": {"enabled": [PLUGIN], "entries": {PLUGIN: {"settings": {"cleanup_delay": 0}}}},
            }))
            os.environ["HERMES_HOME"] = str(home)
            os.environ["HERMES_BUNDLED_PLUGINS"] = str(home / "bundled")
            report = asyncio.run(probe(core))
        serialized = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(serialized)
            print(json.dumps({key: report[key] for key in ("host_probe", "core_revision", "runtime", "model_evaluation")}, ensure_ascii=False))
        else:
            print(serialized, end="")
    finally:
        for key, value in prior.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


if __name__ == "__main__":
    main()
