"""Sensor platform for getAir integration."""
from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    UnitOfTemperature,
    UnitOfTime,
    UnitOfPressure,
    UnitOfPressure,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


@dataclass
class GetAirSensorDescription(SensorEntityDescription):
    service: str = "zone"
    api_key: str = ""
    transform: callable = None


SENSOR_DESCRIPTIONS: list[GetAirSensorDescription] = [
    GetAirSensorDescription(
        key="temperature",
        name="Indoor Temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        service="zone",
        api_key="temperature",
    ),
    GetAirSensorDescription(
        key="humidity",
        name="Indoor Humidity",
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        service="zone",
        api_key="humidity",
    ),
    GetAirSensorDescription(
        key="temperature_outdoors",
        name="Outdoor Temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        service="zone",
        api_key="temp-outdoors",
    ),
    GetAirSensorDescription(
        key="humidity_outdoors",
        name="Outdoor Humidity",
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        service="zone",
        api_key="hmdty-outdoors",
    ),



    GetAirSensorDescription(
        key="fan_speed",
        name="Fan Speed",
        state_class=SensorStateClass.MEASUREMENT,
        service="zone",
        api_key="speed",
        icon="mdi:fan",
    ),
    GetAirSensorDescription(
        key="runtime",
        name="Runtime",
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfTime.HOURS,
        service="zone",
        api_key="runtime",
        icon="mdi:clock-outline",
    ),    GetAirSensorDescription(
        key="mode",
        name="Ventilation Mode",
        service="zone",
        api_key="mode",
        icon="mdi:air-conditioner",
    ),
    GetAirSensorDescription(
        key="air_quality",
        name="Indoor Air Quality",
        state_class=SensorStateClass.MEASUREMENT,
        service="system",
        api_key="indoor-airquality",
        icon="mdi:air-filter",
    ),
    GetAirSensorDescription(
        key="air_pressure",
        name="Air Pressure",
        device_class=SensorDeviceClass.ATMOSPHERIC_PRESSURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPressure.HPA,
        service="system",
        api_key="air-pressure",
    ),
    GetAirSensorDescription(
        key="firmware",
        name="Firmware Version",
        service="system",
        api_key="fw-app-version-str",
        icon="mdi:chip",
        entity_registry_enabled_default=False,
    ),
]


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]

    entities = []
    for device_id in coordinator.data:
        device_info = coordinator.data[device_id]["device"]
        for desc in SENSOR_DESCRIPTIONS:
            entities.append(GetAirSensor(coordinator, device_id, device_info, desc))

    async_add_entities(entities)


class GetAirSensor(CoordinatorEntity, SensorEntity):
    """Sensor entity for a getAir property."""

    entity_description: GetAirSensorDescription

    def __init__(self, coordinator, device_id, device_info, description: GetAirSensorDescription):
        super().__init__(coordinator)
        self.entity_description = description
        self._device_id = device_id
        self._attr_unique_id = f"{device_id}_{description.key}"
        device_name = device_info.get("name", f"getAir {device_id}")
        self._attr_name = f"{device_name} {description.name}"

    @property
    def native_value(self):
        service_data = self.coordinator.data[self._device_id].get(
            self.entity_description.service, {}
        )
        val = service_data.get(self.entity_description.api_key)
        if val is None:
            return None
        if self.entity_description.transform:
            return self.entity_description.transform(float(val))
        # Round floats to 1 decimal to avoid precision noise like 2.09999990463257
        if isinstance(val, float):
            return round(val, 1)
        return val
