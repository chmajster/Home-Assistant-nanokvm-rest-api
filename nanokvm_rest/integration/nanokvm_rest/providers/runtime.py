"""Provider lifecycle factories; NanoKVM entities retain their existing code."""

from __future__ import annotations

from .configuration import async_make_provider
from .registry import provider_name


async def _nano_coordinator(hass, entry, provider):
    from ..const import CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
    from ..coordinator import NanoKVMCoordinator

    return NanoKVMCoordinator(
        hass,
        entry,
        provider.client,
        int(entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)),
    )


async def _jet_coordinator(hass, entry, provider):
    from .coordinator import JetKVMCoordinator
    from .state import async_state_store

    return JetKVMCoordinator(hass, entry, provider.client, await async_state_store(hass))


COORDINATOR_FACTORIES = {"nanokvm": _nano_coordinator, "jetkvm": _jet_coordinator}


async def async_create_coordinator(hass, entry):
    provider = await async_make_provider(hass, entry.data)
    try:
        coordinator = await COORDINATOR_FACTORIES[provider_name(entry.data)](hass, entry, provider)
        coordinator.kvm_provider = provider
        provider.coordinator = coordinator
        return coordinator
    except BaseException:
        await provider.disconnect()
        raise
