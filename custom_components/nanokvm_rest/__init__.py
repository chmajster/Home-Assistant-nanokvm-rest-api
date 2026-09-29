"""NanoKVM REST integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .const import (
    CONF_SHOW_SIDEBAR_PANEL,
    DEFAULT_SHOW_SIDEBAR_PANEL,
    PLATFORMS,
)
from .coordinator import NanoKVMCoordinator
from .panel_v4 import (
    async_setup_panel_backend,
    async_setup_remote_panel,
    async_unload_remote_panel,
)
from .providers.registry import provider_spec, runtime_provider
from .providers.runtime import async_create_coordinator
from .providers.secrets import async_protect_data

type NanoKVMConfigEntry = ConfigEntry[NanoKVMCoordinator]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Expose Manager inventory even if every config entry fails to start."""
    await async_setup_panel_backend(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: NanoKVMConfigEntry) -> bool:
    """Set up NanoKVM REST from a config entry."""
    coordinator = await async_create_coordinator(hass, entry)
    try:
        await coordinator.async_config_entry_first_refresh()
    except BaseException:
        await runtime_provider(coordinator).disconnect()
        raise
    entry.runtime_data = coordinator

    await async_setup_remote_panel(
        hass,
        entry.entry_id,
        bool(
            entry.options.get(
                CONF_SHOW_SIDEBAR_PANEL,
                DEFAULT_SHOW_SIDEBAR_PANEL and provider_spec(entry.data).native_management,
            )
        ),
    )
    if provider_spec(entry.data).platforms:
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    else:
        # JetKVM health must keep polling even without Nano-specific entities.
        entry.async_on_unload(coordinator.async_add_listener(lambda: None))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: NanoKVMConfigEntry) -> bool:
    """Unload NanoKVM REST."""
    from .console import async_disconnect_entry

    await async_disconnect_entry(hass, entry.entry_id)
    unload_ok = True
    if provider_spec(entry.data).platforms:
        unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        await runtime_provider(entry.runtime_data).disconnect()
        await async_unload_remote_panel(hass, entry.entry_id)
    return unload_ok


async def async_migrate_entry(hass: HomeAssistant, entry: NanoKVMConfigEntry) -> bool:
    """Version 2: default old records to NanoKVM and encrypt legacy passwords.

    Encryption and key persistence succeed before the ConfigEntry is changed.
    Failed migration leaves the old entry untouched; it never loses a password.
    """
    if entry.version > 2:
        return False
    if entry.version < 2:
        data = await async_protect_data(hass, dict(entry.data))
        hass.config_entries.async_update_entry(entry, data=data, version=2)
    return True
