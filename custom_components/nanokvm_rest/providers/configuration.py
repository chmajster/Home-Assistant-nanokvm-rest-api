"""Validated provider configuration shared by HA flows and Manager CRUD."""

from __future__ import annotations

import asyncio
import ipaddress

from .errors import KVMError
from .jetkvm import JetKVMClient
from .network import LANPolicy, parse_origin
from .registry import provider_name, provider_spec
from .secrets import async_password

INPUT_FIELDS = {
    "provider",
    "base_url",
    "host",
    "protocol",
    "port",
    "username",
    "password",
    "title",
    "verify_ssl",
    "certificate_sha256",
    "lan_networks",
    "entry_id",
}


def normalize_candidate(payload: dict, previous: dict | None = None) -> dict:
    if not isinstance(payload, dict) or set(payload) - INPUT_FIELDS:
        raise KVMError("invalid_data")
    data = dict(previous or {})
    name = provider_name({**data, **payload})
    if previous is not None and name != provider_name(previous):
        raise KVMError("invalid_data", "Changing a device provider is not permitted")
    address = payload.get("host", payload.get("base_url", data.get("base_url", "")))
    origin = parse_origin(address, payload.get("protocol", "http"), payload.get("port"))
    data.update(provider=name, base_url=origin.url)
    for key in ("username", "password", "certificate_sha256"):
        if key in payload:
            if not isinstance(payload[key], str) or len(payload[key]) > (
                4096 if key == "password" else 256
            ):
                raise KVMError("invalid_data")
            data[key] = payload[key]
    if "verify_ssl" in payload:
        if type(payload["verify_ssl"]) is not bool:
            raise KVMError("invalid_data")
        data["verify_ssl"] = payload["verify_ssl"]
    data.setdefault("verify_ssl", True)
    if name == "nanokvm" and data.get("certificate_sha256"):
        raise KVMError("unsupported", "Certificate pinning is supported by the JetKVM provider")
    if "lan_networks" in payload:
        networks = payload["lan_networks"]
        if isinstance(networks, str):
            networks = [n.strip() for n in networks.split(",") if n.strip()]
        if (
            not isinstance(networks, list)
            or len(networks) > 32
            or not all(isinstance(n, str) for n in networks)
        ):
            raise KVMError("invalid_data", "Invalid LAN CIDRs")
        try:
            parsed = [ipaddress.ip_network(n, strict=False) for n in networks]
        except ValueError as err:
            raise KVMError("invalid_data", "Invalid LAN CIDR") from err
        if any(n.prefixlen < (8 if n.version == 4 else 16) for n in parsed):
            raise KVMError("invalid_data", "LAN CIDR is too broad")
        data["lan_networks"] = [str(n) for n in parsed]
    # Validate policy before doing any network or authentication work.
    LANPolicy(data.get("lan_networks", ())).validate_literal(origin.host)
    return data


async def _nano_client(hass, data):
    from homeassistant.helpers.aiohttp_client import async_get_clientsession

    from ..client import NanoKVMClient

    return NanoKVMClient(
        async_get_clientsession(hass, verify_ssl=data.get("verify_ssl", True)),
        data["base_url"],
        data.get("username", "admin"),
        await async_password(hass, data),
    )


async def _jet_client(hass, data):
    return JetKVMClient(
        parse_origin(data["base_url"]),
        await async_password(hass, data),
        verify_ssl=data.get("verify_ssl", True),
        certificate_sha256=data.get("certificate_sha256", ""),
        policy=LANPolicy(data.get("lan_networks", ())),
    )


CLIENT_FACTORIES = {"nanokvm": _nano_client, "jetkvm": _jet_client}


async def async_make_provider(hass, data, coordinator=None):
    name = provider_name(data)
    client = await CLIENT_FACTORIES[name](hass, data)
    return provider_spec(data).adapter(client, coordinator)


async def async_validate_candidate(
    hass, payload: dict, previous: dict | None = None
) -> tuple[dict, dict]:
    from ..api import NanoKVMAPIError, NanoKVMAuthError, NanoKVMError, NanoKVMPermissionError

    data = normalize_candidate(payload, previous)
    provider = await async_make_provider(hass, data)
    try:
        async with asyncio.timeout(12):
            info = await provider.test_connection()
        data["base_url"] = provider.client.base_url
        data["device_id"] = info["device_id"]
        return data, info
    except NanoKVMAuthError as err:
        raise KVMError("invalid_password", "NanoKVM rejected authentication") from err
    except NanoKVMPermissionError as err:
        raise KVMError("permission_denied") from err
    except NanoKVMAPIError as err:
        raise KVMError("tls_error" if err.code == "ssl_error" else "protocol_error") from err
    except NanoKVMError as err:
        raise KVMError("unreachable", "NanoKVM connection failed") from err
    except TimeoutError as err:
        raise KVMError("timeout") from err
    finally:
        await provider.disconnect()


async def _probe_nano(hass, data):
    from ..api import NanoKVMError
    from ..device_setup import async_probe_connection

    try:
        result = await async_probe_connection(hass, data["base_url"], data["verify_ssl"])
        return {"base_url": result["base_url"], "requires_auth": True}
    except NanoKVMError as err:
        raise KVMError("unreachable", "NanoKVM connection probe failed") from err


async def _probe_jet(hass, data):
    data = {**data, "password": ""}
    provider = await async_make_provider(hass, data)
    try:
        result = await provider.test_connection()
        return {**result, "base_url": data["base_url"], "requires_auth": False}
    except KVMError as err:
        if err.code == "authentication_required":
            return {"base_url": data["base_url"], "requires_auth": True}
        raise
    finally:
        await provider.disconnect()


PROBES = {"nanokvm": _probe_nano, "jetkvm": _probe_jet}


async def async_probe_candidate(hass, payload):
    data = normalize_candidate(payload)
    async with asyncio.timeout(12):
        return await PROBES[provider_name(data)](hass, data)


def unique_id_for(data: dict, device_id: str) -> str:
    # Preserve every existing NanoKVM unique_id, including the URL fallback.
    prefixes = {"nanokvm": "", "jetkvm": "jetkvm:"}
    return prefixes[provider_name(data)] + device_id
