"""Buttons for NanoKVM REST."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import CONF_FORCE_OFF_MS, DEFAULT_FORCE_OFF_MS, DEFAULT_POWER_PRESS_MS
from .coordinator import NanoKVMCoordinator
from .entity import NanoKVMEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up NanoKVM buttons."""
    coordinator: NanoKVMCoordinator = entry.runtime_data
    force_off_ms = int(entry.options.get(CONF_FORCE_OFF_MS, DEFAULT_FORCE_OFF_MS))
    async_add_entities(
        [
            NanoKVMButton(
                coordinator,
                "Power",
                "power",
                DEFAULT_POWER_PRESS_MS,
                "mdi:power",
            ),
            NanoKVMButton(
                coordinator,
                "Reset",
                "reset",
                DEFAULT_POWER_PRESS_MS,
                "mdi:restart",
            ),
            NanoKVMButton(
                coordinator,
                "Force off",
                "power",
                force_off_ms,
                "mdi:power-plug-off",
            ),
        ]
    )


class NanoKVMButton(NanoKVMEntity, ButtonEntity):
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
