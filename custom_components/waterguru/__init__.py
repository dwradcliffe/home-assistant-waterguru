"""Support for WaterGuru."""

from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, CASSETTE_ISSUE_PREFIX
from .waterguru import WaterGuru, WaterGuruApiError, WaterGuruDevice

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BUTTON,
    Platform.SWITCH,
]
INTERVAL = timedelta(minutes=30) # water temperature is updated every 30 minutes

# device IDs we've synced cassette repairs for, keyed by config entry id
_cassette_known_devices: dict[str, set[str]] = {}

WaterGuruDataCoordinatorType = DataUpdateCoordinator[dict[str, WaterGuruDevice]]


def _async_check_cassette_repairs(
    hass: HomeAssistant,
    devices: dict[str, WaterGuruDevice],
    known_device_ids: set[str],
) -> None:
    """Create or clear cassette-empty repair issues for each device."""
    current_device_ids = set(devices)

    for device_id in known_device_ids - current_device_ids:
        ir.async_delete_issue(hass, DOMAIN, f"{CASSETTE_ISSUE_PREFIX}{device_id}")

    known_device_ids.clear()
    known_device_ids.update(current_device_ids)

    for device_id, device in devices.items():
        issue_id = f"{CASSETTE_ISSUE_PREFIX}{device_id}"

        # Evaluate percentage instead of conditional days tex
        # WaterGuru reports this as going negative once the cassette is overdue,
        # so treat anything at or below 0 as empty rather than requiring an exact match.
        pct_remaining = device.sensors.get("cassette")

        if pct_remaining is not None and pct_remaining <= 0:
            ir.async_create_issue(
                hass,
                DOMAIN,
                issue_id,
                is_fixable=True,
                severity=ir.IssueSeverity.WARNING,
                translation_key="cassette_empty",
                translation_placeholders={"name": device.name},
                data={"device_id": device_id, "name": device.name},
            )
        else:
            ir.async_delete_issue(hass, DOMAIN, issue_id)

def _async_clear_cassette_repairs(
    hass: HomeAssistant, device_ids: set[str]
) -> None:
    """Delete cassette-empty repair issues for the given devices."""
    for device_id in device_ids:
        ir.async_delete_issue(hass, DOMAIN, f"{CASSETTE_ISSUE_PREFIX}{device_id}")


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

    # Expose the API client to other platforms
    coordinator.api = waterguru

    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = coordinator
    known_device_ids = _cassette_known_devices.setdefault(entry.entry_id, set())

    @callback
    def _async_update_cassette_repairs() -> None:
        """Sync cassette repair issues with the latest coordinator data."""
        _async_check_cassette_repairs(
            hass, coordinator.data or {}, known_device_ids
        )

    entry.async_on_unload(coordinator.async_add_listener(_async_update_cassette_repairs))
    _async_update_cassette_repairs()

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
        known_device_ids = _cassette_known_devices.pop(entry.entry_id, set())
        _async_clear_cassette_repairs(hass, known_device_ids)

    return unload_ok
