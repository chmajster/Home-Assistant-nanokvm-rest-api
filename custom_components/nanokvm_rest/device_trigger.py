"""Device triggers for NanoKVM REST."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.components.device_automation import DEVICE_TRIGGER_BASE_SCHEMA
from homeassistant.components.homeassistant.triggers import event
from homeassistant.const import CONF_DEVICE_ID, CONF_DOMAIN, CONF_PLATFORM, CONF_TYPE
from homeassistant.core import CALLBACK_TYPE, HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.trigger import TriggerActionType, TriggerInfo
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN, EVENT_TYPE

TRIGGER_TYPES = {
    "power_on",
    "power_off",
    "hdmi_signal_on",
    "hdmi_signal_off",
    "became_unavailable",
}

TRIGGER_SCHEMA = DEVICE_TRIGGER_BASE_SCHEMA.extend(
    {vol.Required(CONF_TYPE): vol.In(TRIGGER_TYPES)}
)


def _get_device_key(hass: HomeAssistant, device_id: str) -> str | None:
    device_registry = dr.async_get(hass)
    if (
        device := device_registry.async_get(device_id, include_child_devices=False)
    ) is None:
        return None
    return next(
        (
            identifier[1]
            for identifier in device.identifiers
            if identifier[0] == DOMAIN
        ),
        None,
    )


async def async_get_triggers(
    hass: HomeAssistant, device_id: str
) -> list[dict[str, str]]:
    """List NanoKVM device triggers."""
    if _get_device_key(hass, device_id) is None:
        return []

    base_trigger = {
        CONF_PLATFORM: "device",
        CONF_DOMAIN: DOMAIN,
        CONF_DEVICE_ID: device_id,
    }
    return [
        {**base_trigger, CONF_TYPE: trigger_type}
        for trigger_type in sorted(TRIGGER_TYPES)
    ]


async def async_attach_trigger(
    hass: HomeAssistant,
    config: ConfigType,
    action: TriggerActionType,
    trigger_info: TriggerInfo,
) -> CALLBACK_TYPE:
    """Attach a NanoKVM trigger to integration events."""
    device_key = _get_device_key(hass, config[CONF_DEVICE_ID])
    event_data: dict[str, Any] = {
        "device_key": device_key,
        "type": config[CONF_TYPE],
    }
    event_config = event.TRIGGER_SCHEMA(
        {
            event.CONF_PLATFORM: "event",
            event.CONF_EVENT_TYPE: EVENT_TYPE,
            event.CONF_EVENT_DATA: event_data,
        }
    )
    return await event.async_attach_trigger(
        hass, event_config, action, trigger_info, platform_type="device"
    )
