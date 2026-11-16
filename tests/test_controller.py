"""Focused controller tests using small Home Assistant test doubles."""

import asyncio
import importlib
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import AsyncMock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def install_home_assistant_doubles():
    """Provide only the Home Assistant APIs used by the controller."""
    names = (
        "homeassistant",
        "homeassistant.config_entries",
        "homeassistant.const",
        "homeassistant.core",
        "homeassistant.exceptions",
        "homeassistant.helpers",
        "homeassistant.helpers.dispatcher",
        "homeassistant.helpers.storage",
    )
    for name in names:
        module = types.ModuleType(name)
        module.__path__ = []
        sys.modules[name] = module
    sys.modules["homeassistant.config_entries"].ConfigEntry = type("ConfigEntry", (), {})
    const = sys.modules["homeassistant.const"]
    const.STATE_UNAVAILABLE = "unavailable"
    const.STATE_UNKNOWN = "unknown"
    const.Platform = types.SimpleNamespace(BUTTON="button", SELECT="select", SENSOR="sensor")
    sys.modules["homeassistant.core"].HomeAssistant = type("HomeAssistant", (), {})
    sys.modules["homeassistant.exceptions"].HomeAssistantError = type(
        "HomeAssistantError", (Exception,), {}
    )
    sys.modules["homeassistant.helpers.dispatcher"].async_dispatcher_send = (
        lambda hass, signal: hass.notifications.append(signal)
    )
    sys.modules["homeassistant.helpers.storage"].Store = MemoryStore


class MemoryStore:
    """Storage that survives controller recreation."""

    def __init__(self, hass, version, key):
        self.data = hass.storage

    async def async_load(self):
        return None if self.data is None else dict(self.data)

    async def async_save(self, data):
        if self.data is None:
            raise AssertionError("Tests must initialize storage")
        self.data.clear()
        self.data.update(data)


install_home_assistant_doubles()
controller_module = importlib.import_module("custom_components.christmas_train.controller")
TrainController = controller_module.TrainController
HomeAssistantError = sys.modules["homeassistant.exceptions"].HomeAssistantError


class ControllerTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.hass = types.SimpleNamespace(
            storage={},
            states=types.SimpleNamespace(
                get=lambda entity_id: types.SimpleNamespace(state="on")
            ),
            services=types.SimpleNamespace(async_call=AsyncMock()),
            notifications=[],
        )
        self.entry = types.SimpleNamespace(
            entry_id="test_entry",
            data={"remote_entity": "remote.x2_hub_remote", "remote_device": "2"},
        )
        self.train = TrainController(self.hass, self.entry)

    async def test_command_payloads_and_state(self):
        expected = {
            "forward": ("1", 3, "forward"),
            "stop": ("2", 3, "stopped"),
            "reverse": ("3", 3, "reverse"),
            "steam": ("4", 1, None),
            "forward_fast": ("5", 3, "forward_fast"),
            "light": ("6", 1, None),
            "noise": ("7", 1, None),
        }
        for name, (command, repeats, movement) in expected.items():
            with self.subTest(name=name):
                await self.train.async_send(name)
                self.hass.services.async_call.assert_awaited_with(
                    "remote",
                    "send_command",
                    {
                        "entity_id": "remote.x2_hub_remote",
                        "device": "2",
                        "command": command,
                        "num_repeats": repeats,
                        "delay_secs": 1,
                        "hold_secs": 0,
                    },
                    blocking=True,
                )
                if movement is not None:
                    self.assertEqual(self.train.states["movement"], movement)

    async def test_toggle_unknown_and_manual_sync(self):
        await self.train.async_send("light")
        self.assertEqual(self.train.states["light"], "unknown")
        self.hass.services.async_call.reset_mock()
        await self.train.async_sync("light", "off")
        self.hass.services.async_call.assert_not_called()
        await self.train.async_send("light")
        self.assertEqual(self.train.states["light"], "on")
        await self.train.async_send("light")
        self.assertEqual(self.train.states["light"], "off")
        await self.train.async_sync("steam", "on")
        await self.train.async_send("steam")
        self.assertEqual(self.train.states["steam"], "off")
        with self.assertRaises(HomeAssistantError):
            await self.train.async_sync("light", "forward")

    async def test_restoration_and_invalid_data(self):
        await self.train.async_sync("movement", "reverse")
        await self.train.async_sync("steam", "on")
        restored = TrainController(self.hass, self.entry)
        await restored.async_load()
        self.assertEqual(restored.states, {"movement": "reverse", "light": "unknown", "steam": "on"})
        self.hass.storage["steam"] = "invalid"
        with self.assertRaises(HomeAssistantError):
            await restored.async_load()

    async def test_failed_or_cancelled_send_remains_unknown_after_restore(self):
        await self.train.async_sync("movement", "forward")
        self.hass.services.async_call.side_effect = RuntimeError("send failed")
        with self.assertRaisesRegex(RuntimeError, "send failed"):
            await self.train.async_send("stop")
        restored = TrainController(self.hass, self.entry)
        await restored.async_load()
        self.assertEqual(restored.states["movement"], "unknown")

        await self.train.async_sync("light", "on")
        self.hass.services.async_call.side_effect = asyncio.CancelledError
        with self.assertRaises(asyncio.CancelledError):
            await self.train.async_send("light")
        await restored.async_load()
        self.assertEqual(restored.states["light"], "unknown")

    async def test_unavailable_remote_does_not_change_state(self):
        await self.train.async_sync("movement", "forward")
        self.hass.states.get = lambda entity_id: types.SimpleNamespace(state="unavailable")
        with self.assertRaises(HomeAssistantError):
            await self.train.async_send("stop")
        self.assertEqual(self.train.states["movement"], "forward")
        self.hass.services.async_call.assert_not_called()

    async def test_commands_and_manual_sync_are_serialized(self):
        entered = asyncio.Event()
        release = asyncio.Event()
        calls = []

        async def send(domain, service, data, blocking):
            calls.append(data["command"])
            if data["command"] == "1":
                entered.set()
                await release.wait()

        self.hass.services.async_call.side_effect = send
        first = asyncio.create_task(self.train.async_send("forward"))
        await entered.wait()
        second = asyncio.create_task(self.train.async_send("stop"))
        sync = asyncio.create_task(self.train.async_sync("movement", "reverse"))
        await asyncio.sleep(0)
        self.assertEqual(calls, ["1"])
        self.assertEqual(self.train.states["movement"], "unknown")
        release.set()
        await asyncio.gather(first, second, sync)
        self.assertEqual(calls, ["1", "2"])
        self.assertEqual(self.train.states["movement"], "reverse")


if __name__ == "__main__":
    unittest.main()
