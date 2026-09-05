"""Persistent Remote Server metadata and event history."""

from __future__ import annotations

import asyncio
from copy import deepcopy
from datetime import datetime, timezone
import re
from typing import Any
from uuid import uuid4

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

STORAGE_VERSION = 1
STORAGE_KEY = "nanokvm_rest.remote_server"
MAX_EVENTS = 500
MAX_TAGS = 20
MAX_TAG_LENGTH = 32
MAX_GROUP_LENGTH = 64
MAX_PROFILE_NAME_LENGTH = 64
_MAC_RE = re.compile(r"^(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}$")


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _default_data() -> dict[str, Any]:
    return {"devices": {}, "events": [], "last_state": {}}


def _clean_text(value: Any, maximum: int) -> str:
    return str(value or "").strip()[:maximum]


def _clean_tags(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    result: list[str] = []
    seen: set[str] = set()
    for raw in values:
        value = _clean_text(raw, MAX_TAG_LENGTH)
        key = value.casefold()
        if not value or key in seen:
            continue
        seen.add(key)
        result.append(value)
        if len(result) >= MAX_TAGS:
            break
    return result


class RemoteServerStore:
    """Store Remote Server metadata in Home Assistant .storage."""

    def __init__(self, hass: HomeAssistant) -> None:
        self._store: Store[dict[str, Any]] = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self._data: dict[str, Any] = _default_data()
        self._lock = asyncio.Lock()

    async def async_load(self) -> None:
        """Load and sanitize persisted data."""
        loaded = await self._store.async_load()
        if not isinstance(loaded, dict):
            return
        devices = loaded.get("devices")
        events = loaded.get("events")
        last_state = loaded.get("last_state")
        self._data = {
            "devices": devices if isinstance(devices, dict) else {},
            "events": events[-MAX_EVENTS:] if isinstance(events, list) else [],
            "last_state": last_state if isinstance(last_state, dict) else {},
        }

    def metadata(self, entry_id: str, *, include_profiles: bool = True) -> dict[str, Any]:
        """Return normalized metadata for one config entry."""
        raw = self._data["devices"].get(entry_id)
        if not isinstance(raw, dict):
            raw = {}
        result = {
            "favorite": bool(raw.get("favorite", False)),
            "group": _clean_text(raw.get("group"), MAX_GROUP_LENGTH),
            "tags": _clean_tags(raw.get("tags")),
            "last_used": _clean_text(raw.get("last_used"), 64),
        }
        profiles = raw.get("wol_profiles")
        if not isinstance(profiles, list):
            profiles = []
        normalized_profiles = []
        for profile in profiles:
            if not isinstance(profile, dict):
                continue
            profile_id = _clean_text(profile.get("id"), 64)
            name = _clean_text(profile.get("name"), MAX_PROFILE_NAME_LENGTH)
            mac = _clean_text(profile.get("mac"), 32)
            if profile_id and name and _MAC_RE.fullmatch(mac):
                normalized_profiles.append({"id": profile_id, "name": name, "mac": mac.upper().replace("-", ":")})
        if include_profiles:
            result["wol_profiles"] = normalized_profiles
        else:
            result["wol_count"] = len(normalized_profiles)
        return result

    async def async_update_metadata(self, entry_id: str, patch: dict[str, Any]) -> dict[str, Any]:
        """Update favorite/group/tags for one entry."""
        async with self._lock:
            current = self.metadata(entry_id)
            if "favorite" in patch:
                current["favorite"] = bool(patch["favorite"])
            if "group" in patch:
                current["group"] = _clean_text(patch["group"], MAX_GROUP_LENGTH)
            if "tags" in patch:
                current["tags"] = _clean_tags(patch["tags"])
            self._data["devices"][entry_id] = current
            await self._store.async_save(self._data)
            return deepcopy(current)

    async def async_touch(self, entry_id: str) -> None:
        """Mark an entry as recently used."""
        async with self._lock:
            current = self.metadata(entry_id)
            current["last_used"] = _utcnow()
            self._data["devices"][entry_id] = current
            await self._store.async_save(self._data)

    async def async_save_wol_profile(
        self, entry_id: str, name: str, mac: str, profile_id: str = ""
    ) -> dict[str, str]:
        """Create or update a Wake-on-LAN profile."""
        name = _clean_text(name, MAX_PROFILE_NAME_LENGTH)
        mac = _clean_text(mac, 32).upper().replace("-", ":")
        if not name:
            raise ValueError("profile name is required")
        if not _MAC_RE.fullmatch(mac):
            raise ValueError("invalid MAC address")
        async with self._lock:
            current = self.metadata(entry_id)
            profiles = list(current.get("wol_profiles") or [])
            profile_id = _clean_text(profile_id, 64) or uuid4().hex[:12]
            profile = {"id": profile_id, "name": name, "mac": mac}
            replaced = False
            for index, item in enumerate(profiles):
                if item.get("id") == profile_id:
                    profiles[index] = profile
                    replaced = True
                    break
            if not replaced:
                profiles.append(profile)
            current["wol_profiles"] = profiles[:50]
            self._data["devices"][entry_id] = current
            await self._store.async_save(self._data)
            return profile

    async def async_delete_wol_profile(self, entry_id: str, profile_id: str) -> None:
        """Delete a Wake-on-LAN profile."""
        async with self._lock:
            current = self.metadata(entry_id)
            profiles = [
                profile
                for profile in current.get("wol_profiles") or []
                if profile.get("id") != profile_id
            ]
            current["wol_profiles"] = profiles
            self._data["devices"][entry_id] = current
            await self._store.async_save(self._data)

    def wol_profile(self, entry_id: str, profile_id: str) -> dict[str, str] | None:
        """Return one Wake-on-LAN profile."""
        for profile in self.metadata(entry_id).get("wol_profiles") or []:
            if profile.get("id") == profile_id:
                return deepcopy(profile)
        return None

    def events(self, entry_id: str = "", limit: int = 100) -> list[dict[str, Any]]:
        """Return newest events, optionally for one entry."""
        source = self._data.get("events") or []
        result = [
            event
            for event in source
            if isinstance(event, dict) and (not entry_id or event.get("entry_id") == entry_id)
        ]
        return deepcopy(result[-max(1, min(limit, 200)):][::-1])

    async def async_add_event(
        self,
        entry_id: str,
        event: str,
        *,
        actor: str = "system",
        result: str = "success",
        details: dict[str, Any] | None = None,
    ) -> None:
        """Append one audit/event-history item."""
        async with self._lock:
            self._append_event_locked(entry_id, event, actor, result, details)
            await self._store.async_save(self._data)

    def _append_event_locked(
        self,
        entry_id: str,
        event: str,
        actor: str,
        result: str,
        details: dict[str, Any] | None,
    ) -> None:
        record = {
            "id": uuid4().hex[:16],
            "timestamp": _utcnow(),
            "entry_id": entry_id,
            "event": _clean_text(event, 64),
            "actor": _clean_text(actor, 128) or "system",
            "result": "error" if result == "error" else "success",
            "details": details if isinstance(details, dict) else {},
        }
        events = self._data.setdefault("events", [])
        events.append(record)
        if len(events) > MAX_EVENTS:
            del events[:-MAX_EVENTS]

    async def async_observe_state(self, entry_id: str, state: dict[str, Any]) -> None:
        """Record availability/power/HDMI transitions without log spam."""
        observed = {
            "available": state.get("available"),
            "power": state.get("power"),
            "hdmi_signal": state.get("hdmi_signal"),
        }
        async with self._lock:
            previous = self._data["last_state"].get(entry_id)
            self._data["last_state"][entry_id] = observed
            if not isinstance(previous, dict):
                await self._store.async_save(self._data)
                return
            changed = False
            labels = {
                "available": ("kvm_online", "kvm_offline"),
                "power": ("host_power_on", "host_power_off"),
                "hdmi_signal": ("hdmi_signal_on", "hdmi_signal_off"),
            }
            for key, (on_event, off_event) in labels.items():
                old = previous.get(key)
                new = observed.get(key)
                if old is None or new is None or old == new:
                    continue
                self._append_event_locked(
                    entry_id,
                    on_event if new else off_event,
                    "system",
                    "success",
                    {"from": old, "to": new},
                )
                changed = True
            if changed:
                await self._store.async_save(self._data)
