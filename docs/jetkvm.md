# JetKVM LAN support in NanoKVM Manager

## Scope and topology

Supported providers are `nanokvm` and `jetkvm`. Manager uses the existing Home Assistant integration, ConfigEntries, administrator authorization and Ingress app. No second backend or iframe-based JetKVM UI is introduced. Existing NanoKVM entities, update/recovery/media functions, native H.264/HID transport and the legacy Remote Server sidebar remain NanoKVM-specific. JetKVM is managed in the shared Manager Devices/Live KVM views; it does not create fictitious NanoKVM entities.

```
Browser -- HA-authorized one-use WebSocket ticket --> Home Assistant
                                                      |
                                            JetKVM HTTP auth + signaling WS
                                                      |
Browser <---- direct encrypted WebRTC H.264 + rpc ---- JetKVM LAN
```

The browser and Home Assistant both need LAN/VPN reachability to JetKVM. No public STUN/TURN service, cloud login or media relay is configured. Reaching Manager via Home Assistant Cloud alone does not make a remote browser able to reach JetKVM media. Use a routed VPN for that topology. Unsupported audio, serial, virtual media and clipboard controls are hidden rather than returning fake success.

## Add, edit and remove

Connect JetKVM to Ethernet, complete onboarding in its own local interface and read its IP from the screen/router. In **Devices → Add**, select **JetKVM**, enter a name and address, optionally the local password, click **Test Connection**, then **Save** and **Live KVM**.

Accepted examples:

```
192.168.1.50
jetkvm.local
192.168.50.12:8080
https://jetkvm.local:8443
fd00::50
[fd00::50]:8080
[fe80::50%eth0]:8080
```

Bare IPv6 is always an address, never a host/port split: use brackets for an explicit IPv6 port. The scope in a link-local address names an interface on Home Assistant, not the browser. DNS/mDNS must work on the HA host. HTTP/80 is the default; HTTPS selects 443 unless explicitly overridden. URL credentials, paths, query strings and fragments are rejected.

Details → Edit preserves an omitted/blank password; **Remove saved password** explicitly clears it. Connection changes are tested and the physical `deviceId` must match before data is replaced. Name-only changes may be saved offline. The credential key is written before encrypted entry data; failed validation/encryption leaves the previous ConfigEntry intact. Delete uses HA's actual entry removal and closes sessions/revokes pending tickets. Save may require the normal HA entry reload; a failed reload is not evidence of a successful physical KVM session.

## Security and migration

Version-1 entries migrate automatically to version 2 with `provider=nanokvm`. Existing unique IDs, options and entities are retained. Plaintext passwords are replaced with authenticated Fernet ciphertext under `credential_encrypted`. JetKVM uses the same vault. There is no SQL migration or separate device database.

**Back up all three together:** HA ConfigEntries, `.storage/nanokvm_rest.credentials.key` and `.storage/nanokvm_rest.kvm_health`. The key is local, mode `0600`, checked for ownership and no symlink following. Missing/corrupt keys do not silently regenerate when encrypted records exist. Restore the matching key, not a new one. An administrator/root who can read both the key and database can decrypt passwords; this protects storage, not a compromised HA host. Older backups outside HA are not rewritten and may contain legacy plaintext passwords. Do not publish ConfigEntries, backups or the key.

Passwords remain only in the input request and backend client memory; JetKVM cookies are never returned to the browser, included in URLs or logged. One-use Manager console tickets are sent in the WebSocket subprotocol header, expire in 30 seconds, are limited to 128 outstanding tickets and re-check the HA administrator. Avoid logging `Sec-WebSocket-Protocol` headers at a reverse proxy. Disconnect/delete revokes unused tickets. No arbitrary HTTP method/path proxy is exposed.

JetKVM LAN policy allows RFC1918, IPv6 ULA and IPv6 link-local by default. An administrator may explicitly add narrowly scoped routed LAN CIDRs. Loopback, unspecified, multicast, cloud metadata IPv4 ranges and known IPv6 metadata/tunnel/mapped destinations remain blocked. All resolved DNS answers are validated and pinned for each actual connection with no DNS cache, including ws/wss. Redirects and environment proxy settings are disabled. The implementation does not replace the pre-existing trusted-administrator NanoKVM client's DNS/redirect policy; its legacy connectivity behavior is intentionally retained.

TLS verification is on by default. The **self-signed** checkbox disables verification **only for that device**; this permits other invalid certificates too and should only be used on a trusted network. Prefer a correctly trusted certificate or a verified SHA-256 certificate fingerprint. Fingerprint pinning applies to JetKVM HTTPS and WSS. HTTP and WS expose device authentication on the LAN; storage encryption is not transport encryption. Do not expose the add-on or device web interface directly to the Internet.

## Verified upstream contract

Protocol inspected in the official repository at commit:

`939422c8b00b423f6320db04df4adfbc6d2b3012`

