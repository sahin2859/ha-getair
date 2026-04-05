"""Climate platform for getAir integration."""
from __future__ import annotations

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MODES

# Map speed values to fan mode names
FAN_SPEEDS = {
    "Off":    0.0,
    "1":      1.0,
    "2":      2.0,
    "3":      3.0,
    "4":      4.0,
}
# Allow half steps too
FAN_SPEED_NAMES = {
    0.0: "Off",
    0.5: "0.5",
    1.0: "1",
    1.5: "1.5",
    2.0: "2",
    2.5: "2.5",
    3.0: "3",
    3.5: "3.5",
    4.0: "4",
}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]
    api = data["api"]

    entities = []
    for device_id in coordinator.data:
        device_info = coordinator.data[device_id]["device"]
        entities.append(GetAirClimate(coordinator, api, device_id, device_info))

    async_add_entities(entities)


class GetAirClimate(CoordinatorEntity, ClimateEntity):
    """Climate entity representing a getAir zone."""

    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_hvac_modes = [HVACMode.FAN_ONLY, HVACMode.AUTO]
    _attr_hvac_mode = HVACMode.FAN_ONLY
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.PRESET_MODE
        | ClimateEntityFeature.FAN_MODE
    )
    _attr_preset_modes = list(MODES.values())
    _attr_fan_modes = list(FAN_SPEED_NAMES.values())
    _attr_min_temp = 10.0
    _attr_max_temp = 30.0
    _attr_target_temperature_step = 0.5

    def __init__(self, coordinator, api, device_id, device_info):
        super().__init__(coordinator)
        self._api = api
        self._device_id = device_id
        self._attr_unique_id = f"{device_id}_climate"
        self._attr_name = device_info.get("name", f"getAir {device_id}")

    @property
    def _zone(self) -> dict:
        return self.coordinator.data[self._device_id]["zone"]

    @property
    def current_temperature(self) -> float | None:
        temp = self._zone.get("temperature")
        return float(temp) if temp is not None else None

    @property
    def target_temperature(self) -> float | None:
        temp = self._zone.get("target-temp")
        return float(temp) if temp is not None else None

    @property
    def current_humidity(self) -> float | None:
        hum = self._zone.get("humidity")
        return float(hum) if hum is not None else None

    @property
    def preset_mode(self) -> str | None:
        mode_key = self._zone.get("mode")
        return MODES.get(mode_key)

    @property
    def hvac_mode(self) -> HVACMode:
        mode_key = self._zone.get("mode")
        return HVACMode.AUTO if mode_key == "auto" else HVACMode.FAN_ONLY

    @property
    def fan_mode(self) -> str | None:
        speed = self._zone.get("speed")
        if speed is None:
            return None
        return FAN_SPEED_NAMES.get(float(speed), str(speed))

    async def async_set_temperature(self, **kwargs) -> None:
        temp = kwargs.get("temperature")
        if temp is not None:
            await self._api.set_target_temp(self._device_id, float(temp))
            await self.coordinator.async_request_refresh()

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        mode_key = next((k for k, v in MODES.items() if v == preset_mode), None)
        if mode_key:
            await self._api.set_mode(self._device_id, mode_key)
            await self.coordinator.async_request_refresh()

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        if hvac_mode == HVACMode.AUTO:
            await self._api.set_mode(self._device_id, "auto")
        else:
            await self._api.set_mode(self._device_id, "ventilate")
        await self.coordinator.async_request_refresh()

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        speed = next((v for k, v in FAN_SPEEDS.items() if k == fan_mode), None)
        if speed is None:
            try:
                raw = float(fan_mode)
                # Snap to nearest 0.5
                speed = round(raw * 2) / 2
            except ValueError:
                return
        await self._api.set_speed(self._device_id, speed)
        await self.coordinator.async_request_refresh()
