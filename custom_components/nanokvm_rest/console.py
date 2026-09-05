"""Live Remote Console WebSocket bridge for NanoKVM REST."""

from __future__ import annotations

import asyncio
import secrets
import time
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import aiohttp
from aiohttp import WSMsgType, web
import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.components.http import KEY_HASS, HomeAssistantView
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant

from .const import COOKIE_NAME, DOMAIN
from .coordinator import NanoKVMCoordinator

DATA_CONSOLE_SESSIONS = f"{DOMAIN}_console_sessions"
CONSOLE_PROTOCOL = "nanokvm-console"
CONSOLE_SESSION_TTL = 30
CONSOLE_MAX_INCOMING = 64 * 1024
UPSTREAM_STREAM_MAX = 4 * 1024 * 1024


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
        },
    )


class NanoKVMConsoleView(HomeAssistantView):
    """Bridge Live KVM H.264 and HID WebSockets through Home Assistant."""

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

        coordinator = _loaded_coordinator(hass, str(session_info.get("entry_id") or ""))
        if coordinator is None:
            raise web.HTTPNotFound(text="NanoKVM is not loaded")

        stream_ws: aiohttp.ClientWebSocketResponse | None = None
        input_ws: aiohttp.ClientWebSocketResponse | None = None
        try:
            stream_ws = await _open_upstream_ws(
                coordinator,
                "/api/stream/h264/direct",
                params={"flow": "8"},
                max_msg_size=UPSTREAM_STREAM_MAX,
            )
            input_ws = await _open_upstream_ws(
                coordinator,
                "/api/ws",
                max_msg_size=CONSOLE_MAX_INCOMING,
            )
        except (aiohttp.ClientError, TimeoutError, RuntimeError) as err:
            if stream_ws is not None:
                await stream_ws.close()
            if input_ws is not None:
                await input_ws.close()
            raise web.HTTPBadGateway(text=f"Unable to open NanoKVM console: {err}") from err

        browser_ws = web.WebSocketResponse(
            protocols=(CONSOLE_PROTOCOL,),
            max_msg_size=CONSOLE_MAX_INCOMING,
            autoping=True,
            heartbeat=30,
            compress=False,
        )
        await browser_ws.prepare(request)
        await browser_ws.send_str('{"type":"console","state":"connected"}')

        async def stream_to_browser() -> None:
            assert stream_ws is not None
            async for item in stream_ws:
                if item.type is WSMsgType.BINARY:
                    await browser_ws.send_bytes(item.data)
                elif item.type in {WSMsgType.CLOSE, WSMsgType.CLOSED, WSMsgType.ERROR}:
                    break

        async def input_to_browser() -> None:
            assert input_ws is not None
            async for item in input_ws:
                if item.type is WSMsgType.TEXT:
                    await browser_ws.send_str(item.data)
                elif item.type in {WSMsgType.CLOSE, WSMsgType.CLOSED, WSMsgType.ERROR}:
                    break

        async def browser_to_upstreams() -> None:
            assert stream_ws is not None and input_ws is not None
            async for item in browser_ws:
                if item.type is WSMsgType.BINARY:
                    data = bytes(item.data)
                    if len(data) < 2:
                        continue
                    channel, payload = data[0], data[1:]
                    if channel == 0:
                        await stream_ws.send_bytes(payload)
                    elif channel == 1:
                        await input_ws.send_bytes(payload)
                elif item.type in {WSMsgType.CLOSE, WSMsgType.CLOSED, WSMsgType.ERROR}:
                    break

        tasks = {
            asyncio.create_task(stream_to_browser()),
            asyncio.create_task(input_to_browser()),
            asyncio.create_task(browser_to_upstreams()),
        }
        try:
            done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            for task in done:
                if not task.cancelled():
                    task.exception()
            for task in pending:
                task.cancel()
            await asyncio.gather(*pending, return_exceptions=True)
        finally:
            for task in tasks:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            await stream_ws.close()
            await input_ws.close()
            if not browser_ws.closed:
                await browser_ws.close()

        return browser_ws
