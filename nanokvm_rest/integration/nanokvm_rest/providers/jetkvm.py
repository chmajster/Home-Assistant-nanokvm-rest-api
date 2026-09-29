"""Official JetKVM local HTTP authentication and WebRTC signaling transport.

Protocol reference: jetkvm/kvm 939422c8b00b423f6320db04df4adfbc6d2b3012.
This client owns a private cookie context; it never shares JetKVM cookies with
Home Assistant's shared session or exposes them to a browser.
"""

from __future__ import annotations

import asyncio
import errno
import json
import logging
import re
import socket
import ssl
import time
from typing import Any

import aiohttp

from .errors import KVMError
from .network import DeviceOrigin, LANPolicy, LANResolver

_LOGGER = logging.getLogger(__name__)
HTTP_TIMEOUT = aiohttp.ClientTimeout(total=8, connect=4, sock_connect=3, sock_read=5)
MAX_JSON = 256 * 1024
SIGNALING_PATH = "/webrtc/signaling/client"
MAC_RE = re.compile(r"(?:[0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}")
COOKIE_RE = re.compile(r"[A-Za-z0-9._-]{1,1024}")


def network_error(err: Exception) -> KVMError:
    """Reduce transport exceptions to safe diagnostic codes, never their repr."""
    if isinstance(err, KVMError):
        return err
    if isinstance(err, (aiohttp.ClientSSLError, aiohttp.ServerFingerprintMismatch, ssl.SSLError)):
        return KVMError("tls_error", type(err).__name__)
    if isinstance(err, (TimeoutError, aiohttp.ServerTimeoutError)):
        return KVMError("timeout", type(err).__name__)
    underlying = getattr(err, "os_error", err)
    if isinstance(underlying, socket.gaierror):
        return KVMError("dns_error", "DNS lookup failed")
    if (
        isinstance(underlying, ConnectionRefusedError)
        or getattr(underlying, "errno", None) == errno.ECONNREFUSED
    ):
        return KVMError("connection_refused", "Connection refused")
    return KVMError("unreachable", type(err).__name__)


