"""Assumed movement state of the Christmas train."""

from homeassistant.components.sensor import SensorEntity

from .const import UNKNOWN, state_label
from .entity import TrainEntity


async def async_setup_entry(hass, entry, async_add_entities):
    """Create the train's movement sensor."""
    async_add_entities([TrainMovementSensor(entry.runtime_data)])


class TrainMovementSensor(TrainEntity, SensorEntity):
    """Show the last assumed movement."""

    _attr_name = None
    _attr_icon = "mdi:train"
    _attr_assumed_state = True

    def __init__(self, controller) -> None:
        super().__init__(controller, "movement")

    @property
    def native_value(self):
        """Return unknown until a movement has been recorded."""
        state = self.controller.states["movement"]
        return None if state == UNKNOWN else state_label(state)
