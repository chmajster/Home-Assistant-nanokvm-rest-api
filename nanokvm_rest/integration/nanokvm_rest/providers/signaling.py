"""Bounded JetKVM signaling relay, independent of HA and testable on real WS."""

from __future__ import annotations

import asyncio
import base64
import binascii
import json
import logging

from aiohttp import WSMsgType

from .errors import KVMError

_LOGGER = logging.getLogger(__name__)
MAX_SIGNAL = 192 * 1024


def session_description(encoded: str, expected_type: str) -> dict:
    if not isinstance(encoded, str) or not 0 < len(encoded) <= MAX_SIGNAL:
        raise KVMError("protocol_error", "Invalid SDP envelope size")
    try:
        decoded = json.loads(base64.b64decode(encoded, validate=True))
    except (ValueError, UnicodeError, binascii.Error) as err:
        raise KVMError("protocol_error", "Invalid SDP envelope") from err
    if (
        not isinstance(decoded, dict)
        or decoded.get("type") != expected_type
        or not isinstance(decoded.get("sdp"), str)
        or not decoded["sdp"].startswith("v=0")
    ):
        raise KVMError("protocol_error", "Invalid SDP description")
    return {"type": expected_type, "sdp": decoded["sdp"]}


def ice_candidate(data: dict) -> dict:
    if (
        not isinstance(data, dict)
        or not isinstance(data.get("candidate"), str)
        or len(data["candidate"]) > 2048
    ):
        raise KVMError("protocol_error", "Invalid ICE candidate")
    candidate = data["candidate"]
    if candidate and not candidate.startswith("candidate:"):
        raise KVMError("protocol_error", "Invalid ICE candidate")
    result = {"candidate": candidate}
    for key, max_len in (("sdpMid", 64), ("usernameFragment", 256)):
        value = data.get(key)
        if value is not None:
            if not isinstance(value, str) or len(value) > max_len:
                raise KVMError("protocol_error", "Invalid ICE field")
            result[key] = value
    index = data.get("sdpMLineIndex")
    if index is not None:
        if type(index) is not int or not 0 <= index < 32:
            raise KVMError("protocol_error", "Invalid ICE media index")
        result["sdpMLineIndex"] = index
    return result


def client_signal(raw: str) -> dict:
    if not isinstance(raw, str) or len(raw) > MAX_SIGNAL:
        raise KVMError("protocol_error", "Invalid signaling message size")
    try:
        packet = json.loads(raw)
    except ValueError as err:
        raise KVMError("protocol_error", "Invalid signaling JSON") from err
    if not isinstance(packet, dict):
        raise KVMError("protocol_error", "Invalid signaling object")
    kind = packet.get("type")
    data = packet.get("data")
    if kind == "offer":
        if not isinstance(data, dict):
            raise KVMError("protocol_error", "Invalid offer data")
        description = session_description(data.get("sd"), "offer")
        # Deliberately discard cloud OIDC, arbitrary ICE servers, source IPs,
        # and every other caller-controlled upstream option.
        encoded = base64.b64encode(json.dumps(description).encode()).decode()
        return {"type": "offer", "data": {"sd": encoded}}
    if kind == "new-ice-candidate":
        return {"type": kind, "data": ice_candidate(data)}
    if kind == "manager-state" and packet.get("state") in {
        "connected",
        "disconnected",
        "reconnecting",
    }:
        return {"type": kind, "state": packet["state"]}
    raise KVMError("protocol_error", "Unsupported signaling message")


async def run_pumps(*coroutines):
    """Cancel both directions when either side ends; consume every exception."""
    tasks = {asyncio.create_task(coro) for coro in coroutines}
    try:
        done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for task in done:
            task.result()
    finally:
        for task in tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)


