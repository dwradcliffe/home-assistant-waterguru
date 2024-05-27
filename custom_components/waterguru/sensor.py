"""Support for WaterGuru sensors."""

from __future__ import annotations

import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    SIGNAL_STRENGTH_DECIBELS,
    EntityCategory,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import WaterGuruDataCoordinatorType
from .const import DOMAIN, WaterGuruEntityAttributes
from .waterguru import WaterGuruDevice

STANDARD_SENSORS: dict[str, SensorEntityDescription] = {
    "temp": SensorEntityDescription(
        key="temp",
        name="Water Temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.FAHRENHEIT,
    ),
    "battery": SensorEntityDescription(
        key="battery",
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    "cassette": SensorEntityDescription(
        key="cassette",
        translation_key="cassette",
        name="Cassette Remaining",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    "cassette_days_remaining": SensorEntityDescription(
        key="cassette_days_remaining",
        translation_key="cassette",
        name="Cassette Days Remaining",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        suggested_display_precision=0,
    ),
    "rssi": SensorEntityDescription(
        key="rssi",
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    "ip": SensorEntityDescription(
        key="ip",
        translation_key="ip",
        name="IP Address",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
}

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the WaterGuru sensor."""

    coordinator: WaterGuruDataCoordinatorType = hass.data[DOMAIN][entry.entry_id]

    entities = [
        WaterGuruSensor(
            coordinator,
            waterguru_device,
            STANDARD_SENSORS[sensor_types],
            STANDARD_SENSORS[sensor_types].key,
        )
        for waterguru_device in coordinator.data.values()
        for sensor_types in waterguru_device.sensors
        if sensor_types in STANDARD_SENSORS
    ]

    for waterguru_device in coordinator.data.values():
        for measurement in waterguru_device.measurements.values():
            entities.append(
                WaterGuruSensor(
                    coordinator,
                    waterguru_device,
                    SensorEntityDescription(
                        key=measurement["type"],
                        translation_key=measurement["type"],
                        name=measurement["title"],
                        device_class=(SensorDeviceClass.PH if measurement["type"] == "PH" else None),
                        state_class=SensorStateClass.MEASUREMENT,
                        native_unit_of_measurement=measurement["cfg"].get("unit"),
                        suggested_display_precision=measurement["cfg"].get("decPlaces"),
                    ),
                    measurement["type"],
                )
            )

            entities.append(
                WaterGuruAlertSensor(
                    coordinator,
                    waterguru_device,
                    SensorEntityDescription(
                        key=measurement["type"] + "_alert",
                        translation_key="alert",
                        name=measurement["title"] + " Alert",
                        entity_category=EntityCategory.DIAGNOSTIC,
                    ),
                    measurement["type"]
                )
            )

    entities.append(
        WaterGuruOverallStatusSensor(
            coordinator,
            waterguru_device,
            SensorEntityDescription(
                key="status",
                translation_key="alert",
                name="Status",
                entity_category=EntityCategory.DIAGNOSTIC,
            ),
            None,
        )
    )

    async_add_entities(entities)


class WaterGuruSensor(
    CoordinatorEntity[WaterGuruDataCoordinatorType], SensorEntity
):
    """Representation of a WaterGuru Sensor device."""

    _attr_has_entity_name = True

    _unrecorded_attributes = frozenset(
        {
            WaterGuruEntityAttributes.LAST_MEASUREMENT,
            WaterGuruEntityAttributes.DESC,
            WaterGuruEntityAttributes.STATUS_COLOR,
            WaterGuruEntityAttributes.ADVICE,
        }
    )

    def __init__(
        self,
        coordinator: WaterGuruDataCoordinatorType,
        waterguru_device: WaterGuruDevice,
        entity_description: SensorEntityDescription,
        waterguru_key: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)

        self._waterguru_key = waterguru_key

        self.entity_description = entity_description

        self._attr_unique_id = f"{waterguru_device.device_id}_{entity_description.key}"
        self._id = waterguru_device.device_id
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, waterguru_device.device_id)},
            name=waterguru_device.name,
            manufacturer="WaterGuru",
            model=waterguru_device.product_name,
            suggested_area="Pool",
            serial_number=waterguru_device.serial_number,
            sw_version=waterguru_device.firmware_version,
        )

    @property
    def extra_state_attributes(self) -> dict[str, str] | None:
        """Return entity specific state attributes."""

        if self._waterguru_key in STANDARD_SENSORS:
            return None

        m = self.coordinator.data[self._id].measurements[self._waterguru_key]

        a = {
            WaterGuruEntityAttributes.LAST_MEASUREMENT: m.get("measureTime"),
            WaterGuruEntityAttributes.DESC: m.get("cfg").get("desc"),
            WaterGuruEntityAttributes.STATUS_COLOR: m.get("status"),
        }

        if m.get("alerts") is not None and len(m.get("alerts")) > 0 and m.get("alerts")[0].get("advice") is not None:
            a[WaterGuruEntityAttributes.ADVICE] = m.get("alerts")[0].get("advice").get("action").get("summary")

        return a

    @property
    def native_value(self) -> StateType:
        """Return the value reported by the sensor."""

        if self._waterguru_key in STANDARD_SENSORS:
            return self.coordinator.data[self._id].sensors[self._waterguru_key]

        m = self.coordinator.data[self._id].measurements[self._waterguru_key]

        if m.get("floatValue") is None:
            return m.get("intValue")

        return m.get("floatValue")

class WaterGuruOverallStatusSensor(WaterGuruSensor):
    """Representation of a WaterGuru Sensor that shows the overall pool status."""

    @property
    def extra_state_attributes(self) -> dict[str, str] | None:
        """Return entity specific state attributes."""

        return None

    @property
    def native_value(self) -> StateType:
        """Return the value reported by the sensor."""

        return self.coordinator.data[self._id].status

class WaterGuruAlertSensor(WaterGuruSensor):
    """Representation of a WaterGuru Sensor that shows the alert status."""

    @property
    def native_value(self) -> StateType:
        """Return the value reported by the sensor."""

        m = self.coordinator.data[self._id].measurements[self._waterguru_key]
        if m.get("status") == "GREEN":
            return "Ok"
        return m.get("firstAlertCondition")
