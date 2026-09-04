"""Diagnostics support for NanoKVM REST."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant

from . import NanoKVMConfigEntry
from .const import CONF_BASE_URL

_ENTRY_REDACT = {CONF_BASE_URL, CONF_USERNAME, CONF_PASSWORD}
_DATA_REDACT = {"ips", "addr", "username", "mdns", "url"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: NanoKVMConfigEntry
) -> dict[str, Any]:
    """Return redacted diagnostics for a NanoKVM config entry."""
    return {
        "entry": async_redact_data(dict(entry.data), _ENTRY_REDACT),
        "options": dict(entry.options),
        "data": async_redact_data(entry.runtime_data.data, _DATA_REDACT),
    }