- [Official local access documentation](https://jetkvm.com/docs/networking/local-access)
- [web.go: routing, auth, status, WebSocket envelopes](https://github.com/jetkvm/kvm/blob/939422c8b00b423f6320db04df4adfbc6d2b3012/web.go)
- [webrtc.go: peer connection and data channels](https://github.com/jetkvm/kvm/blob/939422c8b00b423f6320db04df4adfbc6d2b3012/webrtc.go)
- [jsonrpc.go: actual control methods](https://github.com/jetkvm/kvm/blob/939422c8b00b423f6320db04df4adfbc6d2b3012/jsonrpc.go)
- [Upstream license](https://github.com/jetkvm/kvm/blob/939422c8b00b423f6320db04df4adfbc6d2b3012/LICENSE)

Public `GET /device/status` must return a boolean `isSetup`. A configured device is further identified using protected `GET /device` (`deviceId`, `authMode`, optionally `loopbackOnly`). No-password mode does not call login. Password mode calls `POST /auth/login-local` with JSON `password` and retains `authToken` in the private backend client. A 401 triggers at most one single-flight login/retry. Invalid credentials and HTTP 429 are backoff-limited. HTTP 403 is not treated as session expiration. The client does not log out the device globally, because that can invalidate other upstream sessions.

Signaling uses `GET /webrtc/signaling/client`. The browser offer envelope is `{type:"offer",data:{sd:base64(JSON(RTCSessionDescriptionInit))}}`; the answer uses `{type:"answer",data:base64(JSON(...))}`. ICE uses `new-ice-candidate` with an `RTCIceCandidateInit`. ICE arriving early is queued. Device metadata carries the firmware version. JSON envelopes, sizes and allowed message types are checked; SDP/ICE payloads are not logged.

A real recv-only H.264 video track and ordered reliable data channel `rpc` are negotiated. USB keyboard reports use `keyboardReport {modifier,keys}`, absolute mouse uses `absMouseReport {x,y,buttons}`, relative mouse uses `relMouseReport {dx,dy,buttons}`, and scrolling uses `wheelReport {wheelY,wheelX}`. Keyboard reports are serialized and acknowledged; leaving focus clears input. Absolute coordinates account for letterboxing. Relative mode requires Pointer Lock; full screen is supported where the browser permits it.

ATX buttons are revealed only after `getActiveExtension` returns `atx-power`; `setATXPowerAction` accepts `power-short`, `power-long` and `reset`. They are not offered as fictitious standalone HTTP controls. Wake-on-LAN calls authenticated `POST /device/send-wol/<MAC>`; its successful plain-text response is intentionally supported.

The upstream repository is GPL-2.0; this project's MIT implementation is independently written against its observed protocol. No upstream UI/modules are copied or bundled. Compatibility with other firmware versions is not claimed without testing; this interface is not a formally versioned API.

## Lifecycle, monitoring and diagnostics

JetKVM polls lightweight status/identity requests every 20 seconds by default (configurable 10–30). It does not open WebRTC for monitoring. Four global poll slots, a 12-second whole-probe deadline, connection/read timeouts, an 8-second WS handshake and 30-second WebRTC negotiation deadline bound resources. Last-seen, HTTP latency, safe errors and connection state are persisted; cached data never establishes current availability on startup. Health writes are coalesced. NanoKVM keeps its existing monitoring interval and measured operation-probe latency.

Live states are CONNECTING, CONNECTED, RECONNECTING, DISCONNECTED and ERROR. Retry delays are 1, 2, 5 and 10 seconds, then explicit retry is needed. The attempt budget resets only after a stable session. Authentication, certificate and other non-retryable failures stop automatic retries. Each retry obtains a fresh Manager ticket, tests/authenticates JetKVM and creates new signaling and WebRTC transports. Explicit disconnect must not reconnect. Only one Manager JetKVM session per device is allowed; an external native JetKVM browser session is outside this lock.

Resolution and FPS come from the received video/RTP stats; latency in Live KVM is the selected ICE pair RTT, not fabricated end-to-end display latency. Unsupported/unreported details are omitted. Network, DNS, refused connection, setup, authentication and TLS errors have user-facing explanations and expandable sanitized technical details. Firmware appears only after it is actually received in signaling metadata; no made-up uptime/MAC/model is shown.

## Discovery

**Scan network** is administrator-only and opt-in. It reads `/proc/net/arp` and, if available, `ip -j neigh show` with fixed arguments and a deadline. At most 32 safe neighbour addresses and port 80 are probed, with four concurrent probes and API/JetKVM identity checks. It does not scan every subnet or all ports, send passwords, invent an mDNS service, or label an arbitrary open HTTP port as KVM. A cold table, blocked multicast, different HA interfaces, custom ports or protected NanoKVM identity endpoints can mean a device is not found. Manual add remains available.

## Validation and physical acceptance

Run `tools/verify_kvm.sh` for formatting, lint, source/package contracts, local HTTP/WS/TLS fixtures and Node controller/UI tests. `python tests/browser_jetkvm.py` uses two real Chromium peer connections and the production Manager/JetKVM relay against an isolated test-only protocol peer; it is **not physical JetKVM firmware or a full running Home Assistant instance**. CI additionally builds the actual app Docker image. No production test fixture or dummy success path is used by the integration.

Before treating a deployment as accepted, test on actual JetKVM and NanoKVM hardware:

- Add → Test → Save → ONLINE → Live → H.264 image → keys/mouse → Ctrl+Alt+Del → Disconnect; repeat in tiles/list and at 100%/fit/full screen.
- Password/no-password, correct/wrong password, expired cookie, HTTPS with trusted/self-signed/pinned certificates, custom ports, IPv4/IPv6/DNS.
- Restart Manager/HA, restart JetKVM, disconnect/reconnect LAN, change the same device's address/port and reject a different physical device.
- ATX extension power/reset/long press and WOL to the intended host; no unwanted actions on entry open.
- Native NanoKVM add/edit/delete/status/video/HID/ATX and existing update/recovery/media functions.

Physical devices, LAN loss and full HA appliance restart are not available in this development environment and must not be marked passed solely because protocol tests pass.
