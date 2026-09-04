# NanoKVM REST

This app installs the NanoKVM REST custom integration into Home Assistant.

## How to use

1. Start this app once.
2. Wait until the log says the integration was installed successfully.
3. Restart Home Assistant.
4. Open **Settings → Devices & services → Add integration**.
5. Select **NanoKVM REST** and configure your NanoKVM address and credentials.

The app stops after installation by design.

## Integration features in 0.4.0

The bundled integration includes NanoKVM application updates, writable hostname/web title, OLED/swap/memory controls, virtual USB device switches, device actions and device triggers in addition to the existing power/HDMI/SSH/mDNS monitoring and controls.

Administrator-only NanoKVM endpoints are exposed only when the configured account reports the `admin` role.

## Updates

When a new app version is installed, start the app once to copy the updated integration files, then restart Home Assistant.

## Data access

This installer receives write access to the Home Assistant configuration directory only so it can manage `/config/custom_components/nanokvm_rest`. It does not read or modify `configuration.yaml`, `secrets.yaml`, or unrelated custom integrations.
