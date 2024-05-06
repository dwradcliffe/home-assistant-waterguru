"""Config flow for WaterGuru."""
import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN
from .waterguru import WaterGuru, WaterGuruApiError

_LOGGER = logging.getLogger(__name__)

WATERGURU_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
    }
)

class WaterguruConfigFlow(ConfigFlow, domain=DOMAIN):
    """Config Waterguru config entry."""

    VERSION = 1

    DOMAIN = DOMAIN

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Get configuration from the user."""
        errors = {}
        if user_input:
            if user_input[CONF_USERNAME] is not None:
                user_input[CONF_USERNAME] = user_input[CONF_USERNAME].lower()

            self._async_abort_entries_match({CONF_USERNAME: user_input[CONF_USERNAME]})

            try:
                waterguru = WaterGuru(
                    username=user_input[CONF_USERNAME],
                    password=user_input[CONF_PASSWORD],
                    session=async_get_clientsession(self.hass),
                )
                data = await self.hass.async_add_executor_job(waterguru.get)
            except WaterGuruApiError:
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(user_input[CONF_USERNAME])
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=f"WaterGuru: {user_input[CONF_USERNAME]}",
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=WATERGURU_SCHEMA,
            errors=errors,
        )
