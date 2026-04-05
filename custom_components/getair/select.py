"""Select platform for getAir - time profile selection."""
from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]
    api = data["api"]

    entities = []
    for device_id in coordinator.data:
        device_info = coordinator.data[device_id]["device"]
        entities.append(GetAirTimeProfileSelect(coordinator, api, device_id, device_info))

    async_add_entities(entities)


class GetAirTimeProfileSelect(CoordinatorEntity, SelectEntity):
    """Select entity for choosing a time profile."""

    def __init__(self, coordinator, api, device_id, device_info):
        super().__init__(coordinator)
        self._api = api
        self._device_id = device_id
        self._attr_unique_id = f"{device_id}_time_profile"
        device_name = device_info.get("name", f"getAir {device_id}")
        self._attr_name = f"{device_name} Time Profile"
        self._attr_icon = "mdi:clock-time-eight-outline"

    @property
    def _system(self) -> dict:
        return self.coordinator.data[self._device_id]["system"]

    @property
    def _zone(self) -> dict:
        return self.coordinator.data[self._device_id]["zone"]

    @property
    def options(self) -> list[str]:
        """Build option list from named profiles plus Off."""
        opts = ["Off"]
        for i in range(1, 11):
            name = self._system.get(f"time-profile-{i}-name", "")
            if name:
                opts.append(f"{i}: {name}")
        return opts

    @property
    def current_option(self) -> str | None:
        active = self._zone.get("time-profile", 0)
        if not active:
            return "Off"
        name = self._system.get(f"time-profile-{active}-name", "")
        return f"{active}: {name}" if name else f"{active}"

    async def async_select_option(self, option: str) -> None:
        if option == "Off":
            index = 0
        else:
            index = int(option.split(":")[0])
        await self._api.set_service(f"1.{self._device_id}", "Zone", {"time-profile": index})
        await self.coordinator.async_request_refresh()
