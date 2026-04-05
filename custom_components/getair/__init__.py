"""getAir Home Assistant Integration."""
from __future__ import annotations

import logging
from datetime import timedelta

import aiohttp
import async_timeout

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, API_URL, AUTH_URL, CLIENT_ID, CONF_TOKEN, CONF_REFRESH_TOKEN

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.CLIMATE, Platform.SENSOR, Platform.FAN, Platform.SELECT]
SCAN_INTERVAL = timedelta(seconds=60)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up getAir from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    api = GetAirAPI(
        username=entry.data[CONF_USERNAME],
        password=entry.data[CONF_PASSWORD],
    )

    # Use stored token directly - avoid double-auth which invalidates the token
    stored_token = entry.data.get(CONF_TOKEN)
    stored_refresh = entry.data.get(CONF_REFRESH_TOKEN)
    if stored_token:
        api._access_token = stored_token
        api._refresh_token = stored_refresh
        _LOGGER.warning("getAir using stored token, prefix: %s", stored_token[:20])
    else:
        try:
            await api.authenticate()
        except Exception as err:
            _LOGGER.error("Failed to authenticate with getAir: %s", err)
            return False

    coordinator = GetAirCoordinator(hass, api)
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = {
        "api": api,
        "coordinator": coordinator,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


class GetAirAPI:
    """getAir REST API client."""

    def __init__(self, username: str, password: str) -> None:
        self.username = username
        self.password = password
        self._access_token: str | None = None
        self._refresh_token: str | None = None
        self._session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            # Minimal headers to match curl behaviour
            self._session = aiohttp.ClientSession(
                headers={
                    "User-Agent": "curl/8.5.0",
                    "Accept": "*/*",
                }
            )
        return self._session

    async def authenticate(self) -> None:
        """Authenticate and store access token."""
        session = await self._get_session()
        async with async_timeout.timeout(10):
            resp = await session.post(
                f"{AUTH_URL}/oauth/token",
                headers={"Content-Type": "application/json"},
                json={
                    "username": self.username,
                    "password": self.password,
                    "client_id": CLIENT_ID,
                    "grant_type": "password",
                    "scope": "offline_access",
                },
            )
            resp.raise_for_status()
            # aiohttp may return content-type text/plain even for JSON payloads
            text = await resp.text()
            import json as _json
            data = _json.loads(text)
            self._access_token = data["access_token"]
            self._refresh_token = data.get("refresh_token")
            _LOGGER.warning("getAir auth OK, token prefix: %s", self._access_token[:20])

    async def _refresh_access_token(self) -> None:
        """Use refresh token to get a new access token silently."""
        if not self._refresh_token:
            await self.authenticate()
            return
        session = await self._get_session()
        async with async_timeout.timeout(10):
            resp = await session.post(
                f"{AUTH_URL}/oauth/token",
                json={
                    "client_id": CLIENT_ID,
                    "grant_type": "refresh_token",
                    "refresh_token": self._refresh_token,
                },
            )
            if resp.status == 200:
                data = await resp.json()
                self._access_token = data["access_token"]
                if "refresh_token" in data:
                    self._refresh_token = data["refresh_token"]
                _LOGGER.debug("Successfully refreshed getAir token")
            else:
                _LOGGER.debug("Refresh failed, re-authenticating from scratch")
                await self.authenticate()

    async def _request(self, method: str, path: str, **kwargs):
        """Make an authenticated API request, refresh token on 401."""
        session = await self._get_session()
        headers = {"Authorization": f"Bearer {self._access_token}"}
        if "json" in kwargs:
            headers["Content-Type"] = "application/json"

        _LOGGER.warning("getAir request %s %s body: %s token prefix: %s", method, path, kwargs.get("json"), (self._access_token or "NONE")[:20])
        async with async_timeout.timeout(10):
            resp = await session.request(
                method,
                f"{API_URL}{path}",
                headers=headers,
                **kwargs,
            )
        _LOGGER.warning("getAir response %s for %s", resp.status, path)

        if resp.status == 401:
            body = await resp.text()
            _LOGGER.warning("Token rejected, body: %s", body)
            await self._refresh_access_token()
            headers["Authorization"] = f"Bearer {self._access_token}"
            async with async_timeout.timeout(10):
                resp = await session.request(
                    method,
                    f"{API_URL}{path}",
                    headers=headers,
                    **kwargs,
                )

        resp.raise_for_status()
        if resp.status == 204:
            return None  # No content - caller should keep last known value
        return await resp.json()

    async def get_devices(self) -> list[dict]:
        """Get list of all devices."""
        return await self._request("GET", "/api/v1/devices")

    async def get_service(self, device_id: str, service: str) -> dict:
        """Get all properties of a service."""
        return await self._request("GET", f"/api/v1/devices/{device_id}/services/{service}")

    async def set_service(self, device_id: str, service: str, data: dict) -> dict:
        """Set properties on a service."""
        return await self._request("PUT", f"/api/v1/devices/{device_id}/services/{service}", json=data)

    async def get_system(self, device_id: str) -> dict:
        """Get system service data - uses plain device_id."""
        return await self.get_service(device_id, "System")

    async def get_zone(self, device_id: str, zone_index: int = 1) -> dict:
        """Get zone service data - uses zone_index.device_id format."""
        return await self.get_service(f"{zone_index}.{device_id}", "Zone")

    async def set_speed(self, device_id: str, speed: float, zone_index: int = 1) -> dict:
        """Set fan speed (0.0 - 4.0)."""
        return await self.set_service(f"{zone_index}.{device_id}", "Zone", {"speed": speed})

    async def set_mode(self, device_id: str, mode: str, zone_index: int = 1) -> dict:
        """Set ventilation mode."""
        return await self.set_service(f"{zone_index}.{device_id}", "Zone", {"mode": mode})

    async def set_target_temp(self, device_id: str, temp: float, zone_index: int = 1) -> dict:
        """Set target temperature."""
        return await self.set_service(f"{zone_index}.{device_id}", "Zone", {"target-temp": temp})
    async def close(self) -> None:
        """Close the aiohttp session."""
        if self._session and not self._session.closed:
            await self._session.close()


class GetAirCoordinator(DataUpdateCoordinator):
    """Coordinator to fetch data from all getAir devices."""

    def __init__(self, hass: HomeAssistant, api: GetAirAPI) -> None:
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=SCAN_INTERVAL)
        self.api = api
        self.devices: list[dict] = []
        self._rate_limited_count: int = 0

    async def _async_update_data(self) -> dict:
        try:
            if not self.devices:
                self.devices = await self.api.get_devices()

            data = {}
            for device in self.devices:
                device_id = device.get("deviceIdentifier") or device.get("id")
                # Skip entries with a zone prefix like "1.9035EA409D6A"
                if not device_id or "." in device_id:
                    continue
                system = await self.api.get_system(device_id)
                zone = await self.api.get_zone(device_id)

                # Keep last known values if API returns no content
                if system is None:
                    system = self.data[device_id]["system"] if self.data and device_id in self.data else {}
                if zone is None:
                    self._rate_limited_count += 1
                    _LOGGER.debug("Zone returned no content (x%d), keeping last values", self._rate_limited_count)
                    zone = self.data[device_id]["zone"] if self.data and device_id in self.data else {}
                else:
                    self._rate_limited_count = 0

                data[device_id] = {
                    "device": device,
                    "system": system,
                    "zone": zone,
                }
            return data
        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Error communicating with getAir API: {err}") from err
