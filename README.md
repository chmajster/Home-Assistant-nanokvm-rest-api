# NanoKVM REST for Home Assistant

Custom Home Assistant integration for Sipeed NanoKVM using the local NanoKVM REST API. No MQTT or SSH fallback is required.

## Features

- UI setup through Home Assistant Config Flow and support for multiple NanoKVM devices.
- HTTP/HTTPS connections, optional TLS certificate verification and automatic session reauthentication.
- Power/HDD/HDMI monitoring and power, reset and force-off controls.
- Role- and hardware-aware capability detection for administrator-only and PCIe-only features.
- HDMI capture, SSH, mDNS and mouse-jiggler controls.
- Native NanoKVM application update entity with installed/latest version reporting and one-click update.
- Stable/preview update-channel control and optional custom NanoKVM update-server configuration.
- Writable NanoKVM hostname and web interface title.
- OLED sleep timeout, swap size and Go runtime memory-limit controls.
- Virtual USB network and virtual disk switches.
- Home Assistant device actions for power-on, power-button press, force-off, reset, NanoKVM reboot, Wake-on-LAN, ISO mount/unmount and HID text paste.
- Home Assistant device triggers for host power transitions, HDMI signal transitions and NanoKVM unavailability.
- Diagnostic sensors for hostname, hardware, application, system image, IP, mDNS, account role, web title, mouse-jiggler mode and swap size when available.
- Downloadable Home Assistant diagnostics with credentials and identifying network/account fields redacted.
- Graceful handling of optional endpoints missing on older NanoKVM firmware.
- Polish and English setup/device-automation translations.

## Requirements

- Home Assistant 2026.8.0 or newer.
- NanoKVM reachable from the Home Assistant instance.
- NanoKVM credentials when authentication is enabled.
- Administrator NanoKVM account for update/configuration/virtual-device features that are admin-only upstream.

## Installation from the Home Assistant app/add-on store

1. Open the Home Assistant app/add-on store.
2. Open **Repositories**.
3. Add `https://github.com/chmajster/homeassistant-nanokvm-rest-api`.
4. Install **NanoKVM REST**.
5. Start the app once. It copies the bundled integration to `/config/custom_components/nanokvm_rest` and then stops by design.
6. Restart Home Assistant.
7. Go to **Settings → Devices & services → Add integration** and select **NanoKVM REST**.

After an app update, start the app once again and restart Home Assistant so the updated integration files are loaded.

The repository must be reachable by Home Assistant Supervisor. A normal custom-repository installation cannot clone a private GitHub repository without supported Git authentication, so the repository must be public or otherwise anonymously reachable for direct URL installation.

## Installation with HACS

1. Open HACS in Home Assistant.
2. Add `https://github.com/chmajster/homeassistant-nanokvm-rest-api` as a custom repository of type **Integration**.
3. Install **NanoKVM REST**.
4. Restart Home Assistant.
5. Go to **Settings → Devices & services → Add integration** and select **NanoKVM REST**.

## Manual installation

Copy `custom_components/nanokvm_rest` to `/config/custom_components/nanokvm_rest`, restart Home Assistant and add **NanoKVM REST** from **Settings → Devices & services**.

## Configuration

The setup form accepts the NanoKVM address, username, password and TLS certificate verification setting. If no URL scheme is provided, the integration uses `http://`.

The NanoKVM `deviceKey`, when available, is used as the Home Assistant config-entry unique ID to prevent the same physical device from being configured twice.

The options flow exposes:

- polling interval: 30–3600 seconds;
- force-off power-button duration: 1000–10000 ms.

Connection address, credentials and TLS verification can be changed using Home Assistant reconfigure/reauthentication flows.

## Entities

### Binary sensors

- Power state / power LED.
- HDD activity when reported by the API.
- HDMI signal presence on supported PCIe hardware.

### Buttons

- Power: 800 ms power-button press.
- Reset: 800 ms reset-button press.
- Force off: long power-button press using the configured duration.
- Reset HDMI: PCIe hardware only.
- Reboot NanoKVM: administrator account only.

### Switches

- HDMI capture on PCIe/admin configurations.
- SSH service.
- mDNS advertising.
- Mouse jiggler.
- Preview update channel.
- Custom update server enable/disable.
- Memory-limit enable/disable.
- Virtual USB network device.
- Virtual USB disk device.

### Number controls

- HDMI idle timeout: 0–10080 minutes.
- NanoKVM Go runtime memory limit: 50–1024 MB.
- Swap size: 0–512 MB; `0` disables swap.
- OLED sleep timeout: 0–3600 seconds when OLED hardware is present.

### Text controls

- Hostname.
- Web interface title.
- Custom update-server URL (credential-bearing URLs are rejected so secrets are not exposed as entity state).

