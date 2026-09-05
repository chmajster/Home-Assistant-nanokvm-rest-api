"""Remote Server panel backend for NanoKVM REST."""

from __future__ import annotations

import os
from pathlib import Path
import tempfile
from typing import Any

from aiohttp import web
import voluptuous as vol

from homeassistant.components import panel_custom, websocket_api
from homeassistant.components.http import KEY_HASS, HomeAssistantView, StaticPathConfig
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import Unauthorized

from .api import NanoKVMError
from .const import (
    CONF_BASE_URL,
    CONF_FORCE_OFF_MS,
    DEFAULT_FORCE_OFF_MS,
    DEFAULT_POWER_PRESS_MS,
    DOMAIN,
)
from .coordinator import NanoKVMCoordinator
from .management import (
    async_delete_image,
    async_get_virtual_media,
    async_offline_update,
    async_reset_hid,
    async_set_cdrom_mode,
    validate_offline_update,
)

PANEL_URL = "nanokvm-remote-server"
STATIC_URL = "/nanokvm_rest_static"
PANEL_ELEMENT = "nanokvm-remote-server-panel"
DATA_PANEL_REGISTERED = f"{DOMAIN}_remote_panel_registered"
MAX_OFFLINE_UPDATE_BYTES = 1 << 30
MAX_OFFLINE_REQUEST_BYTES = MAX_OFFLINE_UPDATE_BYTES + (2 << 20)


def _loaded_coordinator(hass: HomeAssistant, entry_id: str) -> NanoKVMCoordinator | None:
    """Return a loaded NanoKVM coordinator for an entry ID."""
    entry = hass.config_entries.async_get_entry(entry_id)
    if (
        entry is None
        or entry.domain != DOMAIN
        or entry.state is not ConfigEntryState.LOADED
        or not hasattr(entry, "runtime_data")
    ):
        return None
    return entry.runtime_data


