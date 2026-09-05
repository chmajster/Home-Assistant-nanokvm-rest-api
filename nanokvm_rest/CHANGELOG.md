# Changelog

## 0.6.1

- Refreshes **Remote Server** with a modern app-like visual design.
- Adds a dedicated mobile layout instead of shrinking the desktop interface.
- Adds a fixed bottom navigation bar on phones for Overview, Virtual Media, Maintenance and Native UI.
- Adds horizontally scrollable NanoKVM device cards on mobile with online/offline and host-power indicators.
- Adds a sticky mobile header and safe-area spacing for phones with display cutouts/home indicators.
- Enlarges touch targets for power, reset, HID and maintenance actions.
- Converts Virtual Media controls into responsive cards that remain usable on narrow screens.
- Improves status cards, typography, spacing, rounded surfaces and Home Assistant theme integration.
- Adds inline SVG icons without external frontend dependencies.
- Adds an extra narrow-screen breakpoint for devices around 390 px wide.
- Loads the redesigned sidepanel from `remote-server-v2.js` while keeping the existing backend/API unchanged.

## 0.6.0

- Rebuilds **Remote Server** as a full Home Assistant sidepanel web interface.
- Adds a persistent left-side NanoKVM device selector with online and host-power status.
- Adds Overview, Virtual Media, Maintenance and Native UI views.
- Adds 15-second selected-device refresh and periodic refresh of the complete KVM list.
- Adds responsive desktop, tablet and mobile layouts using Home Assistant theme variables.
- Adds confirmation prompts for destructive host reset, force-off, NanoKVM reboot, ISO deletion and offline update actions.
- Adds direct access to the selected NanoKVM native web UI and optional iframe embedding when browser security rules allow it.
- Adds address copy support and mixed-content detection for HTTPS Home Assistant with HTTP NanoKVM devices.
- Makes `panel_custom` an explicit integration dependency so the sidepanel is initialized deterministically.
- Aligns the integration, app package and container default version at `0.6.0`.

## 0.5.0

- Adds the administrator-only **Remote Server** sidebar panel.
- Lists all configured NanoKVM config entries and lets the user choose which KVM to manage.
- Adds host Power, Reset and Force Off controls to the Remote Server panel.
- Adds NanoKVM HID Reset without rebooting the KVM or attached host.
- Adds full virtual-media status with available ISO/IMG files, mounted image and CD-ROM mode.
- Adds mount as CD-ROM, mount as USB disk, unmount, remount mode change and image deletion.
- Adds offline NanoKVM application updates from a local `nanokvm_X.Y.Z.tar.gz` package.
- Supports optional SHA-256 verification for offline update packages.
- Proxies offline update packages through Home Assistant to the selected NanoKVM.
- Keeps dangerous Remote Server operations restricted to Home Assistant administrators and NanoKVM administrator accounts where required.

## 0.4.0

- Adds native NanoKVM application update entity.
- Adds writable hostname and web-title entities.
- Adds OLED sleep, swap-size and memory-limit configuration.
- Adds virtual USB network and disk controls.
- Adds Home Assistant device actions for power, reset, WOL, virtual media and HID paste.
- Adds device triggers for power, HDMI signal and NanoKVM availability changes.
- Adds an example Lovelace dashboard.

## 0.3.0

- Initial Home Assistant app repository package.
- Installs the bundled NanoKVM REST integration into Home Assistant's `custom_components` directory.
- Supports `amd64` and `aarch64` Home Assistant systems.