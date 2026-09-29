# JetKVM LAN integration: verification record

Date: 2026-09-29. Application version: 0.12.0.
Repository: chmajster/Home-Assistant-nanokvm-rest-api.
Development branch: feat/jetkvm-lan-provider. Main was not changed by this work.

## Implemented

The existing Home Assistant integration and Flask/JavaScript Manager now share a provider registry for NanoKVM and JetKVM. The implementation includes real JetKVM HTTP authentication and private cookies, authenticated WebSocket signaling, browser WebRTC H.264 and JSON-RPC HID, scoped ATX capabilities, Wake-on-LAN, shared add/edit/test/delete/list/cards/details views, bounded reconnect, HTTP health monitoring, LAN address validation, per-device TLS controls, encrypted credentials and automatic legacy entry migration. Existing NanoKVM transport and device-specific management remain separate adapters. No production protocol fixture or iframe-based JetKVM frontend is used.

The final layout correction keeps actual console controls inside the fullscreen element and preserves native 100% video scaling. NanoKVM's OffscreenCanvas reconnect and explicit disconnect handling were also corrected and covered by regression tests.

## Source revisions and executed CI

- Main implementation: `10b7a15de131cbc7d61b84c0baa1c2eb60910011`.
- Fullscreen correction: `c8d0ee347f9c011c8914a85442d9f053ed3f75db`.
- Official JetKVM reference: `939422c8b00b423f6320db04df4adfbc6d2b3012` in jetkvm/kvm. Protocol and license notes are in [jetkvm.md](jetkvm.md).
- [Full integration CI 36517232113](https://github.com/chmajster/Home-Assistant-nanokvm-rest-api/actions/runs/36517232113): passed formatter, lint, 59 Python tests, 22 Node tests, real Chromium WebRTC acceptance, production amd64 Docker build and image smoke tests at revision `e4d7cdbab20a6f4526196741d3dd5c9fd74b1bf1`.
- [Fullscreen verification 36517569693](https://github.com/chmajster/Home-Assistant-nanokvm-rest-api/actions/runs/36517569693): passed formatter, lint, the same 59 Python/22 Node tests and browser acceptance including fullscreen controls and native scale before publishing the four-file correction as `c8d0ee3`.

The retained Integration Contract workflow reruns the full verification, including Docker, for subsequent pushes to this development branch and for pull requests. Temporary source-transfer and one-off verification workflows have been removed from the final tree. Their earlier runs are not production components.

## Tests

Backend fixtures use real local HTTP, WebSocket, HTTPS and WSS servers. Coverage includes IPv4/IPv6/DNS/ports, URL policy and SSRF protection, device identity, setup state, password/no-password, wrong password, timeout, connection refusal, expired sessions and reauthentication, cookies, TLS and certificate fingerprint pinning, provider/capability selection, legacy migration, encrypted storage, preservation of old credentials on failed edits and removal cleanup.

Frontend tests cover actual control envelopes, keyboard modifiers and Ctrl+Alt+Delete, absolute/relative mouse, wheel, capabilities, SDP/ICE order, bounded reconnect, explicit disconnect, mixed provider views and existing NanoKVM binary transport.

The browser acceptance test uses two real Chromium RTCPeerConnections, an animated test video encoded as H.264, the production Manager UI and production JetKVM HTTP/signaling client, plus an isolated test-only protocol peer and Home Assistant API fixture. It confirms receipt and decoding of video, keyboard and mouse messages, Ctrl+Alt+Delete, acknowledged ATX RPC, actual WOL HTTP request, expired-cookie reauthentication and reconnect, disconnect, fullscreen controls and native scale. Browser reports contain no UI errors. The test peer does not run physical JetKVM firmware.

## Migration and credentials

ConfigEntry version 1 migrates automatically to version 2 with provider nanokvm. Existing unique IDs and options remain. Plaintext passwords move to authenticated Fernet ciphertext; JetKVM uses the same new vault. This project has no SQL device database and requires no SQL migration.

Back up HA ConfigEntries together with `.storage/nanokvm_rest.credentials.key` and `.storage/nanokvm_rest.kvm_health`. Do not replace or publish the key. Older external backups containing legacy plaintext are not rewritten. New connection settings are tested before replacing working encrypted credentials.

## Remaining limitations and acceptance gates

Physical JetKVM and NanoKVM devices were not available. A complete running Home Assistant appliance, DHCP, real HDMI/USB, ATX wiring, real WOL target, appliance/device restarts, physical LAN loss and recovery, and actual hardware address/port changes were not exercised. Automated protocol and browser tests must not be represented as physical-device acceptance. The hardware checklist is in jetkvm.md.

The browser and Home Assistant both require LAN/VPN reachability to JetKVM. Video and control use direct encrypted WebRTC; there is no TURN/media relay or cloud-only remote access. One Manager JetKVM session per device is allowed. Unsupported audio, serial, virtual media and clipboard UI is hidden. ATX appears only after the device reports its ATX extension.

Discovery is optional, neighbour-table based and bounded to 32 candidates on port 80; it is not a complete subnet/mDNS scanner. Empty tables, custom ports or inaccessible identity endpoints may require manual add.

The per-device self-signed exception permits other invalid certificates too. Prefer proper trust or a separately verified SHA-256 fingerprint. HTTP/WS still exposes authentication on the local network. The existing trusted-administrator NanoKVM client's DNS/redirect policy was retained rather than silently changing its legacy behavior.

No deployment to the user's Home Assistant was performed. Pull-request creation was blocked by the tool; no pull request or merge is claimed. The changes are available on the development branch.
