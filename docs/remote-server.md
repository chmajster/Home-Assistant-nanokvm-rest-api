# Remote Server sidepanel

NanoKVM REST 0.6.0 registers an administrator-only Home Assistant sidepanel named **Remote Server** after the first NanoKVM config entry is loaded.

## Web interface

The sidepanel is a native Home Assistant custom panel and uses Home Assistant theme variables. It does not require a separate web server, ingress port, iframe add-on or additional credentials.

The interface contains four views:

- **Overview** — availability, host power, HDMI, hardware, application version, address and host/KVM controls.
- **Virtual Media** — available ISO/IMG files, mounted image, CD-ROM/USB-disk mode, mount, unmount and delete operations.
- **Maintenance** — HID Reset, NanoKVM reboot, address copy and offline application update.
- **Native UI** — direct link to the original NanoKVM interface and optional in-panel iframe embedding.

## Multiple NanoKVM devices

Every configured NanoKVM config entry is shown in the left device rail. The selected entry is remembered in browser local storage. The selected KVM is refreshed every 15 seconds and the complete list is periodically refreshed so availability and host-power indicators remain useful with multiple devices.

## Native UI embedding

Embedding is optional. Browsers block HTTP iframe content when Home Assistant itself is served over HTTPS. NanoKVM firmware or a reverse proxy can also block framing with CSP/X-Frame-Options. In those cases use **Open NanoKVM**, which opens the device web interface directly in a new tab.

## Access control

The sidepanel and its Home Assistant WebSocket/HTTP management endpoints require a Home Assistant administrator. NanoKVM operations that are administrator-only upstream additionally require the configured NanoKVM account to have the administrator role.

Destructive operations use confirmation prompts, and the backend retains its existing validation for force-off, virtual-media deletion and offline update packages.
