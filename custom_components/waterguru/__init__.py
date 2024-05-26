"""Support for WaterGuru."""

from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN
from .waterguru import WaterGuru, WaterGuruApiError, WaterGuruDevice

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]
INTERVAL = timedelta(minutes=30) # water temperature is updated every 30 minutes

WaterGuruDataCoordinatorType = DataUpdateCoordinator[dict[str, WaterGuruDevice]]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up WaterGuru from a config entry."""

    hass.data.setdefault(DOMAIN, {})

    waterguru = WaterGuru(
                    username=entry.data[CONF_USERNAME],
                    password=entry.data[CONF_PASSWORD],
                    session=async_get_clientsession(hass),
                )

    async def _update_method() -> dict[str, WaterGuru]:
        """Get the latest data from WaterGuru."""
        try:
            return await hass.async_add_executor_job(waterguru.get)
        except WaterGuruApiError as err:
            raise UpdateFailed(f"Unable to fetch data: {err}") from err

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=DOMAIN,
        update_method=_update_method,
        update_interval=INTERVAL,
    )
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
