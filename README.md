# NanoKVM REST for Home Assistant

Custom Home Assistant integration for Sipeed NanoKVM using the local NanoKVM REST API. No MQTT or SSH fallback is required.

## Features

- UI setup through Home Assistant Config Flow.
- Multiple NanoKVM devices.
- HTTP and HTTPS connections with optional TLS certificate verification.
- NanoKVM session authentication using the same CryptoJS/OpenSSL-compatible password format as the NanoKVM web UI.
- Automatic re-login after an expired session.
- Reauthentication and reconfiguration from Home Assistant.
- Configurable polling interval and force-off press duration.
- Power and HDD state monitoring.
- Power, reset and force-off actions.
- Diagnostic sensors for hostname, hardware version, application version, system image and IP address.
- Downloadable Home Assistant diagnostics with credentials redacted.
- Polish and English translations.

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

## Entities

### Binary sensors

- Power state / power LED.
- HDD activity only when the NanoKVM API reports an HDD field for the current hardware.

### Buttons

- Power: 800 ms power-button press.
- Reset: 800 ms reset-button press.
- Force off: long power-button press using the configured duration.

### Diagnostic sensors

- Hostname.
- Hardware version.
- NanoKVM application version.
- System image version.
- Active IP address.

## REST API endpoints used

```text
POST /api/auth/login
GET  /api/vm/info
GET  /api/vm/hardware
GET  /api/vm/gpio
GET  /api/vm/hostname
POST /api/vm/gpio
```

The implementation follows the current upstream `sipeed/NanoKVM` routes and frontend authentication behavior. New endpoints should only be added after their request and response structures are confirmed upstream.

## Authentication and security

NanoKVM's web frontend encrypts the password with CryptoJS-compatible AES before sending it to `/api/auth/login`. This integration reproduces that format and stores the returned `nano-kvm-token` session cookie only in memory.

The AES wrapper is not a replacement for transport encryption. Use HTTPS when the NanoKVM installation provides a trustworthy TLS setup. TLS verification is enabled by default and can be disabled only for the configured NanoKVM connection.

Passwords and session tokens are not exposed as Home Assistant entity attributes or diagnostics data. Do not expose the NanoKVM REST API directly to the Internet.

## Troubleshooting

If setup reports **Unable to connect**, verify the NanoKVM address, network reachability and TLS settings.

If setup reports **Invalid username or password**, verify the NanoKVM account and run reauthentication from Home Assistant.

For a self-signed NanoKVM certificate, either install a trusted certificate or explicitly disable certificate verification for that device.

## Compatibility

NanoKVM REST endpoints are not a formally versioned public API and can change between NanoKVM releases. The integration therefore validates behavior against upstream NanoKVM and avoids undocumented endpoints.

## License

MIT
