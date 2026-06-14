"""Config flow for Tologo integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import TologoApiClient, TologoApiError, TologoAuthError
from .const import CONF_ACCESS_TOKEN, CONF_REFRESH_TOKEN, DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_EMAIL): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect."""
    session = async_get_clientsession(hass)
    client = TologoApiClient(hass, session)

    # login sets client.access_token and client.refresh_token if successful
    await client.login(data[CONF_EMAIL], data[CONF_PASSWORD])

    # Return info that you want to store in the config entry.
    return {
        "title": data[CONF_EMAIL],
        CONF_EMAIL: data[CONF_EMAIL],
        CONF_ACCESS_TOKEN: client.access_token,
        CONF_REFRESH_TOKEN: client.refresh_token,
    }


class TologoConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Tologo."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_EMAIL])
            self._abort_if_unique_id_configured()

            try:
                info = await validate_input(self.hass, user_input)
            except TologoAuthError:
                errors["base"] = "invalid_auth"
            except TologoApiError:
                errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title=info["title"],
                    data={
                        CONF_EMAIL: info[CONF_EMAIL],
                        CONF_ACCESS_TOKEN: info[CONF_ACCESS_TOKEN],
                        CONF_REFRESH_TOKEN: info[CONF_REFRESH_TOKEN],
                    },
                )

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )
