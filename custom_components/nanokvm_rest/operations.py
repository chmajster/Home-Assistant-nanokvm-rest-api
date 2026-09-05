"""Operations Center, alerting, monitoring and recovery for NanoKVM REST."""

from __future__ import annotations

import asyncio
from copy import deepcopy
from datetime import datetime, timezone
from time import monotonic, time
from typing import Any

import voluptuous as vol

from homeassistant.components import persistent_notification, websocket_api
from homeassistant.core import HomeAssistant

from . import panel_v2 as base
from .api import NanoKVMError
from .const import DOMAIN
from .management import async_reset_hid
from .operations_store import OperationsStore

DATA_OPERATIONS_STORE = f"{DOMAIN}_operations_store"
DATA_OPERATIONS_RUNTIME = f"{DOMAIN}_operations_runtime"
DATA_OPERATIONS_MONITOR = f"{DOMAIN}_operations_monitor"
DATA_OPERATIONS_LOCK = f"{DOMAIN}_operations_lock"
EVENT_OPERATIONS_ALERT = f"{DOMAIN}_operations_alert"
MONITOR_INTERVAL_SECONDS = 60
HDMI_AUTO_RECOVERY_STREAK = 3


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _store(hass: HomeAssistant) -> OperationsStore:
    return hass.data[DATA_OPERATIONS_STORE]


def _runtime(hass: HomeAssistant) -> dict[str, Any]:
    return hass.data.setdefault(DATA_OPERATIONS_RUNTIME, {"devices": {}, "last_cycle": ""})


def _runtime_device(hass: HomeAssistant, entry_id: str) -> dict[str, Any]:
    devices = _runtime(hass).setdefault("devices", {})
    return devices.setdefault(
        entry_id,
        {
            "available": False,
            "latency_ms": None,
            "last_probe": "",
            "last_successful_probe": "",
            "offline_streak": 0,
            "hdmi_streak": 0,
            "last_auto_recovery": 0.0,
            "auto_attempts": [],
            "recovery": {"state": "idle", "action": "", "message": "", "updated_at": ""},
            "alerts": [],
            "active_alert_ids": [],
        },
    )


def _notification_id(entry_id: str, alert_type: str) -> str:
    safe_entry = "".join(ch for ch in entry_id if ch.isalnum() or ch in "-_")[:48]
    safe_type = "".join(ch for ch in alert_type if ch.isalnum() or ch in "-_")[:48]
    return f"nanokvm_rest_ops_{safe_entry}_{safe_type}"


def _health(
    *,
    available: bool,
    power: bool | None,
    pcie: bool,
    hdmi_signal: bool | None,
    latency_ms: float | None,
    availability_24h: float | None,
    application_version: str,
    update_available: bool,
) -> dict[str, Any]:
    if not available:
        return {"score": 0, "state": "critical", "issues": ["kvm_offline"]}

    score = 100
    issues: list[str] = []
    if power is True and pcie and hdmi_signal is False:
        score -= 30
        issues.append("hdmi_no_signal")
    if latency_ms is not None:
        if latency_ms >= 2000:
            score -= 30
            issues.append("latency_critical")
        elif latency_ms >= 1000:
            score -= 20
            issues.append("latency_high")
        elif latency_ms >= 500:
            score -= 10
            issues.append("latency_elevated")
    if availability_24h is not None:
        if availability_24h < 95:
            score -= 30
            issues.append("availability_critical")
        elif availability_24h < 99:
            score -= 15
            issues.append("availability_low")
        elif availability_24h < 99.9:
            score -= 5
            issues.append("availability_degraded")
    if not application_version:
        score -= 5
        issues.append("version_unknown")
    elif update_available:
        score -= 5
        issues.append("update_available")

    score = max(0, min(100, score))
    state = "healthy" if score >= 80 else "warning" if score >= 50 else "critical"
    return {"score": score, "state": state, "issues": issues}


