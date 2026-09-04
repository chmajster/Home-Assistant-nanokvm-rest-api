"""DataUpdateCoordinator for NanoKVM REST."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable
from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    NanoKVMAPIError,
    NanoKVMAuthError,
    NanoKVMClient,
    NanoKVMError,
    NanoKVMPermissionError,
)
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

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

    async def _async_optional(
        self, request: Awaitable[dict[str, Any]], feature: str
    ) -> dict[str, Any] | None:
        """Fetch an optional endpoint without breaking older firmware support."""
        try:
            return await request
        except NanoKVMPermissionError:
            _LOGGER.debug("NanoKVM feature %s is not permitted for this account", feature)
            return None
        except NanoKVMAPIError as err:
            if err.status in {404, 405}:
                _LOGGER.debug("NanoKVM feature %s is not supported", feature)
                return None
            raise

    async def _async_update_data(self) -> dict[str, Any]:
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
            if is_admin:
                ssh, mdns_state, mouse_jiggler, swap = await asyncio.gather(
                    self._async_optional(self.client.async_get_ssh(), "ssh"),
                    self._async_optional(self.client.async_get_mdns(), "mdns"),
                    self._async_optional(
                        self.client.async_get_mouse_jiggler(), "mouse_jiggler"
                    ),
                    self._async_optional(self.client.async_get_swap(), "swap"),
                )
        except NanoKVMAuthError as err:
            raise ConfigEntryAuthFailed("NanoKVM authentication failed") from err
        except NanoKVMError as err:
            raise UpdateFailed(str(err)) from err

        return {
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
            "capabilities": {
                "admin": is_admin,
                "pcie": is_pcie,
            },
        }
