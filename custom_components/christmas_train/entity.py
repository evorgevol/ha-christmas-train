"""Shared device information for train entities."""

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import Entity

from .const import DOMAIN


class TrainEntity(Entity):
    """An entity belonging to the configured train."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, controller, key: str) -> None:
        self.controller = controller
        self._attr_unique_id = f"{controller.entry_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, controller.entry_id)},
            name="Christmas Train",
        )

    async def async_added_to_hass(self) -> None:
        """Subscribe to assumption changes."""
        await super().async_added_to_hass()
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, self.controller.signal, self.async_write_ha_state
            )
        )