def _build_alerts(
    entry_id: str,
    title: str,
    snapshot: dict[str, Any],
    operations_store: OperationsStore,
    maintenance: bool,
) -> list[dict[str, Any]]:
    alerts: list[dict[str, Any]] = []

    def add(kind: str, severity: str, message: str) -> None:
        alert_id = f"{entry_id}:{kind}"
        alerts.append(
            {
                "id": alert_id,
                "entry_id": entry_id,
                "title": title,
                "type": kind,
                "severity": severity,
                "message": message,
                "acknowledged": operations_store.is_alert_acknowledged(entry_id, alert_id),
                "muted": maintenance,
            }
        )

    if not snapshot.get("available"):
        add("offline", "critical", "NanoKVM is not responding to API probes.")
    if (
        snapshot.get("power") is True
        and snapshot.get("pcie")
        and snapshot.get("hdmi_signal") is False
    ):
        add("hdmi_no_signal", "warning", "Host is powered on but HDMI signal is missing.")
    latency = snapshot.get("latency_ms")
    if isinstance(latency, (int, float)) and latency >= 1500:
        add("high_latency", "warning", f"NanoKVM API latency is {latency:.0f} ms.")
    availability = snapshot.get("availability_24h")
    if isinstance(availability, (int, float)) and availability < 95:
        add("low_availability", "critical", f"24-hour availability is {availability:.2f}%.")
    elif isinstance(availability, (int, float)) and availability < 99:
        add("low_availability", "warning", f"24-hour availability is {availability:.2f}%.")
    if snapshot.get("update_available"):
        add("update_available", "info", "A newer NanoKVM application version is available.")
    recovery = snapshot.get("recovery") or {}
    if recovery.get("state") == "error":
        add("recovery_failed", "warning", str(recovery.get("message") or "Recovery action failed."))
    return alerts


async def _sync_alert_transitions(
    hass: HomeAssistant,
    entry_id: str,
    title: str,
    device_runtime: dict[str, Any],
    alerts: list[dict[str, Any]],
    notify: bool,
    maintenance: bool,
) -> None:
    remote_store = base._remote_store(hass)  # noqa: SLF001
    previous = set(device_runtime.get("active_alert_ids") or [])
    active = {str(alert["id"]) for alert in alerts}
    by_id = {str(alert["id"]): alert for alert in alerts}

    for alert_id in sorted(active - previous):
        alert = by_id[alert_id]
        await remote_store.async_add_event(
            entry_id,
            f"alert_{alert['type']}_opened",
            actor="system",
            result="error" if alert["severity"] == "critical" else "success",
            details={"severity": alert["severity"], "message": alert["message"][:200]},
        )
        if not maintenance and not alert.get("acknowledged"):
            hass.bus.async_fire(
                EVENT_OPERATIONS_ALERT,
                {
                    "entry_id": entry_id,
                    "title": title,
                    "type": alert["type"],
                    "severity": alert["severity"],
                    "message": alert["message"],
                },
            )
            if notify and alert["severity"] in {"warning", "critical"}:
                persistent_notification.async_create(
                    hass,
                    alert["message"],
                    title=f"NanoKVM · {title}",
                    notification_id=_notification_id(entry_id, str(alert["type"])),
                )

    for alert_id in sorted(previous - active):
        alert_type = alert_id.split(":", 1)[-1]
        await remote_store.async_add_event(
            entry_id,
            f"alert_{alert_type}_resolved",
            actor="system",
            details={},
        )
        persistent_notification.async_dismiss(
            hass, notification_id=_notification_id(entry_id, alert_type)
        )

    device_runtime["active_alert_ids"] = sorted(active)
    await _store(hass).async_clear_resolved_acks(entry_id, active)


