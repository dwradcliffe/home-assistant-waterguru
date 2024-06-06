"""Diagnostics support for WaterGuru."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from . import WaterGuruDataCoordinatorType
from .const import DOMAIN

TO_REDACT = {
    "serial_number",
    "url",
    "waterBodyId",
    "userId",
    "addr1",
    "city",
    "state",
    "zip",
    "imageUrl",
    "ipAddr",
    "wifiId"
}

async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator: WaterGuruDataCoordinatorType = hass.data[DOMAIN][entry.entry_id]

    return async_redact_data([device.diagnostics for device in coordinator.data.values()], TO_REDACT)
