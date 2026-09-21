"""Switch platform for WaterGuru."""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import WaterGuruDataCoordinatorType
from .const import DOMAIN
from .waterguru import WaterGuruDevice


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the WaterGuru cassette override switch."""
    coordinator: WaterGuruDataCoordinatorType = hass.data[DOMAIN][config_entry.entry_id]

    async_add_entities(
        WaterGuruOverrideSwitch(coordinator, device)
        for device in coordinator.data.values()
    )


class WaterGuruOverrideSwitch(SwitchEntity):
    """Temporary safety-lockout override for early cassette replacement."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG
    _attr_entity_registry_enabled_default = False

    def __init__(
        self, coordinator: WaterGuruDataCoordinatorType, device: WaterGuruDevice
    ) -> None:
        """Initialize the switch."""
        self.coordinator = coordinator
        self.device = device
        self._attr_unique_id = f"{device.device_id}_cassette_override"
        self._attr_translation_key = "cassette_override"
        self._attr_is_on = False

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return DeviceInfo(identifiers={(DOMAIN, self.device.device_id)})

    async def async_turn_on(self, **kwargs) -> None:
        """Turn on the override."""
        self._attr_is_on = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        """Turn off the override."""
        self._attr_is_on = False
        self.async_write_ha_state()
