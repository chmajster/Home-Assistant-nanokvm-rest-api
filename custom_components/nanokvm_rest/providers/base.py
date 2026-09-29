"""Common KVM operations; device-specific transports implement real work."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from .errors import KVMError

CAPABILITIES = (
    "video",
    "keyboard",
    "mouse",
    "absolute_mouse",
    "relative_mouse",
    "atx",
    "wol",
    "virtual_media",
    "serial",
    "audio",
    "clipboard",
    "native_management",
)


def capabilities(**supported: bool) -> dict[str, bool]:
    return {key: bool(supported.get(key, False)) for key in CAPABILITIES}


class KVMProvider(ABC):
    """Backend half of a provider; live input is carried by its KVMSession.

    JetKVM's keyboard/mouse/ATX RPCs belong to the browser's authenticated
    WebRTC session, not to an invented HTTP endpoint. Its frontend session
    implements sendKeyboard/sendMouse/sendATX with acknowledged JSON-RPC.
    """

    provider_type: str
    label: str
    transport: str

    def __init__(self, client: Any, coordinator: Any = None):
        self.client = client
        self.coordinator = coordinator

    @abstractmethod
    def get_capabilities(self) -> dict[str, bool]:
        """Return supported AND implemented features."""

    @abstractmethod
    def get_status(self) -> dict:
        """Return the latest measured state; never fabricate telemetry."""

    @abstractmethod
    async def test_connection(self) -> dict:
        """Perform an actual authenticated device request."""

    async def connect(self) -> dict:
        return await self.test_connection()

    async def get_device_info(self) -> dict:
        return await self.test_connection()

    def get_video_capabilities(self) -> dict:
        return {"transport": self.transport, "codecs": ["H264"]}

    @abstractmethod
    async def wake_on_lan(self, mac: str) -> None:
        """Send a real WOL request."""

    async def send_atx_command(self, command: str) -> None:
        raise KVMError("session_required")

    async def open_kvm_session(self):
        raise KVMError("unsupported")

    async def close_kvm_session(self, session) -> None:
        raise KVMError("unsupported")

    @abstractmethod
    async def disconnect(self) -> None:
        """Release resources owned by this provider, not another device."""
