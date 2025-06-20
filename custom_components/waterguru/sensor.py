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
from homeassistant.util import dt as dt_util

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
        icon="mdi:cassette",
    ),
    "cassette_days_remaining": SensorEntityDescription(
        key="cassette_days_remaining",
        translation_key="cassette",
        name="Cassette Days Remaining",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        suggested_display_precision=0,
        icon="mdi:cassette",
    ),
    "rssi": SensorEntityDescription(
        key="rssi",
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
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

    entities: list[WaterGuruBaseSensor] = [
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
                        device_class=(
                            SensorDeviceClass.PH if measurement["type"] == "PH" else None
                        ),
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
                        name=measurement["title"] + " Alert",
                        entity_category=EntityCategory.DIAGNOSTIC,
                    ),
                    measurement["type"],
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
            )
        )
        entities.append(
            WaterGuruLastMeasurementSensor(
                coordinator,
                waterguru_device,
                SensorEntityDescription(
                    key="last_measurement",
                    name="Last Measurement",
                    entity_category=EntityCategory.DIAGNOSTIC,
                    device_class=SensorDeviceClass.TIMESTAMP,
                ),
            )
        )

    async_add_entities(entities)


class WaterGuruBaseSensor(
    CoordinatorEntity[WaterGuruDataCoordinatorType], SensorEntity
):
    """Base class for a WaterGuru sensor."""

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
        waterguru_key: str | None = None,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)

        self._waterguru_key = waterguru_key

        self.entity_description = entity_description

        if entity_description.icon is None and entity_description.device_class is None:
            if waterguru_key == "SKIMMER_FLOW":
                self._attr_icon = "mdi:waves"
            else:
                self._attr_icon = "mdi:test-tube"

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

class WaterGuruSensor(WaterGuruBaseSensor):
    """Representation of a WaterGuru sensor."""

    @property
    def extra_state_attributes(self) -> dict[str, str] | None:
        """Return entity specific state attributes."""

        if self._waterguru_key in STANDARD_SENSORS:
            return None

        # Check if the measurement exists before accessing it
        if (self._id not in self.coordinator.data or
            self._waterguru_key not in self.coordinator.data[self._id].measurements):
            return None

        m = self.coordinator.data[self._id].measurements[self._waterguru_key]

        a = {
            WaterGuruEntityAttributes.LAST_MEASUREMENT: m.get("measureTime"),
            WaterGuruEntityAttributes.DESC: m.get("cfg", {}).get("desc"),
            WaterGuruEntityAttributes.STATUS_COLOR: m.get("status"),
        }

        alerts = m.get("alerts")
        if alerts:
            advice = alerts[0].get("advice", {}).get("action", {}).get("summary")
            if advice is not None:
                a[WaterGuruEntityAttributes.ADVICE] = advice

        return a

    @property
    def native_value(self) -> StateType:
        """Return the value reported by the sensor."""

        if self._waterguru_key in STANDARD_SENSORS:
            # Check if the sensor data exists
            if (self._id not in self.coordinator.data or
                self._waterguru_key not in self.coordinator.data[self._id].sensors):
                return None
            return self.coordinator.data[self._id].sensors[self._waterguru_key]

        # Check if the measurement exists before accessing it
        if (self._id not in self.coordinator.data or
            self._waterguru_key not in self.coordinator.data[self._id].measurements):
            return None

        m = self.coordinator.data[self._id].measurements[self._waterguru_key]

        if m.get("floatValue") is None:
            return m.get("intValue")

        return m.get("floatValue")

class WaterGuruOverallStatusSensor(WaterGuruBaseSensor):
    """Representation of a WaterGuru Sensor that shows the overall pool status."""

    @property
    def native_value(self) -> StateType:
        """Return the value reported by the sensor."""

        # Check if the device data exists
        if self._id not in self.coordinator.data:
            return None

        return self.coordinator.data[self._id].status

    @property
    def icon(self) -> str:
        """Return the icon to use in the frontend."""

        # Check if the device data exists
        if self._id not in self.coordinator.data:
            return "mdi:alert-outline"

        if self.coordinator.data[self._id].status == "GREEN":
            return "mdi:alert-circle-check-outline"
        return "mdi:alert-outline"

class WaterGuruAlertSensor(WaterGuruSensor):
    """Representation of a WaterGuru Sensor that shows the alert status."""

    @property
    def native_value(self) -> StateType:
        """Return the value reported by the sensor."""

        # Check if the measurement exists before accessing it
        if (self._id not in self.coordinator.data or
            self._waterguru_key not in self.coordinator.data[self._id].measurements):
            return None

        m = self.coordinator.data[self._id].measurements[self._waterguru_key]
        if m.get("status") == "GREEN":
            return "Ok"
        return m.get("firstAlertCondition")

    @property
    def icon(self) -> str:
        """Return the icon to use in the frontend."""

        # Check if the measurement exists before accessing it
        if (self._id not in self.coordinator.data or
            self._waterguru_key not in self.coordinator.data[self._id].measurements):
            return "mdi:alert-outline"

        m = self.coordinator.data[self._id].measurements[self._waterguru_key]
        if m.get("status") == "GREEN":
            return "mdi:alert-circle-check-outline"
        return "mdi:alert-outline"

class WaterGuruLastMeasurementSensor(WaterGuruBaseSensor):
    """Representation of a WaterGuru Sensor that shows the last time the water was tested."""

    @property
    def native_value(self) -> StateType:
        """Return the value reported by the sensor."""

        # Check if the device data exists
        if self._id not in self.coordinator.data:
            return None

        strTs = self.coordinator.data[self._id].last_measurement_time
        if strTs is None:
            return None
        return dt_util.parse_datetime(strTs)