async def _maybe_auto_recover_hdmi(
    hass: HomeAssistant,
    entry_id: str,
    coordinator: Any,
    device_runtime: dict[str, Any],
    settings: dict[str, Any],
    maintenance: bool,
) -> None:
    auto = settings.get("auto_recovery") or {}
    if maintenance or not auto.get("enabled") or not auto.get("hdmi_reset"):
        return
    if device_runtime.get("hdmi_streak", 0) < HDMI_AUTO_RECOVERY_STREAK:
        return
    if not bool((coordinator.data.get("capabilities") or {}).get("admin")):
        return
    if not bool((coordinator.data.get("capabilities") or {}).get("pcie")):
        return

    now = time()
    cooldown = int(auto.get("cooldown_seconds") or 900)
    if now - float(device_runtime.get("last_auto_recovery") or 0.0) < cooldown:
        return
    attempts = [float(ts) for ts in device_runtime.get("auto_attempts") or [] if now - float(ts) < 3600]
    if len(attempts) >= int(auto.get("max_attempts_per_hour") or 3):
        device_runtime["auto_attempts"] = attempts
        return

    attempts.append(now)
    device_runtime["auto_attempts"] = attempts
    device_runtime["last_auto_recovery"] = now
    recovery = device_runtime["recovery"]
    recovery.update(
        {
            "state": "running",
            "action": "auto_hdmi_reset",
            "message": "Resetting HDMI after repeated missing-signal checks",
            "updated_at": _utcnow(),
        }
    )
    try:
        await coordinator.client.async_reset_hdmi()
        await asyncio.sleep(1)
        await coordinator.async_request_refresh()
        recovery.update(
            {
                "state": "success",
                "message": "Automatic HDMI reset completed",
                "updated_at": _utcnow(),
            }
        )
        device_runtime["hdmi_streak"] = 0
        await base._remote_store(hass).async_add_event(  # noqa: SLF001
            entry_id,
            "auto_recovery_hdmi_reset",
            actor="system",
            details={"reason": "repeated_missing_hdmi_signal"},
        )
    except NanoKVMError as err:
        recovery.update(
            {
                "state": "error",
                "message": str(err)[:200],
                "updated_at": _utcnow(),
            }
        )
        await base._remote_store(hass).async_add_event(  # noqa: SLF001
            entry_id,
            "auto_recovery_failed",
            actor="system",
            result="error",
            details={"message": str(err)[:200]},
        )


