"""Remote Server panel setup with Live Remote Console support."""

from __future__ import annotations

from pathlib import Path

from homeassistant.components import frontend, panel_custom, websocket_api
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant

from . import panel_v2 as base
from .advanced_store import RemoteAdvancedStore
from .console import NanoKVMConsoleView, websocket_console_session
from .const import DOMAIN
from .panel_ext import (
    DATA_ADVANCED_STORE,
    DATA_UPDATE_RUNTIME,
    EXTENDED_COMMANDS,
    NanoKVMISOUploadView,
)

PANEL_URL = base.PANEL_URL
STATIC_URL = base.STATIC_URL
PANEL_ELEMENT = "nanokvm-remote-server-panel-v5"
DATA_PANEL_BACKEND_REGISTERED = f"{DOMAIN}_remote_panel_backend_registered"
DATA_PANEL_VISIBLE_ENTRIES = f"{DOMAIN}_remote_panel_visible_entries"


async def async_setup_remote_panel(
    hass: HomeAssistant,
    entry_id: str,
    show_sidebar: bool = True,
) -> None:
    """Set up Remote Server backend and synchronize sidebar visibility."""
    if not hass.data.get(DATA_PANEL_BACKEND_REGISTERED):
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
        for command in (*base_commands, *EXTENDED_COMMANDS, websocket_console_session):
            websocket_api.async_register_command(hass, command)

        hass.http.register_view(base.NanoKVMOfflineUpdateView())
        hass.http.register_view(NanoKVMISOUploadView())
        hass.http.register_view(NanoKVMConsoleView())

        frontend_path = str(Path(__file__).parent / "www")
        await hass.http.async_register_static_paths(
            [StaticPathConfig(STATIC_URL, frontend_path, cache_headers=False)]
        )
        hass.data[DATA_PANEL_BACKEND_REGISTERED] = True

    visible_entries: set[str] = hass.data.setdefault(DATA_PANEL_VISIBLE_ENTRIES, set())
    if show_sidebar:
        visible_entries.add(entry_id)
    else:
        visible_entries.discard(entry_id)

    await _async_sync_sidebar_panel(hass)


async def async_unload_remote_panel(hass: HomeAssistant, entry_id: str) -> None:
    """Remove one config entry from the set requesting the sidebar panel."""
    visible_entries: set[str] = hass.data.setdefault(DATA_PANEL_VISIBLE_ENTRIES, set())
    visible_entries.discard(entry_id)
    await _async_sync_sidebar_panel(hass)


async def _async_sync_sidebar_panel(hass: HomeAssistant) -> None:
    """Register or remove the Remote Server sidebar panel."""
    visible_entries: set[str] = hass.data.setdefault(DATA_PANEL_VISIBLE_ENTRIES, set())
    panel_registered = bool(hass.data.get(base.DATA_PANEL_REGISTERED))

    if visible_entries and not panel_registered:
        await panel_custom.async_register_panel(
            hass=hass,
            frontend_url_path=PANEL_URL,
            webcomponent_name=PANEL_ELEMENT,
            sidebar_title="Remote Server",
            sidebar_icon="mdi:server-network",
            module_url=f"{STATIC_URL}/remote-server-v5.js?v=5",
            embed_iframe=False,
            require_admin=True,
            handle_safe_area=True,
        )
        hass.data[base.DATA_PANEL_REGISTERED] = True
        return

    if not visible_entries and panel_registered:
        frontend.async_remove_panel(hass, PANEL_URL, warn_if_unknown=False)
        hass.data[base.DATA_PANEL_REGISTERED] = False
