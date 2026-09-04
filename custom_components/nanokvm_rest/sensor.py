"""Diagnostic sensors for NanoKVM REST."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import NanoKVMCoordinator
from .entity import NanoKVMEntity


SENSORS: tuple[tuple[str, str, str, Callable[[dict[str, Any]], Any]], ...] = (
    ("Hostname", "hostname", "mdi:server", lambda d: d.get("hostname", {}).get("hostname")),
    ("Hardware", "hardware", "mdi:chip", lambda d: d.get("hardware", {}).get("version")),
    ("Application", "application", "mdi:package-variant", lambda d: d.get("info", {}).get("application")),
    ("System image", "image", "mdi:memory", lambda d: d.get("info", {}).get("image")),
    (
        "IP address",
        "ip_address",
        "mdi:ip-network",
        lambda d: next((item.get("addr") for item in d.get("info", {}).get("ips", []) if item.get("addr")), None),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator: NanoKVMCoordinator = entry.runtime_data
    async_add_entities(
        NanoKVMSensor(coordinator, name, key, icon, value_fn)
        for name, key, icon, value_fn in SENSORS
    )


class NanoKVMSensor(NanoKVMEntity, SensorEntity):
    """NanoKVM diagnostic sensor."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator: NanoKVMCoordinator,
        name: str,
        key: str,
        icon: str,
        value_fn: Callable[[dict[str, Any]], Any],
    ) -> None:
        super().__init__(coordinator)
        self._attr_name = name
        self._attr_icon = icon
        self._attr_unique_id = f"{self._device_key}_{key}"
        self._value_fn = value_fn

    @property
    def native_value(self) -> Any:
        return self._value_fn(self.coordinator.data)
