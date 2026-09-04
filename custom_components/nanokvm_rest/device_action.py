"""Device actions for NanoKVM REST."""

from __future__ import annotations

from typing import cast

import voluptuous as vol

from homeassistant.components.device_automation import InvalidDeviceAutomationConfig
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_DEVICE_ID, CONF_DOMAIN, CONF_TYPE
from homeassistant.core import Context, HomeAssistant
from homeassistant.helpers import config_validation as cv, device_registry as dr
from homeassistant.helpers.typing import ConfigType, TemplateVarsType

from . import NanoKVMConfigEntry
from .const import (
    CONF_FORCE_OFF_MS,
    DEFAULT_FORCE_OFF_MS,
    DEFAULT_POWER_PRESS_MS,
    DOMAIN,
)
from .coordinator import NanoKVMCoordinator

ACTION_POWER_ON = "power_on"
ACTION_POWER_PRESS = "power_press"
ACTION_FORCE_OFF = "force_off"
ACTION_RESET = "reset"
ACTION_REBOOT_NANOKVM = "reboot_nanokvm"
ACTION_WAKE_ON_LAN = "wake_on_lan"
ACTION_MOUNT_ISO = "mount_iso"
ACTION_UNMOUNT_ISO = "unmount_iso"
ACTION_PASTE_TEXT = "paste_text"

BASE_ACTION_TYPES = {
    ACTION_POWER_ON,
    ACTION_POWER_PRESS,
    ACTION_FORCE_OFF,
    ACTION_RESET,
    ACTION_WAKE_ON_LAN,
    ACTION_PASTE_TEXT,
}
ADMIN_ACTION_TYPES = {
    ACTION_REBOOT_NANOKVM,
    ACTION_MOUNT_ISO,
    ACTION_UNMOUNT_ISO,
}
ACTION_TYPES = BASE_ACTION_TYPES | ADMIN_ACTION_TYPES

CONF_MAC = "mac"
CONF_IMAGE = "image"
CONF_CDROM = "cdrom"
CONF_TEXT = "text"
CONF_LANGUAGE = "language"

ACTION_SCHEMA = cv.DEVICE_ACTION_BASE_SCHEMA.extend(
    {
        vol.Required(CONF_TYPE): vol.In(ACTION_TYPES),
        vol.Optional(CONF_MAC): cv.string,
        vol.Optional(CONF_IMAGE): cv.string,
        vol.Optional(CONF_CDROM, default=True): cv.boolean,
        vol.Optional(CONF_TEXT): cv.string,
        vol.Optional(CONF_LANGUAGE, default="en"): cv.string,
    }
)


def _get_coordinator(hass: HomeAssistant, device_id: str) -> NanoKVMCoordinator | None:
    """Resolve loaded NanoKVM runtime data from a device ID."""
    device_registry = dr.async_get(hass)
    if (
        device := device_registry.async_get(device_id, include_child_devices=False)
    ) is None:
        return None
    _, config_entry = dr.async_get_device_and_config_entry_for_domain(
        hass, device.id, domain=DOMAIN
    )
    if (
        config_entry
        and config_entry.state is ConfigEntryState.LOADED
        and hasattr(config_entry, "runtime_data")
    ):
        return cast(NanoKVMConfigEntry, config_entry).runtime_data
    return None


def _get_coordinator_or_raise(
    hass: HomeAssistant, device_id: str
) -> NanoKVMCoordinator:
    coordinator = _get_coordinator(hass, device_id)
    if coordinator is not None:
        return coordinator
    raise InvalidDeviceAutomationConfig(
        translation_domain=DOMAIN,
        translation_key="config_invalid",
        translation_placeholders={"device_id": device_id},
    )


async def async_get_actions(
    hass: HomeAssistant, device_id: str
) -> list[dict[str, str]]:
    """Return actions exposed by this NanoKVM device."""
    coordinator = _get_coordinator(hass, device_id)
    if coordinator is None:
        return []

    action_types = set(BASE_ACTION_TYPES)
    if coordinator.data.get("capabilities", {}).get("admin"):
        action_types |= ADMIN_ACTION_TYPES

    base = {
        CONF_DEVICE_ID: device_id,
        CONF_DOMAIN: DOMAIN,
    }
    return [{**base, CONF_TYPE: action_type} for action_type in sorted(action_types)]


async def async_get_action_capabilities(
    hass: HomeAssistant, config: ConfigType
) -> dict[str, vol.Schema]:
    """Return extra fields required by parameterized actions."""
    action_type = config[CONF_TYPE]
    if action_type == ACTION_WAKE_ON_LAN:
        return {"extra_fields": vol.Schema({vol.Required(CONF_MAC): cv.string})}
    if action_type == ACTION_MOUNT_ISO:
        return {
            "extra_fields": vol.Schema(
                {
                    vol.Required(CONF_IMAGE): cv.string,
                    vol.Optional(CONF_CDROM, default=True): cv.boolean,
                }
            )
        }
    if action_type == ACTION_PASTE_TEXT:
        return {
            "extra_fields": vol.Schema(
                {
                    vol.Required(CONF_TEXT): cv.string,
                    vol.Optional(CONF_LANGUAGE, default="en"): cv.string,
                }
            )
        }
    return {}


async def async_call_action_from_config(
    hass: HomeAssistant,
    config: ConfigType,
    variables: TemplateVarsType,
    context: Context | None,
) -> None:
    """Execute a NanoKVM device action."""
    coordinator = _get_coordinator_or_raise(hass, config[CONF_DEVICE_ID])
    client = coordinator.client
    action_type = config[CONF_TYPE]

    if action_type == ACTION_POWER_ON:
        if not bool((coordinator.data.get("gpio") or {}).get("pwr")):
            await client.async_press_button("power", DEFAULT_POWER_PRESS_MS)
    elif action_type == ACTION_POWER_PRESS:
        await client.async_press_button("power", DEFAULT_POWER_PRESS_MS)
    elif action_type == ACTION_FORCE_OFF:
        if bool((coordinator.data.get("gpio") or {}).get("pwr")):
            duration = int(
                coordinator.config_entry.options.get(
                    CONF_FORCE_OFF_MS, DEFAULT_FORCE_OFF_MS
                )
            )
            await client.async_press_button("power", duration)
    elif action_type == ACTION_RESET:
        await client.async_press_button("reset", DEFAULT_POWER_PRESS_MS)
    elif action_type == ACTION_REBOOT_NANOKVM:
        await client.async_reboot()
    elif action_type == ACTION_WAKE_ON_LAN:
        mac = config.get(CONF_MAC)
        if not mac:
            raise vol.Invalid("mac is required for wake_on_lan")
        await client.async_wake_on_lan(str(mac))
    elif action_type == ACTION_MOUNT_ISO:
        image = config.get(CONF_IMAGE)
        if not image:
            raise vol.Invalid("image is required for mount_iso")
        await client.async_mount_image(
            str(image), bool(config.get(CONF_CDROM, True))
        )
    elif action_type == ACTION_UNMOUNT_ISO:
        await client.async_unmount_image()
    elif action_type == ACTION_PASTE_TEXT:
        text = config.get(CONF_TEXT)
        if not text:
            raise vol.Invalid("text is required for paste_text")
        await client.async_paste_text(
            str(text), str(config.get(CONF_LANGUAGE, "en"))
        )

    if action_type not in {ACTION_REBOOT_NANOKVM, ACTION_WAKE_ON_LAN, ACTION_PASTE_TEXT}:
        await coordinator.async_request_refresh()