### Update

`update.nanokvm_application` exposes the currently installed NanoKVM application version and the latest version returned by NanoKVM. The external version check is cached for six hours instead of being executed on every normal polling cycle. The **Install** action calls NanoKVM's own application update endpoint. Preview/stable selection and an optional custom update server are exposed as configuration entities. A custom server overrides the normal stable/preview source, matching upstream NanoKVM behavior.

### Diagnostic sensors

Hostname, hardware version, application version, system image, IP address, mDNS address, account role, web title, mouse-jiggler mode and swap size are exposed when supported.

## Device actions

The integration adds native Home Assistant device actions to the automation editor:

- Power on — presses the power button only when the power LED currently reports off.
- Power button — always performs a short power-button press.
- Force off — performs the configured long power-button press only when the host reports on.
- Reset.
- Reboot NanoKVM.
- Wake-on-LAN — accepts a MAC address.
- Mount ISO/image — accepts an image name available on NanoKVM and an optional CD-ROM flag.
- Unmount ISO/image.
- Paste text through NanoKVM HID.

`Ctrl+Alt+Del` is intentionally not exposed: the current upstream NanoKVM REST API provides shortcut management but no confirmed REST endpoint for executing an arbitrary keyboard chord. The integration does not invent undocumented endpoints.

## Device triggers

Automations can trigger when:

- the attached host changes to powered on;
- the attached host changes to powered off;
- HDMI signal appears;
- HDMI signal disappears;
- the NanoKVM becomes unavailable after previously being reachable.

Events are emitted from coordinator state transitions, so initial integration startup does not generate false power/HDMI triggers.

## Example dashboard

An example built only from standard Home Assistant Lovelace cards is available in [`docs/dashboard.yaml`](docs/dashboard.yaml). Entity IDs can differ depending on the device name and existing entity registry, so adjust them after adding the integration.

## REST API endpoints used

Core and host control:

```text
POST /api/auth/login
GET  /api/auth/account
GET  /api/vm/info
GET  /api/vm/hardware
GET  /api/vm/gpio
POST /api/vm/gpio
GET  /api/vm/hostname
POST /api/vm/hostname
GET  /api/vm/web-title
POST /api/vm/web-title
```

PCIe HDMI:

```text
GET  /api/vm/hdmi
POST /api/vm/hdmi/reset
POST /api/vm/hdmi/enable
POST /api/vm/hdmi/disable
POST /api/vm/hdmi/timeout
```

Administrator configuration:

```text
GET  /api/vm/ssh
POST /api/vm/ssh/enable
POST /api/vm/ssh/disable
GET  /api/vm/mdns
POST /api/vm/mdns/enable
POST /api/vm/mdns/disable
GET  /api/vm/mouse-jiggler
POST /api/vm/mouse-jiggler
GET  /api/vm/swap
POST /api/vm/swap
GET  /api/vm/memory/limit
POST /api/vm/memory/limit
GET  /api/vm/oled
POST /api/vm/oled
GET  /api/vm/device/virtual
POST /api/vm/device/virtual
POST /api/vm/system/reboot
```

Updates, WOL, virtual media and HID:

```text
GET  /api/application/version
POST /api/application/update
GET  /api/application/preview
POST /api/application/preview
GET  /api/application/update-server
POST /api/application/update-server
POST /api/network/wol
GET  /api/storage/image
GET  /api/storage/image/mounted
POST /api/storage/image/mount
POST /api/hid/paste
```

New endpoints are added only after their request/response behavior is confirmed in upstream `sipeed/NanoKVM`.

## Authentication and permissions

NanoKVM's web frontend encrypts the password with the same CryptoJS-compatible AES format used by this integration before sending it to `/api/auth/login`. The returned `nano-kvm-token` session cookie is stored only in memory.

NanoKVM uses `401 Unauthorized` for a missing/expired session and `403 Forbidden` for insufficient account role. The integration reauthenticates only after `401`; a `403` is treated as a permission error.

## Security

The AES password wrapper is not a replacement for transport encryption. Use HTTPS when NanoKVM has a trustworthy TLS configuration. TLS verification is enabled by default and can be disabled only for the configured device.

Firmware/application updates, NanoKVM reboot, swap changes, virtual USB changes and virtual-media operations can temporarily interrupt KVM access. Administrator-only controls are not exposed to normal NanoKVM user accounts.

Passwords and session tokens are not exposed as Home Assistant entity attributes or diagnostics data. Diagnostics redact configured addresses, IP fields, usernames and mDNS identifiers. Do not expose the NanoKVM REST API directly to the Internet.

## Compatibility

NanoKVM REST endpoints are not a formally versioned public API and can change between releases. Optional functionality is capability-detected so older firmware remains usable when newer endpoints are absent.

## License

MIT
