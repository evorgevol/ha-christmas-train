"""Optional end-to-end check, run separately with Home Assistant installed."""

import asyncio
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory

from homeassistant import bootstrap, config_entries, loader
from homeassistant.components.remote import DATA_COMPONENT, RemoteEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry, entity_registry
from homeassistant.setup import async_setup_component


class FakeRemote(RemoteEntity):
    """A remote that records commands rather than transmitting them."""

    _attr_name = "X2 Hub Remote"
    _attr_unique_id = "fake_x2"
    _attr_is_on = True

    def __init__(self):
        self.calls = []

    async def async_send_command(self, command, **kwargs):
        self.calls.append((command, kwargs))


async def check_integration(config_dir: Path) -> None:
    source = Path(__file__).resolve().parents[1] / "custom_components" / "christmas_train"
    destination = config_dir / "custom_components" / "christmas_train"
    shutil.copytree(source, destination, ignore=shutil.ignore_patterns("__pycache__"))

    hass = HomeAssistant(str(config_dir))
    hass.config.skip_pip = True
    try:
        loader.async_setup(hass)
        hass.config_entries = config_entries.ConfigEntries(hass, {})
        await loader.async_get_custom_components(hass)
        await bootstrap.async_load_base_functionality(hass)
        assert await async_setup_component(hass, "remote", {})

        remote = FakeRemote()
        await hass.data[DATA_COMPONENT].async_add_entities([remote])
        assert remote.entity_id == "remote.x2_hub_remote"

        flow = await hass.config_entries.flow.async_init(
            "christmas_train", context={"source": "user"}
        )
        assert flow["type"] == "form", flow
        result = await hass.config_entries.flow.async_configure(
            flow["flow_id"], {"remote_entity": remote.entity_id, "remote_device": "2"}
        )
        assert result["type"] == "create_entry", result
        await hass.async_block_till_done()
        entry = result["result"]
        assert entry.state is config_entries.ConfigEntryState.LOADED, entry.state

        entities = entity_registry.async_entries_for_config_entry(
            entity_registry.async_get(hass), entry.entry_id
        )
        devices = device_registry.async_entries_for_config_entry(
            device_registry.async_get(hass), entry.entry_id
        )
        assert len(devices) == 1
        assert len(entities) == 12
        assert hass.states.get("sensor.christmas_train").state == "unknown"

        toggle = {"entity_id": "button.christmas_train_toggle_forward_stop"}
        await hass.services.async_call("button", "press", toggle, blocking=True)
        assert hass.states.get("sensor.christmas_train").state == "forward"
        assert remote.calls[-1][0] == ["1"]

        await hass.services.async_call("button", "press", toggle, blocking=True)
        assert hass.states.get("sensor.christmas_train").state == "stopped"
        assert remote.calls[-1][0] == ["2"]

        await hass.services.async_call("button", "press", toggle, blocking=True)
        assert hass.states.get("sensor.christmas_train").state == "forward"
        assert remote.calls[-1][0] == ["1"]

        await hass.services.async_call(
            "button",
            "press",
            {"entity_id": "button.christmas_train_forward"},
            blocking=True,
        )
        assert hass.states.get("sensor.christmas_train").state == "forward"
        assert remote.calls[-1][0] == ["1"]
        assert remote.calls[-1][1]["num_repeats"] == 3
        assert remote.calls[-1][1]["device"] == "2"

        await hass.services.async_call(
            "select",
            "select_option",
            {"entity_id": "select.christmas_train_sync_assumed_light", "option": "off"},
            blocking=True,
        )
        assert len(remote.calls) == 1
        await hass.services.async_call(
            "button",
            "press",
            {"entity_id": "button.christmas_train_toggle_light"},
            blocking=True,
        )
        assert hass.states.get("select.christmas_train_sync_assumed_light").state == "on"
        assert remote.calls[-1][0] == ["6"]
        assert remote.calls[-1][1]["num_repeats"] == 1

        assert await hass.config_entries.async_reload(entry.entry_id)
        await hass.async_block_till_done()
        assert hass.states.get("sensor.christmas_train").state == "forward"
        assert hass.states.get("select.christmas_train_sync_assumed_light").state == "on"
    finally:
        await hass.async_stop()


def main() -> None:
    with TemporaryDirectory(prefix="christmas-train-check-") as config_dir:
        asyncio.run(check_integration(Path(config_dir)))
    print("Home Assistant device, commands, and reload check passed")


if __name__ == "__main__":
    main()
