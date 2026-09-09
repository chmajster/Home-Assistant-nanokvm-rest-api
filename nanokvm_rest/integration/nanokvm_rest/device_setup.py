"""Connection probe used by the staged NanoKVM config flow."""

from __future__ import annotations

from typing import Any
from urllib.parse import ParseResult, urlparse

import aiohttp

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import NanoKVMConnectionError

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


async def async_probe_connection(
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
                    "base_url": origin,
                    "http_status": response.status,
                }
        except (aiohttp.ClientError, TimeoutError) as err:
            failures.append(f"{origin}: {err}")

    detail = "; ".join(failures[-2:]) or "no HTTP/HTTPS response"
    raise NanoKVMConnectionError(f"Unable to reach NanoKVM ({detail})")
