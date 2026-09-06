from __future__ import annotations

import json
import os
import threading
import time
from functools import wraps
from typing import Any, Callable, TypeVar, cast

import websocket
from flask import Flask, Response, abort, jsonify, render_template, request

APP_VERSION = os.environ.get("BUILD_VERSION", "0.11.0")
HA_WS_URL = os.environ.get("HA_WS_URL", "ws://supervisor/core/websocket")
SUPERVISOR_TOKEN = os.environ.get("SUPERVISOR_TOKEN", "")
ADMIN_GROUP = "system-admin"
USER_CACHE_SECONDS = 30

READ_COMMANDS = {
    "nanokvm_rest/panel/list",
    "nanokvm_rest/panel/status",
    "nanokvm_rest/panel/history",
    "nanokvm_rest/panel/ops/list",
    "nanokvm_rest/panel/ops/device",
    "nanokvm_rest/panel/update/list",
    "nanokvm_rest/panel/media/library",
    "nanokvm_rest/panel/hid/status",
}
WRITE_COMMANDS = {
    "nanokvm_rest/panel/action",
    "nanokvm_rest/panel/metadata/update",
    "nanokvm_rest/panel/ops/refresh",
    "nanokvm_rest/panel/ops/maintenance/set",
    "nanokvm_rest/panel/ops/auto-recovery/set",
    "nanokvm_rest/panel/ops/alert/ack",
    "nanokvm_rest/panel/ops/recovery/action",
    "nanokvm_rest/panel/update/channel",
    "nanokvm_rest/panel/update/start",
    "nanokvm_rest/panel/update/staged/start",
    "nanokvm_rest/panel/update/staged/cancel",
    "nanokvm_rest/panel/media/favorite",
    "nanokvm_rest/panel/media/mount",
    "nanokvm_rest/panel/media/delete_many",
    "nanokvm_rest/panel/media/download/start",
    "nanokvm_rest/panel/media/download/cancel",
    "nanokvm_rest/panel/hid/action",
}

app = Flask(__name__, template_folder="templates", static_folder="static")
app.config.update(MAX_CONTENT_LENGTH=2 * 1024 * 1024, JSON_SORT_KEYS=False)

_user_cache: dict[str, Any] = {"expires": 0.0, "users": []}
_user_cache_lock = threading.Lock()
F = TypeVar("F", bound=Callable[..., Any])


class HAError(RuntimeError):
    pass


def _recv_json(ws: websocket.WebSocket, timeout: float) -> dict[str, Any]:
    ws.settimeout(timeout)
    payload = ws.recv()
    if not isinstance(payload, str):
        raise HAError("Home Assistant returned a non-text WebSocket frame")
    data = json.loads(payload)
    if not isinstance(data, dict):
        raise HAError("Home Assistant returned an invalid WebSocket response")
    return data


def ha_ws_call(message: dict[str, Any], *, timeout: float = 15.0) -> Any:
    if not SUPERVISOR_TOKEN:
        raise HAError("SUPERVISOR_TOKEN is not available. Check homeassistant_api in the add-on configuration.")
    ws: websocket.WebSocket | None = None
    try:
        ws = websocket.create_connection(
            HA_WS_URL,
            timeout=timeout,
            enable_multithread=True,
            suppress_origin=True,
        )
        auth_required = _recv_json(ws, timeout)
        if auth_required.get("type") != "auth_required":
            raise HAError("Unexpected Home Assistant authentication handshake")
        ws.send(json.dumps({"type": "auth", "access_token": SUPERVISOR_TOKEN}))
        auth = _recv_json(ws, timeout)
        if auth.get("type") != "auth_ok":
            raise HAError(str(auth.get("message") or "Home Assistant authentication failed"))

        outbound = dict(message)
        outbound["id"] = 1
        ws.send(json.dumps(outbound, ensure_ascii=False))
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            response = _recv_json(ws, max(0.5, deadline - time.monotonic()))
            if response.get("id") != 1:
                continue
            if response.get("type") != "result":
                continue
            if response.get("success") is not True:
                error = response.get("error") or {}
                raise HAError(str(error.get("message") or error.get("code") or "Home Assistant command failed"))
            return response.get("result")
        raise HAError("Home Assistant command timed out")
    except (OSError, websocket.WebSocketException, json.JSONDecodeError) as err:
        raise HAError(str(err)) from err
    finally:
        if ws is not None:
            try:
                ws.close()
            except Exception:
                pass


def _users() -> list[dict[str, Any]]:
    now = time.monotonic()
    with _user_cache_lock:
        if now < float(_user_cache["expires"]):
            return cast(list[dict[str, Any]], _user_cache["users"])
        result = ha_ws_call({"type": "config/auth/list"})
        users = [item for item in (result or []) if isinstance(item, dict)]
        _user_cache["users"] = users
        _user_cache["expires"] = now + USER_CACHE_SECONDS
        return users


def _ingress_user_is_admin() -> bool:
    user_id = request.headers.get("X-Remote-User-Id", "").strip()
    if not user_id:
        return False
    try:
        user = next((item for item in _users() if str(item.get("id")) == user_id), None)
    except HAError:
        return False
    if not user or user.get("is_active") is False:
        return False
    return bool(user.get("is_owner") or ADMIN_GROUP in (user.get("group_ids") or []))


def require_admin(view: F) -> F:
    @wraps(view)
    def wrapped(*args: Any, **kwargs: Any) -> Any:
        if not _ingress_user_is_admin():
            abort(403)
        return view(*args, **kwargs)

    return cast(F, wrapped)


def require_write_header() -> None:
    if request.headers.get("X-NanoKVM-Request") != "1":
        abort(403)
    if not request.is_json:
        abort(415)


@app.after_request
def security_headers(response: Response) -> Response:
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/health/ready")
def health_ready() -> Response:
    return jsonify({"ok": True, "version": APP_VERSION})


@app.get("/")
@require_admin
def index() -> str:
    return render_template("index.html", version=APP_VERSION)


@app.get("/api/bootstrap")
@require_admin
def api_bootstrap() -> Response:
    try:
        devices = ha_ws_call({"type": "nanokvm_rest/panel/list"})
        operations = ha_ws_call({"type": "nanokvm_rest/panel/ops/list"})
        updates = ha_ws_call({"type": "nanokvm_rest/panel/update/list"})
        return jsonify({"ok": True, "devices": devices, "operations": operations, "updates": updates})
    except HAError as err:
        return jsonify({"ok": False, "error": str(err)}), 502


@app.post("/api/rpc")
@require_admin
def api_rpc() -> Response:
    require_write_header()
    body = request.get_json(silent=True) or {}
    command_type = str(body.get("type") or "")
    if command_type not in READ_COMMANDS | WRITE_COMMANDS:
        return jsonify({"ok": False, "error": "Command is not allowed"}), 400
    payload = {key: value for key, value in body.items() if key != "id"}
    try:
        result = ha_ws_call(payload, timeout=30.0 if command_type.endswith("/device") else 15.0)
        return jsonify({"ok": True, "result": result})
    except HAError as err:
        return jsonify({"ok": False, "error": str(err)}), 502


@app.errorhandler(403)
def forbidden(_: Exception) -> tuple[Response, int]:
    return jsonify({"ok": False, "error": "Administrator access through Home Assistant Ingress is required."}), 403


@app.errorhandler(404)
def not_found(_: Exception) -> tuple[Response, int]:
    return jsonify({"ok": False, "error": "Not found"}), 404


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8099, debug=False)
