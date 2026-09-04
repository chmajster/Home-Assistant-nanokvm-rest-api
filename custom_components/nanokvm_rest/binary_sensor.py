"""Binary sensors for NanoKVM REST."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import NanoKVMCoordinator
from .entity import NanoKVMEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up NanoKVM binary sensors."""
    coordinator: NanoKVMCoordinator = entry.runtime_data
    entities: list[BinarySensorEntity] = [NanoKVMPowerSensor(coordinator)]
    if "hdd" in coordinator.data.get("gpio", {}):
        entities.append(NanoKVMHDDSensor(coordinator))
    async_add_entities(entities)


class NanoKVMPowerSensor(NanoKVMEntity, BinarySensorEntity):
    """Power LED state."""

    _attr_name = "Power"
    _attr_icon = "mdi:power"

    def __init__(self, coordinator: NanoKVMCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device_key}_power"

    @property
    def is_on(self) -> bool:
        """Return target power state."""
        return bool(self.coordinator.data.get("gpio", {}).get("pwr"))


class NanoKVMHDDSensor(NanoKVMEntity, BinarySensorEntity):
    """HDD LED state where supported."""

    _attr_name = "HDD activity"
    _attr_icon = "mdi:harddisk"

    def __init__(self, coordinator: NanoKVMCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device_key}_hdd"

    @property
    def is_on(self) -> bool:
        """Return HDD activity state."""
        return bool(self.coordinator.data.get("gpio", {}).get("hdd"))
