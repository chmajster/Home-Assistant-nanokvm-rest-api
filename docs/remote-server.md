# Remote Server sidepanel

NanoKVM REST 0.6.1 registers an administrator-only Home Assistant sidepanel named **Remote Server** after the first NanoKVM config entry is loaded.

## Web interface

The sidepanel is a native Home Assistant custom panel and uses Home Assistant theme variables. It does not require a separate web server, ingress port, iframe add-on or additional credentials.

The interface contains four views:

- **Overview** — availability, host power, HDMI, hardware, application version and host/KVM controls.
- **Virtual Media** — available ISO/IMG files, mounted image, CD-ROM/USB-disk mode, mount, unmount and delete operations.
- **Maintenance** — HID Reset, NanoKVM reboot, address copy and offline application update.
- **Native UI** — direct link to the original NanoKVM interface and optional in-panel iframe embedding.

## Desktop and tablet

On wider screens the interface uses a persistent device sidebar, summary counters and responsive management cards. The selected NanoKVM remains visible while switching between management views.

## Mobile interface

On phones the panel switches to a dedicated mobile-first layout instead of compressing the desktop sidebar:

- NanoKVM devices are shown as horizontally scrollable cards with online/offline and host-power state.
- A sticky header keeps the selected device and refresh action visible.
- A fixed bottom navigation bar provides one-tap access to Overview, Virtual Media, Maintenance and Native UI.
- Power, reset, HID and maintenance controls use larger touch targets.
- Virtual Media actions collapse into responsive cards suitable for narrow displays.
- Safe-area padding is applied for phones with display cutouts and bottom home indicators.
- Very narrow displays around 390 px switch critical action grids to a single column.

## Multiple NanoKVM devices

Every configured NanoKVM config entry is shown in the desktop device sidebar or mobile device strip. The selected entry is remembered in browser local storage. The selected KVM is refreshed every 15 seconds and the complete list is periodically refreshed so availability and host-power indicators remain useful with multiple devices.

## Native UI embedding

Embedding is optional. Browsers block HTTP iframe content when Home Assistant itself is served over HTTPS. NanoKVM firmware or a reverse proxy can also block framing with CSP/X-Frame-Options. In those cases use **Open NanoKVM**, which opens the device web interface directly in a new tab.

## Access control

The sidepanel and its Home Assistant WebSocket/HTTP management endpoints require a Home Assistant administrator. NanoKVM operations that are administrator-only upstream additionally require the configured NanoKVM account to have the administrator role.

Destructive operations use confirmation prompts, and the backend retains its existing validation for force-off, virtual-media deletion and offline update packages.
