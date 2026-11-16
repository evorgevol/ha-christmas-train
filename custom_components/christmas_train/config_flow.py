"""Configuration flow for the Christmas Train."""

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers.selector import EntitySelector, EntitySelectorConfig

from .const import CONF_REMOTE_DEVICE, CONF_REMOTE_ENTITY, DOMAIN


class ChristmasTrainConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Select an existing remote and its train device ID."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Create an entry for a remote device."""
        errors = {}
        if user_input is not None:
            remote = user_input[CONF_REMOTE_ENTITY]
            device = user_input[CONF_REMOTE_DEVICE].strip()
            if self.hass.states.get(remote) is None:
                errors[CONF_REMOTE_ENTITY] = "remote_not_found"
            elif not device:
                errors[CONF_REMOTE_DEVICE] = "invalid_device"
            else:
                await self.async_set_unique_id(f"{remote}:{device}")
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title="Christmas Train",
                    data={CONF_REMOTE_ENTITY: remote, CONF_REMOTE_DEVICE: device},
                )

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_REMOTE_ENTITY, default="remote.x2_hub_remote"
                ): EntitySelector(EntitySelectorConfig(domain="remote")),
                vol.Required(CONF_REMOTE_DEVICE, default="2"): str,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)
