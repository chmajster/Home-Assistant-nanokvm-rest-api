"""Admin-only multi-provider Manager operations on the existing HA backend."""

from __future__ import annotations

import asyncio
import logging
import time
from collections import deque

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.config_entries import ConfigEntryState
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN
from .providers.configuration import (
    async_make_provider,
    async_probe_candidate,
    async_validate_candidate,
    normalize_candidate,
    unique_id_for,
)
from .providers.errors import KVMError
from .providers.jetkvm import MAC_RE
from .providers.network import parse_origin
from .providers.registry import provider_name, provider_spec, runtime_provider
from .providers.secrets import CREDENTIAL_FIELD, async_protect_data
from .providers.state import async_state_store

_LOGGER = logging.getLogger(__name__)
MAX_DEVICES = 128


def _entry(hass, entry_id):
    entry = hass.config_entries.async_get_entry(str(entry_id or ""))
    if entry is None or entry.domain != DOMAIN:
        raise KVMError("not_found")
    return entry


def _title(payload, default):
    title = payload.get("title", default)
    if (
        not isinstance(title, str)
        or not 1 <= len(title.strip()) <= 128
        or any(ord(c) < 32 for c in title)
    ):
        raise KVMError("invalid_data", "Invalid device name")
    return title.strip()


def _limit(hass, actor, operation):
    if operation in {"get", "disconnect"}:
        return
    now = time.monotonic()
    limits = hass.data.setdefault("nanokvm_rest_kvm_rate_limits", {})
    # This store is bounded by actual authenticated HA users, never caller text.
    for key in list(limits):
        while limits[key] and limits[key][0] < now - 60:
            limits[key].popleft()
        if not limits[key]:
            del limits[key]
    attempts = limits.setdefault(actor, deque())
    if len(attempts) >= 20:
        raise KVMError("rate_limited", "Manager request limit", retry_after=60)
    attempts.append(now)


async def _get(hass, payload):
    entry = _entry(hass, payload.get("entry_id"))
    origin = parse_origin(entry.data["base_url"])
    loaded = entry.state is ConfigEntryState.LOADED and hasattr(entry, "runtime_data")
    result = (await async_state_store(hass)).get(entry.entry_id)
    result["available"] = False  # Persisted health must not claim current online.
    if loaded:
        result.update(runtime_provider(entry.runtime_data).get_status())
    result.update(
        entry_id=entry.entry_id,
        title=entry.title,
        provider=provider_name(entry.data),
        base_url=origin.url,
        host=origin.host,
        protocol=origin.scheme,
        port=origin.port,
        verify_ssl=entry.data.get("verify_ssl", True),
        certificate_sha256=entry.data.get("certificate_sha256", ""),
        lan_networks=entry.data.get("lan_networks", []),
        password_configured=entry.data.get(
            "password_present", CREDENTIAL_FIELD in entry.data or bool(entry.data.get("password"))
        ),
        loaded=loaded,
        transport=provider_spec(entry.data).transport,
    )
    if provider_spec(entry.data).native_management:
        result["username"] = entry.data.get("username", "admin")
    return result


async def _test(hass, payload):
    entry = _entry(hass, payload["entry_id"]) if payload.get("entry_id") else None
    data, info = await async_validate_candidate(hass, payload, dict(entry.data) if entry else None)
    if entry and entry.unique_id and unique_id_for(data, info["device_id"]) != entry.unique_id:
        raise KVMError("wrong_device")
    return {"provider": provider_name(data), "base_url": data["base_url"], **info}


async def _probe(hass, payload):
    return await async_probe_candidate(hass, payload)


async def _save(hass, payload):
    from .console import async_disconnect_entry

    entry = _entry(hass, payload["entry_id"]) if payload.get("entry_id") else None
    if entry is None:
        if len(hass.config_entries.async_entries(DOMAIN)) >= MAX_DEVICES:
            raise KVMError("invalid_data", "Maximum configured KVM devices reached")
        # The config flow validates again, encrypts, checks the physical unique
        # ID, and creates a normal ConfigEntry. No parallel private device DB.
        normalize_candidate(payload)
        _title(payload, "KVM")
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "import"}, data=payload
        )
        if result.get("type") != "create_entry":
            reason = result.get("reason", "invalid_data")
            if reason == "already_configured":
                raise KVMError("invalid_data", "Device is already configured")
            raise KVMError(reason)
        created = result.get("result")
        return {"entry_id": created.entry_id, "title": created.title}

    title = _title(payload, entry.title)
    candidate = normalize_candidate(payload, dict(entry.data))
    if candidate == dict(entry.data):
        # Renaming an offline device does not require changing a credential.
        hass.config_entries.async_update_entry(entry, title=title)
        return {"entry_id": entry.entry_id, "title": title}
    data, info = await async_validate_candidate(hass, payload, dict(entry.data))
    if entry.unique_id and unique_id_for(data, info["device_id"]) != entry.unique_id:
        raise KVMError("wrong_device")
    protected = await async_protect_data(hass, data)
    # Never erase the old record while validating its replacement. ConfigEntry
    # updates use HA's atomic storage subsystem; sessions are closed only after
    # the update was accepted by HA.
    hass.config_entries.async_update_entry(entry, data=protected, title=title)
    await async_disconnect_entry(hass, entry.entry_id)
    await hass.config_entries.async_reload(entry.entry_id)
    return {"entry_id": entry.entry_id, "title": title, "connection": info}