class JetKVMClient:
    """A bounded, LAN-only client for one configured JetKVM origin."""

    def __init__(
        self,
        origin: DeviceOrigin,
        password: str = "",
        *,
        verify_ssl: bool = True,
        certificate_sha256: str = "",
        policy: LANPolicy | None = None,
    ):
        self.origin = origin
        self.policy = policy or LANPolicy()
        self.policy.validate_literal(origin.host)
        self._password = password
        self._cookie = ""
        self._session: aiohttp.ClientSession | None = None
        self._auth_lock = asyncio.Lock()
        self._probe_lock = asyncio.Lock()
        self._websockets: set[aiohttp.ClientWebSocketResponse] = set()
        self._ssl: bool | aiohttp.Fingerprint = verify_ssl
        if certificate_sha256:
            digest = certificate_sha256.replace(":", "").lower()
            if not re.fullmatch(r"[a-f0-9]{64}", digest):
                raise KVMError("invalid_data", "Invalid SHA-256 certificate fingerprint")
            self._ssl = aiohttp.Fingerprint(bytes.fromhex(digest))
        self.device: dict[str, Any] = {}
        self.last_latency_ms: float | None = None
        self._closed = False
        self._retry_auth_after = 0.0
        self._auth_failure = "rate_limited"

    @property
    def base_url(self) -> str:
        return self.origin.url

    def _http(self) -> aiohttp.ClientSession:
        if self._closed:
            raise KVMError("unreachable", "Client is closed")
        if self._session is None:

            async def reject_redirect(session, context, params):
                # ws_connect follows redirects internally; block them before
                # aiohttp can forward a device cookie to another origin.
                raise KVMError("protocol_error", "Redirects are not permitted")

            trace = aiohttp.TraceConfig()
            trace.on_request_redirect.append(reject_redirect)
            _LOGGER.info("[JetKVM] connecting %s", self.origin.host)
            self._session = aiohttp.ClientSession(
                connector=aiohttp.TCPConnector(
                    resolver=LANResolver(self.policy),
                    use_dns_cache=False,
                    ssl=self._ssl,
                    limit=4,
                    family=socket.AF_UNSPEC,
                ),
                cookie_jar=aiohttp.DummyCookieJar(),
                timeout=HTTP_TIMEOUT,
                trust_env=False,
                trace_configs=[trace],
                headers={"Accept": "application/json"},
            )
        return self._session

    def _headers(self) -> dict[str, str]:
        return {"Cookie": f"authToken={self._cookie}"} if self._cookie else {}

    async def _json(
        self, method: str, path: str, body: dict | None = None
    ) -> tuple[int, Any, str, int | None]:
        if (method, path) not in {
            ("GET", "/device/status"),
            ("GET", "/device"),
            ("POST", "/auth/login-local"),
        } and not (
            method == "POST"
            and path.startswith("/device/send-wol/")
            and MAC_RE.fullmatch(path.removeprefix("/device/send-wol/"))
        ):
            raise KVMError("unsupported")
        try:
            async with self._http().request(
                method,
                self.base_url + path,
                json=body,
                headers=self._headers(),
                allow_redirects=False,
            ) as response:
                if 300 <= response.status < 400:
                    raise KVMError("protocol_error", "Redirects are not permitted")
                raw = bytearray()
                async for chunk in response.content.iter_chunked(16384):
                    raw.extend(chunk)
                    if len(raw) > MAX_JSON:
                        raise KVMError("protocol_error", "Device response exceeds size limit")
                try:
                    data = json.loads(raw) if raw else None
                except (ValueError, UnicodeError):
                    data = None
                cookie = response.cookies.get("authToken")
                token = cookie.value if cookie and COOKIE_RE.fullmatch(cookie.value) else ""
                retry = response.headers.get("Retry-After", "")
                retry_after = min(int(retry), 3600) if retry.isdecimal() else None
                return response.status, data, token, retry_after
        except (aiohttp.ClientError, OSError, TimeoutError, KVMError) as err:
            raise network_error(err) from err

    async def _login(self, rejected_cookie: str) -> None:
        async with self._auth_lock:
            if self._cookie and self._cookie != rejected_cookie:
                return  # A concurrent request already renewed the session.
            if not self._password:
                raise KVMError("authentication_required")
            if time.monotonic() < self._retry_auth_after:
                raise KVMError(
                    self._auth_failure,
                    retry_after=max(1, int(self._retry_auth_after - time.monotonic())),
                )
            _LOGGER.info("[JetKVM] authentication required %s", self.origin.host)
            status, _, cookie, retry = await self._json(
                "POST", "/auth/login-local", {"password": self._password}
            )
            if status == 401:
                # Bound invalid-password retries from health monitoring.
                self._auth_failure = "invalid_password"
                self._retry_auth_after = time.monotonic() + 60
                raise KVMError("invalid_password", "HTTP 401")
            if status == 429:
                self._auth_failure = "rate_limited"
                self._retry_auth_after = time.monotonic() + (retry or 60)
                raise KVMError("rate_limited", "HTTP 429", retry_after=retry or 60)
            if status != 200 or not cookie:
                raise KVMError(
                    "protocol_error", f"Local login returned HTTP {status} without a valid session"
                )
            self._cookie = cookie
            _LOGGER.info("[JetKVM] authenticated %s", self.origin.host)

    async def _authorized_json(self, method: str, path: str, body: dict | None = None) -> Any:
        rejected_cookie = self._cookie
        status, data, _, retry = await self._json(method, path, body)
        if status == 401:
            await self._login(rejected_cookie)
            status, data, _, retry = await self._json(method, path, body)
        if status == 401:
            raise KVMError("invalid_password", "Session rejected after one reauthentication")
        if status == 403:
            raise KVMError("permission_denied", "HTTP 403")
        if status == 429:
            raise KVMError("rate_limited", "HTTP 429", retry_after=retry)
        if not 200 <= status < 300:
            raise KVMError("protocol_error", f"Device returned HTTP {status}")
        return data

    async def test_connection(self) -> dict:
        """Probe public status first; only then attempt protected local access."""
        async with self._probe_lock:
            start = time.perf_counter()
            status, data, _, _ = await self._json("GET", "/device/status")
            if status != 200 or not isinstance(data, dict) or type(data.get("isSetup")) is not bool:
                raise KVMError("not_jetkvm", f"Unexpected /device/status response (HTTP {status})")
            if not data["isSetup"]:
                raise KVMError("setup_required")
            device = await self._authorized_json("GET", "/device")
            if (
                not isinstance(device, dict)
                or device.get("authMode") not in {"password", "noPassword"}
                or not isinstance(device.get("deviceId"), str)
                or not 1 <= len(device["deviceId"]) <= 256
            ):
                raise KVMError("not_jetkvm", "Unexpected /device identity response")
            if self.device and self.device["device_id"] != device["deviceId"]:
                self._cookie = ""
                raise KVMError("wrong_device")
            if not self.device:
                _LOGGER.info("[JetKVM] device detected %s", self.origin.host)
            self.device = {"device_id": device["deviceId"], "auth_mode": device["authMode"]}
            if type(device.get("loopbackOnly")) is bool:
                self.device["loopback_only"] = device["loopbackOnly"]
            self.last_latency_ms = round((time.perf_counter() - start) * 1000, 2)
            return {**self.device, "latency_ms": self.last_latency_ms}

    async def open_signaling(self) -> aiohttp.ClientWebSocketResponse:
        """Open ws/wss with an explicit handshake timeout and one auth retry."""
        await self.test_connection()
        for attempt in range(2):
            rejected_cookie = self._cookie
            try:
                async with asyncio.timeout(8):
                    ws = await self._http().ws_connect(
                        self.origin.websocket_url(SIGNALING_PATH),
                        headers=self._headers(),
                        origin=self.base_url,
                        autoping=True,
                        heartbeat=15,
                        autoclose=True,
                        timeout=aiohttp.ClientWSTimeout(ws_receive=45, ws_close=3),
                        max_msg_size=256 * 1024,
                        compress=0,
                    )
                self._websockets.add(ws)
                _LOGGER.info("[JetKVM] signaling websocket connected %s", self.origin.host)
                return ws
            except aiohttp.WSServerHandshakeError as err:
                if err.status == 401 and attempt == 0:
                    await self._login(rejected_cookie)
                    continue
                if err.status == 403:
                    raise KVMError("permission_denied", "Signaling HTTP 403") from err
                raise KVMError("protocol_error", f"Signaling handshake HTTP {err.status}") from err
            except (aiohttp.ClientError, OSError, TimeoutError, KVMError) as err:
                raise network_error(err) from err
        raise KVMError("authentication_required")

    async def close_signaling(self, ws: aiohttp.ClientWebSocketResponse) -> None:
        self._websockets.discard(ws)
        try:
            async with asyncio.timeout(3):
                await ws.close()
        except (TimeoutError, aiohttp.ClientError):
            pass

    async def wake_on_lan(self, mac: str) -> None:
        mac = mac.strip().replace("-", ":").upper()
        if not MAC_RE.fullmatch(mac):
            raise KVMError("invalid_data", "Invalid MAC address")
        # A new client must verify identity before ever sending credentials.
        if not self.device:
            await self.test_connection()
        await self._authorized_json("POST", f"/device/send-wol/{mac}")

    async def close(self) -> None:
        self._closed = True
        await asyncio.gather(
            *(self.close_signaling(ws) for ws in tuple(self._websockets)), return_exceptions=True
        )
        if self._session is not None:
            await self._session.close()
        self._session = None
        self._cookie = ""
        self._password = ""
