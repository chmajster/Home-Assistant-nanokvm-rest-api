"""Extended Remote Server backend: Update Center, media library and HID toolbox."""

from __future__ import annotations

import asyncio
from copy import deepcopy
from datetime import datetime, timezone
import os
from pathlib import Path
import tempfile
from typing import Any
from uuid import uuid4

from aiohttp import web
import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.components.http import KEY_HASS, HomeAssistantView
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import Unauthorized

from . import panel_v2 as base
from .advanced_store import RemoteAdvancedStore
from .api import NanoKVMConnectionError, NanoKVMError
from .const import DOMAIN
from .management import async_delete_image, async_get_virtual_media, async_reset_hid
from .remote_advanced import (
    async_cancel_image_download,
    async_get_hid_toolbox,
    async_get_image_transfer,
    async_set_hid_mode,
    async_start_image_download,
    async_upload_iso,
    validate_iso_filename,
    validate_sha256,
)

DATA_ADVANCED_STORE = f"{DOMAIN}_remote_advanced_store"
DATA_UPDATE_RUNTIME = f"{DOMAIN}_update_center_runtime"
MAX_ISO_BYTES = 16 * (1 << 30)
MAX_ISO_REQUEST_BYTES = MAX_ISO_BYTES + (4 << 20)
UPDATE_RECOVERY_TIMEOUT = 240
UPDATE_RECOVERY_INTERVAL = 5


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _advanced_store(hass: HomeAssistant) -> RemoteAdvancedStore:
    return hass.data[DATA_ADVANCED_STORE]


def _runtime(hass: HomeAssistant) -> dict[str, Any]:
    return hass.data.setdefault(DATA_UPDATE_RUNTIME, {"devices": {}, "batch": None})


def _actor(connection: websocket_api.ActiveConnection) -> str:
    return base._connection_actor(connection)  # noqa: SLF001


def _admin_coordinator(hass: HomeAssistant, entry_id: str):
    coordinator = base._loaded_coordinator(hass, entry_id)  # noqa: SLF001
    if coordinator is None:
        raise ValueError("NanoKVM is not loaded")
    if not bool((coordinator.data.get("capabilities") or {}).get("admin")):
        raise ValueError("NanoKVM administrator account is required")
    return coordinator


def _update_state(hass: HomeAssistant, entry_id: str, **values: Any) -> dict[str, Any]:
    state = _runtime(hass)["devices"].setdefault(entry_id, {"state": "idle"})
    state.update(values)
    state["updated_at"] = _utcnow()
    return state


async def _version_info(coordinator: Any) -> dict[str, Any]:
    version, preview = await asyncio.gather(
        coordinator.client.async_get_application_version(),
        coordinator.client.async_get_preview_updates(),
    )
    current = str(version.get("current") or "")
    latest = str(version.get("latest") or "")
    return {
        "current": current,
        "latest": latest,
        "channel": "preview" if bool(preview.get("enabled")) else "stable",
        "update_available": bool(current and latest and current != latest),
    }


