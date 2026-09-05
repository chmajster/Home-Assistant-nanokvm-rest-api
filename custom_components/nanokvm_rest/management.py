"""Advanced management helpers for NanoKVM REST."""

from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path
from typing import Any

import aiohttp

from .api import (
    NanoKVMAPIError,
    NanoKVMAuthError,
    NanoKVMClient,
    NanoKVMConnectionError,
    NanoKVMPermissionError,
)
from .const import APPLICATION_UPDATE_TIMEOUT, COOKIE_NAME

_OFFLINE_UPDATE_RE = re.compile(r"^nanokvm_\d+\.\d+\.\d+\.tar\.gz$")
_SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")


async def async_reset_hid(client: NanoKVMClient) -> None:
    """Reset the NanoKVM HID subsystem."""
    await client._request("POST", "/api/hid/reset")  # noqa: SLF001


async def async_get_virtual_media(client: NanoKVMClient) -> dict[str, Any]:
    """Return virtual-media images, mounted image and CD-ROM mode."""
    images, mounted, cdrom = await asyncio.gather(
        client.async_get_images(),
        client.async_get_mounted_image(),
        client._request("GET", "/api/storage/cdrom"),  # noqa: SLF001
    )
    files = images.get("files")
    if not isinstance(files, list):
        files = []
    mounted_file = str(mounted.get("file") or "")
    return {
        "files": [str(item) for item in files],
        "mounted": mounted_file,
        "cdrom": bool(int(cdrom.get("cdrom") or 0)),
    }


async def async_delete_image(client: NanoKVMClient, file_name: str) -> None:
    """Delete an existing NanoKVM ISO/IMG after validating it against the device list."""
    file_name = file_name.strip()
    media = await async_get_virtual_media(client)
    if file_name not in media["files"]:
        raise ValueError("image is not present on NanoKVM")
    if file_name == media["mounted"]:
        raise ValueError("mounted image must be unmounted before deletion")
    await client._request(  # noqa: SLF001
        "POST",
        "/api/storage/image/delete",
        json_data={"file": file_name},
    )


async def async_set_cdrom_mode(client: NanoKVMClient, cdrom: bool) -> None:
    """Remount the current image using CD-ROM or writable disk emulation."""
    mounted = await client.async_get_mounted_image()
    file_name = str(mounted.get("file") or "")
    if not file_name:
        raise ValueError("no virtual-media image is mounted")
    await client.async_mount_image(file_name, cdrom=cdrom)


def validate_offline_update(filename: str, checksum: str) -> tuple[str, str]:
    """Validate an offline update package filename and optional checksum."""
    filename = Path(filename).name
    checksum = checksum.strip()
    if not _OFFLINE_UPDATE_RE.fullmatch(filename):
        raise ValueError("package name must match nanokvm_X.Y.Z.tar.gz")
    if checksum and not _SHA256_RE.fullmatch(checksum):
        raise ValueError("SHA-256 checksum must contain exactly 64 hexadecimal characters")
    return filename, checksum.lower()


async def async_offline_update(
    client: NanoKVMClient,
    file_path: str,
    filename: str,
    checksum: str = "",
) -> None:
    """Upload and install a local NanoKVM application package."""
    filename, checksum = validate_offline_update(filename, checksum)

    for attempt in range(2):
        if not client._logged_in:  # noqa: SLF001
            await client.async_login()

        headers: dict[str, str] = {}
        if client._token:  # noqa: SLF001
            headers["Cookie"] = f"{COOKIE_NAME}={client._token}"  # noqa: SLF001
        if checksum:
            headers["X-SHA256-Checksum"] = checksum

        form = aiohttp.FormData()
        with open(file_path, "rb") as package:  # noqa: PTH123
            form.add_field(
                "file",
                package,
                filename=filename,
                content_type="application/gzip",
            )
            try:
                async with client._session.post(  # noqa: SLF001
                    f"{client.base_url}/api/application/update/offline",
                    data=form,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=APPLICATION_UPDATE_TIMEOUT),
                ) as response:
                    if response.status == 401 and attempt == 0:
                        await response.read()
                        client._logged_in = False  # noqa: SLF001
                        client._token = None  # noqa: SLF001
                        continue
                    if response.status == 401:
                        raise NanoKVMAuthError("NanoKVM session is unauthorized")
                    if response.status == 403:
                        await response.read()
                        raise NanoKVMPermissionError(
                            "NanoKVM account is not allowed to perform offline updates"
                        )
                    # Upstream UI explicitly treats a 502 during service restart as success.
                    if response.status == 502:
                        return

                    text = await response.text()
                    if response.status >= 500:
                        raise NanoKVMConnectionError(
                            f"NanoKVM HTTP {response.status}: {text[:200]}"
                        )
                    try:
                        data = json.loads(text)
                    except json.JSONDecodeError as err:
                        raise NanoKVMAPIError(
                            f"Invalid NanoKVM response (HTTP {response.status})",
                            status=response.status,
                        ) from err
                    if response.status >= 400:
                        message = str(data.get("msg") or f"HTTP {response.status}")
                        raise NanoKVMAPIError(message, status=response.status)
                    client._ensure_success(data)  # noqa: SLF001
                    return
            except (aiohttp.ClientError, TimeoutError) as err:
                raise NanoKVMConnectionError(str(err)) from err

    raise NanoKVMAuthError("NanoKVM authentication failed")
