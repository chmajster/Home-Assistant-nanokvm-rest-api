# Remote Server sidepanel

NanoKVM REST 0.7.0 registers an administrator-only Home Assistant sidepanel named **Remote Server** after the first NanoKVM config entry is loaded.

## Dashboard

The default view is an all-device dashboard designed for both desktop and mobile. It shows every configured NanoKVM with:

- availability and host-power state;
- HDMI state when supported;
- hardware and NanoKVM application version;
- calculated Health Score;
- favorite, group and tags;
- quick actions for power-on, host reset, HID reset and opening the native UI.

The dashboard can be filtered by free-text search, group, tag and favorites. Search matches the config-entry title, NanoKVM hostname, address/URL, hardware, group and tags.

## Health Score

Health Score is calculated at runtime and is not persisted as a separate sensor. An unavailable KVM is Critical. A PCIe NanoKVM with a powered-on host but no HDMI signal lowers the score, as do missing hardware/version details. Host power being off by itself is not treated as a failure because it can be intentional.

## Favorites, groups, tags and recently used devices

Favorite state, group names, tags and the last-used timestamp are stored in Home Assistant `.storage` under the integration's Remote Server data. They survive Home Assistant restarts and are not stored in Git or exposed as normal entity state.

On mobile the dashboard includes horizontally scrollable **Favorites** and **Recently used** sections. Device metadata can be edited from the dashboard or device overview.

## Event history

Remote Server stores up to 500 recent events. The history includes explicit management operations and state transitions detected while the panel is polling, including:

- KVM online/offline;
- host power on/off;
- HDMI signal gained/lost;
- host power/reset/force-off actions;
- HID reset and NanoKVM reboot;
- Virtual Media mount/unmount/delete/mode changes;
- offline update;
- Wake-on-LAN;
- group/tag/favorite changes;
- Wake-on-LAN profile changes.

Management events include the Home Assistant user that initiated the operation and whether it succeeded or failed. Event history is local to Home Assistant `.storage`.

## Wake-on-LAN profiles

Each NanoKVM can have multiple persistent Wake-on-LAN profiles. A profile contains a display name and MAC address. Profiles can be created, edited, deleted and executed from **Maintenance**. The integration uses NanoKVM's existing Wake-on-LAN REST action, which accepts a MAC address.

## Device views

The sidepanel retains the device-focused views:

- **KVM** — operational status, Health Score, host controls, HID controls, metadata and per-device event history.
- **Media** — available ISO/IMG files, mounted image, CD-ROM/USB-disk mode, mount, unmount and delete operations.
- **Maintenance** — Wake-on-LAN profiles, HID Reset, NanoKVM reboot, address copy, offline application update and event history.
- **UI** — direct link to the original NanoKVM interface and optional in-panel iframe embedding.

## Mobile interface

At widths up to 760 px the desktop rail is replaced by a touch-oriented layout:

- sticky header;
- horizontally scrollable NanoKVM selector;
- Favorites and Recently used strips on Dashboard;
- fixed bottom navigation for Dashboard, KVM, Media, Maintenance and UI;
- large touch targets for management actions;
- safe-area spacing for phones with a home indicator/display cutout;
- single-column action layouts on very narrow devices.

## Native UI embedding

Embedding is optional. Browsers block HTTP iframe content when Home Assistant itself is served over HTTPS. NanoKVM firmware or a reverse proxy can also block framing with CSP/X-Frame-Options. In those cases use **Open UI**, which opens the device interface directly in a new tab.

## Access control

The sidepanel and all Home Assistant WebSocket/HTTP management endpoints require a Home Assistant administrator. NanoKVM operations that are administrator-only upstream additionally require the configured NanoKVM account to have the administrator role.

Destructive operations retain backend validation for force-off, virtual-media deletion and offline updates. The UI uses confirmation dialogs for reset, force-off, NanoKVM reboot, image deletion and offline update.

## Installation parity

The Home Assistant app/add-on bundle contains the same integration tree as `custom_components/nanokvm_rest`. This keeps HACS/manual installations and app-based installations on the same feature set, including the Remote Server backend, persistent storage helpers and web frontend.
