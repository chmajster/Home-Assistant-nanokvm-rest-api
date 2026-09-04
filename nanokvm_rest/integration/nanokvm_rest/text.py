"""Text entities for NanoKVM REST."""

from __future__ import annotations

from urllib.parse import urlparse

from homeassistant.components.text import TextEntity, TextMode
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
    """Set up writable NanoKVM text settings."""
    coordinator: NanoKVMCoordinator = entry.runtime_data
    if not coordinator.data.get("capabilities", {}).get("admin"):
        return

    entities: list[TextEntity] = []
    if isinstance(coordinator.data.get("hostname"), dict):
        entities.append(NanoKVMHostnameText(coordinator))
    if isinstance(coordinator.data.get("web_title"), dict):
        entities.append(NanoKVMWebTitleText(coordinator))
    if isinstance(coordinator.data.get("update_server"), dict):
        entities.append(NanoKVMUpdateServerURLText(coordinator))
    async_add_entities(entities)


class NanoKVMHostnameText(NanoKVMEntity, TextEntity):
    """Configure the NanoKVM hostname."""

    _attr_name = "Hostname"
    _attr_icon = "mdi:identifier"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_mode = TextMode.TEXT
    _attr_native_min = 1
    _attr_native_max = 63

    def __init__(self, coordinator: NanoKVMCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device_key}_hostname_setting"

    @property
    def native_value(self) -> str:
        """Return current hostname."""
        return str((self.coordinator.data.get("hostname") or {}).get("hostname") or "")

    async def async_set_value(self, value: str) -> None:
        """Set hostname."""
        await self.coordinator.client.async_set_hostname(value)
        await self.coordinator.async_request_refresh()


class NanoKVMWebTitleText(NanoKVMEntity, TextEntity):
    """Configure the NanoKVM web UI title."""

    _attr_name = "Web title"
    _attr_icon = "mdi:format-title"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_mode = TextMode.TEXT
    _attr_native_min = 1
    _attr_native_max = 128

    def __init__(self, coordinator: NanoKVMCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device_key}_web_title_setting"

    @property
    def native_value(self) -> str:
        """Return current web title."""
        data = self.coordinator.data.get("web_title") or {}
        return str(data.get("title") or data.get("webTitle") or "")

    async def async_set_value(self, value: str) -> None:
        """Set web title."""
        await self.coordinator.client.async_set_web_title(value)
        await self.coordinator.async_request_refresh()


class NanoKVMUpdateServerURLText(NanoKVMEntity, TextEntity):
    """Configure NanoKVM's custom application update-server URL."""

    _attr_name = "Update server URL"
    _attr_icon = "mdi:web"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_mode = TextMode.TEXT
    _attr_native_min = 0
    _attr_native_max = 2048

    def __init__(self, coordinator: NanoKVMCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device_key}_update_server_url"

    @property
    def native_value(self) -> str:
        """Return the configured custom update-server URL."""
        url = str((self.coordinator.data.get("update_server") or {}).get("url") or "")
        parsed = urlparse(url)
        if parsed.username or parsed.password:
            return ""
        return url

    async def async_set_value(self, value: str) -> None:
        """Set custom update-server URL while preserving its enabled state."""
        enabled = bool((self.coordinator.data.get("update_server") or {}).get("enabled"))
        await self.coordinator.client.async_set_update_server(enabled, value)
        self.coordinator.invalidate_application_version()
        await self.coordinator.async_request_refresh()
