"""Update entity for the NanoKVM application."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

from homeassistant.components.update import (
    UpdateDeviceClass,
    UpdateEntity,
    UpdateEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .api import NanoKVMConnectionError, NanoKVMError
from .coordinator import NanoKVMCoordinator
from .entity import NanoKVMEntity

UPDATE_RECOVERY_TIMEOUT = 240
UPDATE_RECOVERY_INTERVAL = 5


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the NanoKVM application update entity."""
    coordinator: NanoKVMCoordinator = entry.runtime_data
    if (
        coordinator.data.get("capabilities", {}).get("admin")
        and (
            coordinator.data.get("application_version") is not None
            or coordinator.data.get("preview_updates") is not None
        )
    ):
        async_add_entities([NanoKVMApplicationUpdate(coordinator)])


class NanoKVMApplicationUpdate(NanoKVMEntity, UpdateEntity):
    """Represent NanoKVM application updates."""

    _attr_name = "Application"
    _attr_icon = "mdi:update"
    _attr_device_class = UpdateDeviceClass.FIRMWARE
    _attr_entity_category = EntityCategory.CONFIG
    _attr_supported_features = UpdateEntityFeature.INSTALL

    def __init__(self, coordinator: NanoKVMCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device_key}_application_update"
        self._installing = False
        self._install_stage = "idle"
        self._install_message = ""
        self._install_started_at: str | None = None

    @property
    def installed_version(self) -> str | None:
        """Return installed NanoKVM application version."""
        version_data = self.coordinator.data.get("application_version") or {}
        value = version_data.get("current")
        if value:
            return str(value)
        value = (self.coordinator.data.get("info") or {}).get("application")
        return str(value) if value else None

    @property
    def latest_version(self) -> str | None:
        """Return latest NanoKVM application version."""
        version_data = self.coordinator.data.get("application_version") or {}
        value = version_data.get("latest")
        if value:
            return str(value)
        return self.installed_version

    @property
    def in_progress(self) -> bool:
        """Return whether an update request is running."""
        return self._installing

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose the current update/recovery stage."""
        return {
            "update_stage": self._install_stage,
            "update_message": self._install_message,
            "update_started_at": self._install_started_at,
        }

    def _set_install_state(self, stage: str, message: str) -> None:
        self._install_stage = stage
        self._install_message = message
        self.async_write_ha_state()

    async def _refresh_coordinator_after_update(self) -> None:
        """Refresh HA state after a version change without reusing the stale cache."""
        self.coordinator.invalidate_application_version()
        await self.coordinator.async_request_refresh()

    async def async_install(
        self, version: str | None, backup: bool, **kwargs: Any
    ) -> None:
        """Install the latest release from the NanoKVM configured update channel.

        NanoKVM may intentionally close the HTTP connection while its application
        service restarts. Treat that disconnect as an expected transition, wait
        for the device to return, and verify that the version reaches the target
        reported by NanoKVM before declaring the installation successful.
        """
        self._installing = True
        self._install_started_at = datetime.now(timezone.utc).isoformat()
        self._set_install_state(
            "checking",
            "Checking the latest NanoKVM application version before update.",
        )

        before = self.installed_version or ""
        target = version or self.latest_version or ""

        try:
            # Home Assistant may still hold a cached latest_version. Query the
            # device immediately before starting the update so POST /update and
            # our verification use the same NanoKVM update channel.
            try:
                fresh = await self.coordinator.client.async_get_application_version()
                fresh_current = str(fresh.get("current") or "")
                fresh_latest = str(fresh.get("latest") or "")
                if fresh_current:
                    before = fresh_current
                if fresh_latest:
                    target = fresh_latest
            except NanoKVMError as err:
                if not target:
                    self._set_install_state(
                        "failed",
                        f"Could not determine the latest NanoKVM version: {err}",
                    )
                    raise HomeAssistantError(
                        f"NanoKVM latest version could not be determined: {err}"
                    ) from err

            if before and target and before == target:
                await self._refresh_coordinator_after_update()
                self._set_install_state(
                    "completed",
                    f"NanoKVM already reports the latest version {before}.",
                )
                return

            self._set_install_state(
                "installing",
                (
                    f"Updating NanoKVM from {before or 'unknown'} to "
                    f"{target or 'the latest available version'}. "
                    "Do not power off the device."
                ),
            )

            request_disconnect = False
            try:
                await self.coordinator.client.async_update_application()
            except NanoKVMConnectionError:
                # Expected on NanoKVM versions that restart the API service as
                # part of update/install. Verification below determines success.
                request_disconnect = True
            except NanoKVMError as err:
                self._set_install_state(
                    "failed",
                    f"NanoKVM rejected the update request: {err}",
                )
                raise HomeAssistantError(
                    f"NanoKVM update could not be started: {err}"
                ) from err

            self.coordinator.invalidate_application_version()
            self._set_install_state(
                "restarting" if request_disconnect else "waiting",
                (
                    "Connection to NanoKVM was lost after update/install. "
                    "This can be normal while the NanoKVM application restarts. "
                    "Waiting for the device to return and verifying its version."
                    if request_disconnect
                    else "Update request accepted. Waiting for NanoKVM to restart and report the target version."
                ),
            )

            attempts = max(1, UPDATE_RECOVERY_TIMEOUT // UPDATE_RECOVERY_INTERVAL)
            last_error = "connection lost" if request_disconnect else ""
            last_version = before
            last_reported_latest = target

            for _ in range(attempts):
                await asyncio.sleep(UPDATE_RECOVERY_INTERVAL)
                try:
                    data = await self.coordinator.client.async_get_application_version()
                    current = str(data.get("current") or "")
                    reported_latest = str(data.get("latest") or "")
                    if current:
                        last_version = current
                    if reported_latest:
                        last_reported_latest = reported_latest

                    expected = reported_latest or target

                    self._set_install_state(
                        "verifying",
                        (
                            "NanoKVM is online. Verifying application version "
                            f"({current or 'unknown'} / target {expected or 'unknown'})."
                        ),
                    )

                    # When a target is known, never treat an arbitrary version
                    # change as success. The update is complete only when the
                    # installed version matches the latest version currently
                    # reported by NanoKVM (or the pre-update target if the
                    # endpoint temporarily omits `latest`).
                    if current and expected and current == expected:
                        await self._refresh_coordinator_after_update()
                        self._set_install_state(
                            "completed",
                            (
                                f"Update completed successfully: "
                                f"{before or 'unknown'} → {current}."
                            ),
                        )
                        return

                    # Backward-compatible fallback for firmware that exposes a
                    # current version but no latest version at all.
                    if (
                        current
                        and not expected
                        and ((before and current != before) or not before)
                    ):
                        await self._refresh_coordinator_after_update()
                        self._set_install_state(
                            "completed",
                            (
                                f"Update completed successfully: "
                                f"{before or 'unknown'} → {current}."
                            ),
                        )
                        return

                    last_error = (
                        "NanoKVM returned online but has not reached the target "
                        f"version yet (current {current or 'unknown'}, "
                        f"target {expected or 'unknown'})"
                    )
                except NanoKVMError as err:
                    last_error = str(err)
                    self._set_install_state(
                        "waiting_for_device",
                        "NanoKVM is temporarily unavailable after update/install. Waiting for it to return.",
                    )

            detail = (
                f" Last reported version: {last_version}." if last_version else ""
            )
            if last_reported_latest:
                detail += f" Expected latest version: {last_reported_latest}."
            if last_error:
                detail += f" Last connection status: {last_error}."
            message = (
                f"Could not confirm the NanoKVM update within {UPDATE_RECOVERY_TIMEOUT} seconds."
                f"{detail} The update may still have been started. Check the device/network and "
                "the current NanoKVM application version before running the update again."
            )
            self._set_install_state("timeout", message)
            raise HomeAssistantError(message)
        finally:
            self._installing = False
            self.async_write_ha_state()
