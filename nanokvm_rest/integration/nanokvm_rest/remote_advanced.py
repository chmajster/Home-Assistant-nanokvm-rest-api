"""Advanced update, virtual-media transfer and HID helpers."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import aiohttp

from .api import (
    NanoKVMAPIError,
    NanoKVMAuthError,
    NanoKVMClient,
    NanoKVMConnectionError,
    NanoKVMError,
    NanoKVMPermissionError,
)
from .const import API_TIMEOUT, COOKIE_NAME

_SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")
_ISO_NAME_RE = re.compile(r"^[A-Za-z0-9._-]+\.iso$", re.IGNORECASE)
TRANSFER_TIMEOUT = 24 * 60 * 60


def validate_sha256(value: str) -> str:
    """Validate an optional SHA-256 checksum."""
    value = str(value or "").strip().lower()
    if value and not _SHA256_RE.fullmatch(value):
        raise ValueError("SHA-256 must contain exactly 64 hexadecimal characters")
    return value


def validate_iso_filename(filename: str) -> str:
    """Validate an ISO filename accepted by upstream NanoKVM."""
    filename = str(filename or "").strip()
    if not filename or Path(filename).name != filename or ".." in filename:
        raise ValueError("invalid ISO filename")
    if not _ISO_NAME_RE.fullmatch(filename):
        raise ValueError("only .iso files with letters, numbers, dot, dash and underscore are supported")
    return filename


def validate_iso_url(raw_url: str) -> tuple[str, str]:
    """Validate a remote ISO URL and return normalized URL and filename."""
    raw_url = str(raw_url or "").strip()
    if len(raw_url) > 4096:
        raise ValueError("ISO URL is too long")
    parsed = urlparse(raw_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("ISO URL must use http or https")
    if parsed.username or parsed.password:
        raise ValueError("credentials in ISO URL are not allowed")
    filename = validate_iso_filename(Path(parsed.path).name)
    return raw_url, filename


async def async_get_hid_toolbox(client: NanoKVMClient) -> dict[str, Any]:
    """Return HID mode and remote keyboard LED state."""
    mode, leds = await _gather_pair(
        client._request("GET", "/api/hid/mode"),  # noqa: SLF001
        client._request("GET", "/api/hid/leds"),  # noqa: SLF001
    )
    return {
        "mode": str(mode.get("mode") or "unknown"),
        "leds": {
            "numLock": bool(leds.get("numLock")),
            "capsLock": bool(leds.get("capsLock")),
            "scrollLock": bool(leds.get("scrollLock")),
            "known": bool(leds.get("known")),
            "updatedAt": str(leds.get("updatedAt") or ""),
        },
    }


async def _gather_pair(first: Any, second: Any) -> tuple[Any, Any]:
    import asyncio

    result = await asyncio.gather(first, second)
    return result[0], result[1]


async def async_set_hid_mode(client: NanoKVMClient, mode: str) -> None:
    """Set normal or HID-only mode. Upstream reboots NanoKVM after a change."""
    mode = str(mode or "").strip()
    if mode not in {"normal", "hid-only"}:
        raise ValueError("HID mode must be 'normal' or 'hid-only'")
    await client._request("POST", "/api/hid/mode", json_data={"mode": mode})  # noqa: SLF001


async def async_get_image_transfer(client: NanoKVMClient) -> dict[str, Any]:
    """Return NanoKVM image transfer capability and progress."""
    try:
        enabled, status = await _gather_pair(
            client._request("GET", "/api/download/image/enabled"),  # noqa: SLF001
            client._request("GET", "/api/download/image/status"),  # noqa: SLF001
        )
    except NanoKVMError:
        return {
            "supported": False,
            "enabled": False,
            "status": "unsupported",
            "file": "",
            "percentage": "",
        }
    return {
        "supported": True,
        "enabled": bool(enabled.get("enabled")),
        "status": str(status.get("status") or "idle"),
        "file": str(status.get("file") or ""),
        "percentage": str(status.get("percentage") or ""),
    }


async def async_start_image_download(
    client: NanoKVMClient, raw_url: str, checksum: str = ""
) -> str:
    """Ask NanoKVM to download an ISO from URL in the background."""
    raw_url, filename = validate_iso_url(raw_url)
    checksum = validate_sha256(checksum)
    await client._request(  # noqa: SLF001
        "POST",
        "/api/download/image",
        json_data={"file": raw_url, "sha256sum": checksum},
        timeout=30,
    )
    return filename


async def async_cancel_image_download(client: NanoKVMClient) -> None:
    """Cancel NanoKVM's current ISO URL download."""
    await client._request("POST", "/api/download/image/cancel", timeout=20)  # noqa: SLF001


async def _decode_multipart_response(response: aiohttp.ClientResponse) -> dict[str, Any]:
    text = await response.text()
    if response.status == 401:
        raise NanoKVMAuthError("NanoKVM session is unauthorized")
    if response.status == 403:
        raise NanoKVMPermissionError("NanoKVM administrator account is required")
    if response.status >= 500:
        raise NanoKVMConnectionError(f"NanoKVM HTTP {response.status}: {text[:200]}")
    try:
        data = json.loads(text)
    except json.JSONDecodeError as err:
        raise NanoKVMAPIError(
            f"Invalid NanoKVM response (HTTP {response.status})", status=response.status
        ) from err
    if not isinstance(data, dict):
        raise NanoKVMAPIError("Unexpected NanoKVM response format", status=response.status)
    if response.status >= 400:
        raise NanoKVMAPIError(str(data.get("msg") or f"HTTP {response.status}"), status=response.status)
    return data


async def async_upload_iso(
    client: NanoKVMClient,
    file_path: str,
    filename: str,
    checksum: str = "",
) -> None:
    """Upload an ISO file to NanoKVM using its native multipart endpoint."""
    filename = validate_iso_filename(filename)
    checksum = validate_sha256(checksum)

    for attempt in range(2):
        if not client._logged_in:  # noqa: SLF001
            await client.async_login()
        headers: dict[str, str] = {}
        if client._token:  # noqa: SLF001
            headers["Cookie"] = f"{COOKIE_NAME}={client._token}"  # noqa: SLF001
        if checksum:
            headers["X-SHA256-Sum"] = checksum

        form = aiohttp.FormData()
        with open(file_path, "rb") as source:  # noqa: PTH123
            form.add_field(
                "file",
                source,
                filename=filename,
                content_type="application/octet-stream",
            )
            try:
                async with client._session.post(  # noqa: SLF001
                    f"{client.base_url}/api/download/file",
                    data=form,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=TRANSFER_TIMEOUT),
                ) as response:
                    if response.status == 401 and attempt == 0:
                        await response.read()
                        client._logged_in = False  # noqa: SLF001
                        client._token = None  # noqa: SLF001
                        continue
                    data = await _decode_multipart_response(response)
                    client._ensure_success(data)  # noqa: SLF001
                    return
            except NanoKVMError:
                raise
            except (aiohttp.ClientError, TimeoutError) as err:
                raise NanoKVMConnectionError(str(err)) from err

    raise NanoKVMAuthError("NanoKVM authentication failed")
