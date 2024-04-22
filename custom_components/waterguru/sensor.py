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
    CONCENTRATION_PARTS_PER_MILLION,
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
from .const import DOMAIN
from .waterguru import WaterGuruDevice

SENSORS: dict[str, SensorEntityDescription] = {
    "SKIMMER_FLOW": SensorEntityDescription(
        key="SKIMMER_FLOW",
        name="Skimmer Flow",
        state_class = SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="gpm",
    ),
    "FREE_CL": SensorEntityDescription(
        key="FREE_CL",
        name="Free Chlorine",
        state_class = SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=CONCENTRATION_PARTS_PER_MILLION,
        icon="mdi:flask",
    ),
    "PH": SensorEntityDescription(
        key="PH",
        device_class=SensorDeviceClass.PH,
        state_class = SensorStateClass.MEASUREMENT,
    ),
    "TA": SensorEntityDescription(
        key="TA",
        name="Total Alkalinity",
        state_class = SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=CONCENTRATION_PARTS_PER_MILLION,
    ),
    "CH": SensorEntityDescription(
        key="CH",
        name="Calcium Hardness",
        state_class = SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=CONCENTRATION_PARTS_PER_MILLION,
    ),
    "CYA": SensorEntityDescription(
        key="CYA",
        name="Cyanuric Acid",
        state_class = SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=CONCENTRATION_PARTS_PER_MILLION,
    ),
    "SALT": SensorEntityDescription(
        key="SALT",
        name="Salt",
        state_class = SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=CONCENTRATION_PARTS_PER_MILLION,
    ),
    "PHOS": SensorEntityDescription(
        key="PHOS",
        name="Phosphates",
        state_class = SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=CONCENTRATION_PARTS_PER_MILLION,
    ),
    "SI": SensorEntityDescription(
        key="SI",
        name="Saturation Index",
        state_class = SensorStateClass.MEASUREMENT,
    ),
    "temp": SensorEntityDescription(
        key="temp",
        name="Water Temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class = SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.FAHRENHEIT,
    ),
    "battery": SensorEntityDescription(
        key="battery",
        device_class=SensorDeviceClass.BATTERY,
        state_class = SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    "rssi": SensorEntityDescription(
        key="rssi",
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS,
        state_class = SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    "ip": SensorEntityDescription(
        key="ip",
        name="IP Address",
        icon="mdi:ip-network",
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
            SENSORS[sensor_types],
        )
        for waterguru_device in coordinator.data.values()
        for sensor_types in waterguru_device.sensor_types
        if sensor_types in SENSORS
    ]
    async_add_entities(entities)


class WaterGuruSensor(
    CoordinatorEntity[WaterGuruDataCoordinatorType], SensorEntity
):
    """Representation of a WaterGuru Sensor device."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: WaterGuruDataCoordinatorType,
        waterguru_device: WaterGuruDevice,
        entity_description: SensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)

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
    def native_value(self) -> StateType:
        """Return the value reported by the sensor."""
        return self.coordinator.data[self._id].sensors[self.entity_description.key]  # type: ignore[no-any-return]
