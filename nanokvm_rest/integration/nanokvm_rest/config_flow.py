"""Config flow for NanoKVM REST."""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlparse

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry, ConfigFlowResult, OptionsFlowWithReload
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import (
    NanoKVMAPIError,
    NanoKVMAuthError,
    NanoKVMError,
    NanoKVMPermissionError,
)
from .client import NanoKVMClient
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
from .device_setup import async_probe_connection
from .providers.configuration import async_validate_candidate, unique_id_for
from .providers.errors import KVMError
from .providers.registry import provider_name, provider_spec
from .providers.secrets import async_password, async_protect_data

_LOGGER = logging.getLogger(__name__)


def normalize_base_url(value: str) -> str:
    """Normalize and validate a NanoKVM origin.

    When no scheme is supplied, prefer HTTP because NanoKVM defaults to HTTP.
    The client will automatically fall back to HTTPS when needed.
    """
    value = value.strip()
    if not value:
        raise ValueError("invalid URL")

    if "://" not in value:
        value = f"http://{value}"

    parsed = urlparse(value)
    scheme = parsed.scheme.casefold()

    try:
        parsed_port = parsed.port
    except ValueError as err:
        raise ValueError("invalid URL") from err

    if (
        scheme not in {"http", "https"}
        or not parsed.netloc
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.params
        or parsed.query
        or parsed.fragment
        or parsed.path not in {"", "/"}
        or parsed_port is not None
        and not 1 <= parsed_port <= 65535
    ):
        raise ValueError("invalid URL")

    return f"{scheme}://{parsed.netloc}"


def _api_error_key(err: NanoKVMAPIError) -> str:
    """Map API diagnostics to a stable config-flow error key."""
    if err.code == "ssl_error":
        return "ssl_error"
    return "cannot_connect"


class NanoKVMConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle NanoKVM REST setup."""

    VERSION = 2

    def __init__(self) -> None:
        """Initialize staged setup state."""
        self._pending_data: dict[str, Any] | None = None
        self._pending_title = ""
        self._pending_device_key = ""

    async def _async_validate(self, data: dict[str, Any]) -> tuple[str, str]:
        """Validate connection data and return unique ID and title."""
        base_url = normalize_base_url(data[CONF_BASE_URL])
        session = async_get_clientsession(self.hass, verify_ssl=data.get(CONF_VERIFY_SSL, True))
        client = NanoKVMClient(
            session,
            base_url,
            data[CONF_USERNAME],
            await async_password(self.hass, data),
        )

        await client.async_login()

        # Persist the protocol/origin that actually worked. This avoids probing
        # both schemes again after every Home Assistant restart.
        data[CONF_BASE_URL] = client.base_url

        info = await client.async_get_info()
        try:
            hostname = await client.async_get_hostname()
        except (NanoKVMAPIError, NanoKVMPermissionError) as err:
            # Hostname is cosmetic and older firmware/restricted accounts may
            # not expose the endpoint.
            _LOGGER.debug("NanoKVM hostname unavailable during setup: %s", err)
            hostname = {}

        raw_device_key = info.get("deviceKey")
        device_key = str(raw_device_key or client.base_url)
        if not raw_device_key:
            _LOGGER.warning(
                "NanoKVM at %s did not return deviceKey; using URL as unique ID. "
                "Changing the device IP/hostname may create a duplicate entry.",
                client.base_url,
            )
        title = str(hostname.get("hostname") or urlparse(client.base_url).hostname or "NanoKVM")
        return device_key, title

    async def async_step_user(self, user_input=None):
        """Select the provider without changing the existing NanoKVM steps."""
        handlers = {"nanokvm": self._async_step_nanokvm_user, "jetkvm": self._async_start_jetkvm}
        try:
            name = provider_name(user_input or {})
        except KVMError:
            return self.async_abort(reason="unknown_provider")
        return await handlers[name](user_input)

    async def _async_start_jetkvm(self, user_input):
        self._pending_data = dict(user_input or {})
        return await self.async_step_jetkvm()

    async def async_step_jetkvm(self, user_input=None):
        """Local JetKVM password is optional; no secret is echoed to the form."""
        errors = {}
        if user_input is not None:
            try:
                data, info = await async_validate_candidate(
                    self.hass, {**user_input, "provider": "jetkvm"}
                )
            except KVMError as err:
                errors["base"] = err.code
            else:
                await self.async_set_unique_id(unique_id_for(data, info["device_id"]))
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=str(user_input.get("title") or urlparse(data[CONF_BASE_URL]).hostname),
                    data=await async_protect_data(self.hass, data),
                )
        defaults = self._pending_data or {}
        return self.async_show_form(
            step_id="jetkvm",
            data_schema=vol.Schema(
                {
                    vol.Required("title", default="JetKVM"): str,
                    vol.Required(CONF_BASE_URL, default=defaults.get(CONF_BASE_URL, "")): str,
                    vol.Optional(CONF_PASSWORD): str,
                    vol.Required(
                        CONF_VERIFY_SSL, default=defaults.get(CONF_VERIFY_SSL, True)
                    ): bool,
                    vol.Optional("certificate_sha256", default=""): str,
                    vol.Optional("lan_networks", default=""): str,
                }
            ),
            errors=errors,
        )

    async def async_step_import(self, user_input):
        """Manager Save creates a real ConfigEntry through the standard flow."""
        try:
            data, info = await async_validate_candidate(self.hass, user_input)
        except KVMError as err:
            return self.async_abort(reason=err.code)
        await self.async_set_unique_id(unique_id_for(data, info["device_id"]))
        self._abort_if_unique_id_configured()
        return self.async_create_entry(
            title=str(user_input.get("title") or urlparse(data[CONF_BASE_URL]).hostname),
            data=await async_protect_data(self.hass, data),
        )

    async def _async_step_nanokvm_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Test reachability before asking for credentials."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                base_url = normalize_base_url(user_input[CONF_BASE_URL])
                verify_ssl = bool(user_input.get(CONF_VERIFY_SSL, True))
                probe = await async_probe_connection(
                    self.hass,
                    base_url,
                    verify_ssl,
                )
            except ValueError as err:
                _LOGGER.debug("Invalid NanoKVM URL: %s", err)
                errors["base"] = "invalid_url"
            except NanoKVMAPIError as err:
                _LOGGER.warning("NanoKVM connection probe API/TLS failure: %s", err)
                errors["base"] = _api_error_key(err)
            except NanoKVMError as err:
                _LOGGER.warning("NanoKVM connection probe failed: %s", err)
                errors["base"] = "cannot_connect"
            else:
                self._pending_data = {
                    CONF_BASE_URL: str(probe["base_url"]),
                    CONF_VERIFY_SSL: verify_ssl,
                }
                return await self.async_step_auth()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required("provider", default="nanokvm"): vol.In(
                        {"nanokvm": "NanoKVM", "jetkvm": "JetKVM"}
                    ),
                    vol.Required(CONF_BASE_URL): str,
                    vol.Required(CONF_VERIFY_SSL, default=True): bool,
                }
            ),
            errors=errors,
        )

    async def async_step_auth(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Test NanoKVM authentication without creating the entry yet."""
        if self._pending_data is None:
            return self.async_abort(reason="setup_restart")

        errors: dict[str, str] = {}
        if user_input is not None:
            data = dict(self._pending_data)
            data.update(
                {
                    CONF_USERNAME: user_input[CONF_USERNAME],
                    CONF_PASSWORD: user_input[CONF_PASSWORD],
                }
            )
            try:
                device_key, title = await self._async_validate(data)
            except ValueError as err:
                _LOGGER.debug("Invalid NanoKVM URL during authentication: %s", err)
                errors["base"] = "invalid_url"
            except NanoKVMAuthError as err:
                _LOGGER.warning("NanoKVM authentication rejected: %s", err)
                errors["base"] = "invalid_auth"
            except NanoKVMPermissionError as err:
                _LOGGER.warning("NanoKVM account lacks required setup permission: %s", err)
                errors["base"] = "permission_denied"
            except NanoKVMAPIError as err:
                _LOGGER.warning("NanoKVM API failure during authentication: %s", err)
                errors["base"] = _api_error_key(err)
            except NanoKVMError as err:
                _LOGGER.warning("NanoKVM connection failed during authentication: %s", err)
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(device_key)
                self._abort_if_unique_id_configured()
                self._pending_data = data
                self._pending_title = title
                self._pending_device_key = device_key
                return await self.async_step_confirm()

        return self.async_show_form(
            step_id="auth",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_USERNAME, default="admin"): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            errors=errors,
            description_placeholders={
                "base_url": str(self._pending_data[CONF_BASE_URL]),
            },
        )

    async def async_step_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Create the config entry only after explicit confirmation."""
        if self._pending_data is None or not self._pending_title:
            return self.async_abort(reason="setup_restart")

        if user_input is not None:
            return self.async_create_entry(
                title=self._pending_title,
                data=await async_protect_data(self.hass, self._pending_data),
            )

        return self.async_show_form(
            step_id="confirm",
            data_schema=vol.Schema({}),
            description_placeholders={
                "title": self._pending_title,
                "base_url": str(self._pending_data[CONF_BASE_URL]),
                "device_key": self._pending_device_key,
            },
        )

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> ConfigFlowResult:
        """Start reauthentication after an authentication failure."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Validate replacement credentials."""
        entry = self._get_reauth_entry()
        if not provider_spec(entry.data).native_management:
            return await self._async_provider_update(entry, user_input, "reauth_confirm")
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
            except ValueError:
                errors["base"] = "invalid_url"
            except NanoKVMAuthError:
                errors["base"] = "invalid_auth"
            except NanoKVMPermissionError:
                errors["base"] = "permission_denied"
            except NanoKVMAPIError as err:
                errors["base"] = _api_error_key(err)
            except NanoKVMError:
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(device_key)
                self._abort_if_unique_id_mismatch(reason="wrong_device")
                return self.async_update_reload_and_abort(
                    entry,
                    data_updates=await async_protect_data(self.hass, data),
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
        if not provider_spec(entry.data).native_management:
            return await self._async_provider_update(entry, user_input, "reconfigure")
        errors: dict[str, str] = {}

        if user_input is not None:
            password = user_input.get(CONF_PASSWORD) or await async_password(
                self.hass, dict(entry.data)
            )
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
            except NanoKVMPermissionError:
                errors["base"] = "permission_denied"
            except NanoKVMAPIError as err:
                errors["base"] = _api_error_key(err)
            except NanoKVMError:
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(device_key)
                self._abort_if_unique_id_mismatch(reason="wrong_device")
                return self.async_update_reload_and_abort(
                    entry,
                    data_updates=await async_protect_data(self.hass, data),
                    title=title,
                )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_BASE_URL, default=entry.data[CONF_BASE_URL]): str,
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

    async def _async_provider_update(self, entry, user_input, step_id):
        errors = {}
        if user_input is not None:
            payload = dict(user_input)
            # An omitted/blank field keeps the working password. The Manager
            # offers a separate explicit clear-password control for noPassword.
            if not payload.get(CONF_PASSWORD):
                payload.pop(CONF_PASSWORD, None)
            try:
                data, info = await async_validate_candidate(self.hass, payload, dict(entry.data))
                if entry.unique_id and unique_id_for(data, info["device_id"]) != entry.unique_id:
                    raise KVMError("wrong_device")
            except KVMError as err:
                errors["base"] = err.code
            else:
                return self.async_update_reload_and_abort(
                    entry,
                    data_updates=await async_protect_data(self.hass, data),
                    title=str(user_input.get("title") or entry.title),
                )
        return self.async_show_form(
            step_id=step_id,
            data_schema=vol.Schema(
                {
                    vol.Required("title", default=entry.title): str,
                    vol.Required(CONF_BASE_URL, default=entry.data[CONF_BASE_URL]): str,
                    vol.Optional(CONF_PASSWORD): str,
                    vol.Required(
                        CONF_VERIFY_SSL, default=entry.data.get(CONF_VERIFY_SSL, True)
                    ): bool,
                    vol.Optional(
                        "certificate_sha256", default=entry.data.get("certificate_sha256", "")
                    ): str,
                    vol.Optional(
                        "lan_networks", default=", ".join(entry.data.get("lan_networks", []))
                    ): str,
                }
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> NanoKVMOptionsFlow:
        """Return the options flow."""
        return NanoKVMOptionsFlow()


class NanoKVMOptionsFlow(OptionsFlowWithReload):
    """Manage optional NanoKVM behavior."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Manage NanoKVM options."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        if not provider_spec(self.config_entry.data).native_management:
            return self.async_show_form(
                step_id="init",
                data_schema=vol.Schema(
                    {
                        vol.Required(
                            CONF_SCAN_INTERVAL,
                            default=self.config_entry.options.get(CONF_SCAN_INTERVAL, 20),
                        ): vol.All(vol.Coerce(int), vol.Range(min=10, max=30)),
                    }
                ),
            )

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
                    default=self.config_entry.options.get(CONF_FORCE_OFF_MS, DEFAULT_FORCE_OFF_MS),
                ): vol.All(
                    vol.Coerce(int),
                    vol.Range(min=MIN_FORCE_OFF_MS, max=MAX_FORCE_OFF_MS),
                ),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
