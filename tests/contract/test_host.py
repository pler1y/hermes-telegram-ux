"""Real PluginManager discovery, hook workers, rollback, and SDK contract checks.

Run in a scratch HERMES_HOME with PYTHONPATH pointing at the target Hermes checkout.
The Telegram transport is synthetic; these are not live Telegram acceptance results.
"""
import asyncio
from contextvars import Context
import inspect
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
        (home / "config.yaml").write_text(yaml.safe_dump({"plugins": {"enabled": [NAME]}}))
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
        self.assertEqual(result, [])
        await asyncio.sleep(0.03)

    async def test_real_loader_and_bounded_hook_context_propagation(self):
        self.assertTrue(set(HOOKS) <= VALID_HOOKS)
        manifest = yaml.safe_load((ROOT / "plugin.yaml").read_text())
        self.assertEqual(set(manifest["provides_hooks"]), set(HOOKS))
        self.assertTrue(all(self.manager.has_hook(name) for name in HOOKS))
        await self.begin()
        self.assertEqual(len(self.sent), 1)
        self.assertEqual(self.sent[0]["metadata"], {"thread_id": "42"})
        # Real host callback execution, not a fake ctx: final reply is transformed through dispatch.
        self.assertEqual(self.invoke("pre_tool_call", session_id="s", turn_id="t", tool_call_id="c", tool_name="read_file", args={}), [])
        self.invoke("post_tool_call", session_id="s", turn_id="t", tool_call_id="c", tool_name="read_file", status="ok", result="confidential")
        result = self.invoke("transform_llm_output", session_id="s", turn_id="t", platform="telegram", response_text="Final answer")
        self.assertEqual(len(result), 1)
        self.assertTrue(result[0].startswith("Final answer"))
        self.assertNotIn("confidential", result[0])
        self.invoke("on_session_end", session_id="s", turn_id="t", completed=True)
        await asyncio.sleep(0.04)
        self.assertIn("已结束", self.edits[-1]["content"])
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
        finally:
            disabled.unload()

    async def test_public_transport_signatures(self):
        from gateway.platforms.base import BasePlatformAdapter
        inspect.signature(BasePlatformAdapter.send).bind(None, chat_id="1", content="hello", reply_to="2", metadata={"thread_id": "3"})
        inspect.signature(BasePlatformAdapter.edit_message).bind(None, chat_id="1", message_id="2", content="hello")
        inspect.signature(BasePlatformAdapter.delete_message).bind(None, chat_id="1", message_id="2")


if __name__ == "__main__":
    unittest.main()
