"""Persistent settings and metrics for the NanoKVM Operations Center."""

from __future__ import annotations

import asyncio
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

STORAGE_VERSION = 1
STORAGE_KEY = "nanokvm_rest.operations"
MAX_SAMPLES = 2200
SAMPLE_INTERVAL_SECONDS = 300
MAX_NOTE_LENGTH = 256


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime | None = None) -> str:
    return (value or _utcnow()).isoformat()


def _parse_time(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        result = datetime.fromisoformat(str(value))
    except ValueError:
        return None
    if result.tzinfo is None:
        result = result.replace(tzinfo=timezone.utc)
    return result.astimezone(timezone.utc)


def _default_device() -> dict[str, Any]:
    return {
        "maintenance": {
            "enabled": False,
            "until": "",
            "note": "",
            "actor": "",
            "started_at": "",
        },
        "auto_recovery": {
            "enabled": False,
            "hdmi_reset": True,
            "cooldown_seconds": 900,
            "max_attempts_per_hour": 3,
            "notify": True,
        },
        "samples": [],
        "alert_acks": {},
    }


class OperationsStore:
    """Persist Operations Center settings and compact seven-day metrics."""

    def __init__(self, hass: HomeAssistant) -> None:
        self._store: Store[dict[str, Any]] = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self._data: dict[str, Any] = {"devices": {}}
        self._lock = asyncio.Lock()

    async def async_load(self) -> None:
        loaded = await self._store.async_load()
        if isinstance(loaded, dict) and isinstance(loaded.get("devices"), dict):
            self._data = {"devices": loaded["devices"]}

    def _device(self, entry_id: str) -> dict[str, Any]:
        devices = self._data.setdefault("devices", {})
        raw = devices.get(entry_id)
        if not isinstance(raw, dict):
            raw = _default_device()
            devices[entry_id] = raw
        defaults = _default_device()
        for key, value in defaults.items():
            if key not in raw or not isinstance(raw[key], type(value)):
                raw[key] = deepcopy(value)
        for key, value in defaults["maintenance"].items():
            raw["maintenance"].setdefault(key, value)
        for key, value in defaults["auto_recovery"].items():
            raw["auto_recovery"].setdefault(key, value)
        return raw

    def settings(self, entry_id: str) -> dict[str, Any]:
        raw = self._device(entry_id)
        maintenance = deepcopy(raw["maintenance"])
        until = _parse_time(maintenance.get("until"))
        if maintenance.get("enabled") and until and until <= _utcnow():
            maintenance["enabled"] = False
        recovery = deepcopy(raw["auto_recovery"])
        return {"maintenance": maintenance, "auto_recovery": recovery}

    def maintenance_active(self, entry_id: str) -> bool:
        return bool(self.settings(entry_id)["maintenance"].get("enabled"))

    async def async_set_maintenance(
        self,
        entry_id: str,
        *,
        enabled: bool,
        minutes: int = 0,
        note: str = "",
        actor: str = "",
    ) -> dict[str, Any]:
        minutes = max(0, min(int(minutes), 7 * 24 * 60))
        async with self._lock:
            raw = self._device(entry_id)
            current = raw["maintenance"]
            current.update(
                {
                    "enabled": bool(enabled),
                    "until": _iso(_utcnow() + timedelta(minutes=minutes))
                    if enabled and minutes
                    else "",
                    "note": str(note or "").strip()[:MAX_NOTE_LENGTH] if enabled else "",
                    "actor": str(actor or "").strip()[:128] if enabled else "",
                    "started_at": _iso() if enabled else "",
                }
            )
            await self._store.async_save(self._data)
            return deepcopy(current)

    async def async_expire_maintenance(self, entry_id: str) -> bool:
        async with self._lock:
            raw = self._device(entry_id)
            current = raw["maintenance"]
            until = _parse_time(current.get("until"))
            if not current.get("enabled") or until is None or until > _utcnow():
                return False
            current.update({"enabled": False, "until": "", "note": "", "actor": ""})
            await self._store.async_save(self._data)
            return True

    async def async_set_auto_recovery(
        self,
        entry_id: str,
        *,
        enabled: bool,
        hdmi_reset: bool,
        cooldown_seconds: int,
        max_attempts_per_hour: int,
        notify: bool,
    ) -> dict[str, Any]:
        async with self._lock:
            raw = self._device(entry_id)
            current = raw["auto_recovery"]
            current.update(
                {
                    "enabled": bool(enabled),
                    "hdmi_reset": bool(hdmi_reset),
                    "cooldown_seconds": max(300, min(int(cooldown_seconds), 86400)),
                    "max_attempts_per_hour": max(1, min(int(max_attempts_per_hour), 12)),
                    "notify": bool(notify),
                }
            )
            await self._store.async_save(self._data)
            return deepcopy(current)

    async def async_record_sample(self, entry_id: str, sample: dict[str, Any]) -> bool:
        async with self._lock:
            raw = self._device(entry_id)
            samples = raw.setdefault("samples", [])
            now = _utcnow()
            if samples:
                last = _parse_time(samples[-1].get("timestamp")) if isinstance(samples[-1], dict) else None
                if last and (now - last).total_seconds() < SAMPLE_INTERVAL_SECONDS:
                    return False
            record = {
                "timestamp": _iso(now),
                "available": bool(sample.get("available")),
                "latency_ms": round(float(sample["latency_ms"]), 1)
                if isinstance(sample.get("latency_ms"), (int, float))
                else None,
                "power": sample.get("power") if isinstance(sample.get("power"), bool) else None,
                "hdmi_signal": sample.get("hdmi_signal")
                if isinstance(sample.get("hdmi_signal"), bool)
                else None,
                "health_score": max(0, min(100, int(sample.get("health_score", 0)))),
            }
            samples.append(record)
            if len(samples) > MAX_SAMPLES:
                del samples[:-MAX_SAMPLES]
            await self._store.async_save(self._data)
            return True

    def metrics(self, entry_id: str) -> dict[str, Any]:
        samples = [item for item in self._device(entry_id).get("samples", []) if isinstance(item, dict)]
        now = _utcnow()

        def window(hours: int) -> list[dict[str, Any]]:
            cutoff = now - timedelta(hours=hours)
            return [item for item in samples if (_parse_time(item.get("timestamp")) or now) >= cutoff]

        def availability(items: list[dict[str, Any]]) -> float | None:
            if not items:
                return None
            return round(sum(1 for item in items if item.get("available")) * 100.0 / len(items), 2)

        last24 = window(24)
        last7d = window(24 * 7)
        latencies = [
            float(item["latency_ms"])
            for item in last24
            if isinstance(item.get("latency_ms"), (int, float))
        ]
        return {
            "availability_24h": availability(last24),
            "availability_7d": availability(last7d),
            "latency_avg_24h": round(sum(latencies) / len(latencies), 1) if latencies else None,
            "latency_max_24h": round(max(latencies), 1) if latencies else None,
            "sample_count_24h": len(last24),
            "sample_count_7d": len(last7d),
            "samples": deepcopy(samples[-288:]),
        }

    def is_alert_acknowledged(self, entry_id: str, alert_id: str) -> bool:
        acks = self._device(entry_id).get("alert_acks", {})
        return bool(isinstance(acks, dict) and acks.get(alert_id))

    async def async_ack_alert(self, entry_id: str, alert_id: str, actor: str) -> None:
        async with self._lock:
            raw = self._device(entry_id)
            acks = raw.setdefault("alert_acks", {})
            acks[str(alert_id)[:160]] = {"timestamp": _iso(), "actor": str(actor or "")[:128]}
            if len(acks) > 100:
                for key in list(acks)[:-100]:
                    acks.pop(key, None)
            await self._store.async_save(self._data)

    async def async_clear_resolved_acks(self, entry_id: str, active_ids: set[str]) -> None:
        async with self._lock:
            raw = self._device(entry_id)
            acks = raw.setdefault("alert_acks", {})
            changed = False
            for key in list(acks):
                if key not in active_ids:
                    acks.pop(key, None)
                    changed = True
            if changed:
                await self._store.async_save(self._data)
