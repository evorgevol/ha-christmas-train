"""Serialize remote operations and persist their assumed state."""

import asyncio

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.storage import Store

from .const import (
    COMMANDS,
    CONF_REMOTE_DEVICE,
    CONF_REMOTE_ENTITY,
    DOMAIN,
    STATE_OPTIONS,
    UNKNOWN,
)


class TrainController:
    """Manage a train without pretending the remote provides feedback."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry_id = entry.entry_id
        self.remote = entry.data[CONF_REMOTE_ENTITY]
        self.device = entry.data[CONF_REMOTE_DEVICE]
        self.signal = f"{DOMAIN}_{entry.entry_id}_updated"
        self.store = Store(hass, 1, f"{DOMAIN}.{entry.entry_id}")
        self.states = dict.fromkeys(STATE_OPTIONS, UNKNOWN)
        self.lock = asyncio.Lock()

    async def async_load(self) -> None:
        """Restore assumptions, or begin unknown on the first setup."""
        saved = await self.store.async_load()
        if saved is None:
            return
        if not isinstance(saved, dict) or any(
            saved.get(key) not in options for key, options in STATE_OPTIONS.items()
        ):
            raise HomeAssistantError("Stored Christmas train state is invalid")
        self.states = {key: saved[key] for key in STATE_OPTIONS}

    async def _async_set_state(self, key: str, value: str) -> None:
        self.states[key] = value
        try:
            await self.store.async_save(dict(self.states))
        except (Exception, asyncio.CancelledError):
            self.states[key] = UNKNOWN
            raise
        finally:
            async_dispatcher_send(self.hass, self.signal)

    async def async_sync(self, key: str, value: str) -> None:
        """Record a manually observed state without sending a command."""
        if key not in STATE_OPTIONS or value not in STATE_OPTIONS[key]:
            raise HomeAssistantError(f"Invalid train state: {key}={value}")
        async with self.lock:
            await self._async_set_state(key, value)

    async def async_send(self, command_name: str) -> None:
        """Send a mapped command, leaving ambiguous outcomes unknown."""
        async with self.lock:
            await self._async_send_locked(command_name)

    async def async_toggle_movement(self) -> None:
        """Toggle between forward and stopped movement."""
        async with self.lock:
            command = (
                "stop" if self.states["movement"] == "forward" else "forward"
            )
            await self._async_send_locked(command)

    async def _async_send_locked(self, command_name: str) -> None:
        command, key, result, repeats = COMMANDS[command_name]
        remote_state = self.hass.states.get(self.remote)
        if remote_state is None or remote_state.state in (
            STATE_UNAVAILABLE,
            STATE_UNKNOWN,
        ):
            raise HomeAssistantError(f"Remote {self.remote} is unavailable")

        old_state = self.states[key] if key else None
        if key:
            # Persist uncertainty before sending, including across interruptions.
            await self._async_set_state(key, UNKNOWN)

        await self.hass.services.async_call(
            "remote",
            "send_command",
            {
                "entity_id": self.remote,
                "device": self.device,
                "command": command,
                "num_repeats": repeats,
                "delay_secs": 1,
                "hold_secs": 0,
            },
            blocking=True,
        )
        if key:
            if result is None:
                result = {"on": "off", "off": "on"}.get(old_state, UNKNOWN)
            await self._async_set_state(key, result)
