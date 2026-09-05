"""Persistent state for advanced Remote Server media features."""

from __future__ import annotations

import asyncio
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

STORAGE_VERSION = 1
STORAGE_KEY = "nanokvm_rest.remote_advanced"
MAX_RECENT = 20
MAX_MEDIA_ITEMS = 500


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _entry_template() -> dict[str, Any]:
    return {"favorites": [], "recent": [], "meta": {}}


class RemoteAdvancedStore:
    """Persist ISO favorites, recent images and known metadata."""

    def __init__(self, hass: HomeAssistant) -> None:
        self._store: Store[dict[str, Any]] = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self._data: dict[str, Any] = {"media": {}}
        self._lock = asyncio.Lock()

    async def async_load(self) -> None:
        loaded = await self._store.async_load()
        if isinstance(loaded, dict) and isinstance(loaded.get("media"), dict):
            self._data = {"media": loaded["media"]}

    def _entry(self, entry_id: str) -> dict[str, Any]:
        raw = self._data.setdefault("media", {}).get(entry_id)
        if not isinstance(raw, dict):
            raw = _entry_template()
            self._data["media"][entry_id] = raw
        raw.setdefault("favorites", [])
        raw.setdefault("recent", [])
        raw.setdefault("meta", {})
        return raw

    def library(
        self,
        entry_id: str,
        files: list[str],
        mounted: str = "",
    ) -> list[dict[str, Any]]:
        """Merge NanoKVM file list with locally-known metadata."""
        entry = self._entry(entry_id)
        favorites = {str(item) for item in entry.get("favorites") or []}
        recent = [str(item) for item in entry.get("recent") or []]
        meta = entry.get("meta") if isinstance(entry.get("meta"), dict) else {}
        result: list[dict[str, Any]] = []
        for path in files:
            path = str(path)
            item_meta = meta.get(path) if isinstance(meta.get(path), dict) else {}
            suffix = Path(path).suffix.lower().lstrip(".") or "file"
            result.append(
                {
                    "path": path,
                    "name": Path(path).name,
                    "type": suffix.upper(),
                    "size": item_meta.get("size"),
                    "added_at": str(item_meta.get("added_at") or ""),
                    "source": str(item_meta.get("source") or "device"),
                    "source_url": str(item_meta.get("source_url") or ""),
                    "favorite": path in favorites,
                    "mounted": path == mounted,
                    "recent_rank": recent.index(path) if path in recent else None,
                }
            )
        return result

    async def async_set_favorite(self, entry_id: str, path: str, favorite: bool) -> None:
        async with self._lock:
            entry = self._entry(entry_id)
            values = [str(item) for item in entry.get("favorites") or [] if str(item) != path]
            if favorite:
                values.insert(0, path)
            entry["favorites"] = values[:MAX_MEDIA_ITEMS]
            await self._store.async_save(self._data)

    async def async_mark_used(self, entry_id: str, path: str) -> None:
        async with self._lock:
            entry = self._entry(entry_id)
            recent = [str(item) for item in entry.get("recent") or [] if str(item) != path]
            recent.insert(0, path)
            entry["recent"] = recent[:MAX_RECENT]
            await self._store.async_save(self._data)

    async def async_record_media(
        self,
        entry_id: str,
        path: str,
        *,
        size: int | None = None,
        source: str = "device",
        source_url: str = "",
    ) -> None:
        async with self._lock:
            entry = self._entry(entry_id)
            meta = entry.setdefault("meta", {})
            current = meta.get(path) if isinstance(meta.get(path), dict) else {}
            current.update(
                {
                    "size": int(size) if isinstance(size, int) and size >= 0 else current.get("size"),
                    "added_at": str(current.get("added_at") or _utcnow()),
                    "source": source,
                    "source_url": source_url,
                }
            )
            meta[path] = current
            if len(meta) > MAX_MEDIA_ITEMS:
                keep = set(list(meta)[-MAX_MEDIA_ITEMS:])
                entry["meta"] = {key: value for key, value in meta.items() if key in keep}
            await self._store.async_save(self._data)

    async def async_remove_media(self, entry_id: str, path: str) -> None:
        async with self._lock:
            entry = self._entry(entry_id)
            entry["favorites"] = [item for item in entry.get("favorites") or [] if item != path]
            entry["recent"] = [item for item in entry.get("recent") or [] if item != path]
            if isinstance(entry.get("meta"), dict):
                entry["meta"].pop(path, None)
            await self._store.async_save(self._data)

    def snapshot(self, entry_id: str) -> dict[str, Any]:
        return deepcopy(self._entry(entry_id))
