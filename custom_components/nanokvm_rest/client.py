"""NanoKVM REST client compatibility layer."""

from __future__ import annotations

from typing import Any
from urllib.parse import ParseResult, urljoin, urlparse

import aiohttp

from .api import (
    NanoKVMAPIError,
    NanoKVMAuthError,
    NanoKVMClient as _BaseNanoKVMClient,
    NanoKVMConnectionError,
    NanoKVMError,
    NanoKVMPermissionError,
    encrypt_password,
)
from .const import API_TIMEOUT, COOKIE_NAME

_LOGIN_REDIRECTS = {301, 302, 303, 307, 308}
_MAX_LOGIN_REDIRECTS = 4
_SCHEME_FALLBACK_HTTP_STATUSES = {400, 404, 405, 421, 426}


class NanoKVMClient(_BaseNanoKVMClient):
    """NanoKVM client compatible with legacy and current authentication."""

    async def async_login(self) -> None:
        """Authenticate and automatically detect whether NanoKVM uses HTTP or HTTPS."""
        async with self._login_lock:  # noqa: SLF001
            if self._logged_in:  # noqa: SLF001
                return

            payload = {
                "username": self._username,  # noqa: SLF001
                "password": encrypt_password(self._password),  # noqa: SLF001
            }

            failures: list[str] = []
            for origin in self._candidate_origins():
                try:
                    await self._async_login_origin(origin, payload)
                    return
                except NanoKVMAuthError:
                    # Do not submit valid-looking authentication requests twice.
                    # This avoids triggering NanoKVM brute-force protection.
                    raise
                except NanoKVMAPIError as err:
                    if not self._should_try_alternate_scheme(err):
                        raise
                    failures.append(f"{origin}: {err}")
                except NanoKVMConnectionError as err:
                    failures.append(f"{origin}: {err}")

            detail = "; ".join(failures[-2:]) or "no usable HTTP/HTTPS endpoint"
            raise NanoKVMConnectionError(
                f"Unable to connect to NanoKVM over HTTP or HTTPS ({detail})"
            )

    def _candidate_origins(self) -> tuple[str, ...]:
        """Return the configured origin followed by its HTTP/HTTPS alternative."""
        value = self._base_url.strip().rstrip("/")  # noqa: SLF001
        parsed = urlparse(value)

        if parsed.scheme in {"http", "https"} and parsed.netloc:
            primary = f"{parsed.scheme}://{parsed.netloc}"
            alternate_scheme = "https" if parsed.scheme == "http" else "http"
            alternate = self._alternate_origin(parsed, alternate_scheme)
            return tuple(item for item in dict.fromkeys((primary, alternate)) if item)

        # Be defensive for legacy/manual config entries without a scheme.
        host = value.split("://", 1)[-1].strip("/")
        return (f"https://{host}", f"http://{host}")

    @staticmethod
    def _alternate_origin(parsed: ParseResult, scheme: str) -> str:
        """Build an alternate HTTP/HTTPS origin while handling default ports."""
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

    async def _async_login_origin(
        self, origin: str, payload: dict[str, str]
    ) -> None:
        """Try one origin and preserve POST semantics across same-host redirects."""
        if not origin:
            raise NanoKVMConnectionError("Invalid NanoKVM origin")

        login_url = f"{origin}/api/auth/login"
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
                        if (
                            parsed_redirect.scheme not in {"http", "https"}
                            or parsed_redirect.hostname != original_host
                        ):
                            raise NanoKVMConnectionError(
                                "NanoKVM login redirected outside the configured host"
                            )

                        login_url = redirected
                        continue

                    if response.status in (401, 403):
                        await response.read()
                        raise NanoKVMAuthError("NanoKVM rejected credentials")

                    data = await self._decode_response(response)  # noqa: SLF001
                    self._ensure_login_success(data)

                    effective_origin = self._origin_from_url(str(response.url))
                    self._base_url = effective_origin or origin  # noqa: SLF001

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

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json_data: dict[str, Any] | None = None,
        retry_auth: bool = True,
        timeout: int = API_TIMEOUT,
    ) -> dict[str, Any]:
        """Call an API endpoint while preserving the HTTP method across redirects."""
        if not self._logged_in:  # noqa: SLF001
            await self.async_login()

        headers: dict[str, str] = {}
        if self._token:  # noqa: SLF001
            headers["Cookie"] = f"{COOKIE_NAME}={self._token}"  # noqa: SLF001

        request_url = f"{self._base_url}{path}"  # noqa: SLF001
        original_host = urlparse(request_url).hostname

        try:
            for _ in range(_MAX_LOGIN_REDIRECTS + 1):
                async with self._session.request(  # noqa: SLF001
                    method,
                    request_url,
                    json=json_data,
                    headers=headers,
                    allow_redirects=False,
                    timeout=aiohttp.ClientTimeout(total=timeout),
                ) as response:
                    if response.status in _LOGIN_REDIRECTS:
                        location = response.headers.get("Location")
                        if not location:
                            raise NanoKVMConnectionError(
                                "NanoKVM returned a redirect without Location"
                            )

                        redirected = urljoin(str(response.url), location)
                        parsed_redirect = urlparse(redirected)
                        if (
                            parsed_redirect.scheme not in {"http", "https"}
                            or parsed_redirect.hostname != original_host
                        ):
                            raise NanoKVMConnectionError(
                                "NanoKVM API redirected outside the configured host"
                            )

                        request_url = redirected
                        continue

                    if response.status == 401:
                        await response.read()
                        if retry_auth:
                            self._logged_in = False  # noqa: SLF001
                            self._token = None  # noqa: SLF001
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

                    data = await self._decode_response(response)  # noqa: SLF001
                    self._ensure_success(data)

                    effective_origin = self._origin_from_url(str(response.url))
                    if effective_origin:
                        self._base_url = effective_origin  # noqa: SLF001

                    result = data.get("data")
                    return result if isinstance(result, dict) else {}

            raise NanoKVMConnectionError("Too many NanoKVM API redirects")
        except NanoKVMError:
            raise
        except (aiohttp.ClientError, TimeoutError) as err:
            raise NanoKVMConnectionError(str(err)) from err

    @staticmethod
    def _origin_from_url(value: str) -> str | None:
        """Return only the HTTP/HTTPS origin from a URL."""
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            return None
        return f"{parsed.scheme}://{parsed.netloc}"

    @staticmethod
    def _should_try_alternate_scheme(err: NanoKVMAPIError) -> bool:
        """Return whether the response looks like the wrong protocol/endpoint."""
        if err.status in _SCHEME_FALLBACK_HTTP_STATUSES:
            return True

        message = str(err).casefold()
        return (
            "invalid nanokvm response" in message
            or "unexpected nanokvm response format" in message
        )

    @staticmethod
    def _ensure_login_success(data: dict[str, object]) -> None:
        """Only classify an actual credential rejection as invalid credentials."""
        code = data.get("code")
        if code == 0:
            return

        message = str(data.get("msg") or "NanoKVM authentication error")
        normalized = message.casefold()
        if (
            code in {-2, -4}
            or "invalid username or password" in normalized
            or "invalid login or password" in normalized
            or "invalid credentials" in normalized
        ):
            raise NanoKVMAuthError(message)

        # NanoKVM also returns non-zero auth-endpoint codes for protocol errors,
        # temporary lockouts and backend failures. Those are not bad passwords.
        raise NanoKVMAPIError(f"{message} (code={code})", code=code)

    @staticmethod
    def _ensure_success(data: dict[str, Any], *, auth: bool = False) -> None:
        """Treat non-zero API codes as API errors unless this is an auth call."""
        code = data.get("code")
        if code == 0:
            return

        message = str(data.get("msg") or "NanoKVM API error")
        if auth:
            raise NanoKVMAuthError(message)
        raise NanoKVMAPIError(f"{message} (code={code})", code=code)
