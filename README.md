# NanoKVM REST for Home Assistant

Custom integration for Home Assistant that controls and monitors Sipeed NanoKVM through the local REST API. No MQTT and no SSH are required.

## Functions

- UI configuration via Home Assistant Config Flow
- HTTP or HTTPS connection to NanoKVM
- NanoKVM username/password authentication
- CryptoJS-compatible password encryption during login
- Session cookie handling (`nano-kvm-token`)
- Power state from `GET /api/vm/gpio`
- HDD LED state where supported
- Power button (800 ms)
- Reset button (800 ms)
- Force off (5 s power-button hold)
- Hostname, hardware version, application version, system image and IP sensors
- 30-second polling with `DataUpdateCoordinator`
- HACS-ready repository layout

## Installation with HACS

1. In HACS open **Integrations -> Custom repositories**.
2. Add `https://github.com/chmajster/homeassistant-nanokvm-rest-api` and select **Integration**.
3. Install **NanoKVM REST**.
4. Restart Home Assistant.
5. Open **Settings -> Devices & services -> Add integration -> NanoKVM REST**.
6. Enter the NanoKVM address, username and password.

For plain local HTTP you can enter only the IP address. If no scheme is given, the integration uses `http://`. For HTTPS keep TLS verification enabled unless you intentionally use a self-signed certificate.

## NanoKVM API used

- `POST /api/auth/login`
- `GET /api/vm/info`
- `GET /api/vm/hardware`
- `GET /api/vm/gpio`
- `GET /api/vm/hostname`
- `POST /api/vm/gpio`

The current NanoKVM server authenticates normal API calls using the `nano-kvm-token` session cookie. Login passwords are encoded in the same format as the NanoKVM web UI (`CryptoJS.AES.encrypt(..., "nanokvm-sipeed-2024")` followed by URL encoding).

## Security

Prefer HTTPS if NanoKVM credentials cross anything other than an isolated trusted LAN. The AES wrapper used by the NanoKVM login UI is not a replacement for TLS. Do not expose the NanoKVM REST API directly to the Internet.

## Development

Run HACS validation and Hassfest through the included GitHub Actions workflows.

## License

MIT
