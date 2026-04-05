"""Fan platform for getAir integration - combined speed + mode control."""
from __future__ import annotations

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, SPEED_MIN, SPEED_MAX, MODES


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]
    api = data["api"]

    entities = []
    for device_id in coordinator.data:
        device_info = coordinator.data[device_id]["device"]
        entities.append(GetAirFan(coordinator, api, device_id, device_info))

    async_add_entities(entities)


class GetAirFan(CoordinatorEntity, FanEntity):
    """Fan entity combining speed and mode control for getAir ventilation."""

    _attr_supported_features = (
        FanEntityFeature.SET_SPEED
        | FanEntityFeature.PRESET_MODE
        | FanEntityFeature.TURN_ON
        | FanEntityFeature.TURN_OFF
    )
    _attr_preset_modes = list(MODES.values())
    # 40 steps = 0.1 increments across 0.0-4.0
    _attr_speed_count = 20

    def __init__(self, coordinator, api, device_id, device_info):
        super().__init__(coordinator)
        self._api = api
        self._device_id = device_id
        self._attr_unique_id = f"{device_id}_fan"
        device_name = device_info.get("name", f"getAir {device_id}")
        self._attr_name = f"{device_name} Fan"

    @property
    def _zone(self) -> dict:
        return self.coordinator.data[self._device_id]["zone"]

    @property
    def is_on(self) -> bool:
        speed = self._zone.get("speed", 0)
        return float(speed) > 0

    @property
    def percentage(self) -> int | None:
        speed = self._zone.get("speed")
        if speed is None:
            return None
        return round((float(speed) / SPEED_MAX) * 100)

    @property
    def preset_mode(self) -> str | None:
        mode_key = self._zone.get("mode")
        return MODES.get(mode_key)

    async def async_set_percentage(self, percentage: int) -> None:
        if percentage == 0:
            await self.async_turn_off()
            return
        # Map 0-100% to 0.5-4.0, snapped to nearest 0.5 step
        raw = (percentage / 100) * SPEED_MAX
        speed = max(SPEED_MIN, round(raw * 2) / 2)
        await self._api.set_speed(self._device_id, speed)
        await self.coordinator.async_request_refresh()

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        mode_key = next((k for k, v in MODES.items() if v == preset_mode), None)
        if mode_key:
            await self._api.set_mode(self._device_id, mode_key)
            await self.coordinator.async_request_refresh()

    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs,
    ) -> None:
        if preset_mode:
            await self.async_set_preset_mode(preset_mode)
        elif percentage is not None:
            await self.async_set_percentage(percentage)
        else:
            # Default: restore to speed 2 ventilate if was off
            current_speed = float(self._zone.get("speed", 0))
            speed = round(current_speed * 2) / 2 if current_speed > 0 else SPEED_MIN * 2
            await self._api.set_speed(self._device_id, speed)
            await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        await self._api.set_speed(self._device_id, 0.0)
        await self.coordinator.async_request_refresh()
