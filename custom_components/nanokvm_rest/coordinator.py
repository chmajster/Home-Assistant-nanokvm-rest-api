"""DataUpdateCoordinator for NanoKVM REST."""

from __future__ import annotations

import asyncio
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import NanoKVMAuthError, NanoKVMClient, NanoKVMError
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN


class NanoKVMCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinate NanoKVM polling."""

    def __init__(self, hass: HomeAssistant, client: NanoKVMClient) -> None:
        super().__init__(
            hass,
            logger=__import__("logging").getLogger(__name__),
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
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
            raise UpdateFailed(f"Authentication failed: {err}") from err
        except NanoKVMError as err:
            raise UpdateFailed(str(err)) from err

        return {
            "info": info,
            "hardware": hardware,
            "gpio": gpio,
            "hostname": hostname,
        }