async def _run_update_one(
    hass: HomeAssistant,
    entry_id: str,
    actor: str,
    *,
    batch_id: str = "",
) -> str:
    store = base._remote_store(hass)  # noqa: SLF001
    try:
        coordinator = _admin_coordinator(hass, entry_id)
        info = await _version_info(coordinator)
    except (NanoKVMError, ValueError) as err:
        _update_state(hass, entry_id, state="error", message=str(err), batch_id=batch_id)
        await store.async_add_event(
            entry_id,
            "update_failed",
            actor=actor,
            result="error",
            details={"message": str(err)[:200], "batch_id": batch_id},
        )
        return "error"

    before = info["current"]
    target = info["latest"]
    if before and target and before == target:
        _update_state(
            hass,
            entry_id,
            state="up_to_date",
            current=before,
            latest=target,
            channel=info["channel"],
            message="Already up to date",
            batch_id=batch_id,
        )
        await store.async_add_event(
            entry_id,
            "update_skipped",
            actor=actor,
            details={"current": before, "latest": target, "batch_id": batch_id},
        )
        return "up_to_date"

    _update_state(
        hass,
        entry_id,
        state="updating",
        current=before,
        latest=target,
        channel=info["channel"],
        message="Update request sent",
        started_at=_utcnow(),
        batch_id=batch_id,
    )
    await store.async_add_event(
        entry_id,
        "update_started",
        actor=actor,
        details={"from": before, "target": target, "channel": info["channel"], "batch_id": batch_id},
    )

    request_error = ""
    try:
        await coordinator.client.async_update_application()
    except NanoKVMConnectionError as err:
        # A connection drop is expected on some NanoKVM versions while the service restarts.
        request_error = str(err)
    except NanoKVMError as err:
        _update_state(hass, entry_id, state="error", message=str(err), batch_id=batch_id)
        await store.async_add_event(
            entry_id,
            "update_failed",
            actor=actor,
            result="error",
            details={"message": str(err)[:200], "from": before, "target": target, "batch_id": batch_id},
        )
        return "error"

    coordinator.invalidate_application_version()
    _update_state(
        hass,
        entry_id,
        state="waiting",
        message="Waiting for NanoKVM to return online",
        batch_id=batch_id,
    )

    attempts = max(1, UPDATE_RECOVERY_TIMEOUT // UPDATE_RECOVERY_INTERVAL)
    last_error = request_error
    for _ in range(attempts):
        await asyncio.sleep(UPDATE_RECOVERY_INTERVAL)
        try:
            version = await coordinator.client.async_get_application_version()
            current = str(version.get("current") or "")
            latest = str(version.get("latest") or target)
            if current and (current != before or (target and current == target)):
                _update_state(
                    hass,
                    entry_id,
                    state="success",
                    current=current,
                    latest=latest,
                    message="NanoKVM is online after update",
                    finished_at=_utcnow(),
                    batch_id=batch_id,
                )
                await store.async_add_event(
                    entry_id,
                    "update_completed",
                    actor=actor,
                    details={"from": before, "to": current, "target": target, "batch_id": batch_id},
                )
                return "success"
            last_error = f"NanoKVM is online but still reports version {current or 'unknown'}"
        except NanoKVMError as err:
            last_error = str(err)

    message = f"NanoKVM did not confirm the new version within {UPDATE_RECOVERY_TIMEOUT}s"
    if last_error:
        message = f"{message}: {last_error}"
    _update_state(hass, entry_id, state="error", message=message, batch_id=batch_id)
    await store.async_add_event(
        entry_id,
        "update_failed",
        actor=actor,
        result="error",
        details={"message": message[:200], "from": before, "target": target, "batch_id": batch_id},
    )
    return "error"


async def _run_batch(hass: HomeAssistant, batch_id: str, entry_ids: list[str], actor: str) -> None:
    runtime = _runtime(hass)
    batch = runtime.get("batch")
    if not isinstance(batch, dict) or batch.get("id") != batch_id:
        return
    batch["state"] = "running"
    batch["started_at"] = _utcnow()
    for index, entry_id in enumerate(entry_ids):
        if batch.get("cancel_requested"):
            batch["state"] = "cancelled"
            batch["finished_at"] = _utcnow()
            return
        batch["current_entry_id"] = entry_id
        batch["index"] = index
        outcome = await _run_update_one(hass, entry_id, actor, batch_id=batch_id)
        if outcome not in {"success", "up_to_date"}:
            batch["state"] = "error"
            batch["failed_entry_id"] = entry_id
            batch["finished_at"] = _utcnow()
            return
    batch["current_entry_id"] = ""
    batch["index"] = len(entry_ids)
    batch["state"] = "success"
    batch["finished_at"] = _utcnow()


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/panel/update/list"})
@websocket_api.require_admin
@websocket_api.async_response
async def websocket_update_list(hass, connection, msg) -> None:
    """Return Update Center state for every NanoKVM."""
    async def build(entry: Any) -> dict[str, Any]:
        coordinator = base._loaded_coordinator(hass, entry.entry_id)  # noqa: SLF001
        item = {
            "entry_id": entry.entry_id,
            "title": entry.title,
            "loaded": coordinator is not None,
            "available": bool(coordinator and coordinator.last_update_success),
            "admin": False,
            "current": "",
            "latest": "",
            "channel": "stable",
            "update_available": False,
            "error": "",
        }
        if coordinator is None:
            return item
        item["admin"] = bool((coordinator.data.get("capabilities") or {}).get("admin"))
        if not item["admin"]:
            return item
        try:
            item.update(await _version_info(coordinator))
        except NanoKVMError as err:
            item["error"] = str(err)
        item["runtime"] = deepcopy(_runtime(hass)["devices"].get(entry.entry_id, {"state": "idle"}))
        return item

    entries = hass.config_entries.async_entries(DOMAIN)
    items = await asyncio.gather(*(build(entry) for entry in entries))
    connection.send_result(
        msg["id"],
        {"devices": items, "batch": deepcopy(_runtime(hass).get("batch"))},
    )


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/panel/update/channel",
        vol.Required("entry_id"): str,
        vol.Required("channel"): vol.In({"stable", "preview"}),
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def websocket_update_channel(hass, connection, msg) -> None:
    try:
        coordinator = _admin_coordinator(hass, msg["entry_id"])
        enabled = msg["channel"] == "preview"
        await coordinator.client.async_set_preview_updates(enabled)
        coordinator.invalidate_application_version()
        await base._remote_store(hass).async_add_event(  # noqa: SLF001
            msg["entry_id"],
            "update_channel_changed",
            actor=_actor(connection),
            details={"channel": msg["channel"]},
        )
        connection.send_result(msg["id"], {"ok": True, "channel": msg["channel"]})
    except (NanoKVMError, ValueError) as err:
        connection.send_error(msg["id"], "channel_failed", str(err))


@websocket_api.websocket_command(
    {vol.Required("type"): f"{DOMAIN}/panel/update/start", vol.Required("entry_id"): str}
)
@websocket_api.require_admin
@websocket_api.async_response
async def websocket_update_start(hass, connection, msg) -> None:
    entry_id = msg["entry_id"]
    try:
        _admin_coordinator(hass, entry_id)
        current = _runtime(hass)["devices"].get(entry_id, {})
        if current.get("state") in {"updating", "waiting"}:
            raise ValueError("update is already running for this NanoKVM")
        _update_state(hass, entry_id, state="queued", message="Queued")
        hass.async_create_task(
            _run_update_one(hass, entry_id, _actor(connection)),
            f"NanoKVM update {entry_id}",
        )
        connection.send_result(msg["id"], {"accepted": True})
    except ValueError as err:
        connection.send_error(msg["id"], "update_not_started", str(err))


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/panel/update/staged/start",
        vol.Required("entry_ids"): [str],
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def websocket_staged_update_start(hass, connection, msg) -> None:
    entry_ids = list(dict.fromkeys(msg.get("entry_ids") or []))
    if not entry_ids or len(entry_ids) > 50:
        connection.send_error(msg["id"], "invalid_batch", "select between 1 and 50 NanoKVM devices")
        return
    runtime = _runtime(hass)
    batch = runtime.get("batch")
    if isinstance(batch, dict) and batch.get("state") in {"queued", "running"}:
        connection.send_error(msg["id"], "batch_running", "a staged update is already running")
        return
    try:
        for entry_id in entry_ids:
            _admin_coordinator(hass, entry_id)
    except ValueError as err:
        connection.send_error(msg["id"], "invalid_batch", str(err))
        return

    batch_id = uuid4().hex[:12]
    runtime["batch"] = {
        "id": batch_id,
        "state": "queued",
        "entry_ids": entry_ids,
        "current_entry_id": "",
        "index": 0,
        "cancel_requested": False,
        "created_at": _utcnow(),
    }
    hass.async_create_task(
        _run_batch(hass, batch_id, entry_ids, _actor(connection)),
        f"NanoKVM staged update {batch_id}",
    )
    connection.send_result(msg["id"], {"accepted": True, "batch_id": batch_id})


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/panel/update/staged/cancel"})
@websocket_api.require_admin
@websocket_api.async_response
async def websocket_staged_update_cancel(hass, connection, msg) -> None:
    batch = _runtime(hass).get("batch")
    if not isinstance(batch, dict) or batch.get("state") not in {"queued", "running"}:
        connection.send_error(msg["id"], "no_batch", "no staged update is running")
        return
    batch["cancel_requested"] = True
    connection.send_result(msg["id"], {"ok": True})


@websocket_api.websocket_command(
    {vol.Required("type"): f"{DOMAIN}/panel/media/library", vol.Required("entry_id"): str}
)
@websocket_api.require_admin
@websocket_api.async_response
async def websocket_media_library(hass, connection, msg) -> None:
    try:
        coordinator = _admin_coordinator(hass, msg["entry_id"])
        media, transfer = await asyncio.gather(
            async_get_virtual_media(coordinator.client),
            async_get_image_transfer(coordinator.client),
        )
        library = _advanced_store(hass).library(msg["entry_id"], media["files"], media["mounted"])
        connection.send_result(
            msg["id"],
            {
                "items": library,
                "mounted": media["mounted"],
                "cdrom": media["cdrom"],
                "transfer": transfer,
            },
        )
    except (NanoKVMError, ValueError) as err:
        connection.send_error(msg["id"], "media_failed", str(err))


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/panel/media/favorite",
        vol.Required("entry_id"): str,
        vol.Required("path"): str,
        vol.Required("favorite"): bool,
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def websocket_media_favorite(hass, connection, msg) -> None:
    try:
        coordinator = _admin_coordinator(hass, msg["entry_id"])
        images = await coordinator.client.async_get_images()
        files = [str(item) for item in images.get("files") or []]
        if msg["path"] not in files:
            raise ValueError("image is not present on NanoKVM")
        await _advanced_store(hass).async_set_favorite(msg["entry_id"], msg["path"], msg["favorite"])
        connection.send_result(msg["id"], {"ok": True})
    except (NanoKVMError, ValueError) as err:
        connection.send_error(msg["id"], "favorite_failed", str(err))


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/panel/media/mount",
        vol.Required("entry_id"): str,
        vol.Required("path"): str,
        vol.Optional("cdrom", default=True): bool,
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def websocket_media_mount(hass, connection, msg) -> None:
    try:
        coordinator = _admin_coordinator(hass, msg["entry_id"])
        images = await coordinator.client.async_get_images()
        files = [str(item) for item in images.get("files") or []]
        if msg["path"] not in files:
            raise ValueError("image is not present on NanoKVM")
        await coordinator.client.async_mount_image(msg["path"], bool(msg.get("cdrom", True)))
        await _advanced_store(hass).async_mark_used(msg["entry_id"], msg["path"])
        await base._remote_store(hass).async_add_event(  # noqa: SLF001
            msg["entry_id"],
            "mount_image",
            actor=_actor(connection),
            details={"image": Path(msg["path"]).name, "cdrom": bool(msg.get("cdrom", True))},
        )
        connection.send_result(msg["id"], {"ok": True})
    except (NanoKVMError, ValueError) as err:
        connection.send_error(msg["id"], "mount_failed", str(err))


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/panel/media/delete_many",
        vol.Required("entry_id"): str,
        vol.Required("paths"): [str],
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def websocket_media_delete_many(hass, connection, msg) -> None:
    paths = list(dict.fromkeys(msg.get("paths") or []))
    if not paths or len(paths) > 50:
        connection.send_error(msg["id"], "invalid_selection", "select between 1 and 50 images")
        return
    try:
        coordinator = _admin_coordinator(hass, msg["entry_id"])
        media = await async_get_virtual_media(coordinator.client)
        for path in paths:
            if path not in media["files"]:
                raise ValueError(f"image is not present on NanoKVM: {Path(path).name}")
            if path == media["mounted"]:
                raise ValueError(f"mounted image cannot be deleted: {Path(path).name}")
        deleted: list[str] = []
        for path in paths:
            await async_delete_image(coordinator.client, path)
            await _advanced_store(hass).async_remove_media(msg["entry_id"], path)
            deleted.append(path)
        await base._remote_store(hass).async_add_event(  # noqa: SLF001
            msg["entry_id"],
            "images_deleted",
            actor=_actor(connection),
            details={"images": [Path(path).name for path in deleted]},
        )
        connection.send_result(msg["id"], {"deleted": deleted})
    except (NanoKVMError, ValueError) as err:
        connection.send_error(msg["id"], "delete_failed", str(err))


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/panel/media/download/start",
        vol.Required("entry_id"): str,
        vol.Required("url"): str,
        vol.Optional("sha256", default=""): str,
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def websocket_media_download_start(hass, connection, msg) -> None:
    try:
        coordinator = _admin_coordinator(hass, msg["entry_id"])
        filename = await async_start_image_download(
            coordinator.client, msg["url"], msg.get("sha256", "")
        )
        path = f"/data/{filename}"
        await _advanced_store(hass).async_record_media(
            msg["entry_id"], path, source="url", source_url=msg["url"]
        )
        await base._remote_store(hass).async_add_event(  # noqa: SLF001
            msg["entry_id"],
            "iso_download_started",
            actor=_actor(connection),
            details={"filename": filename, "url": msg["url"][:300]},
        )
        connection.send_result(msg["id"], {"accepted": True, "filename": filename})
    except (NanoKVMError, ValueError) as err:
        connection.send_error(msg["id"], "download_failed", str(err))


@websocket_api.websocket_command(
    {vol.Required("type"): f"{DOMAIN}/panel/media/download/cancel", vol.Required("entry_id"): str}
)
@websocket_api.require_admin
@websocket_api.async_response
async def websocket_media_download_cancel(hass, connection, msg) -> None:
    try:
        coordinator = _admin_coordinator(hass, msg["entry_id"])
        await async_cancel_image_download(coordinator.client)
        await base._remote_store(hass).async_add_event(  # noqa: SLF001
            msg["entry_id"], "iso_download_cancelled", actor=_actor(connection)
        )
        connection.send_result(msg["id"], {"ok": True})
    except (NanoKVMError, ValueError) as err:
        connection.send_error(msg["id"], "cancel_failed", str(err))


@websocket_api.websocket_command(
    {vol.Required("type"): f"{DOMAIN}/panel/hid/status", vol.Required("entry_id"): str}
)
@websocket_api.require_admin
@websocket_api.async_response
async def websocket_hid_status(hass, connection, msg) -> None:
    try:
        coordinator = _admin_coordinator(hass, msg["entry_id"])
        connection.send_result(msg["id"], await async_get_hid_toolbox(coordinator.client))
    except (NanoKVMError, ValueError) as err:
        connection.send_error(msg["id"], "hid_failed", str(err))


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/panel/hid/action",
        vol.Required("entry_id"): str,
        vol.Required("action"): vol.In({"reset", "reconnect", "paste", "set_mode"}),
        vol.Optional("text", default=""): str,
        vol.Optional("language", default="en"): str,
        vol.Optional("mode", default="normal"): str,
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def websocket_hid_action(hass, connection, msg) -> None:
    action = msg["action"]
    try:
        coordinator = _admin_coordinator(hass, msg["entry_id"])
        details: dict[str, Any] = {}
        if action in {"reset", "reconnect"}:
            await async_reset_hid(coordinator.client)
        elif action == "paste":
            text = str(msg.get("text") or "")
            if not text:
                raise ValueError("text is required")
            await coordinator.client.async_paste_text(text, str(msg.get("language") or "en"))
            details["characters"] = len(text)
        elif action == "set_mode":
            mode = str(msg.get("mode") or "normal")
            details["mode"] = mode
            await async_set_hid_mode(coordinator.client, mode)
        await base._remote_store(hass).async_add_event(  # noqa: SLF001
            msg["entry_id"], f"hid_{action}", actor=_actor(connection), details=details
        )
        connection.send_result(
            msg["id"],
            {"ok": True, "reboot_expected": action == "set_mode"},
        )
    except (NanoKVMError, ValueError) as err:
        connection.send_error(msg["id"], "hid_action_failed", str(err))


class NanoKVMISOUploadView(HomeAssistantView):
    """Proxy an ISO uploaded to Home Assistant to the selected NanoKVM."""

    url = f"/api/{DOMAIN}/iso-upload/{{entry_id}}"
    name = f"api:{DOMAIN}:iso-upload"
    requires_auth = True

    async def post(self, request: web.Request, entry_id: str) -> web.Response:
        if not request["hass_user"].is_admin:
            raise Unauthorized
        hass: HomeAssistant = request.app[KEY_HASS]
        try:
            coordinator = _admin_coordinator(hass, entry_id)
        except ValueError as err:
            return self.json({"error": str(err)}, status_code=404)

        request._client_max_size = MAX_ISO_REQUEST_BYTES  # noqa: SLF001
        checksum = request.headers.get("X-SHA256-Sum", "").strip()
        temp_path = ""
        filename = ""
        written = 0
        actor = base._user_name(request["hass_user"])  # noqa: SLF001
        store = base._remote_store(hass)  # noqa: SLF001
        try:
            checksum = validate_sha256(checksum)
            reader = await request.multipart()
            part = await reader.next()
            if part is None or part.name != "file" or not part.filename:
                return self.json({"error": "file field is required"}, status_code=400)
            filename = validate_iso_filename(part.filename)
            fd, temp_path = tempfile.mkstemp(prefix="nanokvm-iso-", suffix=".iso")
            os.close(fd)
            with open(temp_path, "wb") as target:  # noqa: PTH123
                while True:
                    chunk = await part.read_chunk(size=1024 * 1024)
                    if not chunk:
                        break
                    written += len(chunk)
                    if written > MAX_ISO_BYTES:
                        return self.json({"error": "ISO exceeds 16 GiB"}, status_code=413)
                    await hass.async_add_executor_job(target.write, chunk)
            if written == 0:
                return self.json({"error": "ISO file is empty"}, status_code=400)
            await async_upload_iso(coordinator.client, temp_path, filename, checksum)
            path = f"/data/{filename}"
            await _advanced_store(hass).async_record_media(
                entry_id, path, size=written, source="upload"
            )
            await store.async_add_event(
                entry_id,
                "iso_uploaded",
                actor=actor,
                details={"filename": filename, "bytes": written},
            )
            return self.json({"ok": True, "filename": filename, "bytes": written})
        except (NanoKVMError, ValueError, web.HTTPException) as err:
            await store.async_add_event(
                entry_id,
                "iso_upload_failed",
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


EXTENDED_COMMANDS = (
    websocket_update_list,
    websocket_update_channel,
    websocket_update_start,
    websocket_staged_update_start,
    websocket_staged_update_cancel,
    websocket_media_library,
    websocket_media_favorite,
    websocket_media_mount,
    websocket_media_delete_many,
    websocket_media_download_start,
    websocket_media_download_cancel,
    websocket_hid_status,
    websocket_hid_action,
)
