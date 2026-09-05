# Remote Console / Live KVM

Version 0.9.0 adds a native Live KVM console to the **Remote Server** Home Assistant sidepanel.

## What it provides

- H.264 live video rendered directly inside the sidepanel.
- Fullscreen mode.
- Fit, 100%, 125%, 150% and 200% scaling.
- Mobile landscape mode with fullscreen/orientation-lock support when the browser allows it.
- Absolute mouse control, wheel scrolling and touch input.
- Touch gestures: tap for left click, long press for right click and two-finger vertical scrolling.
- Physical keyboard forwarding using standard USB HID reports.
- Touch-friendly Esc, F2, F8, F12, Enter, Delete and Ctrl+Alt+Delete buttons.
- Text paste through the existing NanoKVM HID paste API.
- Live keyboard LED status when NanoKVM reports it.

## Security model

The browser never receives the NanoKVM username, password or NanoKVM session cookie.

Home Assistant administrators request a short-lived one-time token over the authenticated Home Assistant WebSocket API. The browser then connects to a same-origin Home Assistant WebSocket using that token as a WebSocket subprotocol. Home Assistant opens the authenticated NanoKVM H.264 and HID WebSockets server-side and bridges them to the sidepanel.

This design also avoids browser mixed-content restrictions when Home Assistant uses HTTPS while NanoKVM itself is configured with HTTP.

## Stream protocol

The console uses NanoKVM's native direct H.264 stream at `/api/stream/h264/direct` and manual HID WebSocket at `/api/ws`. H.264 is decoded with the browser WebCodecs API using low-latency settings and stream flow-control acknowledgements.

Modern browsers with WebCodecs and OffscreenCanvas support are required for the embedded live stream. The native NanoKVM UI remains available as a fallback.
