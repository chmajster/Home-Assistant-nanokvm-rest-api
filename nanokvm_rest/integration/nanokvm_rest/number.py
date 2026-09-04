"""Number entities for NanoKVM REST."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfInformation, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import (
    DEFAULT_MEMORY_LIMIT_MB,
    MAX_HDMI_IDLE_TIMEOUT,
    MAX_MEMORY_LIMIT_MB,
    MAX_OLED_SLEEP_SECONDS,
    MAX_SWAP_SIZE_MB,
    MIN_HDMI_IDLE_TIMEOUT,
    MIN_MEMORY_LIMIT_MB,
    MIN_OLED_SLEEP_SECONDS,
    MIN_SWAP_SIZE_MB,
    OLED_SLEEP_STEP_SECONDS,
    SWAP_STEP_MB,
)
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
    data = coordinator.data
    entities: list[NumberEntity] = []

    hdmi = data.get("hdmi")
    if (
        capabilities.get("admin")
        and capabilities.get("pcie")
        and isinstance(hdmi, dict)
        and "idleTimeout" in hdmi
    ):
        entities.append(NanoKVMHDMIIdleTimeoutNumber(coordinator))

    if capabilities.get("admin"):
        if isinstance(data.get("memory_limit"), dict):
            entities.append(NanoKVMMemoryLimitNumber(coordinator))
        if isinstance(data.get("swap"), dict):
            entities.append(NanoKVMSwapSizeNumber(coordinator))
        oled = data.get("oled")
        if isinstance(oled, dict) and oled.get("exist"):
            entities.append(NanoKVMOLEDSleepNumber(coordinator))

    async_add_entities(entities)


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


class NanoKVMMemoryLimitNumber(NanoKVMEntity, NumberEntity):
    """Configure NanoKVM server memory limit."""

    _attr_name = "Memory limit"
    _attr_icon = "mdi:memory"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_native_min_value = MIN_MEMORY_LIMIT_MB
    _attr_native_max_value = MAX_MEMORY_LIMIT_MB
    _attr_native_step = 1
    _attr_native_unit_of_measurement = UnitOfInformation.MEGABYTES
    _attr_mode = NumberMode.BOX

    def __init__(self, coordinator: NanoKVMCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device_key}_memory_limit"

    @property
    def native_value(self) -> float:
        """Return configured memory limit in MB."""
        data = self.coordinator.data.get("memory_limit") or {}
        value = data.get("limit")
        if isinstance(value, (int, float)) and value >= MIN_MEMORY_LIMIT_MB:
            return float(value)
        return float(DEFAULT_MEMORY_LIMIT_MB)

    async def async_set_native_value(self, value: float) -> None:
        """Set and enable the memory limit."""
        await self.coordinator.client.async_set_memory_limit(True, int(value))
        await self.coordinator.async_request_refresh()


class NanoKVMSwapSizeNumber(NanoKVMEntity, NumberEntity):
    """Configure swap size."""

    _attr_name = "Swap size"
    _attr_icon = "mdi:swap-horizontal"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_native_min_value = MIN_SWAP_SIZE_MB
    _attr_native_max_value = MAX_SWAP_SIZE_MB
    _attr_native_step = SWAP_STEP_MB
    _attr_native_unit_of_measurement = UnitOfInformation.MEGABYTES
    _attr_mode = NumberMode.BOX

    def __init__(self, coordinator: NanoKVMCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device_key}_swap_size"

    @property
    def native_value(self) -> float:
        """Return swap size in MB; zero means disabled."""
        value = (self.coordinator.data.get("swap") or {}).get("size")
        return float(value) if isinstance(value, (int, float)) else 0.0

    async def async_set_native_value(self, value: float) -> None:
        """Set swap size, or disable swap when zero."""
        await self.coordinator.client.async_set_swap(int(value))
        await self.coordinator.async_request_refresh()


class NanoKVMOLEDSleepNumber(NanoKVMEntity, NumberEntity):
    """Configure OLED sleep timeout."""

    _attr_name = "OLED sleep"
    _attr_icon = "mdi:monitor-off"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_native_min_value = MIN_OLED_SLEEP_SECONDS
    _attr_native_max_value = MAX_OLED_SLEEP_SECONDS
    _attr_native_step = OLED_SLEEP_STEP_SECONDS
    _attr_native_unit_of_measurement = UnitOfTime.SECONDS
    _attr_mode = NumberMode.BOX

    def __init__(self, coordinator: NanoKVMCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device_key}_oled_sleep"

    @property
    def native_value(self) -> float:
        """Return OLED sleep timeout in seconds."""
        value = (self.coordinator.data.get("oled") or {}).get("sleep")
        return float(value) if isinstance(value, (int, float)) else 0.0

    async def async_set_native_value(self, value: float) -> None:
        """Set OLED sleep timeout."""
        await self.coordinator.client.async_set_oled_sleep(int(value))
        await self.coordinator.async_request_refresh()
