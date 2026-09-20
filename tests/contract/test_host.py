"""Real PluginManager discovery, hook workers, rollback, and SDK contract checks.

Run in a scratch HERMES_HOME with PYTHONPATH pointing at the target Hermes checkout.
The Telegram transport is synthetic; these are not live Telegram acceptance results.
"""
import asyncio
from contextvars import Context
import inspect
import json
import os
from pathlib import Path
import shutil
import tempfile
from types import SimpleNamespace
import unittest

import yaml
from hermes_cli.plugins import PluginManager, VALID_HOOKS
from catalog.adapter import HOOKS

ROOT = Path(__file__).resolve().parents[2]
NAME = "hermes-telegram-ux-catalog"


class HostTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.scratch = tempfile.TemporaryDirectory(prefix="catalog-host-")
        home = Path(self.scratch.name)
        self.home = home
        plugin = home / "plugins" / NAME
        plugin.mkdir(parents=True)
        for name in ("__init__.py", "plugin.yaml"):
            shutil.copy2(ROOT / name, plugin / name)
        shutil.copytree(ROOT / "catalog", plugin / "catalog", ignore=shutil.ignore_patterns("__pycache__"))
        (home / "bundled").mkdir()
        self.prior = {key: os.environ.get(key) for key in ("HERMES_HOME", "HERMES_BUNDLED_PLUGINS")}
        os.environ["HERMES_HOME"] = str(home)
        os.environ["HERMES_BUNDLED_PLUGINS"] = str(home / "bundled")
        # Legacy final_summary must not bring answer rewriting back. A short
        # cleanup window keeps the actual host lifecycle test deterministic.
        (home / "config.yaml").write_text(yaml.safe_dump({"plugins": {"enabled": [NAME], "entries": {NAME: {"settings": {"final_summary": True, "progress": False, "emoji": False, "cleanup_delay": 0.005}}}}}))
        self.manager = PluginManager()
        self.manager.discover_and_load()
        self.sent, self.edits, self.deleted = [], [], []

        async def send(**kwargs):
            self.sent.append(kwargs)
            return SimpleNamespace(success=True, message_id="77")

        async def edit_message(**kwargs):
            self.edits.append(kwargs)
            return SimpleNamespace(success=True)

        async def delete_message(**kwargs):
            self.deleted.append(kwargs)
            return True

        self.telegram = SimpleNamespace(send=send, edit_message=edit_message, delete_message=delete_message)
        factories = self.manager.get_platform_handler_factories("telegram")
        self.assertEqual(len(factories), 1)
        factories[0][0](None, self.telegram)

    async def asyncTearDown(self):
        self.manager.unload()
        await asyncio.sleep(0.03)
        for key, value in self.prior.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        self.scratch.cleanup()

    def invoke(self, name, **kwargs):
        return self.manager.invoke_hook(name, **kwargs)

    async def begin(self):
        source = SimpleNamespace(platform="telegram", chat_id="10", user_id="10", thread_id="42")
        incoming = SimpleNamespace(source=source, message_id="3", internal=False)
        self.assertEqual(self.invoke("pre_gateway_dispatch", event=incoming), [])
        self.assertFalse(self.sent)
        result = await asyncio.to_thread(self.invoke, "pre_llm_call", session_id="s", turn_id="t", platform="telegram", sender_id="10", parent_session_id="")
        self.assertEqual(len(result), 1)
        self.assertIn("telegram_ux_update", result[0]["context"])
        await asyncio.sleep(0.03)

    async def test_real_loader_and_bounded_hook_context_propagation(self):
        self.assertTrue(set(HOOKS) <= VALID_HOOKS)
        manifest = yaml.safe_load((ROOT / "plugin.yaml").read_text())
        self.assertEqual(set(manifest["provides_hooks"]), set(HOOKS))
        self.assertEqual(len(HOOKS), 16)
        self.assertNotIn("pre_command", HOOKS)
        self.assertNotIn("tgux", self.manager._plugin_commands)
        self.assertEqual(manifest["config_schema"]["language"]["default"], "auto")
        self.assertFalse({"progress", "emoji"} & set(manifest["config_schema"]))
        self.assertTrue(all(self.manager.has_hook(name) for name in HOOKS))
        self.assertFalse(self.manager.has_hook("transform_llm_output"))
        self.assertTrue(self.manager.has_hook("post_llm_call"))
        await self.begin()
        self.assertEqual(len(self.sent), 1)
        self.assertEqual(self.sent[0]["metadata"], {"thread_id": "42"})
        # Real host callback execution, not a fake ctx: public observations must
        # never register a transformer or resend the native final answer.
        self.assertEqual(self.invoke("pre_tool_call", session_id="s", turn_id="t", tool_call_id="c", tool_name="read_file", args={}), [])
        self.invoke("post_tool_call", session_id="s", turn_id="t", tool_call_id="c", tool_name="read_file", status="ok", result="confidential")
        result = self.invoke("transform_llm_output", session_id="s", turn_id="t", platform="telegram", response_text="Final answer")
        self.assertEqual(result, [])
        self.assertEqual(self.invoke("post_llm_call", session_id="s", turn_id="t", platform="telegram", assistant_response="Final answer"), [])
        self.invoke("on_session_end", session_id="s", turn_id="t", completed=True)
        await asyncio.sleep(0.04)
        self.assertIn("正在整理最终回答", self.edits[-1]["content"])
        self.assertEqual(self.deleted, [{"chat_id": "10", "message_id": "77"}])
        self.assertEqual(len(self.sent), 1)
        self.assertFalse(any("reply_markup" in item for item in self.sent + self.edits))
        self.assertNotIn("confidential", repr(self.sent + self.edits))
        self.assertNotIn("Final answer", repr(self.sent + self.edits))
        self.assertEqual(self.invoke("transform_llm_output", session_id="s", turn_id="t", platform="telegram", response_text="Later"), [])

    async def test_unload_removes_hooks_and_cancels_owned_messages(self):
        await self.begin()
        self.assertTrue(self.manager.unload(NAME))
        await asyncio.sleep(0.05)
        self.assertFalse(any(self.manager.has_hook(name) for name in HOOKS))
        self.assertEqual(len(self.deleted), 1)
        self.assertEqual(self.invoke("transform_llm_output", session_id="s", turn_id="t", platform="telegram", response_text="Native reply"), [])

    async def test_config_disabled_discovery_has_no_behavior(self):
        self.manager.unload()
        (self.home / "config.yaml").write_text(yaml.safe_dump({"plugins": {"enabled": []}}))
        disabled = PluginManager()
        disabled.discover_and_load()
        try:
            self.assertFalse(any(disabled.has_hook(name) for name in HOOKS))
            self.assertEqual(disabled.get_platform_handler_factories("telegram"), [])
            self.assertNotIn("tgux", disabled._plugin_commands)
            from tools.registry import registry
            from catalog.experience import TOOL
            self.assertIsNone(registry.get_entry(TOOL, scope=disabled.scope_key))
            self.assertEqual(disabled.invoke_hook("pre_llm_call", platform="telegram", session_id="off", turn_id="off"), [])
            self.assertEqual(disabled.invoke_hook("transform_llm_output", platform="telegram", response_text="MEDIA:/tmp/native.csv"), [])
        finally:
            disabled.unload()

    async def test_public_transport_signatures(self):
        from gateway.platforms.base import BasePlatformAdapter
        inspect.signature(BasePlatformAdapter.send).bind(None, chat_id="1", content="hello", reply_to="2", metadata={"thread_id": "3"})
        inspect.signature(BasePlatformAdapter.edit_message).bind(None, chat_id="1", message_id="2", content="hello", finalize=True)
        inspect.signature(BasePlatformAdapter.delete_message).bind(None, chat_id="1", message_id="2")

    async def test_registered_progress_tool_works_and_is_removed_on_unload(self):
        from tools.registry import registry
        from catalog.experience import TOOL
        result = registry.dispatch(TOOL, {"goal": "Public progress", "action": "Checking current results"}, scope=self.manager.scope_key)
        parsed = json.loads(result)
        self.assertTrue(parsed["ok"])
        self.assertEqual(parsed["note"]["goal"], "Public progress")
        self.manager.unload(NAME)
        self.assertIsNone(registry.get_entry(TOOL, scope=self.manager.scope_key))

    async def test_native_handlers_and_commands_are_untouched(self):
        approval = object()
        handlers, messages = [approval], []

        async def send_message(**kwargs):
            messages.append(kwargs)
            return SimpleNamespace(message_id=77)

        native = SimpleNamespace(add_handler=handlers.append, remove_handler=handlers.remove,
                                 bot=SimpleNamespace(send_message=send_message))
        factory = self.manager.get_platform_handler_factories("telegram")[0][0]
        factory(native, self.telegram)
        for command in ("new", "stop", "usage", "tgux"):
            incoming = SimpleNamespace(internal=False, text="/" + command, message_id="3",
                source=SimpleNamespace(platform="telegram", chat_id="10", user_id="10", thread_id="42"))
            self.invoke("pre_gateway_dispatch", event=incoming)
            self.assertEqual(self.invoke("pre_command", surface="gateway", command=command,
                                         platform="telegram", session_key="opaque"), [])
        await asyncio.sleep(.03)
        self.assertNotIn("tgux", self.manager._plugin_commands)
        self.assertFalse(messages or self.sent)
        self.assertEqual(handlers, [approval])
        self.manager.unload(NAME)
        await asyncio.sleep(.03)
        self.assertEqual(handlers, [approval])

    async def test_global_reenable_restores_public_observation_only(self):
        self.manager.unload()
        (self.home / "config.yaml").write_text(yaml.safe_dump({"plugins": {"enabled": []}}))
        disabled = PluginManager()
        disabled.discover_and_load()
        self.assertFalse(disabled.has_hook("pre_llm_call"))
        disabled.unload()
        (self.home / "config.yaml").write_text(yaml.safe_dump({"plugins": {"enabled": [NAME]}}))
        enabled = PluginManager()
        enabled.discover_and_load()
        try:
            self.assertTrue(enabled.has_hook("pre_llm_call"))
            self.assertEqual(len(enabled.get_platform_handler_factories("telegram")), 1)
            self.assertFalse(enabled.has_hook("transform_llm_output"))
            self.assertFalse(enabled.has_hook("pre_command"))
            self.assertNotIn("tgux", enabled._plugin_commands)
        finally:
            enabled.unload()


if __name__ == "__main__":
    unittest.main()
