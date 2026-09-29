"""JetKVM HTTP health polling; no WebRTC session is opened by monitoring."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .errors import KVMError
from .jetkvm_provider import JetKVMProvider

_LOGGER = logging.getLogger(__name__)


class JetKVMCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, entry, client, state_store):
        super().__init__(
            hass,
            logger=_LOGGER,
            config_entry=entry,
            name="JetKVM",
            update_interval=timedelta(
                seconds=max(10, min(30, int(entry.options.get("scan_interval", 20))))
            ),
        )
        self.client = client
        self.kvm_provider = JetKVMProvider(client, self)
        self.state_store = state_store
        self._state = state_store.get(entry.entry_id)
        self._state.update(available=False, connection_state="DISCONNECTED", last_error=None)
        self._poll_slots = hass.data.setdefault(
            "nanokvm_rest_jetkvm_poll_slots", asyncio.Semaphore(4)
        )

    async def _async_update_data(self):
        async with self._poll_slots:
            try:
                # Bound the whole status + optional auth + identity transaction,
                # not just each individual HTTP request.
                async with asyncio.timeout(12):
                    result = await self.kvm_provider.test_connection()
                expected = self.config_entry.unique_id
                if expected and expected != "jetkvm:" + result["device_id"]:
                    raise KVMError("wrong_device")
            except (KVMError, TimeoutError) as err:
                problem = err if isinstance(err, KVMError) else KVMError("timeout")
                self._state.update(
                    available=False, connection_state="ERROR", last_error=problem.public()
                )
            else:
                self._state.update(
                    available=True,
                    connection_state="CONNECTED",
                    last_error=None,
                    last_seen_at=datetime.now(timezone.utc).isoformat(),
                    last_latency_ms=result["latency_ms"],
                    device_id=result["device_id"],
                    device_key=result["device_id"],
                    auth_mode=result["auth_mode"],
                )
            await self.state_store.update(self.config_entry.entry_id, self._state)
            # A configured offline device stays loaded and polls at 20 seconds;
            # its explicit available=false is not confused with a successful
            # device connection by the common inventory/console adapters.
            return dict(self._state)
