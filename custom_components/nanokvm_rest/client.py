"""NanoKVM REST client compatibility layer."""

from __future__ import annotations

from urllib.parse import urljoin, urlparse

import aiohttp

from .api import (
    NanoKVMAPIError,
    NanoKVMAuthError,
    NanoKVMClient as _BaseNanoKVMClient,
    NanoKVMConnectionError,
    NanoKVMError,
    encrypt_password,
)
from .const import API_TIMEOUT

_LOGIN_REDIRECTS = {301, 302, 303, 307, 308}
_MAX_LOGIN_REDIRECTS = 4


class NanoKVMClient(_BaseNanoKVMClient):
    """NanoKVM client compatible with legacy and current authentication."""

    async def async_login(self) -> None:
        """Authenticate while preserving NanoKVM's POST semantics and session token."""
        async with self._login_lock:  # noqa: SLF001
            if self._logged_in:  # noqa: SLF001
                return

            payload = {
                "username": self._username,  # noqa: SLF001
                "password": encrypt_password(self._password),  # noqa: SLF001
            }
            login_url = f"{self._base_url}/api/auth/login"  # noqa: SLF001
            original_host = urlparse(login_url).hostname

            try:
                for _ in range(_MAX_LOGIN_REDIRECTS + 1):
                    async with self._session.post(  # noqa: SLF001
                        login_url,
                        json=payload,
                        allow_redirects=False,
                        timeout=aiohttp.ClientTimeout(total=API_TIMEOUT),
                    ) as response:
                        if response.status in _LOGIN_REDIRECTS:
                            location = response.headers.get("Location")
                            if not location:
                                raise NanoKVMConnectionError(
                                    "NanoKVM returned a redirect without Location"
                                )
                            redirected = urljoin(str(response.url), location)
                            parsed_redirect = urlparse(redirected)
                            if parsed_redirect.hostname != original_host:
                                raise NanoKVMConnectionError(
                                    "NanoKVM login redirected to a different host"
                                )
                            login_url = redirected
                            continue

                        if response.status in (401, 403):
                            await response.read()
                            raise NanoKVMAuthError("NanoKVM rejected credentials")

                        data = await self._decode_response(response)  # noqa: SLF001
                        self._ensure_login_success(data)

                        # Keep the effective origin. This matters when a NanoKVM
                        # configured for HTTPS redirects an entered http:// URL.
                        parsed_response = urlparse(str(response.url))
                        if parsed_response.scheme and parsed_response.netloc:
                            self._base_url = (  # noqa: SLF001
                                f"{parsed_response.scheme}://{parsed_response.netloc}"
                            )

                        # Current firmware sets an HttpOnly nano-kvm-token cookie.
                        # Legacy firmware returns the JWT in data.token instead.
                        token = self._extract_token(response)  # noqa: SLF001
                        if token is None:
                            response_data = data.get("data")
                            if isinstance(response_data, dict):
                                legacy_token = response_data.get("token")
                                if isinstance(legacy_token, str) and legacy_token:
                                    token = legacy_token

                        self._token = token  # noqa: SLF001
                        self._logged_in = True  # noqa: SLF001
                        return

                raise NanoKVMConnectionError("Too many NanoKVM login redirects")
            except NanoKVMError:
                raise
            except (aiohttp.ClientError, TimeoutError) as err:
                raise NanoKVMConnectionError(str(err)) from err

    @staticmethod
    def _ensure_login_success(data: dict[str, object]) -> None:
        """Only classify an actual credential rejection as invalid credentials."""
        code = data.get("code")
        if code == 0:
            return

        message = str(data.get("msg") or "NanoKVM authentication error")
        normalized = message.casefold()
        if (
            "invalid username or password" in normalized
            or "invalid login or password" in normalized
            or "invalid credentials" in normalized
        ):
            raise NanoKVMAuthError(message)

        # NanoKVM also returns non-zero auth-endpoint codes for protocol errors,
        # temporary lockouts and backend failures. Those are not bad passwords.
        raise NanoKVMAPIError(f"{message} (code={code})", code=code)
