"""Button platform for Tologo integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import TologoApiClient, TologoApiError, TologoRateLimitError
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Tologo button platform."""
    data = hass.data[DOMAIN][entry.entry_id]
    client: TologoApiClient = data["client"]
    doors: list[dict[str, Any]] = data.get("doors", [])

    entities = []
    for door in doors:
        entities.append(TologoDoorButton(client, door))

    async_add_entities(entities)


class TologoDoorButton(ButtonEntity):
    """Representation of a Tologo Door button."""

    _attr_has_entity_name = True
    _attr_name = None

    def __init__(self, client: TologoApiClient, door: dict[str, Any]) -> None:
        """Initialize the button."""
        self._client = client
        self._door = door

        door_id = door.get("id")
        self._attr_unique_id = f"tologo_door_{door_id}"

        location = door.get("location", {})
        location_id = location.get("id")
        location_name = location.get("name", "Unknown Location")

        if location_id:
            self._attr_device_info = DeviceInfo(
                identifiers={(DOMAIN, str(location_id))},
                name=location_name,
                manufacturer="Tologo",
            )
        else:
            _LOGGER.warning("Door %s is missing location metadata", door_id)

    async def async_press(self) -> None:
        """Press the button to open the door.

        The cooldown check runs synchronously for instant feedback on
        rapid presses.  The actual API call is dispatched as a background
        task so the UI returns immediately, giving the user visual
        confirmation that the button was pressed.
        """
        door_id = self._door.get("id")
        if not door_id:
            raise HomeAssistantError("Door ID is missing")

        # Cooldown check is local and instant — block here so rapid
        # presses are still rejected immediately with a clear message.
        try:
            self._client.check_door_cooldown(door_id)
        except TologoRateLimitError as err:
            raise HomeAssistantError(
                f"Please wait before pressing again: {err}"
            ) from err

        # Dispatch the actual API call in the background so the button
        # press animation completes instantly in the HA UI.
        self.hass.async_create_task(
            self._perform_open_door(door_id),
            f"tologo_open_door_{door_id}",
        )

    async def _perform_open_door(self, door_id: str | int) -> None:
        """Perform the door-open API call in the background."""
        door_name = self._door.get("name", f"Door {door_id}")
        try:
            response = await self._client.open_door(door_id)
        except TologoApiError as err:
            _LOGGER.error("Failed to open %s: %s", door_name, err)
            self.hass.components.persistent_notification.async_create(
                f"Failed to open {door_name}: {err}",
                title="Tologo",
                notification_id=f"tologo_door_error_{door_id}",
            )
            return

        device_status = response.get("device_status")
        if not device_status:
            device_message = response.get(
                "device_message", "Unknown error opening door"
            )
            _LOGGER.error("Door %s error: %s", door_name, device_message)
            self.hass.components.persistent_notification.async_create(
                f"{door_name}: {device_message}",
                title="Tologo",
                notification_id=f"tologo_door_error_{door_id}",
            )
