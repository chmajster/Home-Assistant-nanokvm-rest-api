"""Update entity for the NanoKVM application."""

from __future__ import annotations

from typing import Any

from homeassistant.components.update import (
    UpdateDeviceClass,
    UpdateEntity,
    UpdateEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import NanoKVMCoordinator
from .entity import NanoKVMEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the NanoKVM application update entity."""
    coordinator: NanoKVMCoordinator = entry.runtime_data
    if (
        coordinator.data.get("capabilities", {}).get("admin")
        and (
            coordinator.data.get("application_version") is not None
            or coordinator.data.get("preview_updates") is not None
        )
    ):
        async_add_entities([NanoKVMApplicationUpdate(coordinator)])


class NanoKVMApplicationUpdate(NanoKVMEntity, UpdateEntity):
    """Represent NanoKVM application updates."""

    _attr_name = "Application"
    _attr_icon = "mdi:update"
    _attr_device_class = UpdateDeviceClass.FIRMWARE
    _attr_entity_category = EntityCategory.CONFIG
    _attr_supported_features = UpdateEntityFeature.INSTALL

    def __init__(self, coordinator: NanoKVMCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device_key}_application_update"
        self._installing = False

    @property
    def installed_version(self) -> str | None:
        """Return installed NanoKVM application version."""
        version_data = self.coordinator.data.get("application_version") or {}
        value = version_data.get("current")
        if value:
            return str(value)
        value = (self.coordinator.data.get("info") or {}).get("application")
        return str(value) if value else None

    @property
    def latest_version(self) -> str | None:
        """Return latest NanoKVM application version."""
        version_data = self.coordinator.data.get("application_version") or {}
        value = version_data.get("latest")
        if value:
            return str(value)
        return self.installed_version

    @property
    def in_progress(self) -> bool:
        """Return whether an update request is running."""
        return self._installing

    async def async_install(
        self, version: str | None, backup: bool, **kwargs: Any
    ) -> None:
        """Install the latest NanoKVM application release."""
        self._installing = True
        self.async_write_ha_state()
        try:
            await self.coordinator.client.async_update_application()
            self.coordinator.invalidate_application_version()
        finally:
            self._installing = False
            self.async_write_ha_state()
