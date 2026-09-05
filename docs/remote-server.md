# Remote Server sidepanel

NanoKVM REST 0.8.0 provides an administrator-only Home Assistant sidepanel named **Remote Server**.

## Dashboard

The dashboard lists all configured NanoKVM devices and keeps the 0.7.x management features: health score, online/offline and host-power state, quick actions, favorites, groups, tags, search, recently used devices, Wake-on-LAN profiles and persistent event history.

## Update Center

Update Center shows every configured NanoKVM with:

- current application version,
- latest version reported by NanoKVM,
- Stable or Preview channel,
- update availability,
- queued/updating/waiting/success/error runtime state,
- one-click online update,
- offline update package upload,
- update-related history from the persistent Remote Server event log.

### Staged updates

Select multiple NanoKVM devices and start a staged update. The integration updates exactly one device at a time. After requesting the update it polls the device API and verifies that NanoKVM returns online and reports the expected/new application version. Only then is the next device started. A failed recovery or update stops the batch. Cancellation is honored between devices, so an update already running on a device is not interrupted mid-install.

## Virtual Media Library

The library supports:

- search,
- sort by name/date/known size,
- ISO/IMG type,
- mounted state,
- mount as CD-ROM or USB disk,
- unmount,
- favorites,
- recent usage,
- multi-select delete with mounted-image protection,
- direct ISO upload through Home Assistant,
- ISO download from URL,
- optional SHA-256 verification,
- NanoKVM-native transfer progress and cancellation.

Upstream NanoKVM's storage list returns image paths only. Therefore size and added date are displayed when Home Assistant knows them (for example, an ISO uploaded through this panel). Existing files discovered only through `/api/storage/image` intentionally show unknown size/date rather than fabricated metadata.

### ISO upload

The browser uploads the ISO to Home Assistant, which forwards it to NanoKVM's native `/api/download/file` endpoint. NanoKVM validates that the uploaded file is an ISO-9660 image. The panel accepts an optional SHA-256 checksum and forwards it using the upstream `X-SHA256-Sum` header.

### ISO URL download

The URL is sent to NanoKVM's native `/api/download/image` background downloader. The panel polls `/api/download/image/status`, displays the upstream progress value, and can request cancellation through `/api/download/image/cancel`. URLs must use HTTP or HTTPS and end in a safe `.iso` filename. Credentials embedded in the URL are rejected.

## HID Toolbox

HID Toolbox provides:

- HID reset,
- keyboard/mouse reconnect (the upstream HID reset performs a USB PHY reset and reopens HID devices),
- text paste,
- keyboard LED state for NumLock, CapsLock and ScrollLock,
- Normal / HID-only mode selection.

Changing HID mode follows upstream NanoKVM behavior and reboots the NanoKVM device after applying the mode. The panel displays an explicit warning before this operation.

## Mobile UI

At widths below 900 px the desktop sidebar is replaced by a bottom navigation bar. Cards and control groups collapse to one column where appropriate, touch targets remain large, and Home Assistant safe-area insets are respected.

## Persistence

Device organization and WOL metadata live in `nanokvm_rest.remote_server` under Home Assistant `.storage`. Advanced ISO favorites/recent usage/known metadata live in `nanokvm_rest.remote_advanced`. Update runtime state is intentionally in-memory; durable update outcomes are written to the normal Remote Server event history.

## Security

The sidepanel requires a Home Assistant administrator. NanoKVM administrator-only operations additionally require an administrator account configured for that NanoKVM entry. Destructive actions are confirmed in the UI, mounted images cannot be bulk-deleted, uploaded filenames are restricted to safe `.iso` names, SHA-256 values are validated, and ISO URLs reject embedded credentials.