async def _probe_device(hass: HomeAssistant, entry_id: str, *, allow_recovery: bool = True) -> dict[str, Any]:
    entry = hass.config_entries.async_get_entry(entry_id)
    coordinator = base._loaded_coordinator(hass, entry_id)  # noqa: SLF001
    title = entry.title if entry is not None else entry_id
    runtime = _runtime_device(hass, entry_id)
    operations_store = _store(hass)
    if await operations_store.async_expire_maintenance(entry_id):
        await base._remote_store(hass).async_add_event(  # noqa: SLF001
            entry_id, "maintenance_expired", actor="system"
        )
    settings = operations_store.settings(entry_id)
    maintenance = bool(settings["maintenance"].get("enabled"))

    available = False
    latency_ms: float | None = None
    gpio: dict[str, Any] = {}
    if coordinator is not None:
        started = monotonic()
        try:
            gpio = await coordinator.client.async_get_gpio()
            latency_ms = round((monotonic() - started) * 1000.0, 1)
            available = True
        except NanoKVMError:
            latency_ms = None

    data = coordinator.data if coordinator is not None else {}
    capabilities = data.get("capabilities") or {}
    hdmi = data.get("hdmi")
    version = data.get("application_version") or {}
    power = bool(gpio.get("pwr")) if "pwr" in gpio else (
        bool((data.get("gpio") or {}).get("pwr")) if "pwr" in (data.get("gpio") or {}) else None
    )
    hdmi_signal = (
        bool(hdmi.get("signal"))
        if isinstance(hdmi, dict) and "signal" in hdmi
        else None
    )
    current_version = str(version.get("current") or version.get("version") or version.get("installed") or "")
    latest_version = str(version.get("latest") or "")
    update_available = bool(current_version and latest_version and current_version != latest_version)

    runtime["available"] = available
    runtime["latency_ms"] = latency_ms
    runtime["last_probe"] = _utcnow()
    if available:
        runtime["last_successful_probe"] = runtime["last_probe"]
        runtime["offline_streak"] = 0
    else:
        runtime["offline_streak"] = int(runtime.get("offline_streak") or 0) + 1
    if available and power is True and capabilities.get("pcie") and hdmi_signal is False:
        runtime["hdmi_streak"] = int(runtime.get("hdmi_streak") or 0) + 1
    else:
        runtime["hdmi_streak"] = 0

    metrics_before = operations_store.metrics(entry_id)
    health = _health(
        available=available,
        power=power,
        pcie=bool(capabilities.get("pcie")),
        hdmi_signal=hdmi_signal,
        latency_ms=latency_ms,
        availability_24h=metrics_before.get("availability_24h"),
        application_version=current_version,
        update_available=update_available,
    )
    await operations_store.async_record_sample(
        entry_id,
        {
            "available": available,
            "latency_ms": latency_ms,
            "power": power,
            "hdmi_signal": hdmi_signal,
            "health_score": health["score"],
        },
    )
    metrics = operations_store.metrics(entry_id)
    health = _health(
        available=available,
        power=power,
        pcie=bool(capabilities.get("pcie")),
        hdmi_signal=hdmi_signal,
        latency_ms=latency_ms,
        availability_24h=metrics.get("availability_24h"),
        application_version=current_version,
        update_available=update_available,
    )

    snapshot = {
        "entry_id": entry_id,
        "title": title,
        "available": available,
        "latency_ms": latency_ms,
        "last_probe": runtime.get("last_probe"),
        "last_successful_probe": runtime.get("last_successful_probe"),
        "offline_streak": runtime.get("offline_streak", 0),
        "power": power,
        "pcie": bool(capabilities.get("pcie")),
        "admin": bool(capabilities.get("admin")),
        "hdmi_signal": hdmi_signal,
        "application_version": current_version,
        "latest_version": latest_version,
        "update_available": update_available,
        "health": health,
        "availability_24h": metrics.get("availability_24h"),
        "availability_7d": metrics.get("availability_7d"),
        "latency_avg_24h": metrics.get("latency_avg_24h"),
        "latency_max_24h": metrics.get("latency_max_24h"),
        "sample_count_24h": metrics.get("sample_count_24h"),
        "sample_count_7d": metrics.get("sample_count_7d"),
        "maintenance": deepcopy(settings["maintenance"]),
        "auto_recovery": deepcopy(settings["auto_recovery"]),
        "recovery": deepcopy(runtime.get("recovery") or {}),
    }

    if coordinator is not None and allow_recovery:
        await _maybe_auto_recover_hdmi(
            hass, entry_id, coordinator, runtime, settings, maintenance
        )
        snapshot["recovery"] = deepcopy(runtime.get("recovery") or {})

    alerts = _build_alerts(entry_id, title, snapshot, operations_store, maintenance)
    runtime["alerts"] = alerts
    snapshot["alerts"] = deepcopy(alerts)
    await _sync_alert_transitions(
        hass,
        entry_id,
        title,
        runtime,
        alerts,
        bool(settings["auto_recovery"].get("notify", True)),
        maintenance,
    )
    runtime["snapshot"] = deepcopy(snapshot)
    return snapshot


async def _monitor_cycle(hass: HomeAssistant) -> None:
    lock: asyncio.Lock = hass.data.setdefault(DATA_OPERATIONS_LOCK, asyncio.Lock())
    if lock.locked():
        return
    async with lock:
        entries = hass.config_entries.async_entries(DOMAIN)
        if entries:
            await asyncio.gather(
                *(_probe_device(hass, entry.entry_id) for entry in entries),
                return_exceptions=True,
            )
        _runtime(hass)["last_cycle"] = _utcnow()


