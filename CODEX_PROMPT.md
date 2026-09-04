# Codex prompt — NanoKVM REST integration for Home Assistant

Create and maintain a production-quality Home Assistant custom integration for Sipeed NanoKVM using the local NanoKVM REST API only. The repository must be directly installable as a HACS custom repository.

## Goal

Implement domain `nanokvm_rest` under `custom_components/nanokvm_rest`. Users must configure the device from Home Assistant UI without editing YAML. Support multiple NanoKVM devices.

## Current NanoKVM API facts

Use the current upstream Sipeed NanoKVM implementation as the source of truth. Verify endpoint behavior against `sipeed/NanoKVM` before changing the client.

Core endpoints currently used:

- `POST /api/auth/login`
- `GET /api/auth/account`
- `GET /api/vm/info`
- `GET /api/vm/hardware`
- `GET /api/vm/gpio`
- `GET /api/vm/hostname`
- `GET /api/vm/web-title`
- `POST /api/vm/gpio` with JSON `{"type": "power"|"reset", "duration": <milliseconds>}`

Confirmed optional/admin endpoints currently supported by the integration:

- `GET /api/vm/hdmi`
- `POST /api/vm/hdmi/reset`
- `POST /api/vm/hdmi/enable`
- `POST /api/vm/hdmi/disable`
- `POST /api/vm/hdmi/timeout`
- `GET /api/vm/ssh`
- `POST /api/vm/ssh/enable`
- `POST /api/vm/ssh/disable`
- `GET /api/vm/mdns`
- `POST /api/vm/mdns/enable`
- `POST /api/vm/mdns/disable`
- `GET /api/vm/mouse-jiggler`
- `POST /api/vm/mouse-jiggler`
- `GET /api/vm/swap`
- `POST /api/vm/system/reboot`

Authentication and authorization details:

- Login username/password is used.
- NanoKVM expects the password in the same encoding used by its web frontend: `CryptoJS.AES.encrypt(password, "nanokvm-sipeed-2024").toString()` and then `encodeURIComponent`.
- Reproduce the OpenSSL/CryptoJS salted AES-256-CBC format in Python. Do not send a plaintext password to `/api/auth/login`.
- Successful login sets HttpOnly cookie `nano-kvm-token`. Home Assistant's shared aiohttp cookie jar may not persist cookies, so explicitly capture the token from `Set-Cookie`/`response.cookies` and send it on API calls.
- If authentication is disabled on NanoKVM, the integration must still work when login returns success without a cookie.
- HTTP `401` means the session is missing/invalid/expired: re-login once and retry the original request once. Never create an infinite retry loop.
- HTTP `403` means the authenticated account lacks the required role. Do not reauthenticate on `403`; raise/handle a permission-specific error.
- Use `GET /api/auth/account` when available to determine whether admin-only entities should be exposed.

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

Implement and preserve at minimum:

1. `binary_sensor`
   - Power LED / target power state from `data.pwr` returned by `GET /api/vm/gpio`.
   - HDD LED/activity from `data.hdd` when reported by the API.
   - HDMI signal only on confirmed PCIe hardware with the HDMI endpoint available.

2. `button`
   - Power short press: `power`, 800 ms.
   - Reset: `reset`, 800 ms.
   - Force off: `power`, configurable default 5000 ms.
   - Reset HDMI on supported PCIe hardware.
   - Reboot NanoKVM only for administrator accounts. This reboots NanoKVM, not the attached host.

3. `switch`
   - HDMI capture enable/disable on PCIe hardware for administrator accounts.
   - SSH enable/disable for administrator accounts.
   - mDNS enable/disable for administrator accounts.
   - Mouse jiggler enable/disable while preserving the mode reported by NanoKVM.

4. `number`
   - HDMI idle timeout from 0 to 10080 minutes for supported PCIe/admin configurations.

5. `sensor`
   - Hostname.
   - Hardware version.
   - Application version.
   - System image version.
   - Active IP address(es).
   - mDNS address when reported.
   - Account role when reported.
   - Web title when supported.
   - Mouse-jiggler mode and swap size for supported administrator endpoints.

Treat newer feature endpoints as optional. A missing optional endpoint on older firmware must not make the entire config entry unavailable. Add feature-specific entities only when the corresponding upstream endpoint, authorization requirements, request schema and hardware support are confirmed. Do not invent endpoints.

## Error handling

Create explicit exceptions for connection, authentication, permission and API response errors. Handle timeouts, malformed JSON, non-zero NanoKVM `code`, 401, 403 and 5xx responses. User-facing config-flow errors must distinguish `cannot_connect`, `invalid_auth`, and invalid URL/TLS problems. Never swallow core polling errors silently. Optional unsupported endpoints may be skipped only when their absence is explicitly detected.

## Security

- Default TLS certificate verification to enabled.
- Permit local HTTP because NanoKVM commonly uses it, but document that NanoKVM's AES password wrapper is only transport obfuscation and not a TLS replacement.
- Never disable TLS verification globally.
- Never expose credentials, session tokens, account usernames, device addresses or IPs in diagnostics/logs where they should be redacted.
- Do not add SSH or shell execution as a fallback. The SSH switch may control NanoKVM's own confirmed REST endpoint only.
- Do not disable NanoKVM authentication as part of setup.
- Admin-only entities must not be created for a normal NanoKVM `user` account.

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
  diagnostics.py
  entity.py
  manifest.json
  number.py
  sensor.py
  switch.py
  translations/en.json
  translations/pl.json
hacs.json
README.md
LICENSE
.github/workflows/hacs.yaml
.github/workflows/hassfest.yaml
```

Add/maintain tests for:

- CryptoJS/OpenSSL-compatible password encryption.
- Login and cookie extraction.
- Authentication-disabled mode.
- `401 -> re-login -> one retry`.
- `403 -> permission error` without re-login.
- API error parsing.
- Config flow success, duplicate device, invalid auth and unreachable host.
- Coordinator update and optional-endpoint fallback.
- Power/reset/force-off calls with correct durations.
- Hardware-dependent HDD and HDMI entities.
- Admin-only entity exposure.
- SSH, mDNS, HDMI and mouse-jiggler control calls.

Use mocked aiohttp responses; tests must never require physical NanoKVM hardware.

## CI and quality gate

Run/require:

- HACS validation or the repository's private-repository-safe equivalent when HACS Action cannot read private content.
- Hassfest.
- Ruff or equivalent linting when configured.
- Pytest when tests are present.
- Python compile/import checks.

Do not merge changes while applicable validation fails.

## README

Document HACS custom repository installation, manual installation, UI configuration, supported entities, exact REST endpoints used, admin/PCIe capability requirements, troubleshooting, security notes, tested NanoKVM firmware/application versions when known, and compatibility limitations.

## Implementation rule

Before coding, inspect the current upstream `sipeed/NanoKVM` routes, middleware authorization rules, frontend calls and protobuf/request structures. If upstream API behavior conflicts with this prompt, update the implementation to match upstream and document the difference. Do not guess.
