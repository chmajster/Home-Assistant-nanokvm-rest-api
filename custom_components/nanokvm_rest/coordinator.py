"""DataUpdateCoordinator for NanoKVM REST."""

from __future__ import annotations

import asyncio
from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import NanoKVMAuthError, NanoKVMClient, NanoKVMError
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

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            info, hardware, gpio, hostname = await asyncio.gather(
                self.client.async_get_info(),
                self.client.async_get_hardware(),
                self.client.async_get_gpio(),
                self.client.async_get_hostname(),
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
        }