async def _monitor_loop(hass: HomeAssistant) -> None:
    while True:
        try:
            await _monitor_cycle(hass)
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001 - monitor must survive an individual cycle failure
            pass
        await asyncio.sleep(MONITOR_INTERVAL_SECONDS)


async def async_setup_operations(hass: HomeAssistant) -> None:
    """Initialize persistent operations state and the fleet monitor once."""
    if DATA_OPERATIONS_STORE not in hass.data:
        store = OperationsStore(hass)
        await store.async_load()
        hass.data[DATA_OPERATIONS_STORE] = store
    hass.data.setdefault(DATA_OPERATIONS_RUNTIME, {"devices": {}, "last_cycle": ""})
    if DATA_OPERATIONS_MONITOR not in hass.data:
        hass.data[DATA_OPERATIONS_MONITOR] = hass.async_create_task(
            _monitor_loop(hass), "NanoKVM Operations Center monitor"
        )


def _device_view(hass: HomeAssistant, entry_id: str) -> dict[str, Any]:
    runtime = _runtime_device(hass, entry_id)
    snapshot = deepcopy(runtime.get("snapshot") or {})
    snapshot["metrics"] = _store(hass).metrics(entry_id)
    events = base._remote_store(hass).events(entry_id, 200)  # noqa: SLF001
    power_events = {
        "host_power_on",
        "host_power_off",
        "power_on",
        "power_press",
        "force_off",
        "reset",
    }
    snapshot["power_timeline"] = [event for event in events if event.get("event") in power_events][:100]
    snapshot["recent_events"] = events[:50]
    return snapshot


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/panel/ops/list"})
@websocket_api.require_admin
@websocket_api.async_response
async def websocket_ops_list(hass, connection, msg) -> None:
    if not _runtime(hass).get("devices"):
        await _monitor_cycle(hass)
    remote_store = base._remote_store(hass)  # noqa: SLF001
    devices: list[dict[str, Any]] = []
    alerts: list[dict[str, Any]] = []
    for entry in hass.config_entries.async_entries(DOMAIN):
        runtime = _runtime_device(hass, entry.entry_id)
        item = deepcopy(runtime.get("snapshot") or {})
        if not item:
            item = {"entry_id": entry.entry_id, "title": entry.title, "available": False}
        item.update(base._public_metadata(remote_store, entry.entry_id))  # noqa: SLF001
        devices.append(item)
        alerts.extend(deepcopy(runtime.get("alerts") or []))
    devices.sort(key=lambda item: (item.get("health", {}).get("score", 0), str(item.get("title", "")).casefold()))
    severity_order = {"critical": 0, "warning": 1, "info": 2}
    alerts.sort(key=lambda item: (severity_order.get(str(item.get("severity")), 9), str(item.get("title", "")).casefold()))
    connection.send_result(
        msg["id"],
        {
            "devices": devices,
            "alerts": alerts,
            "last_cycle": _runtime(hass).get("last_cycle", ""),
            "summary": {
                "total": len(devices),
                "online": sum(1 for item in devices if item.get("available")),
                "maintenance": sum(1 for item in devices if (item.get("maintenance") or {}).get("enabled")),
                "critical": sum(1 for item in alerts if item.get("severity") == "critical" and not item.get("acknowledged")),
                "warning": sum(1 for item in alerts if item.get("severity") == "warning" and not item.get("acknowledged")),
            },
        },
    )


