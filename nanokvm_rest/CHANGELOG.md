# Changelog

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
