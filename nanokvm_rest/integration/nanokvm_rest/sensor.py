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


SensorDefinition = tuple[
    str,
    str,
    str,
    Callable[[dict[str, Any]], Any],
    str | None,
]

BASE_SENSORS: tuple[SensorDefinition, ...] = (
    (
        "Hostname",
        "hostname",
        "mdi:server",
        lambda d: d.get("hostname", {}).get("hostname"),
        None,
    ),
    (
        "Hardware",
        "hardware",
        "mdi:chip",
        lambda d: d.get("hardware", {}).get("version"),
        None,
    ),
    (
        "Application",
        "application",
        "mdi:package-variant",
        lambda d: d.get("info", {}).get("application"),
        None,
    ),
    (
        "System image",
        "image",
        "mdi:memory",
        lambda d: d.get("info", {}).get("image"),
        None,
    ),
    (
        "IP address",
        "ip_address",
        "mdi:ip-network",
        lambda d: next(
            (
                item.get("addr")
                for item in d.get("info", {}).get("ips", [])
                if item.get("addr")
            ),
            None,
        ),
        None,
    ),
    (
        "mDNS address",
        "mdns_address",
        "mdi:lan",
        lambda d: d.get("info", {}).get("mdns"),
        None,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up NanoKVM diagnostic sensors."""
    coordinator: NanoKVMCoordinator = entry.runtime_data
    definitions = list(BASE_SENSORS)

    if coordinator.data.get("account") is not None:
        definitions.append(
            (
                "Account role",
                "account_role",
                "mdi:account-key",
                lambda d: (d.get("account") or {}).get("role"),
                None,
            )
        )

    if coordinator.data.get("web_title") is not None:
        definitions.append(
            (
                "Web title",
                "web_title",
                "mdi:web",
                lambda d: (d.get("web_title") or {}).get("title"),
                None,
            )
        )

    if coordinator.data.get("mouse_jiggler") is not None:
        definitions.append(
            (
                "Mouse jiggler mode",
                "mouse_jiggler_mode",
                "mdi:mouse-move-down",
                lambda d: (d.get("mouse_jiggler") or {}).get("mode"),
                None,
            )
        )

    if coordinator.data.get("swap") is not None:
        definitions.append(
            (
                "Swap size",
                "swap_size",
                "mdi:memory",
                lambda d: (d.get("swap") or {}).get("size"),
                "MB",
            )
        )

    async_add_entities(
        NanoKVMSensor(coordinator, name, key, icon, value_fn, unit)
        for name, key, icon, value_fn, unit in definitions
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
        unit: str | None,
    ) -> None:
        super().__init__(coordinator)
        self._attr_name = name
        self._attr_icon = icon
        self._attr_unique_id = f"{self._device_key}_{key}"
        self._attr_native_unit_of_measurement = unit
        self._value_fn = value_fn

    @property
    def native_value(self) -> Any:
        """Return the current sensor value."""
        return self._value_fn(self.coordinator.data)
