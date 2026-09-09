"""WebSocket helpers for adding NanoKVM devices from the management UI."""

from __future__ import annotations

from typing import Any
from urllib.parse import ParseResult, urlparse

import aiohttp
import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import (
    NanoKVMAPIError,
    NanoKVMAuthError,
    NanoKVMConnectionError,
    NanoKVMError,
)
from .client import NanoKVMClient
from .config_flow import normalize_base_url
from .const import CONF_BASE_URL, CONF_VERIFY_SSL, DOMAIN

_CONNECTION_TIMEOUT = 6


def _alternate_origin(parsed: ParseResult, scheme: str) -> str:
    """Return the same host using the alternate HTTP scheme."""
    hostname = parsed.hostname
    if not hostname:
        return ""

    try:
        port = parsed.port
    except ValueError:
        port = None

    if port in {80, 443}:
        port = None

    host = f"[{hostname}]" if ":" in hostname else hostname
    if port is not None:
        host = f"{host}:{port}"
    return f"{scheme}://{host}"


def _candidate_origins(base_url: str) -> tuple[str, ...]:
    """Return the requested origin followed by its HTTP/HTTPS alternative."""
    parsed = urlparse(base_url)
    primary = f"{parsed.scheme}://{parsed.netloc}"
    alternate_scheme = "https" if parsed.scheme == "http" else "http"
    alternate = _alternate_origin(parsed, alternate_scheme)
    return tuple(item for item in dict.fromkeys((primary, alternate)) if item)


async def _async_probe_connection(
    hass: HomeAssistant,
    base_url: str,
    verify_ssl: bool,
) -> dict[str, Any]:
    """Check HTTP(S) reachability without submitting credentials."""
    session = async_get_clientsession(hass, verify_ssl=verify_ssl)
    failures: list[str] = []

    for origin in _candidate_origins(base_url):
        try:
            async with session.get(
                f"{origin}/api/auth/login",
                allow_redirects=False,
                timeout=aiohttp.ClientTimeout(total=_CONNECTION_TIMEOUT),
            ) as response:
                await response.read()
                return {
                    "ok": True,
                    "base_url": origin,
                    "http_status": response.status,
                }
        except (aiohttp.ClientError, TimeoutError) as err:
            failures.append(f"{origin}: {err}")

    detail = "; ".join(failures[-2:]) or "no HTTP/HTTPS response"
    raise NanoKVMConnectionError(f"Unable to reach NanoKVM ({detail})")


def _setup_schema(command: str, *, credentials: bool) -> dict[Any, Any]:
    schema: dict[Any, Any] = {
        vol.Required("type"): command,
        vol.Required(CONF_BASE_URL): str,
        vol.Optional(CONF_VERIFY_SSL, default=True): bool,
    }
    if credentials:
        schema[vol.Required(CONF_USERNAME)] = str
        schema[vol.Required(CONF_PASSWORD)] = str
    return schema


@websocket_api.websocket_command(
    _setup_schema(f"{DOMAIN}/panel/device/test_connection", credentials=False)
)
@websocket_api.require_admin
@websocket_api.async_response
async def websocket_test_device_connection(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Test network and HTTP(S) reachability without authenticating."""
    try:
        base_url = normalize_base_url(msg[CONF_BASE_URL])
        result = await _async_probe_connection(
            hass,
            base_url,
            bool(msg.get(CONF_VERIFY_SSL, True)),
        )
        connection.send_result(msg["id"], result)
    except ValueError:
        connection.send_error(msg["id"], "invalid_url", "Invalid NanoKVM URL")
    except NanoKVMConnectionError as err:
        connection.send_error(msg["id"], "cannot_connect", str(err))


@websocket_api.websocket_command(
    _setup_schema(f"{DOMAIN}/panel/device/test_authentication", credentials=True)
)
@websocket_api.require_admin
@websocket_api.async_response
async def websocket_test_device_authentication(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Authenticate and identify a NanoKVM without creating a config entry."""
    try:
        base_url = normalize_base_url(msg[CONF_BASE_URL])
        session = async_get_clientsession(
            hass,
            verify_ssl=bool(msg.get(CONF_VERIFY_SSL, True)),
        )
        client = NanoKVMClient(
            session,
            base_url,
            msg[CONF_USERNAME],
            msg[CONF_PASSWORD],
        )
        await client.async_login()
        info = await client.async_get_info()
        try:
            hostname = await client.async_get_hostname()
        except NanoKVMAPIError:
            hostname = {}

        device_key = str(info.get("deviceKey") or client.base_url)
        title = str(
            hostname.get("hostname")
            or urlparse(client.base_url).hostname
            or "NanoKVM"
        )
        already_configured = any(
            entry.unique_id == device_key
            or str(entry.data.get(CONF_BASE_URL) or "").rstrip("/")
            == client.base_url.rstrip("/")
            for entry in hass.config_entries.async_entries(DOMAIN)
        )
        connection.send_result(
            msg["id"],
            {
                "ok": True,
                "base_url": client.base_url,
                "device_key": device_key,
                "title": title,
                "already_configured": already_configured,
            },
        )
    except ValueError:
        connection.send_error(msg["id"], "invalid_url", "Invalid NanoKVM URL")
    except NanoKVMAuthError as err:
        connection.send_error(msg["id"], "invalid_auth", str(err))
    except NanoKVMConnectionError as err:
        connection.send_error(msg["id"], "cannot_connect", str(err))
    except NanoKVMAPIError as err:
        connection.send_error(msg["id"], "api_error", str(err))
    except NanoKVMError as err:
        connection.send_error(msg["id"], "setup_failed", str(err))


@websocket_api.websocket_command(
    _setup_schema(f"{DOMAIN}/panel/device/create", credentials=True)
)
@websocket_api.require_admin
@websocket_api.async_response
async def websocket_create_device(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Create the NanoKVM config entry through the integration config flow."""
    try:
        data = {
            CONF_BASE_URL: normalize_base_url(msg[CONF_BASE_URL]),
            CONF_USERNAME: msg[CONF_USERNAME],
            CONF_PASSWORD: msg[CONF_PASSWORD],
            CONF_VERIFY_SSL: bool(msg.get(CONF_VERIFY_SSL, True)),
        }
    except ValueError:
        connection.send_error(msg["id"], "invalid_url", "Invalid NanoKVM URL")
        return

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": "user"},
        data=data,
    )
    result_type = getattr(result.get("type"), "value", result.get("type"))

    if result_type == "create_entry":
        entry = result.get("result")
        connection.send_result(
            msg["id"],
            {
                "ok": True,
                "entry_id": getattr(entry, "entry_id", ""),
                "title": getattr(entry, "title", result.get("title", "NanoKVM")),
            },
        )
        return

    if result_type == "abort":
        reason = str(result.get("reason") or "setup_aborted")
        connection.send_error(msg["id"], reason, reason.replace("_", " "))
        return

    flow_id = result.get("flow_id")
    if flow_id:
        await hass.config_entries.flow.async_abort(flow_id)

    errors = result.get("errors") or {}
    reason = str(next(iter(errors.values()), "setup_failed"))
    connection.send_error(msg["id"], reason, reason.replace("_", " "))


DEVICE_SETUP_COMMANDS = (
    websocket_test_device_connection,
    websocket_test_device_authentication,
    websocket_create_device,
)
