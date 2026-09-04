"""Config flow for NanoKVM REST."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import NanoKVMAuthError, NanoKVMClient, NanoKVMError
from .const import CONF_BASE_URL, CONF_VERIFY_SSL, DOMAIN


def normalize_base_url(value: str) -> str:
    value = value.strip().rstrip("/")
    if not value.startswith(("http://", "https://")):
        value = f"http://{value}"
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("invalid URL")
    return value


class NanoKVMConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle NanoKVM REST setup."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                base_url = normalize_base_url(user_input[CONF_BASE_URL])
                session = async_get_clientsession(
                    self.hass, verify_ssl=user_input[CONF_VERIFY_SSL]
                )
                client = NanoKVMClient(
                    session,
                    base_url,
                    user_input[CONF_USERNAME],
                    user_input[CONF_PASSWORD],
                )
                await client.async_login()
                info = await client.async_get_info()
                hostname = await client.async_get_hostname()
            except ValueError:
                errors["base"] = "invalid_url"
            except NanoKVMAuthError:
                errors["base"] = "invalid_auth"
            except NanoKVMError:
                errors["base"] = "cannot_connect"
            else:
                device_key = str(info.get("deviceKey") or base_url)
                await self.async_set_unique_id(device_key)
                self._abort_if_unique_id_configured()
                title = hostname.get("hostname") or "NanoKVM"
                return self.async_create_entry(
                    title=title,
                    data={
                        CONF_BASE_URL: base_url,
                        CONF_USERNAME: user_input[CONF_USERNAME],
                        CONF_PASSWORD: user_input[CONF_PASSWORD],
                        CONF_VERIFY_SSL: user_input[CONF_VERIFY_SSL],
                    },
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_BASE_URL): str,
                vol.Required(CONF_USERNAME, default="admin"): str,
                vol.Required(CONF_PASSWORD): str,
                vol.Required(CONF_VERIFY_SSL, default=True): bool,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)
