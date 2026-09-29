"""Last-measured KVM state persisted without credentials or WebRTC secrets."""

from __future__ import annotations

import asyncio
from copy import deepcopy

from homeassistant.helpers.storage import Store

PUBLIC_STATE_FIELDS = {
    "last_seen_at",
    "last_latency_ms",
    "last_error",
    "connection_state",
    "device_id",
    "auth_mode",
}


class KVMStateStore:
    def __init__(self, hass):
        self.store = Store(hass, 1, "nanokvm_rest.kvm_health")
        self.data = {}
        self.lock = asyncio.Lock()

    async def load(self):
        raw = await self.store.async_load()
        if isinstance(raw, dict):
            self.data = {
                key: {k: v for k, v in value.items() if k in PUBLIC_STATE_FIELDS}
                for key, value in raw.items()
                if isinstance(value, dict)
            }

    def get(self, entry_id):
        return deepcopy(self.data.get(entry_id, {}))

    async def update(self, entry_id, value):
        async with self.lock:
            self.data[entry_id] = {
                key: deepcopy(val) for key, val in value.items() if key in PUBLIC_STATE_FIELDS
            }
            self.store.async_delay_save(lambda: deepcopy(self.data), 5)

    async def remove(self, entry_id):
        async with self.lock:
            self.data.pop(entry_id, None)
            await self.store.async_save(self.data)


async def async_state_store(hass):
    key = "nanokvm_rest_kvm_state"
    lock = hass.data.setdefault(key + "_lock", asyncio.Lock())
    async with lock:
        if key not in hass.data:
            store = KVMStateStore(hass)
            await store.load()
            hass.data[key] = store
        return hass.data[key]
