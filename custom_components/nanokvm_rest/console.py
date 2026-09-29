"""Live Remote Console WebSocket bridge for NanoKVM REST."""

from __future__ import annotations

import asyncio
import logging
import secrets
import time
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import aiohttp
import voluptuous as vol
from aiohttp import web
from homeassistant.components import websocket_api
from homeassistant.components.http import KEY_HASS, HomeAssistantView
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant

from .const import COOKIE_NAME, DOMAIN
from .coordinator import NanoKVMCoordinator
from .providers.errors import KVMError
from .providers.jetkvm import network_error
from .providers.registry import runtime_provider
from .providers.signaling import RELAYS

_LOGGER = logging.getLogger(__name__)
DATA_ACTIVE_CONSOLES = f"{DOMAIN}_active_consoles"
DATA_CONSOLE_SESSIONS = f"{DOMAIN}_console_sessions"
CONSOLE_PROTOCOL = "nanokvm-console"
CONSOLE_SESSION_TTL = 30


def _loaded_coordinator(hass: HomeAssistant, entry_id: str) -> NanoKVMCoordinator | None:
    entry = hass.config_entries.async_get_entry(entry_id)
    if (
        entry is None
        or entry.domain != DOMAIN
        or entry.state is not ConfigEntryState.LOADED
        or not hasattr(entry, "runtime_data")
    ):
        return None
    return entry.runtime_data


def _sessions(hass: HomeAssistant) -> dict[str, dict[str, Any]]:
    store = hass.data.setdefault(DATA_CONSOLE_SESSIONS, {})
    now = time.monotonic()
    expired = [token for token, item in store.items() if float(item.get("expires", 0)) <= now]
    for token in expired:
        store.pop(token, None)
    return store


def _upstream_ws_url(base_url: str, path: str) -> str:
    parsed = urlsplit(base_url.rstrip("/"))
    scheme = "wss" if parsed.scheme == "https" else "ws"
    base_path = parsed.path.rstrip("/")
    return urlunsplit((scheme, parsed.netloc, f"{base_path}{path}", "", ""))