async def relay_jetkvm(provider, upstream, browser):
    connected = asyncio.Event()
    offer_seen = False

    async def to_device():
        nonlocal offer_seen
        async for message in browser:
            if message.type is WSMsgType.TEXT:
                if message.data == "ping":
                    await upstream.send_str("ping")
                    continue
                packet = client_signal(message.data)
                if packet["type"] == "manager-state":
                    if packet["state"] == "connected" and not connected.is_set():
                        connected.set()
                        _LOGGER.info(
                            "[JetKVM] WebRTC connected %s (browser state)",
                            provider.client.origin.host,
                        )
                    continue
                if packet["type"] == "offer":
                    if offer_seen:
                        raise KVMError("protocol_error", "Only one offer is allowed per session")
                    offer_seen = True
                elif not offer_seen:
                    raise KVMError("protocol_error", "ICE candidate received before SDP offer")
                await upstream.send_json(packet)
            elif message.type is WSMsgType.BINARY:
                raise KVMError("protocol_error", "Expected text WebRTC signaling")
            elif message.type in {WSMsgType.CLOSE, WSMsgType.CLOSED, WSMsgType.ERROR}:
                return

    async def to_browser():
        async for message in upstream:
            if message.type is WSMsgType.TEXT:
                if message.data == "pong":
                    await browser.send_str("pong")
                    continue
                try:
                    packet = json.loads(message.data)
                except ValueError as err:
                    raise KVMError("protocol_error", "Invalid upstream signaling JSON") from err
                if not isinstance(packet, dict):
                    raise KVMError("protocol_error", "Invalid upstream signaling object")
                kind = packet.get("type")
                data = packet.get("data")
                if kind == "answer":
                    session_description(data, "answer")
                    await browser.send_json({"type": kind, "data": data})
                elif kind == "new-ice-candidate":
                    await browser.send_json({"type": kind, "data": ice_candidate(data)})
                elif kind == "device-metadata":
                    version = data.get("deviceVersion") if isinstance(data, dict) else None
                    if isinstance(version, str) and len(version) <= 128:
                        provider.client.firmware_version = version
                        await browser.send_json({"type": kind, "data": {"deviceVersion": version}})
                # Unknown upstream notifications are not forwarded as arbitrary
                # browser commands. No packet, SDP or credential is logged.
            elif message.type in {WSMsgType.CLOSE, WSMsgType.CLOSED, WSMsgType.ERROR}:
                return

    async def negotiation_guard():
        try:
            await asyncio.wait_for(connected.wait(), timeout=30)
        except TimeoutError as err:
            raise KVMError("timeout", "WebRTC negotiation timeout") from err
        await asyncio.Future()  # Cancelled by run_pumps when either socket ends.

    await run_pumps(to_device(), to_browser(), negotiation_guard())


async def relay_nanokvm(provider, upstreams, browser):
    stream, inputs = upstreams

    async def stream_to_browser():
        async for item in stream:
            if item.type is WSMsgType.BINARY:
                await browser.send_bytes(item.data)
            elif item.type in {WSMsgType.CLOSE, WSMsgType.CLOSED, WSMsgType.ERROR}:
                return

    async def input_to_browser():
        async for item in inputs:
            if item.type is WSMsgType.TEXT:
                await browser.send_str(item.data)
            elif item.type in {WSMsgType.CLOSE, WSMsgType.CLOSED, WSMsgType.ERROR}:
                return

    async def browser_to_device():
        async for item in browser:
            if item.type is WSMsgType.BINARY:
                data = bytes(item.data)
                if len(data) >= 2:
                    if data[0] == 0:
                        await stream.send_bytes(data[1:])
                    elif data[0] == 1:
                        await inputs.send_bytes(data[1:])
            elif item.type in {WSMsgType.CLOSE, WSMsgType.CLOSED, WSMsgType.ERROR}:
                return

    await run_pumps(stream_to_browser(), input_to_browser(), browser_to_device())


RELAYS = {"h264-websocket": relay_nanokvm, "webrtc": relay_jetkvm}
