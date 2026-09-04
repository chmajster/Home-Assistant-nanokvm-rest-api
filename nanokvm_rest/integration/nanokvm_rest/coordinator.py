"""DataUpdateCoordinator for NanoKVM REST."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable
from datetime import timedelta
import logging
from time import monotonic
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    NanoKVMAPIError,
    NanoKVMAuthError,
    NanoKVMClient,
    NanoKVMConnectionError,
    NanoKVMError,
    NanoKVMPermissionError,
)
from .const import (
    APPLICATION_VERSION_CHECK_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    EVENT_TYPE,
)

_LOGGER = logging.getLogger(__name__)


class NanoKVMCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinate NanoKVM polling."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        client: NanoKVMClient,
        scan_interval: int = DEFAULT_SCAN_INTERVAL,
    ) -> None:
        super().__init__(
            hass,
            logger=_LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )
        self.client = client
        self._application_version_cache: dict[str, Any] | None = None
        self._application_version_checked_at = 0.0

    async def _async_optional(
        self,
        request: Awaitable[dict[str, Any]],
        feature: str,
        *,
        tolerate_api_errors: bool = False,
    ) -> dict[str, Any] | None:
        """Fetch an optional endpoint without breaking older firmware support."""
        try:
            return await request
        except NanoKVMPermissionError:
            _LOGGER.debug("NanoKVM feature %s is not permitted for this account", feature)
            return None
        except NanoKVMAPIError as err:
            if err.status in {404, 405} or tolerate_api_errors:
                _LOGGER.debug("NanoKVM feature %s is unavailable: %s", feature, err)
                return None
            raise
        except NanoKVMConnectionError as err:
            if tolerate_api_errors:
                _LOGGER.debug("NanoKVM feature %s could not be queried: %s", feature, err)
                return None
            raise

    async def _async_get_application_version_cached(self) -> dict[str, Any] | None:
        """Query the upstream version endpoint at most once every six hours."""
        now = monotonic()
        if (
            self._application_version_checked_at
            and now - self._application_version_checked_at
            < APPLICATION_VERSION_CHECK_INTERVAL
        ):
            return self._application_version_cache

        self._application_version_checked_at = now
        self._application_version_cache = await self._async_optional(
            self.client.async_get_application_version(),
            "application_version",
            tolerate_api_errors=True,
        )
        return self._application_version_cache

    def invalidate_application_version(self) -> None:
        """Force the next coordinator refresh to re-check application versions."""
        self._application_version_checked_at = 0.0

    def _device_key(self, data: dict[str, Any]) -> str:
        info = data.get("info") or {}
        return str(info.get("deviceKey") or self.client.base_url)

    def _fire_device_event(self, data: dict[str, Any], event_type: str) -> None:
        """Fire an integration event consumed by device automation triggers."""
        self.hass.bus.async_fire(
            EVENT_TYPE,
            {
                "device_key": self._device_key(data),
                "type": event_type,
            },
        )

    def _emit_state_change_events(
        self, old: dict[str, Any] | None, new: dict[str, Any]
    ) -> None:
        """Emit power and HDMI events only for real state transitions."""
        if not old:
            return

        old_gpio = old.get("gpio") or {}
        new_gpio = new.get("gpio") or {}
        if "pwr" in old_gpio and "pwr" in new_gpio:
            old_power = bool(old_gpio.get("pwr"))
            new_power = bool(new_gpio.get("pwr"))
            if old_power != new_power:
                self._fire_device_event(new, "power_on" if new_power else "power_off")

        old_hdmi = old.get("hdmi")
        new_hdmi = new.get("hdmi")
        if isinstance(old_hdmi, dict) and isinstance(new_hdmi, dict):
            if "signal" in old_hdmi and "signal" in new_hdmi:
                old_signal = bool(old_hdmi.get("signal"))
                new_signal = bool(new_hdmi.get("signal"))
                if old_signal != new_signal:
                    self._fire_device_event(
                        new,
                        "hdmi_signal_on" if new_signal else "hdmi_signal_off",
                    )

    async def _async_update_data(self) -> dict[str, Any]:
        previous_data = self.data
        try:
            info, hardware, gpio, hostname = await asyncio.gather(
                self.client.async_get_info(),
                self.client.async_get_hardware(),
                self.client.async_get_gpio(),
                self.client.async_get_hostname(),
            )

            account, web_title = await asyncio.gather(
                self._async_optional(self.client.async_get_account(), "account"),
                self._async_optional(self.client.async_get_web_title(), "web_title"),
            )

            hardware_version = str(hardware.get("version") or "").upper()
            role = str((account or {}).get("role") or "").lower()
            is_pcie = hardware_version == "PCIE"
            is_admin = role == "admin"

            hdmi: dict[str, Any] | None = None
            if is_pcie:
                hdmi = await self._async_optional(
                    self.client.async_get_hdmi(), "hdmi"
                )

            ssh: dict[str, Any] | None = None
            mdns_state: dict[str, Any] | None = None
            mouse_jiggler: dict[str, Any] | None = None
            swap: dict[str, Any] | None = None
            memory_limit: dict[str, Any] | None = None
            oled: dict[str, Any] | None = None
            virtual_devices: dict[str, Any] | None = None
            application_version: dict[str, Any] | None = None
            preview_updates: dict[str, Any] | None = None
            update_server: dict[str, Any] | None = None

            if is_admin:
                (
                    ssh,
                    mdns_state,
                    mouse_jiggler,
                    swap,
                    memory_limit,
                    oled,
                    virtual_devices,
                    preview_updates,
                    update_server,
                    application_version,
                ) = await asyncio.gather(
                    self._async_optional(self.client.async_get_ssh(), "ssh"),
                    self._async_optional(self.client.async_get_mdns(), "mdns"),
                    self._async_optional(
                        self.client.async_get_mouse_jiggler(), "mouse_jiggler"
                    ),
                    self._async_optional(self.client.async_get_swap(), "swap"),
                    self._async_optional(
                        self.client.async_get_memory_limit(), "memory_limit"
                    ),
                    self._async_optional(self.client.async_get_oled(), "oled"),
                    self._async_optional(
                        self.client.async_get_virtual_devices(), "virtual_devices"
                    ),
                    self._async_optional(
                        self.client.async_get_preview_updates(), "preview_updates"
                    ),
                    self._async_optional(
                        self.client.async_get_update_server(), "update_server"
                    ),
                    self._async_get_application_version_cached(),
                )
        except NanoKVMAuthError as err:
            if previous_data and self.last_update_success:
                self._fire_device_event(previous_data, "became_unavailable")
            raise ConfigEntryAuthFailed("NanoKVM authentication failed") from err
        except NanoKVMError as err:
            if previous_data and self.last_update_success:
                self._fire_device_event(previous_data, "became_unavailable")
            raise UpdateFailed(str(err)) from err

        data = {
            "info": info,
            "hardware": hardware,
            "gpio": gpio,
            "hostname": hostname,
            "account": account,
            "web_title": web_title,
            "hdmi": hdmi,
            "ssh": ssh,
            "mdns_state": mdns_state,
            "mouse_jiggler": mouse_jiggler,
            "swap": swap,
            "memory_limit": memory_limit,
            "oled": oled,
            "virtual_devices": virtual_devices,
            "preview_updates": preview_updates,
            "update_server": update_server,
            "application_version": application_version,
            "capabilities": {
                "admin": is_admin,
                "pcie": is_pcie,
            },
        }
        self._emit_state_change_events(previous_data, data)
        return data