async def _open_upstream_ws(
    coordinator: NanoKVMCoordinator,
    path: str,
    *,
    params: dict[str, str] | None = None,
    max_msg_size: int = 0,
) -> aiohttp.ClientWebSocketResponse:
    """Open an authenticated NanoKVM WebSocket using integration credentials."""
    client = coordinator.client
    for attempt in range(2):
        await client.async_login()
        token = getattr(client, "_token", None)
        session = getattr(client, "_session", None)
        base_url = getattr(client, "_base_url", client.base_url)
        if session is None:
            raise RuntimeError("NanoKVM HTTP session is unavailable")
        headers: dict[str, str] = {}
        if token:
            headers["Cookie"] = f"{COOKIE_NAME}={token}"
        try:
            async with asyncio.timeout(8):
                return await session.ws_connect(
                    _upstream_ws_url(base_url, path),
                    headers=headers,
                    params=params,
                    max_msg_size=max_msg_size,
                    autoping=True,
                    autoclose=True,
                )
        except aiohttp.WSServerHandshakeError as err:
            if err.status == 401 and attempt == 0:
                setattr(client, "_logged_in", False)
                setattr(client, "_token", None)
                continue
            raise
    raise RuntimeError("Unable to authenticate NanoKVM WebSocket")


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/panel/console/session",
        vol.Required("entry_id"): str,
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def websocket_console_session(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Issue a short-lived one-time token for a live console WebSocket."""
    coordinator = _loaded_coordinator(hass, msg["entry_id"])
    if coordinator is None:
        connection.send_error(msg["id"], "not_loaded", "NanoKVM is not loaded")
        return

    provider = runtime_provider(coordinator)
    active = hass.data.setdefault(DATA_ACTIVE_CONSOLES, {}).get(msg["entry_id"], set())
    if provider.transport == "webrtc" and active:
        connection.send_error(msg["id"], "busy", KVMError("busy").message)
        return
    if len(_sessions(hass)) >= 128:
        connection.send_error(msg["id"], "rate_limited", KVMError("rate_limited").message)
        return
    token = f"nkv-{secrets.token_urlsafe(32)}"
    _sessions(hass)[token] = {
        "entry_id": msg["entry_id"],
        "user_id": str(getattr(getattr(connection, "user", None), "id", "")),
        "expires": time.monotonic() + CONSOLE_SESSION_TTL,
    }
    connection.send_result(
        msg["id"],
        {
            "path": f"/api/{DOMAIN}/console",
            "protocol": CONSOLE_PROTOCOL,
            "token": token,
            "expires_in": CONSOLE_SESSION_TTL,
            "provider": provider.provider_type,
            "transport": provider.transport,
        },
    )


async def async_disconnect_entry(hass: HomeAssistant, entry_id: str) -> int:
    """Revoke unused tickets and close all Manager sessions for an entry."""
    for token, item in list(_sessions(hass).items()):
        if item.get("entry_id") == entry_id:
            _sessions(hass).pop(token, None)
    sessions = tuple(hass.data.setdefault(DATA_ACTIVE_CONSOLES, {}).get(entry_id, set()))

    async def close(ws):
        try:
            async with asyncio.timeout(3):
                if ws.prepared and not ws.closed:
                    await ws.send_json(
                        {"type": "console", "state": "disconnected", "reason": "user"}
                    )
                await ws.close(code=1000, message=b"Manager disconnected session")
        except (TimeoutError, aiohttp.ClientError):
            pass

    await asyncio.gather(*(close(ws) for ws in sessions))
    return len(sessions)


class NanoKVMConsoleView(HomeAssistantView):
    """One admin-authorized session endpoint with provider-specific transports."""

    url = f"/api/{DOMAIN}/console"
    name = f"api:{DOMAIN}:console"
    requires_auth = False

    async def get(self, request: web.Request) -> web.StreamResponse:
        hass: HomeAssistant = request.app[KEY_HASS]
        offered = [
            value.strip()
            for value in request.headers.get("Sec-WebSocket-Protocol", "").split(",")
            if value.strip()
        ]
        token = next((value for value in offered if value.startswith("nkv-")), "")
        if CONSOLE_PROTOCOL not in offered or not token:
            raise web.HTTPForbidden(text="Missing Remote Console session")
        session_info = _sessions(hass).pop(token, None)
        if not session_info or float(session_info.get("expires", 0)) <= time.monotonic():
            raise web.HTTPForbidden(text="Remote Console session expired")
        user = await hass.auth.async_get_user(session_info["user_id"])
        if user is None or not user.is_active or not user.is_admin:
            raise web.HTTPForbidden(text="Administrator session is no longer active")
        entry_id = str(session_info.get("entry_id") or "")
        coordinator = _loaded_coordinator(hass, entry_id)
        if coordinator is None:
            raise web.HTTPNotFound(text="KVM configuration is not loaded")
        provider = runtime_provider(coordinator)
        active_store = hass.data.setdefault(DATA_ACTIVE_CONSOLES, {})
        active = active_store.setdefault(entry_id, set())
        if provider.transport == "webrtc" and active:
            raise web.HTTPConflict(text=KVMError("busy").message)
        browser = web.WebSocketResponse(
            protocols=(CONSOLE_PROTOCOL,),
            max_msg_size=256 * 1024,
            autoping=True,
            heartbeat=30,
            compress=False,
        )
        # Reserve before the first await, avoiding simultaneous exclusive JetKVM
        # sessions against upstream's single currentSession.
        active.add(browser)
        upstream = None
        try:
            await browser.prepare(request)
            await browser.send_json(
                {"type": "console", "state": "connecting", "provider": provider.provider_type}
            )
            async with asyncio.timeout(15):
                upstream = await provider.open_kvm_session()
            await browser.send_json(
                {"type": "console", "state": "connected", "provider": provider.provider_type}
            )
            await RELAYS[provider.transport](provider, upstream, browser)
        except (KVMError, aiohttp.ClientError, TimeoutError, OSError, RuntimeError) as err:
            problem = network_error(err)
            if browser.prepared and not browser.closed:
                await browser.send_json({"type": "manager-error", "error": problem.public()})
            _LOGGER.warning("[%s] console failed %s: %s", provider.label, entry_id, problem.code)
        finally:
            try:
                if upstream is not None:
                    await provider.close_kvm_session(upstream)
            finally:
                active.discard(browser)
                if not active:
                    active_store.pop(entry_id, None)
                if browser.prepared and not browser.closed:
                    try:
                        async with asyncio.timeout(3):
                            await browser.close()
                    except (TimeoutError, aiohttp.ClientError):
                        pass
                _LOGGER.info("[%s] session closed %s", provider.label, entry_id)
        return browser
