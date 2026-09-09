"""Repository-level contracts for the NanoKVM integration packages."""

from __future__ import annotations

import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
HACS = ROOT / "custom_components" / "nanokvm_rest"
BUNDLED = ROOT / "nanokvm_rest" / "integration" / "nanokvm_rest"


class IntegrationContractTests(unittest.TestCase):
    """Protect real-device compatibility and package synchronization."""

    def test_hacs_and_bundled_integration_are_identical(self) -> None:
        hacs_files = {
            path.relative_to(HACS)
            for path in HACS.rglob("*")
            if path.is_file() and "__pycache__" not in path.parts
        }
        bundled_files = {
            path.relative_to(BUNDLED)
            for path in BUNDLED.rglob("*")
            if path.is_file() and "__pycache__" not in path.parts
        }
        self.assertEqual(hacs_files, bundled_files)
        for relative in sorted(hacs_files):
            self.assertEqual(
                (HACS / relative).read_bytes(),
                (BUNDLED / relative).read_bytes(),
                f"Integration copies differ: {relative}",
            )

    def test_release_versions_are_aligned(self) -> None:
        manifest = json.loads((HACS / "manifest.json").read_text(encoding="utf-8"))
        bundled_manifest = json.loads(
            (BUNDLED / "manifest.json").read_text(encoding="utf-8")
        )
        addon_config = (ROOT / "nanokvm_rest" / "config.yaml").read_text(
            encoding="utf-8"
        )
        dockerfile = (ROOT / "nanokvm_rest" / "Dockerfile").read_text(
            encoding="utf-8"
        )
        version = manifest["version"]
        self.assertEqual(version, bundled_manifest["version"])
        self.assertRegex(addon_config, rf'(?m)^version: "{re.escape(version)}"$')
        self.assertIn(f'ARG BUILD_VERSION="{version}"', dockerfile)

    def test_setup_error_messages_are_translated(self) -> None:
        required = {
            "cannot_connect",
            "invalid_auth",
            "invalid_url",
            "permission_denied",
            "ssl_error",
        }
        for relative in (
            Path("strings.json"),
            Path("translations/en.json"),
            Path("translations/pl.json"),
        ):
            payload = json.loads((HACS / relative).read_text(encoding="utf-8"))
            self.assertTrue(required.issubset(payload["config"]["error"]), relative)

    def test_connection_probe_requires_nanokvm_fingerprint(self) -> None:
        source = (HACS / "device_setup.py").read_text(encoding="utf-8")
        self.assertIn('/api/vm/info', source)
        self.assertIn('_looks_like_nanokvm_response', source)
        self.assertIn('ssl_error', source)

    def test_optional_core_endpoints_do_not_gate_identity(self) -> None:
        source = (HACS / "coordinator.py").read_text(encoding="utf-8")
        self.assertIn('info = await self.client.async_get_info()', source)
        for capability in ("hardware", "gpio", "hostname"):
            self.assertIn(f'"{capability}"', source)
        self.assertGreaterEqual(source.count('tolerate_api_errors=True'), 3)


if __name__ == "__main__":
    unittest.main()