async def _delete(hass, payload):
    from .console import async_disconnect_entry

    entry = _entry(hass, payload.get("entry_id"))
    await async_disconnect_entry(hass, entry.entry_id)
    result = await hass.config_entries.async_remove(entry.entry_id)
    if result is False:
        raise KVMError("protocol_error", "Home Assistant did not remove the entry")
    await (await async_state_store(hass)).remove(entry.entry_id)
    return {"entry_id": entry.entry_id, "deleted": True}


async def _disconnect(hass, payload):
    from .console import async_disconnect_entry

    entry = _entry(hass, payload.get("entry_id"))
    count = await async_disconnect_entry(hass, entry.entry_id)
    return {"entry_id": entry.entry_id, "closed_sessions": count}


async def _wol(hass, payload):
    entry = _entry(hass, payload.get("entry_id"))
    mac = str(payload.get("mac", "")).strip().replace("-", ":").upper()
    if not MAC_RE.fullmatch(mac):
        raise KVMError("invalid_data", "Invalid MAC address")
    if entry.state is ConfigEntryState.LOADED and hasattr(entry, "runtime_data"):
        await runtime_provider(entry.runtime_data).wake_on_lan(mac)
    else:
        provider = await async_make_provider(hass, dict(entry.data))
        try:
            await provider.test_connection()
            await provider.wake_on_lan(mac)
        finally:
            await provider.disconnect()
    return {"sent": True, "mac": mac}


async def _discover(hass, payload):
    from .providers.discovery import async_discover

    if payload:
        raise KVMError("invalid_data")
    return await async_discover(hass)


OPERATIONS = {
    "get": _get,
    "probe": _probe,
    "test": _test,
    "save": _save,
    "delete": _delete,
    "disconnect": _disconnect,
    "wol": _wol,
    "discover": _discover,
}


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/panel/kvm/list"})
@websocket_api.require_admin
@websocket_api.async_response
async def websocket_kvm_list(hass, connection, msg):
    from .panel_v2 import async_device_inventory

    connection.send_result(
        msg["id"], await async_device_inventory(hass, hass.config_entries.async_entries(DOMAIN))
    )


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/panel/kvm/manage",
        vol.Required("operation"): vol.In(OPERATIONS),
        vol.Optional("payload", default=dict): dict,
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def websocket_kvm_manage(hass, connection, msg):
    actor = str(connection.user.id)
    operation = msg["operation"]
    payload = msg["payload"]
    try:
        _limit(hass, actor, operation)
        slots = hass.data.setdefault("nanokvm_rest_kvm_request_slots", asyncio.Semaphore(4))
        locks = hass.data.setdefault("nanokvm_rest_kvm_edit_locks", {})
        lock_id = str(payload.get("entry_id") or "create")
        # Resolve existing IDs before allocating lock entries; arbitrary IDs
        # cannot grow the lock table without bound.
        if payload.get("entry_id"):
            _entry(hass, payload["entry_id"])
        lock = locks.setdefault(lock_id, asyncio.Lock())
        async with asyncio.timeout(30):
            async with slots, lock:
                result = await OPERATIONS[operation](hass, payload)
        if operation in {"save", "delete", "disconnect", "wol"}:
            _LOGGER.info(
                "[KVM] %s device=%s actor=%s",
                operation,
                str(result.get("entry_id", lock_id)),
                actor,
            )
        connection.send_result(msg["id"], {"ok": True, **result})
    except KVMError as err:
        connection.send_result(msg["id"], {"ok": False, "error": err.public()})
    except TimeoutError:
        connection.send_result(msg["id"], {"ok": False, "error": KVMError("timeout").public()})
    except (ValueError, KeyError, TypeError):
        connection.send_result(msg["id"], {"ok": False, "error": KVMError("invalid_data").public()})
    except (OSError, HomeAssistantError):
        connection.send_result(
            msg["id"],
            {
                "ok": False,
                "error": KVMError(
                    "protocol_error", "Home Assistant could not complete the operation"
                ).public(),
            },
        )


KVM_COMMANDS = (websocket_kvm_list, websocket_kvm_manage)
