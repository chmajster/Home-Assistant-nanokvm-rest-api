# NanoKVM Manager Home Assistant app

NanoKVM Manager is a persistent Home Assistant app/add-on with its own Web UI delivered through Home Assistant Ingress. It also keeps the bundled `NanoKVM REST` custom integration synchronized in `/config/custom_components/nanokvm_rest` (mounted inside the app as `/homeassistant`).

## Web UI and sidebar

The app uses Home Assistant Ingress. After installation Home Assistant shows the native **Show in sidebar** switch on the app page. Enable it to add **NanoKVM Manager** to the Home Assistant sidebar.

The Web UI includes:

- fleet dashboard and device status,
- host Power / Reset / HID Reset quick actions,
- Operations Center and Health Score,
- Alert Center and acknowledgements,
- Recovery Center and Maintenance Mode,
- Update Center with Stable/Preview channels,
- Virtual Media library and URL ISO download,
- HID Toolbox and text paste,
- direct jump to the existing Remote Server / Live KVM panel.

The add-on does not store a second copy of NanoKVM credentials. Its backend talks to the existing NanoKVM REST integration through the Home Assistant WebSocket API using `SUPERVISOR_TOKEN`. The browser never receives the Supervisor token.

## Installation

1. Add `https://github.com/chmajster/homeassistant-nanokvm-rest-api` as a custom repository in the Home Assistant app/add-on store.
2. Install **NanoKVM Manager**.
3. Start the app. It now stays running because it serves the Ingress Web UI.
4. Restart Home Assistant after the first install/update so the synchronized custom integration is reloaded.
5. Go to **Settings → Devices & services → Add integration** and select **NanoKVM REST** if it has not been configured yet.
6. Open the app page and enable **Show in sidebar** if you want the Ingress manager in the main navigation.

## Security

- Ingress access is restricted to Home Assistant administrators (`panel_admin: true`).
- The backend also validates the Ingress `X-Remote-User-Id` against the Home Assistant administrator group.
- `SUPERVISOR_TOKEN` stays server-side.
- Browser actions are limited to an allowlist of NanoKVM REST WebSocket commands.
- Mutating requests require the app-specific request header and JSON content type.
- No external port is exposed by default.

## Existing Remote Server sidebar panel

The custom integration still provides its own **Remote Server** panel, including Live KVM. It is independent from the app Ingress panel. If you only want one sidebar entry, disable `Show Remote Server in Home Assistant sidebar` in the NanoKVM REST integration options and use the app's **Show in sidebar** switch instead.
