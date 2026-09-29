"""Execute Manager inventory/lifecycle functions with isolated HA transports.

No Home Assistant installation or hardware is required. AST loading executes
production function bodies; only framework objects and network calls are faked.
"""

from __future__ import annotations

import ast
import asyncio
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

ROOT = Path(__file__).resolve().parents[1]
WEBUI = ROOT / "nanokvm_rest/webui/app.py"
INTEGRATION = ROOT / "custom_components/nanokvm_rest"


def load_functions(path, names, namespace=None):
    """Load selected production functions without importing framework packages."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    nodes = [ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0)]
    found = set()
    for node in tree.body:
        if (
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
            and node.name in names
        ):
            node.decorator_list = []
            nodes.append(node)
            found.add(node.name)
    if found != set(names):
        raise AssertionError(f"Missing production functions: {set(names) - found}")
    module = ast.fix_missing_locations(ast.Module(body=nodes, type_ignores=[]))
    result = dict(namespace or {})
    exec(compile(module, str(path), "exec"), result)
    return result


class ManagerInventoryTests(unittest.TestCase):
    def setUp(self):
        self.ns = load_functions(
            WEBUI,
            {
                "HAError",
                "_commands_not_registered",
                "_configured_inventory",
                "_inventory_response",
                "api_bootstrap",
            },
            {"jsonify": lambda payload: payload, "app": SimpleNamespace(logger=Mock())},
        )
        self.error = self.ns["HAError"]
        self.inventory = {
            "devices": [{"entry_id": "saved-1", "title": "My NanoKVM", "loaded": False}],
            "groups": [],
            "tags": [],
        }
        self.replies = {
            "nanokvm_rest/panel/kvm/list": self.inventory,
            "nanokvm_rest/panel/list": self.error("Unknown command.", code="unknown_command"),
            "nanokvm_rest/panel/ops/list": {"devices": [], "summary": {}, "alerts": []},
            "nanokvm_rest/panel/update/list": {"devices": []},
            "config_entries/get": [],
        }
        self.calls = []

        def ws_call(message):
            self.calls.append(message)
            reply = self.replies[message["type"]]
            if isinstance(reply, Exception):
                raise reply
            return reply

        self.ns["ha_ws_call"] = ws_call

    def bootstrap(self):
        return self.ns["api_bootstrap"]()

    def test_success_retains_devices(self):
        result = self.bootstrap()
        self.assertTrue(result["ok"])
        self.assertIs(result["devices"], self.inventory)
        self.assertEqual(result["warnings"], [])
        self.assertTrue(result["backend_ready"])

    def test_each_optional_module_failure_retains_devices(self):
        for command in ("nanokvm_rest/panel/ops/list", "nanokvm_rest/panel/update/list"):
            for reason in ("Unknown command.", "Device not found", "Timed out", "Unauthorized"):
                with self.subTest(command=command, reason=reason):
                    original = self.replies[command]
                    self.replies[command] = self.error(reason)
                    result = self.bootstrap()
                    self.assertTrue(result["ok"])
                    self.assertIs(result["devices"], self.inventory)
                    self.assertEqual(len(result["warnings"]), 1)
                    self.assertIn(reason, result["warnings"][0])
                    self.replies[command] = original

    def test_both_optional_failures_preserve_inventory(self):
        self.replies["nanokvm_rest/panel/ops/list"] = self.error("Unknown command.")
        self.replies["nanokvm_rest/panel/update/list"] = self.error("Timeout")
        result = self.bootstrap()
        self.assertIs(result["devices"], self.inventory)
        self.assertEqual(len(result["warnings"]), 2)

    def test_malformed_optional_response_is_warning(self):
        self.replies["nanokvm_rest/panel/ops/list"] = None
        result = self.bootstrap()
        self.assertIs(result["devices"], self.inventory)
        self.assertEqual(len(result["warnings"]), 1)

    def test_missing_backend_uses_saved_entries_without_secrets(self):
        self.replies["nanokvm_rest/panel/kvm/list"] = self.error("Unknown command.")
        self.replies["config_entries/get"] = [
            {
                "domain": "nanokvm_rest",
                "entry_id": f"id-{state}",
                "title": state,
                "state": state,
                "data": {"password": "DO-NOT-EXPOSE"},
                "options": {"token": "PRIVATE"},
            }
            for state in ("loaded", "setup_retry", "setup_error", "not_loaded", "setup_in_progress")
        ] + [
            {"domain": "another_integration", "entry_id": "other"},
            {"domain": "nanokvm_rest", "entry_id": "ignored", "source": "ignore"},
        ]
        result = self.bootstrap()
        self.assertEqual(len(result["devices"]["devices"]), 5)
        self.assertFalse(result["backend_ready"])
        self.assertEqual(len(result["warnings"]), 1)
        self.assertIn("Home Assistant Core", result["warnings"][0])
        self.assertNotIn("DO-NOT-EXPOSE", str(result))
        self.assertNotIn("PRIVATE", str(result))
        for device in result["devices"]["devices"]:
            self.assertFalse(device["backend_available"])
            self.assertFalse(device["available"])
            self.assertFalse(device["admin"])
            self.assertNotIn("data", device)
            self.assertNotIn("options", device)
        self.assertEqual(
            self.calls,
            [
                {"type": "nanokvm_rest/panel/kvm/list"},
                {"type": "nanokvm_rest/panel/list"},
                {"type": "config_entries/get", "domain": "nanokvm_rest"},
            ],
        )

    def test_structured_unknown_command_code_works(self):
        self.replies["nanokvm_rest/panel/kvm/list"] = self.error(
            "Unsupported type", code="unknown_command"
        )
        self.assertFalse(self.bootstrap()["backend_ready"])

    def test_real_empty_inventory_is_distinct_from_backend_failure(self):
        self.inventory["devices"] = []
        result = self.bootstrap()
        self.assertEqual(result["devices"]["devices"], [])
        self.assertTrue(result["backend_ready"])
        self.assertEqual(result["warnings"], [])

    def test_empty_saved_inventory_still_warns_about_missing_backend(self):
        self.replies["nanokvm_rest/panel/kvm/list"] = self.error("Unknown command.")
        result = self.bootstrap()
        self.assertEqual(result["devices"]["devices"], [])
        self.assertTrue(result["warnings"])

    def test_list_errors_never_become_successful_empty_inventory(self):
        for message in ("Device not found", "Timeout", "Invalid token", "Unauthorized"):
            with self.subTest(message=message):
                self.calls.clear()
                self.replies["nanokvm_rest/panel/kvm/list"] = self.error(message)
                payload, status = self.bootstrap()
                self.assertEqual(status, 502)
                self.assertFalse(payload["ok"])
                self.assertNotIn("devices", payload)
                self.assertEqual(len(self.calls), 1)

    def test_failed_core_fallback_is_an_error(self):
        self.replies["nanokvm_rest/panel/kvm/list"] = self.error("Unknown command.")
        self.replies["config_entries/get"] = self.error("Core unavailable")
        payload, status = self.bootstrap()
        self.assertEqual(status, 502)
        self.assertFalse(payload["ok"])

    def test_invalid_core_responses_are_errors(self):
        self.replies["nanokvm_rest/panel/kvm/list"] = self.error("Unknown command.")
        for invalid in (None, {}, [None], [{"domain": "nanokvm_rest"}]):
            with self.subTest(invalid=invalid):
                self.replies["config_entries/get"] = invalid
                payload, status = self.bootstrap()
                self.assertEqual(status, 502)
                self.assertFalse(payload["ok"])

    def test_invalid_device_lists_are_errors(self):
        for invalid in (None, [], {}, {"devices": {}}, {"devices": [None]}, {"devices": [{}]}):
            with self.subTest(invalid=invalid):
                self.replies["nanokvm_rest/panel/kvm/list"] = invalid
                payload, status = self.bootstrap()
                self.assertEqual(status, 502)
                self.assertFalse(payload["ok"])

    def test_newly_saved_entry_appears_on_next_refresh(self):
        self.replies["nanokvm_rest/panel/kvm/list"] = self.error("Unknown command.")
        self.assertEqual(self.bootstrap()["devices"]["devices"], [])
        self.replies["config_entries/get"].append(
            {
                "domain": "nanokvm_rest",
                "entry_id": "new",
                "title": "New",
                "state": "setup_in_progress",
            }
        )
        self.assertEqual(self.bootstrap()["devices"]["devices"][0]["entry_id"], "new")

    def test_legacy_backend_retains_nanokvm_inventory(self):
        self.replies["nanokvm_rest/panel/kvm/list"] = self.error("Unknown command.")
        self.replies["nanokvm_rest/panel/list"] = self.inventory
        result = self.bootstrap()
        self.assertIs(result["devices"], self.inventory)
        self.assertTrue(result["backend_ready"])
        self.assertEqual(
            self.calls[:2],
            [{"type": "nanokvm_rest/panel/kvm/list"}, {"type": "nanokvm_rest/panel/list"}],
        )

    def test_not_found_is_not_a_missing_command(self):
        self.assertFalse(self.ns["_commands_not_registered"](self.error("Device not found")))


class ManagerConsoleSessionTests(unittest.TestCase):
    def setUp(self):
        self.calls = []
        self.payload = {"entry_id": "device-1"}

        def ws_call(message, *, timeout=15.0):
            self.calls.append((message, timeout))
            return {
                "path": "/api/nanokvm_rest/console",
                "protocol": "nanokvm-console",
                "token": "nkv-test-token",
                "expires_in": 30,
            }

        self.request = SimpleNamespace(get_json=lambda silent=True: dict(self.payload))
        self.ns = load_functions(
            WEBUI,
            {"HAError", "api_console_session"},
            {
                "jsonify": lambda payload: payload,
                "request": self.request,
                "require_write_header": lambda: None,
                "ha_ws_call": ws_call,
            },
        )

    def test_console_session_uses_selected_entry_and_returns_bridge_session(self):
        result = self.ns["api_console_session"]()
        self.assertTrue(result["ok"])
        self.assertEqual(result["path"], "/api/nanokvm_rest/console")
        self.assertEqual(result["protocol"], "nanokvm-console")
        self.assertEqual(result["token"], "nkv-test-token")
        self.assertEqual(
            self.calls,
            [({"type": "nanokvm_rest/panel/console/session", "entry_id": "device-1"}, 10.0)],
        )

    def test_console_session_requires_entry_id(self):
        self.payload.clear()
        payload, status = self.ns["api_console_session"]()
        self.assertEqual(status, 400)
        self.assertFalse(payload["ok"])

    def test_console_session_rejects_malformed_backend_response(self):
        self.ns["ha_ws_call"] = lambda *args, **kwargs: {"path": "/api/nanokvm_rest/console"}
        payload, status = self.ns["api_console_session"]()
        self.assertEqual(status, 502)
        self.assertFalse(payload["ok"])
        self.assertIn("invalid Remote Console session", payload["error"])


class BackendLifecycleTests(unittest.IsolatedAsyncioTestCase):
    def panel_namespace(self, fail_first_load=False):
        events = []
        failed = False

        class Store:
            def __init__(self, hass):
                self.hass = hass

            async def async_load(self):
                nonlocal failed
                await asyncio.sleep(0)
                if fail_first_load and not failed:
                    failed = True
                    raise OSError("Temporary store read error")
                events.append("store_loaded")

        base = SimpleNamespace(
            RemoteServerStore=Store,
            DATA_REMOTE_STORE="remote_store",
            NanoKVMOfflineUpdateView=Mock(),
        )
        for name in (
            "list_devices",
            "device_status",
            "device_action",
            "update_metadata",
            "history",
            "wol_save",
            "wol_delete",
            "wol_run",
        ):
            setattr(base, "websocket_" + name, name)
        hass = SimpleNamespace(
            data={},
            http=SimpleNamespace(register_view=Mock(), async_register_static_paths=AsyncMock()),
        )
        ns = load_functions(
            INTEGRATION / "panel_v4.py",
            {"async_setup_panel_backend"},
            {
                "asyncio": asyncio,
                "Path": Path,
                "__file__": str(INTEGRATION / "panel_v4.py"),
                "base": base,
                "RemoteAdvancedStore": Store,
                "DATA_PANEL_BACKEND_LOCK": "backend_lock",
                "DATA_PANEL_BACKEND_REGISTERED": "registered",
                "DATA_ADVANCED_STORE": "advanced",
                "DATA_UPDATE_RUNTIME": "updates",
                "async_setup_operations": AsyncMock(),
                "websocket_api": SimpleNamespace(async_register_command=Mock()),
                "EXTENDED_COMMANDS": ("extended",),
                "OPERATIONS_COMMANDS": ("operations",),
                "KVM_COMMANDS": ("kvm-list", "kvm-manage"),
                "websocket_console_session": "console",
                "NanoKVMISOUploadView": Mock(),
                "NanoKVMConsoleView": Mock(),
                "StaticPathConfig": Mock(),
                "STATIC_URL": "/nanokvm_rest_static",
            },
        )
        return ns, hass, events

    async def test_backend_initializes_without_any_device(self):
        ns, hass, events = self.panel_namespace()
        await ns["async_setup_panel_backend"](hass)
        self.assertTrue(hass.data["registered"])
        self.assertEqual(len(events), 2)
        self.assertEqual(ns["websocket_api"].async_register_command.call_count, 13)
        self.assertNotIn("visible_entries", hass.data)

    async def test_concurrent_and_repeated_registration_is_idempotent(self):
        ns, hass, events = self.panel_namespace()
        await asyncio.gather(*(ns["async_setup_panel_backend"](hass) for _ in range(4)))
        await ns["async_setup_panel_backend"](hass)
        self.assertEqual(len(events), 2)
        self.assertEqual(ns["websocket_api"].async_register_command.call_count, 13)
        hass.http.async_register_static_paths.assert_awaited_once()
        ns["async_setup_operations"].assert_awaited_once()

    async def test_failed_store_load_releases_registration_lock(self):
        ns, hass, _ = self.panel_namespace(fail_first_load=True)
        with self.assertRaises(OSError):
            await ns["async_setup_panel_backend"](hass)
        self.assertFalse(hass.data.get("registered"))
        await ns["async_setup_panel_backend"](hass)
        self.assertTrue(hass.data["registered"])

    async def test_domain_setup_registers_backend_before_failed_first_refresh(self):
        backend = AsyncMock()
        coordinator = SimpleNamespace(
            async_config_entry_first_refresh=AsyncMock(side_effect=OSError("NanoKVM offline"))
        )
        ns = load_functions(
            INTEGRATION / "__init__.py",
            {"async_setup", "async_setup_entry"},
            {
                "async_setup_panel_backend": backend,
                "async_get_clientsession": Mock(),
                "NanoKVMClient": Mock(),
                "NanoKVMCoordinator": Mock(return_value=coordinator),
                "CONF_VERIFY_SSL": "verify_ssl",
                "async_create_coordinator": AsyncMock(return_value=coordinator),
                "runtime_provider": Mock(return_value=SimpleNamespace(disconnect=AsyncMock())),
                "CONF_BASE_URL": "base_url",
                "CONF_USERNAME": "username",
                "CONF_PASSWORD": "password",
                "CONF_SCAN_INTERVAL": "scan_interval",
                "DEFAULT_SCAN_INTERVAL": 30,
            },
        )
        hass = SimpleNamespace(data={})
        entry = SimpleNamespace(
            data={"base_url": "http://nanokvm.test", "username": "admin", "password": "test-only"},
            options={},
        )
        self.assertTrue(await ns["async_setup"](hass, {}))
        backend.assert_awaited_once_with(hass)
        with self.assertRaises(OSError):
            await ns["async_setup_entry"](hass, entry)
        backend.assert_awaited_once_with(hass)


if __name__ == "__main__":
    unittest.main()
