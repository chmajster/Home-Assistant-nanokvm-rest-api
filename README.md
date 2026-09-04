# NanoKVM REST for Home Assistant

Custom Home Assistant integration for Sipeed NanoKVM using the local NanoKVM REST API. No MQTT or SSH fallback is required.

## Features

- UI setup through Home Assistant Config Flow.
- Multiple NanoKVM devices.
- HTTP and HTTPS connections with optional TLS certificate verification.
- NanoKVM session authentication using the same CryptoJS/OpenSSL-compatible password format as the NanoKVM web UI.
- Automatic re-login after an expired session.
- Correct distinction between an expired session (`401`) and insufficient account permissions (`403`).
- Reauthentication and reconfiguration from Home Assistant.
- Configurable polling interval and force-off press duration.
- Power and HDD state monitoring.
- Power, reset and force-off actions for the attached computer.
- Automatic NanoKVM account-role and hardware capability detection.
- PCIe NanoKVM HDMI monitoring and controls.
- Admin-only controls for SSH, mDNS, mouse jiggler and NanoKVM reboot.
- Diagnostic sensors for hostname, hardware, application, system image, IP, mDNS, account role, web title, mouse-jiggler mode and swap size when available.
- Downloadable Home Assistant diagnostics with credentials and identifying network/account fields redacted.
- Graceful handling of optional endpoints missing on older NanoKVM firmware.
- Polish and English setup translations.

## Requirements

- Home Assistant 2026.8.0 or newer.
- NanoKVM reachable from the Home Assistant instance.
- NanoKVM credentials when authentication is enabled.

## Installation with HACS

1. Open HACS in Home Assistant.
2. Add `https://github.com/chmajster/homeassistant-nanokvm-rest-api` as a custom repository of type **Integration**.
3. Install **NanoKVM REST**.
4. Restart Home Assistant.
5. Go to **Settings → Devices & services → Add integration** and select **NanoKVM REST**.

## Manual installation

Copy:

```text
custom_components/nanokvm_rest
```

into:

```text
/config/custom_components/nanokvm_rest
```

Restart Home Assistant and add the integration from **Settings → Devices & services**.

## Configuration

The setup form accepts:

- NanoKVM address, for example `http://192.168.1.50` or `https://nanokvm.local`.
- Username.
- Password.
- TLS certificate verification.

If no URL scheme is provided, the integration uses `http://`.

The NanoKVM `deviceKey`, when available, is used as the Home Assistant config-entry unique ID to prevent the same physical device from being configured twice.

## Options

The integration exposes an options flow for:

- Polling interval: 30–3600 seconds.
- Force-off power-button duration: 1000–10000 ms.

Connection address, username, password and TLS verification can be changed through Home Assistant reconfigure/reauthentication flows.

## Capability detection

The integration reads `/api/auth/account` when supported. Admin-only entities are created only when NanoKVM reports the account role as `admin`.

Older firmware that does not expose optional endpoints remains usable. Missing optional endpoints are ignored instead of making the whole config entry unavailable.

PCIe-specific HDMI entities are created only when `/api/vm/hardware` reports `PCIE` and the HDMI endpoint is available.

## Entities

### Binary sensors

- Power state / power LED.
- HDD activity when the API exposes the HDD field.
- HDMI signal presence on supported PCIe hardware.

### Buttons

- Power: 800 ms power-button press.
- Reset: 800 ms reset-button press.
- Force off: long power-button press using the configured duration.
- Reset HDMI: PCIe hardware only.
- Reboot NanoKVM: administrator account only. This reboots the NanoKVM device, not the attached computer.

### Switches

Administrator-only controls are exposed only when their corresponding API endpoint is available:

- HDMI capture enable/disable on PCIe hardware.
- SSH service.
- mDNS advertising.
- Mouse jiggler while preserving the NanoKVM-configured jiggler mode.

### Number controls

- HDMI idle timeout: 0–10080 minutes, PCIe hardware and administrator account only.

### Diagnostic sensors

- Hostname.
- Hardware version.
- NanoKVM application version.
- System image version.
- Active IP address.
- mDNS address.
- NanoKVM account role when available.
- Web interface title when available.
- Mouse-jiggler mode for administrator accounts when available.
- Swap size for administrator accounts when available.

## REST API endpoints used

Core:

```text
POST /api/auth/login
GET  /api/auth/account
GET  /api/vm/info
GET  /api/vm/hardware
GET  /api/vm/gpio
GET  /api/vm/hostname
GET  /api/vm/web-title
POST /api/vm/gpio
```

PCIe HDMI:

```text
GET  /api/vm/hdmi
POST /api/vm/hdmi/reset
POST /api/vm/hdmi/enable
POST /api/vm/hdmi/disable
POST /api/vm/hdmi/timeout
```

Administrator controls and diagnostics:

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
POST /api/vm/system/reboot
```

The implementation follows the current upstream `sipeed/NanoKVM` routes and frontend authentication behavior. New endpoints should only be added after their request and response structures are confirmed upstream.

## Authentication and permissions

NanoKVM's web frontend encrypts the password with CryptoJS-compatible AES before sending it to `/api/auth/login`. This integration reproduces that format and stores the returned `nano-kvm-token` session cookie only in memory.

NanoKVM uses `401 Unauthorized` for a missing or expired session and `403 Forbidden` when an authenticated account does not have the required role. The integration retries authentication only after `401`; a `403` does not trigger a false reauthentication loop.

## Security

The AES password wrapper is not a replacement for transport encryption. Use HTTPS when the NanoKVM installation provides a trustworthy TLS setup. TLS verification is enabled by default and can be disabled only for the configured NanoKVM connection.

Enabling SSH increases the management surface of NanoKVM. Expose SSH only on trusted networks and disable it when it is not required.

Passwords and session tokens are not exposed as Home Assistant entity attributes or diagnostics data. Diagnostics also redact configured addresses, IP fields, account usernames and mDNS identifiers. Do not expose the NanoKVM REST API directly to the Internet.

## Troubleshooting

If setup reports **Unable to connect**, verify the NanoKVM address, network reachability and TLS settings.

If setup reports **Invalid username or password**, verify the NanoKVM account and run reauthentication from Home Assistant.

If administrator switches or the NanoKVM reboot button are absent, check the account role reported by NanoKVM. A normal `user` account can use the non-admin monitoring and GPIO controls but cannot access admin routes.

If HDMI entities are absent, verify that NanoKVM reports PCIe hardware and that the firmware exposes `/api/vm/hdmi`.

For a self-signed NanoKVM certificate, either install a trusted certificate or explicitly disable certificate verification for that device.

## Compatibility

NanoKVM REST endpoints are not a formally versioned public API and can change between NanoKVM releases. The integration therefore validates behavior against upstream NanoKVM and treats newer optional functionality as capability-detected rather than mandatory.

## License

MIT
