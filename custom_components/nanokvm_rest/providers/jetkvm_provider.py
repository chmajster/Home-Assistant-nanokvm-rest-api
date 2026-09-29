"""JetKVM adapter: local HTTP health plus authenticated WebRTC signaling."""

from __future__ import annotations

from .base import KVMProvider, capabilities


class JetKVMProvider(KVMProvider):
    provider_type = "jetkvm"
    label = "JetKVM"
    transport = "webrtc"

    def get_capabilities(self) -> dict[str, bool]:
        # ATX is only exposed by the live session after getActiveExtension
        # confirms atx-power. WOL is a real authenticated HTTP endpoint.
        return capabilities(
            video=True,
            keyboard=True,
            mouse=True,
            absolute_mouse=True,
            relative_mouse=True,
            wol=True,
        )

    def get_status(self) -> dict:
        data = self.coordinator.data if self.coordinator is not None else {}
        return {
            **(data or {}),
            **(
                {"firmware_version": self.client.firmware_version}
                if getattr(self.client, "firmware_version", None)
                else {}
            ),
            "provider": self.provider_type,
            "transport": self.transport,
            "capabilities": self.get_capabilities(),
            "admin": False,
            "pcie": False,
        }

    async def test_connection(self) -> dict:
        return await self.client.test_connection()

    async def wake_on_lan(self, mac: str) -> None:
        await self.client.wake_on_lan(mac)

    async def open_kvm_session(self):
        return await self.client.open_signaling()

    async def close_kvm_session(self, session) -> None:
        await self.client.close_signaling(session)

    async def disconnect(self) -> None:
        await self.client.close()
