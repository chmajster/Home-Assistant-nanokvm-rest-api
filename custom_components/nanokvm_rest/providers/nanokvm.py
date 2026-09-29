"""Adapter preserving the existing NanoKVM client and streaming protocol."""

from __future__ import annotations

import asyncio
from time import perf_counter

from .base import KVMProvider, capabilities
from .errors import KVMError


class NanoKVMProvider(KVMProvider):
    provider_type = "nanokvm"
    label = "NanoKVM"
    transport = "h264-websocket"

    def get_capabilities(self) -> dict[str, bool]:
        data = (self.coordinator.data or {}) if self.coordinator is not None else {}
        admin = bool((data.get("capabilities") or {}).get("admin"))
        return capabilities(
            video=True,
            keyboard=True,
            mouse=True,
            absolute_mouse=True,
            atx=bool(data.get("gpio")),
            wol=True,
            virtual_media=admin,
            clipboard=admin,
            native_management=True,
        )

    def get_status(self) -> dict:
        coordinator = self.coordinator
        if coordinator is None:
            raise KVMError("session_required")
        data = coordinator.data or {}
        gpio = data.get("gpio") or {}
        hdmi = data.get("hdmi")
        info = data.get("info") or {}
        hostname = data.get("hostname") or {}
        hardware = data.get("hardware") or {}
        version = data.get("application_version") or {}
        detected = data.get("capabilities") or {}
        measured = (
            coordinator.hass.data.get("nanokvm_rest_operations_runtime", {})
            .get("devices", {})
            .get(coordinator.config_entry.entry_id, {})
        )
        return {
            **(
                {"last_latency_ms": measured["latency_ms"]}
                if measured.get("latency_ms") is not None
                else {}
            ),
            **(
                {"last_seen_at": measured["last_successful_probe"]}
                if measured.get("last_successful_probe")
                else {}
            ),
            "provider": self.provider_type,
            "transport": self.transport,
            "capabilities": self.get_capabilities(),
            "available": coordinator.last_update_success,
            "device_key": str(info.get("deviceKey") or coordinator.client.base_url),
            "hostname": str(hostname.get("hostname") or coordinator.config_entry.title),
            "hardware": str(hardware.get("version") or ""),
            "power": bool(gpio.get("pwr")) if "pwr" in gpio else None,
            "hdd": bool(gpio.get("hdd")) if "hdd" in gpio else None,
            "hdmi_signal": bool(hdmi.get("signal"))
            if isinstance(hdmi, dict) and "signal" in hdmi
            else None,
            "admin": bool(detected.get("admin")),
            "pcie": bool(detected.get("pcie")),
            "application_version": str(
                version.get("current") or version.get("version") or version.get("installed") or ""
            ),
        }

    async def test_connection(self) -> dict:
        start = perf_counter()
        await self.client.async_login()
        info = await self.client.async_get_info()
        return {
            "device_id": str(info.get("deviceKey") or self.client.base_url),
            "latency_ms": round((perf_counter() - start) * 1000, 2),
            "base_url": self.client.base_url,
        }

    async def wake_on_lan(self, mac: str) -> None:
        await self.client.async_wake_on_lan(mac)

    async def send_atx_command(self, command: str) -> None:
        commands = {
            "power-short": ("power", 800),
            "power-long": ("power", 5000),
            "reset": ("reset", 800),
        }
        if command not in commands:
            raise KVMError("unsupported")
        await self.client.async_press_button(*commands[command])

    async def open_kvm_session(self):
        # Keep the proven NanoKVM bridge, H264 framing and HID transport intact.
        from ..console import _open_upstream_ws

        stream = await _open_upstream_ws(
            self.coordinator,
            "/api/stream/h264/direct",
            params={"flow": "8"},
            max_msg_size=4 * 1024 * 1024,
        )
        try:
            inputs = await _open_upstream_ws(self.coordinator, "/api/ws", max_msg_size=65536)
        except BaseException:
            await stream.close()
            raise
        return stream, inputs

    async def close_kvm_session(self, session) -> None:
        async def close(ws):
            try:
                async with asyncio.timeout(3):
                    await ws.close()
            except TimeoutError:
                pass

        await asyncio.gather(*(close(ws) for ws in session))

    async def disconnect(self) -> None:
        # The HTTP session belongs to HA. Console sockets are closed by the
        # common session lifecycle; never close HA's shared HTTP connector.
        return None