@websocket_api.websocket_command(
    {vol.Required("type"): f"{DOMAIN}/panel/ops/device", vol.Required("entry_id"): str}
)
@websocket_api.require_admin
@websocket_api.async_response
async def websocket_ops_device(hass, connection, msg) -> None:
    if base._domain_entry(hass, msg["entry_id"]) is None:  # noqa: SLF001
        connection.send_error(msg["id"], "not_found", "NanoKVM entry does not exist")
        return
    await _probe_device(hass, msg["entry_id"])
    connection.send_result(msg["id"], _device_view(hass, msg["entry_id"]))


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/panel/ops/refresh"})
@websocket_api.require_admin
@websocket_api.async_response
async def websocket_ops_refresh(hass, connection, msg) -> None:
    await _monitor_cycle(hass)
    connection.send_result(msg["id"], {"ok": True, "last_cycle": _runtime(hass).get("last_cycle", "")})


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/panel/ops/maintenance/set",
        vol.Required("entry_id"): str,
        vol.Required("enabled"): bool,
        vol.Optional("minutes", default=0): vol.All(int, vol.Range(min=0, max=10080)),
        vol.Optional("note", default=""): str,
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def websocket_ops_maintenance_set(hass, connection, msg) -> None:
    if base._domain_entry(hass, msg["entry_id"]) is None:  # noqa: SLF001
        connection.send_error(msg["id"], "not_found", "NanoKVM entry does not exist")
        return
    actor = base._connection_actor(connection)  # noqa: SLF001
    state = await _store(hass).async_set_maintenance(
        msg["entry_id"],
        enabled=msg["enabled"],
        minutes=msg.get("minutes", 0),
        note=msg.get("note", ""),
        actor=actor,
    )
    await base._remote_store(hass).async_add_event(  # noqa: SLF001
        msg["entry_id"],
        "maintenance_enabled" if msg["enabled"] else "maintenance_disabled",
        actor=actor,
        details={"until": state.get("until", ""), "note": state.get("note", "")[:200]},
    )
    await _probe_device(hass, msg["entry_id"], allow_recovery=False)
    connection.send_result(msg["id"], state)


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/panel/ops/auto-recovery/set",
        vol.Required("entry_id"): str,
        vol.Required("enabled"): bool,
        vol.Optional("hdmi_reset", default=True): bool,
        vol.Optional("cooldown_seconds", default=900): vol.All(int, vol.Range(min=300, max=86400)),
        vol.Optional("max_attempts_per_hour", default=3): vol.All(int, vol.Range(min=1, max=12)),
        vol.Optional("notify", default=True): bool,
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def websocket_ops_auto_recovery_set(hass, connection, msg) -> None:
    if base._domain_entry(hass, msg["entry_id"]) is None:  # noqa: SLF001
        connection.send_error(msg["id"], "not_found", "NanoKVM entry does not exist")
        return
    actor = base._connection_actor(connection)  # noqa: SLF001
    state = await _store(hass).async_set_auto_recovery(
        msg["entry_id"],
        enabled=msg["enabled"],
        hdmi_reset=msg.get("hdmi_reset", True),
        cooldown_seconds=msg.get("cooldown_seconds", 900),
        max_attempts_per_hour=msg.get("max_attempts_per_hour", 3),
        notify=msg.get("notify", True),
    )
    await base._remote_store(hass).async_add_event(  # noqa: SLF001
        msg["entry_id"],
        "auto_recovery_settings_updated",
        actor=actor,
        details={key: state[key] for key in ("enabled", "hdmi_reset", "cooldown_seconds", "max_attempts_per_hour", "notify")},
    )
    connection.send_result(msg["id"], state)


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/panel/ops/alert/ack",
        vol.Required("entry_id"): str,
        vol.Required("alert_id"): str,
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def websocket_ops_alert_ack(hass, connection, msg) -> None:
    actor = base._connection_actor(connection)  # noqa: SLF001
    await _store(hass).async_ack_alert(msg["entry_id"], msg["alert_id"], actor)
    runtime = _runtime_device(hass, msg["entry_id"])
    for alert in runtime.get("alerts") or []:
        if alert.get("id") == msg["alert_id"]:
            alert["acknowledged"] = True
            persistent_notification.async_dismiss(
                hass,
                notification_id=_notification_id(msg["entry_id"], str(alert.get("type") or "alert")),
            )
    await base._remote_store(hass).async_add_event(  # noqa: SLF001
        msg["entry_id"], "alert_acknowledged", actor=actor, details={"alert_id": msg["alert_id"][:160]}
    )
    connection.send_result(msg["id"], {"ok": True})


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/panel/ops/recovery/action",
        vol.Required("entry_id"): str,
        vol.Required("action"): vol.In({"diagnose", "safe_recovery", "reset_hid", "reset_hdmi", "reboot_nanokvm"}),
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def websocket_ops_recovery_action(hass, connection, msg) -> None:
    coordinator = base._loaded_coordinator(hass, msg["entry_id"])  # noqa: SLF001
    if coordinator is None:
        connection.send_error(msg["id"], "not_loaded", "NanoKVM is not loaded")
        return
    actor = base._connection_actor(connection)  # noqa: SLF001
    action = msg["action"]
    runtime = _runtime_device(hass, msg["entry_id"])
    recovery = runtime["recovery"]
    recovery.update({"state": "running", "action": action, "message": "", "updated_at": _utcnow()})
    started = monotonic()
    details: dict[str, Any] = {"action": action}
    try:
        admin = bool((coordinator.data.get("capabilities") or {}).get("admin"))
        pcie = bool((coordinator.data.get("capabilities") or {}).get("pcie"))
        if action == "diagnose":
            pass
        elif action == "reset_hid":
            if not admin:
                raise ValueError("NanoKVM administrator account is required")
            await async_reset_hid(coordinator.client)
        elif action == "reset_hdmi":
            if not admin or not pcie:
                raise ValueError("HDMI reset requires an administrator account and PCIe NanoKVM")
            await coordinator.client.async_reset_hdmi()
        elif action == "safe_recovery":
            if not admin:
                raise ValueError("NanoKVM administrator account is required")
            await async_reset_hid(coordinator.client)
            details["hid_reset"] = True
            if pcie:
                await coordinator.client.async_reset_hdmi()
                details["hdmi_reset"] = True
        elif action == "reboot_nanokvm":
            if not admin:
                raise ValueError("NanoKVM administrator account is required")
            await coordinator.client.async_reboot()
            details["reboot_expected"] = True

        if action != "reboot_nanokvm":
            await coordinator.async_request_refresh()
        duration_ms = round((monotonic() - started) * 1000.0, 1)
        details["duration_ms"] = duration_ms
        recovery.update(
            {
                "state": "success",
                "message": "Diagnostics completed" if action == "diagnose" else "Recovery action completed",
                "updated_at": _utcnow(),
                "duration_ms": duration_ms,
            }
        )
        await base._remote_store(hass).async_add_event(  # noqa: SLF001
            msg["entry_id"], f"recovery_{action}", actor=actor, details=details
        )
        if action != "reboot_nanokvm":
            await _probe_device(hass, msg["entry_id"], allow_recovery=False)
        connection.send_result(msg["id"], {"ok": True, "recovery": deepcopy(recovery), "device": _device_view(hass, msg["entry_id"])})
    except (NanoKVMError, ValueError) as err:
        recovery.update(
            {"state": "error", "message": str(err)[:200], "updated_at": _utcnow()}
        )
        await base._remote_store(hass).async_add_event(  # noqa: SLF001
            msg["entry_id"],
            f"recovery_{action}",
            actor=actor,
            result="error",
            details={"message": str(err)[:200]},
        )
        connection.send_error(msg["id"], "recovery_failed", str(err))


OPERATIONS_COMMANDS = (
    websocket_ops_list,
    websocket_ops_device,
    websocket_ops_refresh,
    websocket_ops_maintenance_set,
    websocket_ops_auto_recovery_set,
    websocket_ops_alert_ack,
    websocket_ops_recovery_action,
)
