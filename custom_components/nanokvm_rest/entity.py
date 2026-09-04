"""Base entities for NanoKVM REST."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DEFAULT_NAME, DOMAIN
from .coordinator import NanoKVMCoordinator


class NanoKVMEntity(CoordinatorEntity[NanoKVMCoordinator]):
    """Base NanoKVM entity."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: NanoKVMCoordinator) -> None:
        super().__init__(coordinator)
        info = coordinator.data.get("info", {})
        hostname = coordinator.data.get("hostname", {}).get("hostname")
        device_key = info.get("deviceKey") or coordinator.client.base_url
        self._device_key = str(device_key)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._device_key)},
            name=f"{DEFAULT_NAME} {hostname}" if hostname else DEFAULT_NAME,
            manufacturer="Sipeed",
            model=f"NanoKVM {coordinator.data.get('hardware', {}).get('version', '')}".strip(),
            sw_version=str(info.get("application") or "") or None,
            configuration_url=coordinator.client.base_url,
        )
