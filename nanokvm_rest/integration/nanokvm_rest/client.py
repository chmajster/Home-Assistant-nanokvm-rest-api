"""NanoKVM REST client compatibility layer."""

from __future__ import annotations

import aiohttp

from .api import (
    NanoKVMAuthError,
    NanoKVMClient as _BaseNanoKVMClient,
    NanoKVMConnectionError,
    NanoKVMError,
    encrypt_password,
)
from .const import API_TIMEOUT


class NanoKVMClient(_BaseNanoKVMClient):
    """NanoKVM client compatible with both legacy and current auth responses."""

    async def async_login(self) -> None:
        """Authenticate and preserve tokens returned as a cookie or JSON payload."""
        async with self._login_lock:  # noqa: SLF001
            if self._logged_in:  # noqa: SLF001
                return

            payload = {
                "username": self._username,  # noqa: SLF001
                "password": encrypt_password(self._password),  # noqa: SLF001
            }
            try:
                async with self._session.post(  # noqa: SLF001
                    f"{self._base_url}/api/auth/login",  # noqa: SLF001
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=API_TIMEOUT),
                ) as response:
                    if response.status in (401, 403):
                        raise NanoKVMAuthError("NanoKVM rejected credentials")

                    data = await self._decode_response(response)  # noqa: SLF001
                    self._ensure_success(data, auth=True)  # noqa: SLF001

                    # Current NanoKVM sets an HttpOnly nano-kvm-token cookie.
                    # Older firmware returned the same JWT in data.token and
                    # expected the web client to create the cookie itself.
                    token = self._extract_token(response)  # noqa: SLF001
                    if token is None:
                        response_data = data.get("data")
                        if isinstance(response_data, dict):
                            legacy_token = response_data.get("token")
                            if isinstance(legacy_token, str) and legacy_token:
                                token = legacy_token

                    self._token = token  # noqa: SLF001
                    self._logged_in = True  # noqa: SLF001
            except NanoKVMError:
                raise
            except (aiohttp.ClientError, TimeoutError) as err:
                raise NanoKVMConnectionError(str(err)) from err
