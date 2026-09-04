"""NanoKVM REST integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import NanoKVMClient
from .const import CONF_BASE_URL, CONF_VERIFY_SSL, PLATFORMS
from .coordinator import NanoKVMCoordinator


type NanoKVMConfigEntry = ConfigEntry[NanoKVMCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: NanoKVMConfigEntry) -> bool:
    """Set up NanoKVM REST from a config entry."""
    session = async_get_clientsession(
        hass, verify_ssl=entry.data.get(CONF_VERIFY_SSL, True)
    )
    client = NanoKVMClient(
        session,
        entry.data[CONF_BASE_URL],
        entry.data[CONF_USERNAME],
        entry.data[CONF_PASSWORD],
    )
    coordinator = NanoKVMCoordinator(hass, client)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: NanoKVMConfigEntry) -> bool:
    """Unload NanoKVM REST."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
