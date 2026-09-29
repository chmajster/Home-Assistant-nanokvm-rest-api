"""Single provider selection point for config entries, APIs and consoles."""

from __future__ import annotations

from dataclasses import dataclass

from .errors import KVMError
from .jetkvm_provider import JetKVMProvider
from .nanokvm import NanoKVMProvider


@dataclass(frozen=True)
class ProviderSpec:
    adapter: type
    native_management: bool
    platforms: bool

    @property
    def label(self) -> str:
        return self.adapter.label

    @property
    def transport(self) -> str:
        return self.adapter.transport


PROVIDERS = {
    "nanokvm": ProviderSpec(NanoKVMProvider, native_management=True, platforms=True),
    "jetkvm": ProviderSpec(JetKVMProvider, native_management=False, platforms=False),
}


def provider_name(data: dict) -> str:
    name = data.get("provider", "nanokvm")
    if not isinstance(name, str) or name not in PROVIDERS:
        raise KVMError("unknown_provider")
    return name


def provider_spec(data: dict) -> ProviderSpec:
    return PROVIDERS[provider_name(data)]


def runtime_provider(coordinator):
    """Legacy entries and already loaded runtimes default safely to NanoKVM."""
    provider = getattr(coordinator, "kvm_provider", None)
    if provider is None:
        provider = provider_spec(coordinator.config_entry.data).adapter(
            coordinator.client, coordinator
        )
        coordinator.kvm_provider = provider
    return provider


def native_entries(hass):
    """Keep Nano-only update/recovery/media services away from other providers."""
    return [
        entry
        for entry in hass.config_entries.async_entries("nanokvm_rest")
        if provider_spec(entry.data).native_management
    ]
