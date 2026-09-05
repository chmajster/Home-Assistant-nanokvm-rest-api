"""Buttons for NanoKVM REST."""

from __future__ import annotations

from homeassistant.components.button import ButtonDeviceClass, ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import CONF_FORCE_OFF_MS, DEFAULT_FORCE_OFF_MS, DEFAULT_POWER_PRESS_MS
from .coordinator import NanoKVMCoordinator
from .entity import NanoKVMEntity
from .management import async_reset_hid


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up NanoKVM buttons."""
    coordinator: NanoKVMCoordinator = entry.runtime_data
    force_off_ms = int(entry.options.get(CONF_FORCE_OFF_MS, DEFAULT_FORCE_OFF_MS))
    entities: list[ButtonEntity] = [
        NanoKVMGPIOButton(
            coordinator,
            "Power",
            "power",
            DEFAULT_POWER_PRESS_MS,
            "mdi:power",
        ),
        NanoKVMGPIOButton(
            coordinator,
            "Reset",
            "reset",
            DEFAULT_POWER_PRESS_MS,
            "mdi:restart",
        ),
        NanoKVMGPIOButton(
            coordinator,
            "Force off",
            "power",
            force_off_ms,
            "mdi:power-plug-off",
        ),
    ]

    capabilities = coordinator.data.get("capabilities", {})
    if capabilities.get("pcie") and coordinator.data.get("hdmi") is not None:
        entities.append(NanoKVMResetHDMIButton(coordinator))
    if capabilities.get("admin"):
        entities.extend(
            [
                NanoKVMResetHIDButton(coordinator),
                NanoKVMRebootButton(coordinator),
            ]
        )

    async_add_entities(entities)


class NanoKVMGPIOButton(NanoKVMEntity, ButtonEntity):
    """NanoKVM GPIO action button."""

    def __init__(
        self,
        coordinator: NanoKVMCoordinator,
        name: str,
        button_type: str,
        duration_ms: int,
        icon: str,
    ) -> None:
        super().__init__(coordinator)
        self._button_type = button_type
        self._duration_ms = duration_ms
        self._attr_name = name
        self._attr_icon = icon
        slug = name.lower().replace(" ", "_")
        self._attr_unique_id = f"{self._device_key}_{slug}"

    async def async_press(self) -> None:
        """Press the configured NanoKVM GPIO button."""
        await self.coordinator.client.async_press_button(
            self._button_type, self._duration_ms
        )
        await self.coordinator.async_request_refresh()


class NanoKVMResetHDMIButton(NanoKVMEntity, ButtonEntity):
    """Reset the HDMI subsystem on PCIe NanoKVM hardware."""

    _attr_name = "Reset HDMI"
    _attr_icon = "mdi:video-input-hdmi"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: NanoKVMCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device_key}_reset_hdmi"

    async def async_press(self) -> None:
        """Reset HDMI and refresh state."""
        await self.coordinator.client.async_reset_hdmi()
        await self.coordinator.async_request_refresh()


class NanoKVMResetHIDButton(NanoKVMEntity, ButtonEntity):
    """Reset the NanoKVM HID subsystem without rebooting the device."""

    _attr_name = "Reset HID"
    _attr_icon = "mdi:keyboard-off-outline"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: NanoKVMCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device_key}_reset_hid"

    async def async_press(self) -> None:
        """Reset HID and refresh state."""
        await async_reset_hid(self.coordinator.client)
        await self.coordinator.async_request_refresh()


class NanoKVMRebootButton(NanoKVMEntity, ButtonEntity):
    """Reboot the NanoKVM device itself."""

    _attr_name = "Reboot NanoKVM"
    _attr_icon = "mdi:restart-alert"
    _attr_device_class = ButtonDeviceClass.RESTART
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: NanoKVMCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device_key}_reboot"

    async def async_press(self) -> None:
        """Reboot NanoKVM."""
        await self.coordinator.client.async_reboot()