def _coordinator_summary(coordinator: NanoKVMCoordinator) -> dict[str, Any]:
    """Build a serializable summary for the frontend."""
    data = coordinator.data or {}
    gpio = data.get("gpio") or {}
    hdmi = data.get("hdmi")
    info = data.get("info") or {}
    hostname = data.get("hostname") or {}
    hardware = data.get("hardware") or {}
    version = data.get("application_version") or {}
    capabilities = data.get("capabilities") or {}
    return {
        "available": coordinator.last_update_success,
        "device_key": str(info.get("deviceKey") or coordinator.client.base_url),
        "hostname": str(hostname.get("hostname") or coordinator.config_entry.title),
        "hardware": str(hardware.get("version") or ""),
        "power": bool(gpio.get("pwr")) if "pwr" in gpio else None,
        "hdd": bool(gpio.get("hdd")) if "hdd" in gpio else None,
        "hdmi_signal": (
            bool(hdmi.get("signal"))
            if isinstance(hdmi, dict) and "signal" in hdmi
            else None
        ),
        "admin": bool(capabilities.get("admin")),
        "pcie": bool(capabilities.get("pcie")),
        "application_version": str(
            version.get("current")
            or version.get("version")
            or version.get("installed")
            or ""
        ),
    }


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/panel/list"})
@websocket_api.require_admin
@websocket_api.async_response
async def websocket_list_devices(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """List all configured NanoKVM devices for the Remote Server panel."""
    devices: list[dict[str, Any]] = []
    for entry in hass.config_entries.async_entries(DOMAIN):
        item: dict[str, Any] = {
            "entry_id": entry.entry_id,
            "title": entry.title,
            "base_url": str(entry.data.get(CONF_BASE_URL) or ""),
            "loaded": entry.state is ConfigEntryState.LOADED,
        }
        if entry.state is ConfigEntryState.LOADED and hasattr(entry, "runtime_data"):
            item.update(_coordinator_summary(entry.runtime_data))
        else:
            item.update({"available": False, "admin": False, "pcie": False})
        devices.append(item)
    connection.send_result(msg["id"], {"devices": devices})


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/panel/status",
        vol.Required("entry_id"): str,
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def websocket_device_status(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Return current state and virtual-media details for one NanoKVM."""
    coordinator = _loaded_coordinator(hass, msg["entry_id"])
    if coordinator is None:
        connection.send_error(msg["id"], "not_loaded", "NanoKVM is not loaded")
        return

    try:
        await coordinator.async_request_refresh()
        result = _coordinator_summary(coordinator)
        result["entry_id"] = msg["entry_id"]
        result["title"] = coordinator.config_entry.title
        result["base_url"] = coordinator.client.base_url
        if result["admin"]:
            result["media"] = await async_get_virtual_media(coordinator.client)
        else:
            result["media"] = {"files": [], "mounted": "", "cdrom": False}
        connection.send_result(msg["id"], result)
    except (NanoKVMError, ValueError) as err:
        connection.send_error(msg["id"], "status_failed", str(err))


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/panel/action",
        vol.Required("entry_id"): str,
        vol.Required("action"): vol.In(
            {
                "power_on",
                "power_press",
                "reset",
                "force_off",
                "reboot_nanokvm",
                "reset_hid",
                "mount_image",
                "unmount_image",
                "delete_image",
                "set_cdrom",
            }
        ),
        vol.Optional("image"): str,
        vol.Optional("cdrom"): bool,
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def websocket_device_action(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Execute an action against the selected NanoKVM."""
    coordinator = _loaded_coordinator(hass, msg["entry_id"])
    if coordinator is None:
        connection.send_error(msg["id"], "not_loaded", "NanoKVM is not loaded")
        return

    client = coordinator.client
    action = msg["action"]
    admin = bool((coordinator.data.get("capabilities") or {}).get("admin"))

    try:
        if action == "power_on":
            if not bool((coordinator.data.get("gpio") or {}).get("pwr")):
                await client.async_press_button("power", DEFAULT_POWER_PRESS_MS)
        elif action == "power_press":
            await client.async_press_button("power", DEFAULT_POWER_PRESS_MS)
        elif action == "reset":
            await client.async_press_button("reset", DEFAULT_POWER_PRESS_MS)
        elif action == "force_off":
            duration = int(
                coordinator.config_entry.options.get(
                    CONF_FORCE_OFF_MS, DEFAULT_FORCE_OFF_MS
                )
            )
            await client.async_press_button("power", duration)
        elif action == "reboot_nanokvm":
            if not admin:
                raise ValueError("administrator account is required")
            await client.async_reboot()
        elif action == "reset_hid":
            if not admin:
                raise ValueError("administrator account is required")
            await async_reset_hid(client)
        elif action == "mount_image":
            if not admin:
                raise ValueError("administrator account is required")
            image = str(msg.get("image") or "").strip()
            if not image:
                raise ValueError("image is required")
            media = await async_get_virtual_media(client)
            if image not in media["files"]:
                raise ValueError("image is not present on NanoKVM")
            await client.async_mount_image(image, bool(msg.get("cdrom", True)))
        elif action == "unmount_image":
            if not admin:
                raise ValueError("administrator account is required")
            await client.async_unmount_image()
        elif action == "delete_image":
            if not admin:
                raise ValueError("administrator account is required")
            image = str(msg.get("image") or "").strip()
            if not image:
                raise ValueError("image is required")
            await async_delete_image(client, image)
        elif action == "set_cdrom":
            if not admin:
                raise ValueError("administrator account is required")
            await async_set_cdrom_mode(client, bool(msg.get("cdrom", True)))

        if action != "reboot_nanokvm":
            await coordinator.async_request_refresh()
        connection.send_result(msg["id"], {"ok": True})
    except (NanoKVMError, ValueError) as err:
        connection.send_error(msg["id"], "action_failed", str(err))


class NanoKVMOfflineUpdateView(HomeAssistantView):
    """Proxy offline application packages from Home Assistant to NanoKVM."""

    url = f"/api/{DOMAIN}/offline-update/{{entry_id}}"
    name = f"api:{DOMAIN}:offline-update"
    requires_auth = True

    async def post(self, request: web.Request, entry_id: str) -> web.Response:
        """Receive a package, spool it to disk and forward it to the selected NanoKVM."""
        if not request["hass_user"].is_admin:
            raise Unauthorized

        hass: HomeAssistant = request.app[KEY_HASS]
        coordinator = _loaded_coordinator(hass, entry_id)
        if coordinator is None:
            return self.json({"error": "NanoKVM is not loaded"}, status_code=404)
        if not bool((coordinator.data.get("capabilities") or {}).get("admin")):
            return self.json(
                {"error": "NanoKVM administrator account is required"},
                status_code=403,
            )

        request._client_max_size = MAX_OFFLINE_REQUEST_BYTES  # noqa: SLF001
        checksum = request.headers.get("X-SHA256-Checksum", "").strip()
        temp_path = ""
        filename = ""
        written = 0

        try:
            reader = await request.multipart()
            part = await reader.next()
            if part is None or part.name != "file" or not part.filename:
                return self.json({"error": "file field is required"}, status_code=400)

            filename, checksum = validate_offline_update(part.filename, checksum)
            fd, temp_path = tempfile.mkstemp(prefix="nanokvm-update-", suffix=".tar.gz")
            os.close(fd)

            with open(temp_path, "wb") as target:  # noqa: PTH123
                while True:
                    chunk = await part.read_chunk(size=1024 * 1024)
                    if not chunk:
                        break
                    written += len(chunk)
                    if written > MAX_OFFLINE_UPDATE_BYTES:
                        return self.json(
                            {"error": "offline update package exceeds 1 GiB"},
                            status_code=413,
                        )
                    await hass.async_add_executor_job(target.write, chunk)

            await async_offline_update(
                coordinator.client,
                temp_path,
                filename,
                checksum,
            )
            coordinator.invalidate_application_version()
            return self.json(
                {
                    "ok": True,
                    "filename": filename,
                    "bytes": written,
                    "message": "Offline update accepted by NanoKVM",
                }
            )
        except (NanoKVMError, ValueError, web.HTTPException) as err:
            return self.json({"error": str(err)}, status_code=400)
        finally:
            if temp_path:
                try:
                    await hass.async_add_executor_job(os.remove, temp_path)
                except FileNotFoundError:
                    pass


async def async_setup_remote_panel(hass: HomeAssistant) -> None:
    """Register the Remote Server sidebar panel once."""
    if hass.data.get(DATA_PANEL_REGISTERED):
        return

    websocket_api.async_register_command(hass, websocket_list_devices)
    websocket_api.async_register_command(hass, websocket_device_status)
    websocket_api.async_register_command(hass, websocket_device_action)
    hass.http.register_view(NanoKVMOfflineUpdateView())

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
        module_url=f"{STATIC_URL}/remote-server.js?v=1",
        embed_iframe=False,
        require_admin=True,
        handle_safe_area=True,
    )
    hass.data[DATA_PANEL_REGISTERED] = True
