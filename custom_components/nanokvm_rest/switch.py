"""Switch entities for NanoKVM REST."""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DEFAULT_MEMORY_LIMIT_MB, MIN_MEMORY_LIMIT_MB
from .coordinator import NanoKVMCoordinator
from .entity import NanoKVMEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up NanoKVM switches supported by this device and account."""
    coordinator: NanoKVMCoordinator = entry.runtime_data
    data = coordinator.data
    capabilities = data.get("capabilities", {})
    entities: list[SwitchEntity] = []

    if capabilities.get("admin"):
        if capabilities.get("pcie") and data.get("hdmi") is not None:
            entities.append(NanoKVMHDMISwitch(coordinator))
        if data.get("ssh") is not None:
            entities.append(NanoKVMSSHSwitch(coordinator))
        if data.get("mdns_state") is not None:
            entities.append(NanoKVMmDNSSwitch(coordinator))
        mouse_jiggler = data.get("mouse_jiggler")
        if isinstance(mouse_jiggler, dict) and mouse_jiggler.get("mode"):
            entities.append(NanoKVMMouseJigglerSwitch(coordinator))
        if isinstance(data.get("memory_limit"), dict):
            entities.append(NanoKVMMemoryLimitSwitch(coordinator))
        if isinstance(data.get("preview_updates"), dict):
            entities.append(NanoKVMPreviewUpdatesSwitch(coordinator))
        if isinstance(data.get("update_server"), dict):
            entities.append(NanoKVMCustomUpdateServerSwitch(coordinator))
        virtual_devices = data.get("virtual_devices")
        if isinstance(virtual_devices, dict):
            if "network" in virtual_devices:
                entities.append(
                    NanoKVMVirtualDeviceSwitch(
                        coordinator, "network", "Virtual network", "mdi:ethernet"
                    )
                )
            if "disk" in virtual_devices:
                entities.append(
                    NanoKVMVirtualDeviceSwitch(
                        coordinator, "disk", "Virtual disk", "mdi:harddisk"
                    )
                )

    async_add_entities(entities)


class NanoKVMHDMISwitch(NanoKVMEntity, SwitchEntity):
    """Control HDMI capture on PCIe NanoKVM hardware."""

    _attr_name = "HDMI capture"
    _attr_icon = "mdi:video-input-hdmi"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: NanoKVMCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device_key}_hdmi_capture"

    @property
    def is_on(self) -> bool:
        """Return whether HDMI capture is enabled."""
        return bool((self.coordinator.data.get("hdmi") or {}).get("enabled"))

    async def async_turn_on(self, **kwargs: object) -> None:
        """Enable HDMI capture."""
        await self.coordinator.client.async_set_hdmi(True)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: object) -> None:
        """Disable HDMI capture."""
        await self.coordinator.client.async_set_hdmi(False)
        await self.coordinator.async_request_refresh()


class NanoKVMSSHSwitch(NanoKVMEntity, SwitchEntity):
    """Control the NanoKVM SSH service."""

    _attr_name = "SSH"
    _attr_icon = "mdi:console"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: NanoKVMCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device_key}_ssh"

    @property
    def is_on(self) -> bool:
        """Return whether SSH is enabled."""
        return bool((self.coordinator.data.get("ssh") or {}).get("enabled"))

    async def async_turn_on(self, **kwargs: object) -> None:
        """Enable SSH."""
        await self.coordinator.client.async_set_ssh(True)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: object) -> None:
        """Disable SSH."""
        await self.coordinator.client.async_set_ssh(False)
        await self.coordinator.async_request_refresh()


class NanoKVMmDNSSwitch(NanoKVMEntity, SwitchEntity):
    """Control NanoKVM mDNS advertising."""

    _attr_name = "mDNS"
    _attr_icon = "mdi:lan-connect"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: NanoKVMCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device_key}_mdns"

    @property
    def is_on(self) -> bool:
        """Return whether mDNS is enabled."""
        return bool((self.coordinator.data.get("mdns_state") or {}).get("enabled"))

    async def async_turn_on(self, **kwargs: object) -> None:
        """Enable mDNS."""
        await self.coordinator.client.async_set_mdns(True)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: object) -> None:
        """Disable mDNS."""
        await self.coordinator.client.async_set_mdns(False)
        await self.coordinator.async_request_refresh()


class NanoKVMMouseJigglerSwitch(NanoKVMEntity, SwitchEntity):
    """Control the NanoKVM mouse jiggler."""

    _attr_name = "Mouse jiggler"
    _attr_icon = "mdi:mouse-move-down"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: NanoKVMCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device_key}_mouse_jiggler"

    @property
    def is_on(self) -> bool:
        """Return whether the mouse jiggler is enabled."""
        return bool(
            (self.coordinator.data.get("mouse_jiggler") or {}).get("enabled")
        )

    async def _async_set_state(self, enabled: bool) -> None:
        mode = str(
            (self.coordinator.data.get("mouse_jiggler") or {}).get("mode") or ""
        )
        await self.coordinator.client.async_set_mouse_jiggler(enabled, mode)
        await self.coordinator.async_request_refresh()

    async def async_turn_on(self, **kwargs: object) -> None:
        """Enable the mouse jiggler."""
        await self._async_set_state(True)

    async def async_turn_off(self, **kwargs: object) -> None:
        """Disable the mouse jiggler."""
        await self._async_set_state(False)


class NanoKVMMemoryLimitSwitch(NanoKVMEntity, SwitchEntity):
    """Enable or disable the NanoKVM server memory limit."""

    _attr_name = "Memory limit"
    _attr_icon = "mdi:memory"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: NanoKVMCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device_key}_memory_limit_enabled"

    @property
    def is_on(self) -> bool:
        """Return whether the memory limit is enabled."""
        return bool(
            (self.coordinator.data.get("memory_limit") or {}).get("enabled")
        )

    async def async_turn_on(self, **kwargs: object) -> None:
        """Enable the memory limit using the existing or upstream default value."""
        data = self.coordinator.data.get("memory_limit") or {}
        limit = data.get("limit")
        if not isinstance(limit, (int, float)) or limit < MIN_MEMORY_LIMIT_MB:
            limit = DEFAULT_MEMORY_LIMIT_MB
        await self.coordinator.client.async_set_memory_limit(True, int(limit))
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: object) -> None:
        """Disable the memory limit."""
        await self.coordinator.client.async_set_memory_limit(False, 0)
        await self.coordinator.async_request_refresh()


class NanoKVMVirtualDeviceSwitch(NanoKVMEntity, SwitchEntity):
    """Toggle one NanoKVM virtual USB device."""

    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self,
        coordinator: NanoKVMCoordinator,
        device: str,
        name: str,
        icon: str,
    ) -> None:
        super().__init__(coordinator)
        self._device = device
        self._attr_name = name
        self._attr_icon = icon
        self._attr_unique_id = f"{self._device_key}_virtual_{device}"

    @property
    def is_on(self) -> bool:
        """Return whether this virtual USB device is mounted."""
        return bool(
            (self.coordinator.data.get("virtual_devices") or {}).get(self._device)
        )

    async def _async_set_state(self, enabled: bool) -> None:
        await self.coordinator.client.async_set_virtual_device(self._device, enabled)
        await self.coordinator.async_request_refresh()

    async def async_turn_on(self, **kwargs: object) -> None:
        """Enable the virtual device."""
        await self._async_set_state(True)

    async def async_turn_off(self, **kwargs: object) -> None:
        """Disable the virtual device."""
        await self._async_set_state(False)


class NanoKVMPreviewUpdatesSwitch(NanoKVMEntity, SwitchEntity):
    """Select NanoKVM preview updates instead of the stable channel."""

    _attr_name = "Preview updates"
    _attr_icon = "mdi:test-tube"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: NanoKVMCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device_key}_preview_updates"

    @property
    def is_on(self) -> bool:
        """Return whether preview updates are enabled."""
        return bool((self.coordinator.data.get("preview_updates") or {}).get("enabled"))

    async def _async_set_state(self, enabled: bool) -> None:
        await self.coordinator.client.async_set_preview_updates(enabled)
        self.coordinator.invalidate_application_version()
        await self.coordinator.async_request_refresh()

    async def async_turn_on(self, **kwargs: object) -> None:
        """Enable preview updates."""
        await self._async_set_state(True)

    async def async_turn_off(self, **kwargs: object) -> None:
        """Disable preview updates."""
        await self._async_set_state(False)


class NanoKVMCustomUpdateServerSwitch(NanoKVMEntity, SwitchEntity):
    """Enable or disable NanoKVM's custom update server."""

    _attr_name = "Custom update server"
    _attr_icon = "mdi:server-network"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: NanoKVMCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device_key}_custom_update_server"

    @property
    def is_on(self) -> bool:
        """Return whether the custom update server is active."""
        return bool((self.coordinator.data.get("update_server") or {}).get("enabled"))

    async def _async_set_state(self, enabled: bool) -> None:
        data = self.coordinator.data.get("update_server") or {}
        url = str(data.get("url") or "")
        await self.coordinator.client.async_set_update_server(enabled, url)
        self.coordinator.invalidate_application_version()
        await self.coordinator.async_request_refresh()

    async def async_turn_on(self, **kwargs: object) -> None:
        """Enable the configured custom update server."""
        await self._async_set_state(True)

    async def async_turn_off(self, **kwargs: object) -> None:
        """Disable the custom update server."""
        await self._async_set_state(False)
