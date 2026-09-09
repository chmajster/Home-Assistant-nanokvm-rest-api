"""Connection probe used by the staged NanoKVM config flow."""

from __future__ import annotations

import json
from typing import Any
from urllib.parse import ParseResult, urlparse

import aiohttp

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import NanoKVMAPIError, NanoKVMConnectionError

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


def _looks_like_nanokvm_response(text: str) -> bool:
    """Return whether a response has the characteristic NanoKVM API envelope."""
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return False
    return isinstance(payload, dict) and bool({"code", "msg", "data"} & payload.keys())


async def async_probe_connection(
    hass: HomeAssistant,
    base_url: str,
    verify_ssl: bool,
) -> dict[str, Any]:
    """Check HTTP(S) reachability and verify a NanoKVM API fingerprint."""
    session = async_get_clientsession(hass, verify_ssl=verify_ssl)
    failures: list[str] = []
    ssl_failures: list[str] = []

    for origin in _candidate_origins(base_url):
        try:
            # /api/vm/info is a safe read-only endpoint. Authenticated firmware
            # normally returns either the standard NanoKVM JSON envelope or an
            # auth response using that same envelope. This avoids accepting an
            # arbitrary web server/captive portal as a NanoKVM device.
            async with session.get(
                f"{origin}/api/vm/info",
                allow_redirects=False,
                timeout=aiohttp.ClientTimeout(total=_CONNECTION_TIMEOUT),
            ) as response:
                text = await response.text()
                if _looks_like_nanokvm_response(text):
                    return {
                        "base_url": origin,
                        "http_status": response.status,
                    }
                failures.append(
                    f"{origin}: HTTP {response.status}, response is not NanoKVM API JSON"
                )
        except (aiohttp.ClientConnectorCertificateError, aiohttp.ClientSSLError) as err:
            ssl_failures.append(f"{origin}: {err}")
        except (aiohttp.ClientError, TimeoutError) as err:
            failures.append(f"{origin}: {err}")

    if ssl_failures and not failures:
        detail = "; ".join(ssl_failures[-2:])
        raise NanoKVMAPIError(
            f"NanoKVM TLS certificate validation failed ({detail})",
            code="ssl_error",
        )

    detail = "; ".join((failures + ssl_failures)[-2:]) or "no HTTP/HTTPS response"
    raise NanoKVMConnectionError(f"Unable to reach a NanoKVM API ({detail})")
