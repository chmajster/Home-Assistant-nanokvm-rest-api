"""Switch entities for NanoKVM REST."""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
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
