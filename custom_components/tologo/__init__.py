"""The Tologo integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import TologoApiClient, TologoApiError, TologoAuthError
from .const import CONF_ACCESS_TOKEN, CONF_REFRESH_TOKEN, DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.BUTTON]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Tologo from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    def token_update_callback(new_tokens: dict[str, str]) -> None:
        """Update config entry with new tokens."""
        _LOGGER.debug("Tokens refreshed, saving to config entry")
        data = dict(entry.data)
        data.update(new_tokens)
        hass.config_entries.async_update_entry(entry, data=data)

    session = async_get_clientsession(hass)

    client = TologoApiClient(
        hass,
        session,
        access_token=entry.data.get(CONF_ACCESS_TOKEN),
        refresh_token=entry.data.get(CONF_REFRESH_TOKEN),
        token_update_callback=token_update_callback,
    )

    try:
        # Fetch doors data to cache it for the entities
        # If the access token is stale on boot, client will automatically refresh it.
        # If refresh fails, it throws TologoAuthError.
        doors_response = await client.get_doors()
    except TologoAuthError as err:
        raise ConfigEntryAuthFailed from err
    except TologoApiError as err:
        raise ConfigEntryNotReady from err

    # Ensure doors are handled gracefully if response schema differs
    # The API is expected to return a structure with doors.
    # From instructions: The /user/doors endpoint contains all required nested location metadata.
    doors_data = doors_response if isinstance(doors_response, list) else doors_response.get("doors", [])

    hass.data[DOMAIN][entry.entry_id] = {
        "client": client,
        "doors": doors_data,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    # As explicitly requested: Do NOT remove hass.data cleanup here so that a manual "Reload" 
    # discovers new doors/locations without issues.
    # If we removed hass.data[DOMAIN][entry.entry_id], it would prevent reloading natively without a service.
    
    return unload_ok
