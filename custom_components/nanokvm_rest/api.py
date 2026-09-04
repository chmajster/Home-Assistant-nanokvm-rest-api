"""Async REST client for NanoKVM."""

from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import os
from http.cookies import SimpleCookie
from typing import Any
from urllib.parse import quote

import aiohttp
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.padding import PKCS7

from .const import API_TIMEOUT, COOKIE_NAME, SECRET_KEY


class NanoKVMError(Exception):
    """Base NanoKVM API error."""


class NanoKVMConnectionError(NanoKVMError):
    """Connection to NanoKVM failed."""


class NanoKVMAuthError(NanoKVMError):
    """Authentication failed."""


class NanoKVMAPIError(NanoKVMError):
    """NanoKVM returned an unsuccessful API response."""


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
                timeout=aiohttp.ClientTimeout(total=API_TIMEOUT),
            ) as response:
                if response.status in (401, 403):
                    if retry_auth:
                        self._logged_in = False
                        self._token = None
                        await self.async_login()
                        return await self._request(
                            method, path, json_data=json_data, retry_auth=False
                        )
                    raise NanoKVMAuthError("NanoKVM session is unauthorized")

                data = await self._decode_response(response)
                if response.status >= 400:
                    message = str(data.get("msg") or f"HTTP {response.status}")
                    raise NanoKVMAPIError(message)

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
            raise NanoKVMAPIError(
                f"Invalid NanoKVM response (HTTP {response.status})"
            ) from err
        if not isinstance(data, dict):
            raise NanoKVMAPIError("Unexpected NanoKVM response format")
        return data

    @staticmethod
    def _ensure_success(data: dict[str, Any], *, auth: bool = False) -> None:
        code = data.get("code")
        if code == 0:
            return
        message = str(data.get("msg") or "NanoKVM API error")
        if auth or code in {-2, -3}:
            raise NanoKVMAuthError(message)
        raise NanoKVMAPIError(f"{message} (code={code})")

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
