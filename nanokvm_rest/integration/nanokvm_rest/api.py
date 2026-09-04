"""Async REST client for NanoKVM."""

from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import os
import re
from http.cookies import SimpleCookie
from typing import Any
from urllib.parse import quote, urlparse

import aiohttp
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.padding import PKCS7

from .const import (
    API_TIMEOUT,
    APPLICATION_UPDATE_TIMEOUT,
    COOKIE_NAME,
    MAX_MEMORY_LIMIT_MB,
    MAX_OLED_SLEEP_SECONDS,
    MAX_SWAP_SIZE_MB,
    MIN_MEMORY_LIMIT_MB,
    MIN_OLED_SLEEP_SECONDS,
    MIN_SWAP_SIZE_MB,
    SECRET_KEY,
)

_MAC_RE = re.compile(r"^(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}$")


class NanoKVMError(Exception):
    """Base NanoKVM API error."""


class NanoKVMConnectionError(NanoKVMError):
    """Connection to NanoKVM failed."""


class NanoKVMAuthError(NanoKVMError):
    """Authentication failed."""


class NanoKVMPermissionError(NanoKVMError):
    """The authenticated NanoKVM account lacks permission for an action."""


class NanoKVMAPIError(NanoKVMError):
    """NanoKVM returned an unsuccessful API response."""

    def __init__(
        self,
        message: str,
        *,
        status: int | None = None,
        code: int | str | None = None,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.code = code


def _evp_bytes_to_key(passphrase: bytes, salt: bytes) -> tuple[bytes, bytes]:
    """Implement OpenSSL/CryptoJS EVP_BytesToKey (MD5) for AES-256-CBC."""
    derived = b""
    block = b""
    while len(derived) < 48:
        block = hashlib.md5(block + passphrase + salt).digest()  # noqa: S324
        derived += block
    return derived[:32], derived[32:48]


def encrypt_password(password: str) -> str:
    """Match CryptoJS.AES.encrypt(password, SECRET_KEY).toString()."""
    salt = os.urandom(8)
    key, iv = _evp_bytes_to_key(SECRET_KEY.encode(), salt)

    padder = PKCS7(128).padder()
    padded = padder.update(password.encode()) + padder.finalize()

    encryptor = Cipher(algorithms.AES(key), modes.CBC(iv)).encryptor()
    encrypted = encryptor.update(padded) + encryptor.finalize()

    openssl_payload = b"Salted__" + salt + encrypted
    return quote(base64.b64encode(openssl_payload).decode(), safe="")


class NanoKVMClient:
    """NanoKVM REST API client using Home Assistant's aiohttp session."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        base_url: str,
        username: str,
        password: str,
    ) -> None:
        self._session = session
        self._base_url = base_url.rstrip("/")
        self._username = username
        self._password = password
        self._token: str | None = None
        self._logged_in = False
        self._login_lock = asyncio.Lock()

    @property
    def base_url(self) -> str:
        """Return the configured NanoKVM base URL."""
        return self._base_url

    async def async_login(self) -> None:
        """Authenticate and store the NanoKVM session cookie locally."""
        async with self._login_lock:
            if self._logged_in:
                return

            payload = {
                "username": self._username,
                "password": encrypt_password(self._password),
            }
            try:
                async with self._session.post(
                    f"{self._base_url}/api/auth/login",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=API_TIMEOUT),
                ) as response:
                    if response.status in (401, 403):
                        raise NanoKVMAuthError("NanoKVM rejected credentials")
                    data = await self._decode_response(response)
                    self._ensure_success(data, auth=True)
                    self._token = self._extract_token(response)
                    self._logged_in = True
            except NanoKVMError:
                raise
            except (aiohttp.ClientError, TimeoutError) as err:
                raise NanoKVMConnectionError(str(err)) from err

    async def async_get_account(self) -> dict[str, Any]:
        """Return information about the authenticated NanoKVM account."""
        return await self._request("GET", "/api/auth/account")

    async def async_get_info(self) -> dict[str, Any]:
        """Return NanoKVM device information."""
        return await self._request("GET", "/api/vm/info")

    async def async_get_hardware(self) -> dict[str, Any]:
        """Return NanoKVM hardware information."""
        return await self._request("GET", "/api/vm/hardware")

    async def async_get_gpio(self) -> dict[str, Any]:
        """Return GPIO/LED state."""
        return await self._request("GET", "/api/vm/gpio")

    async def async_get_hostname(self) -> dict[str, Any]:
        """Return NanoKVM hostname."""
        return await self._request("GET", "/api/vm/hostname")

    async def async_set_hostname(self, hostname: str) -> None:
        """Set the NanoKVM hostname."""
        hostname = hostname.strip()
        if not hostname or len(hostname) > 63:
            raise ValueError("hostname must contain 1 to 63 characters")
        await self._request(
            "POST", "/api/vm/hostname", json_data={"hostname": hostname}
        )

    async def async_get_web_title(self) -> dict[str, Any]:
        """Return NanoKVM web interface title."""
        return await self._request("GET", "/api/vm/web-title")

    async def async_set_web_title(self, title: str) -> None:
        """Set the NanoKVM web interface title."""
        title = title.strip()
        if not title or len(title) > 128:
            raise ValueError("title must contain 1 to 128 characters")
        await self._request("POST", "/api/vm/web-title", json_data={"title": title})

    async def async_get_hdmi(self) -> dict[str, Any]:
        """Return HDMI state for PCIe NanoKVM hardware."""
        return await self._request("GET", "/api/vm/hdmi")

    async def async_set_hdmi(self, enabled: bool) -> None:
        """Enable or disable HDMI capture."""
        path = "/api/vm/hdmi/enable" if enabled else "/api/vm/hdmi/disable"
        await self._request("POST", path)

    async def async_reset_hdmi(self) -> None:
        """Reset the NanoKVM HDMI subsystem."""
        await self._request("POST", "/api/vm/hdmi/reset")

    async def async_set_hdmi_idle_timeout(self, minutes: int) -> None:
        """Set HDMI idle timeout in minutes."""
        if not 0 <= minutes <= 10080:
            raise ValueError("minutes must be between 0 and 10080")
        await self._request(
            "POST",
            "/api/vm/hdmi/timeout",
            json_data={"minutes": minutes},
        )

    async def async_get_ssh(self) -> dict[str, Any]:
        """Return SSH service state."""
        return await self._request("GET", "/api/vm/ssh")

    async def async_set_ssh(self, enabled: bool) -> None:
        """Enable or disable SSH on NanoKVM."""
        path = "/api/vm/ssh/enable" if enabled else "/api/vm/ssh/disable"
        await self._request("POST", path)

    async def async_get_mdns(self) -> dict[str, Any]:
        """Return mDNS service state."""
        return await self._request("GET", "/api/vm/mdns")

    async def async_set_mdns(self, enabled: bool) -> None:
        """Enable or disable mDNS on NanoKVM."""
        path = "/api/vm/mdns/enable" if enabled else "/api/vm/mdns/disable"
        await self._request("POST", path)

    async def async_get_mouse_jiggler(self) -> dict[str, Any]:
        """Return mouse jiggler state."""
        return await self._request("GET", "/api/vm/mouse-jiggler")

    async def async_set_mouse_jiggler(self, enabled: bool, mode: str) -> None:
        """Enable or disable the mouse jiggler while preserving its mode."""
        await self._request(
            "POST",
            "/api/vm/mouse-jiggler",
            json_data={"enabled": enabled, "mode": mode},
        )

    async def async_get_swap(self) -> dict[str, Any]:
        """Return configured swap file size in MB."""
        return await self._request("GET", "/api/vm/swap")

    async def async_set_swap(self, size_mb: int) -> None:
        """Set or disable the NanoKVM swap file."""
        if not MIN_SWAP_SIZE_MB <= size_mb <= MAX_SWAP_SIZE_MB:
            raise ValueError(
                f"swap size must be between {MIN_SWAP_SIZE_MB} and "
                f"{MAX_SWAP_SIZE_MB} MB"
            )
        await self._request(
            "POST", "/api/vm/swap", json_data={"size": int(size_mb)}
        )

    async def async_get_memory_limit(self) -> dict[str, Any]:
        """Return the NanoKVM Go runtime memory limit."""
        return await self._request("GET", "/api/vm/memory/limit")

    async def async_set_memory_limit(self, enabled: bool, limit_mb: int) -> None:
        """Enable, disable or change the NanoKVM memory limit."""
        if enabled and not MIN_MEMORY_LIMIT_MB <= limit_mb <= MAX_MEMORY_LIMIT_MB:
            raise ValueError(
                f"memory limit must be between {MIN_MEMORY_LIMIT_MB} and "
                f"{MAX_MEMORY_LIMIT_MB} MB"
            )
        await self._request(
            "POST",
            "/api/vm/memory/limit",
            json_data={"enabled": enabled, "limit": int(limit_mb if enabled else 0)},
        )

    async def async_get_oled(self) -> dict[str, Any]:
        """Return OLED availability and sleep timeout."""
        return await self._request("GET", "/api/vm/oled")

    async def async_set_oled_sleep(self, seconds: int) -> None:
        """Set OLED sleep timeout in seconds."""
        if not MIN_OLED_SLEEP_SECONDS <= seconds <= MAX_OLED_SLEEP_SECONDS:
            raise ValueError(
                f"OLED sleep must be between {MIN_OLED_SLEEP_SECONDS} and "
                f"{MAX_OLED_SLEEP_SECONDS} seconds"
            )
        await self._request("POST", "/api/vm/oled", json_data={"sleep": int(seconds)})

    async def async_get_virtual_devices(self) -> dict[str, Any]:
        """Return NanoKVM virtual USB device states."""
        return await self._request("GET", "/api/vm/device/virtual")

    async def async_set_virtual_device(self, device: str, enabled: bool) -> None:
        """Set a toggle-only NanoKVM virtual USB device idempotently."""
        if device not in {"network", "disk"}:
            raise ValueError("device must be 'network' or 'disk'")
        current = await self.async_get_virtual_devices()
        if bool(current.get(device)) == enabled:
            return
        await self._request(
            "POST", "/api/vm/device/virtual", json_data={"device": device}
        )

    async def async_get_application_version(self) -> dict[str, Any]:
        """Return installed and latest NanoKVM application versions."""
        return await self._request("GET", "/api/application/version", timeout=20)

    async def async_get_preview_updates(self) -> dict[str, Any]:
        """Return whether NanoKVM preview updates are enabled."""
        return await self._request("GET", "/api/application/preview")

    async def async_set_preview_updates(self, enabled: bool) -> None:
        """Enable or disable NanoKVM preview updates."""
        await self._request(
            "POST", "/api/application/preview", json_data={"enable": enabled}
        )

    async def async_get_update_server(self) -> dict[str, Any]:
        """Return custom NanoKVM update-server configuration."""
        return await self._request("GET", "/api/application/update-server")

    async def async_set_update_server(self, enabled: bool, url: str) -> None:
        """Configure NanoKVM's custom application update server."""
        url = url.strip()
        if url:
            if len(url) > 2048:
                raise ValueError("update server URL must not exceed 2048 characters")
            parsed = urlparse(url)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                raise ValueError("update server URL must use http or https")
            if parsed.username or parsed.password:
                raise ValueError("credentials are not allowed in the update server URL")
            if parsed.query or parsed.fragment:
                raise ValueError("update server URL must not contain query or fragment")
        if enabled and not url:
            raise ValueError("update server URL is required when enabling it")
        await self._request(
            "POST",
            "/api/application/update-server",
            json_data={"enabled": enabled, "url": url},
        )

    async def async_update_application(self) -> None:
        """Update the NanoKVM application to the latest available version."""
        await self._request(
            "POST",
            "/api/application/update",
            timeout=APPLICATION_UPDATE_TIMEOUT,
        )

    async def async_wake_on_lan(self, mac: str) -> None:
        """Send Wake-on-LAN through NanoKVM."""
        mac = mac.strip()
        if not _MAC_RE.fullmatch(mac):
            raise ValueError("invalid MAC address")
        await self._request("POST", "/api/network/wol", json_data={"mac": mac})

    async def async_get_images(self) -> dict[str, Any]:
        """Return virtual-media image list."""
        return await self._request("GET", "/api/storage/image")

    async def async_get_mounted_image(self) -> dict[str, Any]:
        """Return the currently mounted virtual-media image."""
        return await self._request("GET", "/api/storage/image/mounted")

    async def async_mount_image(self, file_name: str, cdrom: bool = True) -> None:
        """Mount a virtual-media image."""
        file_name = file_name.strip()
        if not file_name:
            raise ValueError("image file name must not be empty")
        await self._request(
            "POST",
            "/api/storage/image/mount",
            json_data={"file": file_name, "cdrom": bool(cdrom)},
        )

    async def async_unmount_image(self) -> None:
        """Unmount the current virtual-media image."""
        await self._request(
            "POST",
            "/api/storage/image/mount",
            json_data={"file": "", "cdrom": True},
        )

    async def async_paste_text(self, content: str, language: str = "en") -> None:
        """Paste text to the remote host through NanoKVM HID."""
        if not content:
            raise ValueError("content must not be empty")
        await self._request(
            "POST",
            "/api/hid/paste",
            json_data={"content": content, "langue": language or "en"},
        )

    async def async_reboot(self) -> None:
        """Reboot the NanoKVM device itself."""
        await self._request("POST", "/api/vm/system/reboot")

    async def async_press_button(self, button_type: str, duration_ms: int) -> None:
        """Press the target power or reset button through NanoKVM GPIO."""
        if button_type not in {"power", "reset"}:
            raise ValueError("button_type must be 'power' or 'reset'")
        if not 100 <= duration_ms <= 10000:
            raise ValueError("duration_ms must be between 100 and 10000")
        await self._request(
            "POST",
            "/api/vm/gpio",
            json_data={"type": button_type, "duration": duration_ms},
        )

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json_data: dict[str, Any] | None = None,
        retry_auth: bool = True,
        timeout: int = API_TIMEOUT,
    ) -> dict[str, Any]:
        if not self._logged_in:
            await self.async_login()

        headers: dict[str, str] = {}
        if self._token:
            headers["Cookie"] = f"{COOKIE_NAME}={self._token}"

        try:
            async with self._session.request(
                method,
                f"{self._base_url}{path}",
                json=json_data,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=timeout),
            ) as response:
                if response.status == 401:
                    if retry_auth:
                        self._logged_in = False
                        self._token = None
                        await self.async_login()
                        return await self._request(
                            method,
                            path,
                            json_data=json_data,
                            retry_auth=False,
                            timeout=timeout,
                        )
                    raise NanoKVMAuthError("NanoKVM session is unauthorized")

                if response.status == 403:
                    await response.read()
                    raise NanoKVMPermissionError(
                        f"NanoKVM account is not allowed to access {path}"
                    )

                data = await self._decode_response(response)
                self._ensure_success(data)
                result = data.get("data")
                return result if isinstance(result, dict) else {}
        except NanoKVMError:
            raise
        except (aiohttp.ClientError, TimeoutError) as err:
            raise NanoKVMConnectionError(str(err)) from err

    @staticmethod
    async def _decode_response(response: aiohttp.ClientResponse) -> dict[str, Any]:
        text = await response.text()
        if response.status >= 500:
            raise NanoKVMConnectionError(
                f"NanoKVM HTTP {response.status}: {text[:200]}"
            )

        try:
            data = json.loads(text)
        except json.JSONDecodeError as err:
            if response.status >= 400:
                raise NanoKVMAPIError(
                    f"NanoKVM HTTP {response.status}", status=response.status
                ) from err
            raise NanoKVMAPIError(
                f"Invalid NanoKVM response (HTTP {response.status})",
                status=response.status,
            ) from err

        if response.status >= 400:
            if isinstance(data, dict):
                message = str(data.get("msg") or f"HTTP {response.status}")
            else:
                message = str(data)
            raise NanoKVMAPIError(message, status=response.status)

        if not isinstance(data, dict):
            raise NanoKVMAPIError(
                "Unexpected NanoKVM response format", status=response.status
            )
        return data

    @staticmethod
    def _ensure_success(data: dict[str, Any], *, auth: bool = False) -> None:
        code = data.get("code")
        if code == 0:
            return
        message = str(data.get("msg") or "NanoKVM API error")
        if auth or code in {-2, -3}:
            raise NanoKVMAuthError(message)
        raise NanoKVMAPIError(f"{message} (code={code})", code=code)

    @staticmethod
    def _extract_token(response: aiohttp.ClientResponse) -> str | None:
        morsel = response.cookies.get(COOKIE_NAME)
        if morsel is not None:
            return morsel.value

        raw_cookie = response.headers.get("Set-Cookie")
        if not raw_cookie:
            return None
        cookie = SimpleCookie()
        cookie.load(raw_cookie)
        morsel = cookie.get(COOKIE_NAME)
        return morsel.value if morsel else None
