"""Remote Server dashboard and management backend for NanoKVM REST."""

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
from .remote_store import RemoteServerStore

PANEL_URL = "nanokvm-remote-server"
STATIC_URL = "/nanokvm_rest_static"
PANEL_ELEMENT = "nanokvm-remote-server-panel"
DATA_PANEL_REGISTERED = f"{DOMAIN}_remote_panel_registered"
DATA_REMOTE_STORE = f"{DOMAIN}_remote_server_store"
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


def _domain_entry(hass: HomeAssistant, entry_id: str):
    entry = hass.config_entries.async_get_entry(entry_id)
    if entry is None or entry.domain != DOMAIN:
        return None
    return entry


def _remote_store(hass: HomeAssistant) -> RemoteServerStore:
    return hass.data[DATA_REMOTE_STORE]


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


def _health(summary: dict[str, Any]) -> dict[str, Any]:
    """Calculate a simple operational health score."""
    if not summary.get("available"):
        return {"score": 0, "state": "critical", "issues": ["kvm_offline"]}

    score = 100
    issues: list[str] = []
    if summary.get("power") is True and summary.get("pcie") and summary.get("hdmi_signal") is False:
        score -= 30
        issues.append("hdmi_no_signal")
    if not summary.get("hardware"):
        score -= 5
        issues.append("hardware_unknown")
    if not summary.get("application_version"):
        score -= 10
        issues.append("version_unknown")
    if score >= 80:
        state = "healthy"
    elif score >= 50:
        state = "warning"
    else:
        state = "critical"
    return {"score": max(0, score), "state": state, "issues": issues}


def _user_name(user: Any) -> str:
    return str(getattr(user, "name", None) or getattr(user, "id", None) or "Home Assistant")


def _connection_actor(connection: websocket_api.ActiveConnection) -> str:
    return _user_name(getattr(connection, "user", None))


