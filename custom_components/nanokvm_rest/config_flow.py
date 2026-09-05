"""Config flow for NanoKVM REST."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry, OptionsFlowWithReload
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import callback
from homeassistant.data_entry_flow import ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import NanoKVMAuthError, NanoKVMClient, NanoKVMError
from .const import (
    CONF_BASE_URL,
    CONF_FORCE_OFF_MS,
    CONF_SCAN_INTERVAL,
    CONF_SHOW_SIDEBAR_PANEL,
    CONF_VERIFY_SSL,
    DEFAULT_FORCE_OFF_MS,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SHOW_SIDEBAR_PANEL,
    DOMAIN,
    MAX_FORCE_OFF_MS,
    MAX_SCAN_INTERVAL,
    MIN_FORCE_OFF_MS,
    MIN_SCAN_INTERVAL,
)


def normalize_base_url(value: str) -> str:
    """Normalize and validate a NanoKVM base URL."""
    value = value.strip().rstrip("/")
    if not value.startswith(("http://", "https://")):
        value = f"http://{value}"

    parsed = urlparse(value)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.netloc
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("invalid URL")
    return value


class NanoKVMConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle NanoKVM REST setup."""

    VERSION = 1

    async def _async_validate(
        self, data: dict[str, Any]
    ) -> tuple[str, str]:
        """Validate connection data and return unique ID and title."""
        base_url = normalize_base_url(data[CONF_BASE_URL])
        session = async_get_clientsession(
            self.hass, verify_ssl=data.get(CONF_VERIFY_SSL, True)
        )
        client = NanoKVMClient(
            session,
            base_url,
            data[CONF_USERNAME],
            data[CONF_PASSWORD],
        )
        await client.async_login()
        info = await client.async_get_info()
        hostname = await client.async_get_hostname()
        device_key = str(info.get("deviceKey") or base_url)
        title = str(hostname.get("hostname") or "NanoKVM")
        return device_key, title

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle user initiated setup."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                data = dict(user_input)
                data[CONF_BASE_URL] = normalize_base_url(data[CONF_BASE_URL])
                device_key, title = await self._async_validate(data)
            except ValueError:
                errors["base"] = "invalid_url"
            except NanoKVMAuthError:
                errors["base"] = "invalid_auth"
            except NanoKVMError:
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(device_key)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=title, data=data)

        schema = vol.Schema(
            {
                vol.Required(CONF_BASE_URL): str,
                vol.Required(CONF_USERNAME, default="admin"): str,
                vol.Required(CONF_PASSWORD): str,
                vol.Required(CONF_VERIFY_SSL, default=True): bool,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_reauth(
        self, entry_data: dict[str, Any]
    ) -> ConfigFlowResult:
        """Start reauthentication after an authentication failure."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Validate replacement credentials."""
        entry = self._get_reauth_entry()
        errors: dict[str, str] = {}

        if user_input is not None:
            data = dict(entry.data)
            data.update(
                {
                    CONF_USERNAME: user_input[CONF_USERNAME],
                    CONF_PASSWORD: user_input[CONF_PASSWORD],
                }
            )
            try:
                device_key, _ = await self._async_validate(data)
            except NanoKVMAuthError:
                errors["base"] = "invalid_auth"
            except NanoKVMError:
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(device_key)
                self._abort_if_unique_id_mismatch(reason="wrong_device")
                return self.async_update_reload_and_abort(
                    entry,
                    data_updates={
                        CONF_USERNAME: user_input[CONF_USERNAME],
                        CONF_PASSWORD: user_input[CONF_PASSWORD],
                    },
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_USERNAME, default=entry.data.get(CONF_USERNAME, "admin")
                    ): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Reconfigure connection settings."""
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}

        if user_input is not None:
            password = user_input.get(CONF_PASSWORD) or entry.data[CONF_PASSWORD]
            data = {
                CONF_BASE_URL: user_input[CONF_BASE_URL],
                CONF_USERNAME: user_input[CONF_USERNAME],
                CONF_PASSWORD: password,
                CONF_VERIFY_SSL: user_input[CONF_VERIFY_SSL],
            }
            try:
                data[CONF_BASE_URL] = normalize_base_url(data[CONF_BASE_URL])
                device_key, title = await self._async_validate(data)
            except ValueError:
                errors["base"] = "invalid_url"
            except NanoKVMAuthError:
                errors["base"] = "invalid_auth"
            except NanoKVMError:
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(device_key)
                self._abort_if_unique_id_mismatch(reason="wrong_device")
                return self.async_update_reload_and_abort(
                    entry,
                    data_updates=data,
                    title=title,
                )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_BASE_URL, default=entry.data[CONF_BASE_URL]
                    ): str,
                    vol.Required(
                        CONF_USERNAME, default=entry.data.get(CONF_USERNAME, "admin")
                    ): str,
                    vol.Optional(CONF_PASSWORD): str,
                    vol.Required(
                        CONF_VERIFY_SSL,
                        default=entry.data.get(CONF_VERIFY_SSL, True),
                    ): bool,
                }
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> NanoKVMOptionsFlow:
        """Return the NanoKVM options flow."""
        return NanoKVMOptionsFlow()


class NanoKVMOptionsFlow(OptionsFlowWithReload):
    """Manage optional NanoKVM behavior."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage NanoKVM options."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_SHOW_SIDEBAR_PANEL,
                    default=self.config_entry.options.get(
                        CONF_SHOW_SIDEBAR_PANEL,
                        DEFAULT_SHOW_SIDEBAR_PANEL,
                    ),
                ): bool,
                vol.Required(
                    CONF_SCAN_INTERVAL,
                    default=self.config_entry.options.get(
                        CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                    ),
                ): vol.All(
                    vol.Coerce(int),
                    vol.Range(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL),
                ),
                vol.Required(
                    CONF_FORCE_OFF_MS,
                    default=self.config_entry.options.get(
                        CONF_FORCE_OFF_MS, DEFAULT_FORCE_OFF_MS
                    ),
                ): vol.All(
                    vol.Coerce(int),
                    vol.Range(min=MIN_FORCE_OFF_MS, max=MAX_FORCE_OFF_MS),
                ),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
