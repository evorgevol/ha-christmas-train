"""Buttons for the Christmas train remote commands."""

from homeassistant.components.button import ButtonEntity

from .const import COMMANDS
from .entity import TrainEntity

NAMES = {
    "forward": "Forward",
    "stop": "Stop",
    "reverse": "Reverse",
    "steam": "Toggle steam",
    "forward_fast": "Forward fast",
    "light": "Toggle light",
    "noise": "Cycle noise",
}


async def async_setup_entry(hass, entry, async_add_entities):
    """Create one button for each remote command."""
    async_add_entities(
        [
            *(TrainButton(entry.runtime_data, key) for key in COMMANDS),
            TrainMovementToggleButton(entry.runtime_data),
        ]
    )


class TrainButton(TrainEntity, ButtonEntity):
    """Send one remote command."""

    _attr_icon = "mdi:train"

    def __init__(self, controller, command: str) -> None:
        super().__init__(controller, f"button_{command}")
        self.command = command
        self._attr_name = NAMES[command]

    async def async_press(self) -> None:
        """Send the command."""
        await self.controller.async_send(self.command)


class TrainMovementToggleButton(TrainEntity, ButtonEntity):
    """Toggle between forward and stopped movement."""

    _attr_icon = "mdi:train"

    def __init__(self, controller) -> None:
        super().__init__(controller, "toggle_forward_stop")
        self._attr_name = "Toggle forward/stop"

    async def async_press(self) -> None:
        """Toggle between forward and stopped movement."""
        await self.controller.async_toggle_movement()