def _public_metadata(store: RemoteServerStore, entry_id: str) -> dict[str, Any]:
    return store.metadata(entry_id, include_profiles=False)


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/panel/list"})
@websocket_api.require_admin
@websocket_api.async_response
async def websocket_list_devices(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """List all configured NanoKVM devices for the dashboard."""
    store = _remote_store(hass)
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
            item.update(
                {
                    "available": False,
                    "admin": False,
                    "pcie": False,
                    "power": None,
                    "hdmi_signal": None,
                    "hardware": "",
                    "application_version": "",
                }
            )
        item.update(_public_metadata(store, entry.entry_id))
        item["health"] = _health(item)
        await store.async_observe_state(entry.entry_id, item)
        devices.append(item)

    devices.sort(
        key=lambda item: (
            not bool(item.get("favorite")),
            str(item.get("group") or "").casefold(),
            str(item.get("hostname") or item.get("title") or "").casefold(),
        )
    )
    groups = sorted({str(item.get("group")) for item in devices if item.get("group")}, key=str.casefold)
    tags = sorted(
        {str(tag) for item in devices for tag in (item.get("tags") or []) if tag},
        key=str.casefold,
    )
    connection.send_result(msg["id"], {"devices": devices, "groups": groups, "tags": tags})


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/panel/status",
        vol.Required("entry_id"): str,
        vol.Optional("touch", default=False): bool,
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def websocket_device_status(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Return current state and management details for one NanoKVM."""
    coordinator = _loaded_coordinator(hass, msg["entry_id"])
    if coordinator is None:
        connection.send_error(msg["id"], "not_loaded", "NanoKVM is not loaded")
        return

    store = _remote_store(hass)
    try:
        await coordinator.async_request_refresh()
        if msg.get("touch"):
            await store.async_touch(msg["entry_id"])
        result = _coordinator_summary(coordinator)
        result["entry_id"] = msg["entry_id"]
        result["title"] = coordinator.config_entry.title
        result["base_url"] = coordinator.client.base_url
        result.update(store.metadata(msg["entry_id"], include_profiles=True))
        result["health"] = _health(result)
        if result["admin"]:
            result["media"] = await async_get_virtual_media(coordinator.client)
        else:
            result["media"] = {"files": [], "mounted": "", "cdrom": False}
        await store.async_observe_state(msg["entry_id"], result)
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
                "wake_on_lan",
                "mount_image",
                "unmount_image",
                "delete_image",
                "set_cdrom",
            }
        ),
        vol.Optional("image"): str,
        vol.Optional("cdrom"): bool,
        vol.Optional("mac"): str,
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def websocket_device_action(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Execute an action against the selected NanoKVM and audit it."""
    coordinator = _loaded_coordinator(hass, msg["entry_id"])
    if coordinator is None:
        connection.send_error(msg["id"], "not_loaded", "NanoKVM is not loaded")
        return

    client = coordinator.client
    action = msg["action"]
    admin = bool((coordinator.data.get("capabilities") or {}).get("admin"))
    store = _remote_store(hass)
    actor = _connection_actor(connection)
    details: dict[str, Any] = {}

    try:
        if action == "power_on":
            if not bool((coordinator.data.get("gpio") or {}).get("pwr")):
                await client.async_press_button("power", DEFAULT_POWER_PRESS_MS)
        elif action == "power_press":
            await client.async_press_button("power", DEFAULT_POWER_PRESS_MS)
        elif action == "reset":
            await client.async_press_button("reset", DEFAULT_POWER_PRESS_MS)
        elif action == "force_off":
            if bool((coordinator.data.get("gpio") or {}).get("pwr")):
                duration = int(
                    coordinator.config_entry.options.get(
                        CONF_FORCE_OFF_MS, DEFAULT_FORCE_OFF_MS
                    )
                )
                details["duration_ms"] = duration
                await client.async_press_button("power", duration)
        elif action == "reboot_nanokvm":
            if not admin:
                raise ValueError("administrator account is required")
            await client.async_reboot()
        elif action == "reset_hid":
            if not admin:
                raise ValueError("administrator account is required")
            await async_reset_hid(client)
        elif action == "wake_on_lan":
            mac = str(msg.get("mac") or "").strip()
            if not mac:
                raise ValueError("MAC address is required")
            await client.async_wake_on_lan(mac)
        elif action == "mount_image":
            if not admin:
                raise ValueError("administrator account is required")
            image = str(msg.get("image") or "").strip()
            if not image:
                raise ValueError("image is required")
            media = await async_get_virtual_media(client)
            if image not in media["files"]:
                raise ValueError("image is not present on NanoKVM")
            details["image"] = Path(image).name
            details["cdrom"] = bool(msg.get("cdrom", True))
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
            details["image"] = Path(image).name
            await async_delete_image(client, image)
        elif action == "set_cdrom":
            if not admin:
                raise ValueError("administrator account is required")
            details["cdrom"] = bool(msg.get("cdrom", True))
            await async_set_cdrom_mode(client, bool(msg.get("cdrom", True)))

        if action != "reboot_nanokvm":
            await coordinator.async_request_refresh()
        await store.async_add_event(
            msg["entry_id"], action, actor=actor, result="success", details=details
        )
        connection.send_result(msg["id"], {"ok": True})
    except (NanoKVMError, ValueError) as err:
        await store.async_add_event(
            msg["entry_id"],
            action,
            actor=actor,
            result="error",
            details={"message": str(err)[:200], **details},
        )
        connection.send_error(msg["id"], "action_failed", str(err))


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/panel/metadata/update",
        vol.Required("entry_id"): str,
        vol.Optional("favorite"): bool,
        vol.Optional("group"): str,
        vol.Optional("tags"): [str],
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def websocket_update_metadata(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Update favorite, group and tags for a NanoKVM."""
    if _domain_entry(hass, msg["entry_id"]) is None:
        connection.send_error(msg["id"], "not_found", "NanoKVM entry does not exist")
        return
    patch = {key: msg[key] for key in ("favorite", "group", "tags") if key in msg}
    metadata = await _remote_store(hass).async_update_metadata(msg["entry_id"], patch)
    await _remote_store(hass).async_add_event(
        msg["entry_id"],
        "metadata_updated",
        actor=_connection_actor(connection),
        details={"fields": sorted(patch)},
    )
    connection.send_result(msg["id"], metadata)


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/panel/history",
        vol.Optional("entry_id", default=""): str,
        vol.Optional("limit", default=100): vol.All(int, vol.Range(min=1, max=200)),
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def websocket_history(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Return Remote Server event history."""
    events = _remote_store(hass).events(msg.get("entry_id", ""), int(msg.get("limit", 100)))
    connection.send_result(msg["id"], {"events": events})


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/panel/wol/save",
        vol.Required("entry_id"): str,
        vol.Required("name"): str,
        vol.Required("mac"): str,
        vol.Optional("profile_id", default=""): str,
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def websocket_wol_save(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Create or update a Wake-on-LAN profile."""
    if _domain_entry(hass, msg["entry_id"]) is None:
        connection.send_error(msg["id"], "not_found", "NanoKVM entry does not exist")
        return
    try:
        profile = await _remote_store(hass).async_save_wol_profile(
            msg["entry_id"], msg["name"], msg["mac"], msg.get("profile_id", "")
        )
        await _remote_store(hass).async_add_event(
            msg["entry_id"],
            "wol_profile_saved",
            actor=_connection_actor(connection),
            details={"profile": profile["name"]},
        )
        connection.send_result(msg["id"], {"profile": profile})
    except ValueError as err:
        connection.send_error(msg["id"], "invalid_profile", str(err))


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/panel/wol/delete",
        vol.Required("entry_id"): str,
        vol.Required("profile_id"): str,
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def websocket_wol_delete(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Delete a Wake-on-LAN profile."""
    store = _remote_store(hass)
    profile = store.wol_profile(msg["entry_id"], msg["profile_id"])
    if profile is None:
        connection.send_error(msg["id"], "not_found", "Wake-on-LAN profile does not exist")
        return
    await store.async_delete_wol_profile(msg["entry_id"], msg["profile_id"])
    await store.async_add_event(
        msg["entry_id"],
        "wol_profile_deleted",
        actor=_connection_actor(connection),
        details={"profile": profile["name"]},
    )
    connection.send_result(msg["id"], {"ok": True})


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/panel/wol/run",
        vol.Required("entry_id"): str,
        vol.Required("profile_id"): str,
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def websocket_wol_run(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Run a saved Wake-on-LAN profile through NanoKVM."""
    coordinator = _loaded_coordinator(hass, msg["entry_id"])
    if coordinator is None:
        connection.send_error(msg["id"], "not_loaded", "NanoKVM is not loaded")
        return
    store = _remote_store(hass)
    profile = store.wol_profile(msg["entry_id"], msg["profile_id"])
    if profile is None:
        connection.send_error(msg["id"], "not_found", "Wake-on-LAN profile does not exist")
        return
    try:
        await coordinator.client.async_wake_on_lan(profile["mac"])
        await store.async_add_event(
            msg["entry_id"],
            "wake_on_lan",
            actor=_connection_actor(connection),
            details={"profile": profile["name"]},
        )
        connection.send_result(msg["id"], {"ok": True})
    except (NanoKVMError, ValueError) as err:
        await store.async_add_event(
            msg["entry_id"],
            "wake_on_lan",
            actor=_connection_actor(connection),
            result="error",
            details={"profile": profile["name"], "message": str(err)[:200]},
        )
        connection.send_error(msg["id"], "wol_failed", str(err))


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
        store = _remote_store(hass)
        actor = _user_name(request["hass_user"])

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

            if written == 0:
                return self.json({"error": "offline update package is empty"}, status_code=400)

            await async_offline_update(
                coordinator.client,
                temp_path,
                filename,
                checksum,
            )
            coordinator.invalidate_application_version()
            await store.async_add_event(
                entry_id,
                "offline_update",
                actor=actor,
                details={"filename": filename, "bytes": written},
            )
            return self.json(
                {
                    "ok": True,
                    "filename": filename,
                    "bytes": written,
                    "message": "Offline update accepted by NanoKVM",
                }
            )
        except (NanoKVMError, ValueError, web.HTTPException) as err:
            await store.async_add_event(
                entry_id,
                "offline_update",
                actor=actor,
                result="error",
                details={"filename": filename, "message": str(err)[:200]},
            )
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

    store = RemoteServerStore(hass)
    await store.async_load()
    hass.data[DATA_REMOTE_STORE] = store

    websocket_api.async_register_command(hass, websocket_list_devices)
    websocket_api.async_register_command(hass, websocket_device_status)
    websocket_api.async_register_command(hass, websocket_device_action)
    websocket_api.async_register_command(hass, websocket_update_metadata)
    websocket_api.async_register_command(hass, websocket_history)
    websocket_api.async_register_command(hass, websocket_wol_save)
    websocket_api.async_register_command(hass, websocket_wol_delete)
    websocket_api.async_register_command(hass, websocket_wol_run)
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
        module_url=f"{STATIC_URL}/remote-server-v3.js?v=3",
        embed_iframe=False,
        require_admin=True,
        handle_safe_area=True,
    )
    hass.data[DATA_PANEL_REGISTERED] = True
