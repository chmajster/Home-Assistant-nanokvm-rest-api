"""Number entities for NanoKVM REST."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import MAX_HDMI_IDLE_TIMEOUT, MIN_HDMI_IDLE_TIMEOUT
from .coordinator import NanoKVMCoordinator
from .entity import NanoKVMEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up NanoKVM number entities."""
    coordinator: NanoKVMCoordinator = entry.runtime_data
    capabilities = coordinator.data.get("capabilities", {})
    hdmi = coordinator.data.get("hdmi")

    if (
        capabilities.get("admin")
        and capabilities.get("pcie")
        and isinstance(hdmi, dict)
        and "idleTimeout" in hdmi
    ):
        async_add_entities([NanoKVMHDMIIdleTimeoutNumber(coordinator)])


class NanoKVMHDMIIdleTimeoutNumber(NanoKVMEntity, NumberEntity):
    """Configure the HDMI idle timeout on PCIe NanoKVM hardware."""

    _attr_name = "HDMI idle timeout"
    _attr_icon = "mdi:timer-cog-outline"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_native_min_value = MIN_HDMI_IDLE_TIMEOUT
    _attr_native_max_value = MAX_HDMI_IDLE_TIMEOUT
    _attr_native_step = 1
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES

    def __init__(self, coordinator: NanoKVMCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device_key}_hdmi_idle_timeout"

    @property
    def native_value(self) -> float | None:
        """Return the configured HDMI idle timeout."""
        value = (self.coordinator.data.get("hdmi") or {}).get("idleTimeout")
        return float(value) if isinstance(value, (int, float)) else None

    async def async_set_native_value(self, value: float) -> None:
        """Set the HDMI idle timeout."""
        await self.coordinator.client.async_set_hdmi_idle_timeout(int(value))
        await self.coordinator.async_request_refresh()
