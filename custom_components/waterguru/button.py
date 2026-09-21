"""Button platform for WaterGuru."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
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
    """Set up the WaterGuru reset button."""
    coordinator: WaterGuruDataCoordinatorType = hass.data[DOMAIN][config_entry.entry_id]

    async_add_entities(
        WaterGuruResetButton(coordinator, device)
        for device in coordinator.data.values()
    )


class WaterGuruResetButton(ButtonEntity):
    """Button that resets the cassette life after a physical replacement."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self, coordinator: WaterGuruDataCoordinatorType, device: WaterGuruDevice
    ) -> None:
        """Initialize the button."""
        self.coordinator = coordinator
        self.device = device
        self._attr_unique_id = f"{device.device_id}_replace_cassette"
        self._attr_translation_key = "replace_cassette"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return DeviceInfo(identifiers={(DOMAIN, self.device.device_id)})

    async def async_press(self) -> None:
        """Reset the cassette life on the WaterGuru pod."""
        device_data = self.coordinator.data.get(self.device.device_id)
        if not device_data:
            raise HomeAssistantError("Device data not available.")

        pct_remaining = device_data.sensors.get("cassette")
        days_remaining = device_data.sensors.get("cassette_days_remaining")

        registry = er.async_get(self.hass)
        switch_unique_id = f"{self.device.device_id}_cassette_override"
        override_switch_id = registry.async_get_entity_id("switch", DOMAIN, switch_unique_id)

        override_state = self.hass.states.get(override_switch_id) if override_switch_id else None
        is_overridden = override_state is not None and override_state.state == STATE_ON

        if pct_remaining is not None and pct_remaining > 0 and not is_overridden:
            if days_remaining is not None:
                error_msg = f"Cannot replace: {days_remaining} days remaining."
            else:
                error_msg = f"Cannot replace: {pct_remaining}% remaining."

            error_msg += " Enable the 'Temporarily Allow Early Cassette Replacement' switch to bypass."
            raise HomeAssistantError(error_msg)

        # device_data.serial_number is the pod's podId, which is what the Lambda
        # expects here -- distinct from device.device_id (waterBodyId), which is
        # used for entity unique_ids and repair issue_ids.
        api = self.coordinator.api
        await self.hass.async_add_executor_job(api.reset_cassette, device_data.serial_number)

        # Only clear the override after a successful reset, so a failed attempt
        # can be retried without needing to re-enable the switch.
        if is_overridden and override_switch_id:
            await self.hass.services.async_call(
                "switch",
                "turn_off",
                {"entity_id": override_switch_id},
                blocking=False,
            )

        await self.coordinator.async_request_refresh()
