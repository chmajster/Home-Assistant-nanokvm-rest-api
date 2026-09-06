# NanoKVM Manager

NanoKVM Manager is a persistent Home Assistant Ingress application for managing all NanoKVM devices configured through the NanoKVM REST integration.

## First start

1. Start **NanoKVM Manager**.
2. The app synchronizes the bundled integration into `/config/custom_components/nanokvm_rest` and then starts the Web UI on the internal Ingress port.
3. Restart Home Assistant after the first installation or after an integration update.
4. Configure **NanoKVM REST** under **Settings → Devices & services** if it is not configured yet.

## Show in sidebar

Because the app uses Home Assistant Ingress, the app page contains the native **Show in sidebar** switch. Enable it to add **NanoKVM Manager** to the Home Assistant sidebar. Disable it to remove only the shortcut; the app keeps running.

The integration's separate `Remote Server` sidebar panel can still be enabled or disabled independently in integration options.

## Web UI

The Ingress interface provides:

- fleet dashboard,
- device power controls,
- Operations and Health Score,
- alerts and acknowledgement,
- safe recovery and Maintenance Mode,
- application updates,
- virtual media management,
- HID reset/reconnect and text paste,
- shortcut to Live KVM / Remote Server.

## Security

The UI is administrator-only. The backend verifies the Home Assistant Ingress user ID, communicates with Home Assistant through `ws://supervisor/core/websocket`, and keeps `SUPERVISOR_TOKEN` inside the add-on container. The frontend receives neither the Supervisor token nor NanoKVM credentials.

## Health and watchdog

Supervisor checks `/health/ready` on the internal port `8099`. If Gunicorn stops responding, Home Assistant can mark/restart the app according to watchdog behavior.

## Data access

The app has write access to the Home Assistant configuration directory only to synchronize `/config/custom_components/nanokvm_rest`. It does not edit `configuration.yaml`, `secrets.yaml`, or unrelated custom integrations.
