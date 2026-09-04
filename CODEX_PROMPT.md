# Codex prompt — NanoKVM REST integration for Home Assistant

Create and maintain a production-quality Home Assistant custom integration for Sipeed NanoKVM using the local NanoKVM REST API only. The repository must be directly installable as a HACS custom repository.

## Goal

Implement domain `nanokvm_rest` under `custom_components/nanokvm_rest`. Users must configure the device from Home Assistant UI without editing YAML. Support multiple NanoKVM devices.

## Current NanoKVM API facts

Use the current upstream Sipeed NanoKVM implementation as the source of truth. Verify endpoint behavior against `sipeed/NanoKVM` before changing the client. At minimum support:

- `POST /api/auth/login`
- `GET /api/auth/account`
- `GET /api/vm/info`
- `GET /api/vm/hardware`
- `GET /api/vm/gpio`
- `GET /api/vm/hostname`
- `POST /api/vm/gpio` with JSON `{"type": "power"|"reset", "duration": <milliseconds>}`

Authentication details:

- Login username/password is used.
- NanoKVM expects the password in the same encoding used by its web frontend: `CryptoJS.AES.encrypt(password, "nanokvm-sipeed-2024").toString()` and then `encodeURIComponent`.
- Reproduce the OpenSSL/CryptoJS salted AES-256-CBC format in Python. Do not send a plaintext password to `/api/auth/login`.
- Successful login sets HttpOnly cookie `nano-kvm-token`. Home Assistant's shared aiohttp cookie jar may not persist cookies, so explicitly capture the token from `Set-Cookie`/`response.cookies` and send it on API calls.
- If authentication is disabled on NanoKVM, the integration must still work when login returns success without a cookie.
- On HTTP 401/403, re-login once and retry the original request once. Never create an infinite retry loop.

## Home Assistant requirements

Follow current Home Assistant developer documentation, not old examples.

- Use Config Flow and Config Entries.
- `manifest.json` must include a SemVer `version`, `config_flow: true`, `integration_type: device`, and `iot_class: local_polling`.
- Use `DataUpdateCoordinator`; poll no faster than every 30 seconds by default.
- Use the Home Assistant shared aiohttp session.
- Store connection data in the Config Entry; never log passwords or session tokens.
- Use the NanoKVM `deviceKey` from `/api/vm/info` as unique ID when available.
- Add a reauthentication flow for changed/expired credentials.
- Add a reconfigure/options flow for URL/TLS verification and polling interval.
- Add Polish and English translations in `custom_components/nanokvm_rest/translations/`. For custom integrations do not rely on Core-only translation build behavior.
- Support multiple configured NanoKVM devices.
- Use `DeviceInfo` with manufacturer `Sipeed`, model/hardware version, software/application version, and configuration URL.

## Entities

Implement at minimum:

1. `binary_sensor`
   - Power LED / target power state from `data.pwr` returned by `GET /api/vm/gpio`.
   - HDD LED/activity from `data.hdd` when supported by the hardware. Do not expose a misleading HDD entity on hardware where it is unsupported if the hardware version can be determined.

2. `button`
   - Power short press: `power`, 800 ms.
   - Reset: `reset`, 800 ms.
   - Force off: `power`, configurable default 5000 ms.
   - Protect destructive actions with appropriate HA semantics/documentation.

3. `sensor`
   - Hostname.
   - Hardware version.
   - Application version.
   - System image version.
   - Active IP address(es), using diagnostics category where appropriate.

Add feature-specific entities only when the corresponding upstream endpoint and hardware support are confirmed. Do not invent endpoints.

## Error handling

Create explicit exceptions for connection, authentication and API response errors. Handle timeouts, malformed JSON, non-zero NanoKVM `code`, 401/403, and 5xx responses. User-facing config-flow errors must distinguish `cannot_connect`, `invalid_auth`, and invalid URL/TLS problems. Never swallow errors silently.

## Security

- Default TLS certificate verification to enabled.
- Permit local HTTP because NanoKVM commonly uses it, but document that NanoKVM's AES password wrapper is only transport obfuscation and not a TLS replacement.
- Never disable TLS verification globally.
- Never expose credentials in entity attributes, diagnostics, logs, exceptions, issue templates, or test fixtures.
- Do not add SSH or shell execution as a fallback.
- Do not disable NanoKVM authentication as part of setup.

## Repository / HACS

Repository structure must include:

```text
custom_components/nanokvm_rest/
  __init__.py
  api.py
  binary_sensor.py
  button.py
  config_flow.py
  const.py
  coordinator.py
  entity.py
  manifest.json
  sensor.py
  translations/en.json
  translations/pl.json
hacs.json
README.md
LICENSE
.github/workflows/hacs.yaml
.github/workflows/hassfest.yaml
tests/
```

Add tests for:

- CryptoJS/OpenSSL-compatible password encryption.
- Login and cookie extraction.
- Authentication-disabled mode.
- 401 -> re-login -> one retry.
- API error parsing.
- Config flow success, duplicate device, invalid auth and unreachable host.
- Coordinator update.
- Power/reset/force-off calls with correct durations.
- Hardware-dependent HDD entity.

Use mocked aiohttp responses; tests must never require physical NanoKVM hardware.

## CI and quality gate

Run/require:

- HACS validation.
- Hassfest.
- Ruff or equivalent linting.
- Pytest.
- Python compile/import checks.

Do not merge changes while tests or validation fail.

## README

Document HACS custom repository installation, manual installation, UI configuration, supported entities, exact REST endpoints used, troubleshooting, security notes, tested NanoKVM firmware/application versions, and compatibility limitations.

## Implementation rule

Before coding, inspect the current upstream `sipeed/NanoKVM` routes and protobuf/request structures. If upstream API behavior conflicts with this prompt, update the implementation to match upstream and document the difference. Do not guess.
