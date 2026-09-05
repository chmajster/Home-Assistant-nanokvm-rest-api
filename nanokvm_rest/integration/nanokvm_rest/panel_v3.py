"""Remote Server panel setup for the advanced management suite."""

from __future__ import annotations

from pathlib import Path

from homeassistant.components import panel_custom, websocket_api
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant

from . import panel_v2 as base
from .advanced_store import RemoteAdvancedStore
from .const import DOMAIN
from .panel_ext import (
    DATA_ADVANCED_STORE,
    DATA_UPDATE_RUNTIME,
    EXTENDED_COMMANDS,
    NanoKVMISOUploadView,
)

PANEL_URL = base.PANEL_URL
STATIC_URL = base.STATIC_URL
PANEL_ELEMENT = base.PANEL_ELEMENT


async def async_setup_remote_panel(hass: HomeAssistant) -> None:
    """Register the complete Remote Server panel once."""
    if hass.data.get(base.DATA_PANEL_REGISTERED):
        return

    store = base.RemoteServerStore(hass)
    await store.async_load()
    hass.data[base.DATA_REMOTE_STORE] = store

    advanced_store = RemoteAdvancedStore(hass)
    await advanced_store.async_load()
    hass.data[DATA_ADVANCED_STORE] = advanced_store
    hass.data.setdefault(DATA_UPDATE_RUNTIME, {"devices": {}, "batch": None})

    base_commands = (
        base.websocket_list_devices,
        base.websocket_device_status,
        base.websocket_device_action,
        base.websocket_update_metadata,
        base.websocket_history,
        base.websocket_wol_save,
        base.websocket_wol_delete,
        base.websocket_wol_run,
    )
    for command in (*base_commands, *EXTENDED_COMMANDS):
        websocket_api.async_register_command(hass, command)

    hass.http.register_view(base.NanoKVMOfflineUpdateView())
    hass.http.register_view(NanoKVMISOUploadView())

    frontend_path = str(Path(__file__).parent / "www")
    await hass.http.async_register_static_paths(
        [StaticPathConfig(STATIC_URL, frontend_path, cache_headers=False)]
    )
    await panel_custom.async_register_panel(
        hass=hass,
        frontend_url_path=PANEL_URL,
        webcomponent_name=PANEL_ELEMENT,
        sidebar_title="Remote Server",
        sidebar_icon="mdi:server-network",
        module_url=f"{STATIC_URL}/remote-server-v4.js?v=4",
        embed_iframe=False,
        require_admin=True,
        handle_safe_area=True,
    )
    hass.data[base.DATA_PANEL_REGISTERED] = True
