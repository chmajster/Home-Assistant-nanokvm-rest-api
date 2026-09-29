"""Execute production configuration/migration/CRUD bodies with HA entry fixtures.

Network authentication is covered by the real protocol server tests. This suite
isolates atomic persistence behavior; it does not pretend to run full HA.
"""

from __future__ import annotations

import asyncio
import sys
import tempfile
import unittest
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from kvm_test_support import PACKAGE, ROOT, provider
from test_manager_inventory import load_functions

configuration = provider("configuration")
secrets = provider("secrets")
registry = provider("registry")
KVMError = provider("errors").KVMError


class ConfigurationTests(unittest.TestCase):
    def test_legacy_default_provider_and_secret_retention(self):
        previous = {
            "base_url": "http://192.168.1.10",
            "credential_encrypted": "opaque",
            "verify_ssl": True,
        }
        candidate = configuration.normalize_candidate({"title": "New name"}, previous)
        self.assertEqual(candidate["provider"], "nanokvm")
        self.assertEqual(candidate["credential_encrypted"], "opaque")
        self.assertNotIn("provider", previous)
        self.assertNotIn("password", candidate)

    def test_provider_cannot_change_and_explicit_empty_password(self):
        previous = {
            "provider": "jetkvm",
            "base_url": "http://192.168.1.10",
            "credential_encrypted": "opaque",
        }
        with self.assertRaises(KVMError):
            configuration.normalize_candidate({"provider": "nanokvm"}, previous)
        candidate = configuration.normalize_candidate({"password": ""}, previous)
        self.assertEqual(candidate["password"], "")
        self.assertEqual(previous["credential_encrypted"], "opaque")

    def test_unknown_fields_invalid_policy_and_fractional_port(self):
        for payload in [
            {"request_url": "http://127.0.0.1"},
            {"lan_networks": "0.0.0.0/0"},
            {"port": 80.5},
            {"port": True},
        ]:
            with self.subTest(payload=payload), self.assertRaises(KVMError):
                configuration.normalize_candidate({"host": "192.168.1.10", **payload})


class StorageTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.entry = SimpleNamespace(
            entry_id="jet-1",
            domain="nanokvm_rest",
            version=1,
            title="Old name",
            unique_id="jetkvm:physical-1",
            data={
                "provider": "jetkvm",
                "base_url": "http://192.168.1.10",
                "password": "old-private-value",
                "verify_ssl": True,
            },
        )
        self.hass = SimpleNamespace(
            data={}, config=SimpleNamespace(path=lambda path: str(Path(self.tmp.name) / path))
        )
        self.hass.config_entries = SimpleNamespace(
            async_entries=lambda domain: [self.entry],
            async_get_entry=lambda id: self.entry if id == self.entry.entry_id else None,
            async_update_entry=Mock(),
            async_reload=AsyncMock(return_value=True),
            async_remove=AsyncMock(return_value=True),
        )
        self.hass.async_add_executor_job = lambda fn: asyncio.to_thread(fn)
        self.entry.data = await secrets.async_protect_data(self.hass, self.entry.data)
        self.disconnect = AsyncMock(return_value=1)
        console = ModuleType(PACKAGE + ".console")
        console.async_disconnect_entry = self.disconnect
        self.console_patch = patch.dict(sys.modules, {PACKAGE + ".console": console})
        self.console_patch.start()
        self.validate = AsyncMock()
        self.state = SimpleNamespace(remove=AsyncMock())
        self.ns = load_functions(
            ROOT / "custom_components/nanokvm_rest/kvm_api.py",
            {"_entry", "_title", "_save", "_delete"},
            {
                "__package__": PACKAGE,
                "DOMAIN": "nanokvm_rest",
                "KVMError": KVMError,
                "normalize_candidate": configuration.normalize_candidate,
                "async_validate_candidate": self.validate,
                "unique_id_for": configuration.unique_id_for,
                "async_protect_data": secrets.async_protect_data,
                "async_state_store": AsyncMock(return_value=self.state),
                "MAX_DEVICES": 128,
            },
        )

    async def asyncTearDown(self):
        self.console_patch.stop()
        self.tmp.cleanup()

    async def test_failed_edit_keeps_ciphertext_and_active_session(self):
        before = dict(self.entry.data)
        self.validate.side_effect = KVMError("invalid_password")
        with self.assertRaises(KVMError):
            await self.ns["_save"](self.hass, {"entry_id": "jet-1", "password": "incorrect"})
        self.assertEqual(self.entry.data, before)
        self.hass.config_entries.async_update_entry.assert_not_called()
        self.disconnect.assert_not_awaited()
        self.assertEqual(
            await secrets.async_password(self.hass, self.entry.data), "old-private-value"
        )

    async def test_edit_saves_encrypted_password_after_success(self):
        candidate = {**self.entry.data, "password": "new-private-value"}
        self.validate.return_value = (candidate, {"device_id": "physical-1"})
        await self.ns["_save"](self.hass, {"entry_id": "jet-1", "password": "new-private-value"})
        saved = self.hass.config_entries.async_update_entry.call_args.kwargs["data"]
        self.assertNotIn("password", saved)
        self.assertNotIn("new-private-value", str(saved))
        self.assertEqual(await secrets.async_password(self.hass, saved), "new-private-value")
        self.disconnect.assert_awaited_once()
        self.hass.config_entries.async_reload.assert_awaited_once_with("jet-1")

    async def test_edit_rejects_different_physical_device(self):
        self.validate.return_value = (
            {**self.entry.data, "base_url": "http://192.168.1.99"},
            {"device_id": "different"},
        )
        with self.assertRaises(KVMError) as caught:
            await self.ns["_save"](self.hass, {"entry_id": "jet-1", "host": "192.168.1.99"})
        self.assertEqual(caught.exception.code, "wrong_device")
        self.hass.config_entries.async_update_entry.assert_not_called()

    async def test_name_only_edit_does_not_require_online(self):
        await self.ns["_save"](self.hass, {"entry_id": "jet-1", "title": "New name"})
        self.validate.assert_not_awaited()
        self.hass.config_entries.async_update_entry.assert_called_once_with(
            self.entry, title="New name"
        )

    async def test_actual_ha_delete_and_state_cleanup_are_requested(self):
        result = await self.ns["_delete"](self.hass, {"entry_id": "jet-1"})
        self.assertTrue(result["deleted"])
        self.hass.config_entries.async_remove.assert_awaited_once_with("jet-1")
        self.state.remove.assert_awaited_once_with("jet-1")

    async def test_migration_encrypts_old_nano_and_preserves_identity(self):
        self.entry.data = {
            "base_url": "http://192.168.1.10",
            "password": "legacy",
            "username": "admin",
        }
        self.entry.unique_id = "old-nanokvm-id"
        ns = load_functions(
            ROOT / "custom_components/nanokvm_rest/__init__.py",
            {"async_migrate_entry"},
            {"async_protect_data": secrets.async_protect_data},
        )
        self.assertTrue(await ns["async_migrate_entry"](self.hass, self.entry))
        changes = self.hass.config_entries.async_update_entry.call_args.kwargs
        self.assertEqual(changes["version"], 2)
        self.assertEqual(changes["data"]["provider"], "nanokvm")
        self.assertNotIn("password", changes["data"])
        self.assertEqual(self.entry.unique_id, "old-nanokvm-id")
        self.assertEqual(await secrets.async_password(self.hass, changes["data"]), "legacy")

    async def test_vault_failure_does_not_write_entry(self):
        ns = load_functions(
            ROOT / "custom_components/nanokvm_rest/__init__.py",
            {"async_migrate_entry"},
            {"async_protect_data": AsyncMock(side_effect=KVMError("secret_storage"))},
        )
        with self.assertRaises(KVMError):
            await ns["async_migrate_entry"](self.hass, self.entry)
        self.hass.config_entries.async_update_entry.assert_not_called()
