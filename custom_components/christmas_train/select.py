"""Manual synchronization of assumed train states."""

from homeassistant.components.select import SelectEntity
from homeassistant.exceptions import HomeAssistantError

from .const import STATE_OPTIONS
from .entity import TrainEntity

NAMES = {
    "movement": "Sync assumed movement",
    "light": "Sync assumed light",
    "steam": "Sync assumed steam",
}


async def async_setup_entry(hass, entry, async_add_entities):
    """Create selects for recording manually observed states."""
    async_add_entities(TrainStateSelect(entry.runtime_data, key) for key in STATE_OPTIONS)


class TrainStateSelect(TrainEntity, SelectEntity):
    """Record an assumption without sending a remote command."""

    _attr_assumed_state = True
    _attr_icon = "mdi:clipboard-edit-outline"

    def __init__(self, controller, key: str) -> None:
        super().__init__(controller, f"sync_{key}")
        self.key = key
        self._attr_name = NAMES[key]
        self._attr_options = list(STATE_OPTIONS[key])

    @property
    def current_option(self):
        """Return the last assumed state."""
        return self.controller.states[self.key]

    async def async_select_option(self, option: str) -> None:
        """Synchronize with a manually observed state."""
        if option not in STATE_OPTIONS[self.key]:
            raise HomeAssistantError(f"Invalid {self.key} state: {option}")
        await self.controller.async_sync(self.key, option)
