"""Real Chromium WebRTC/H264 acceptance against an isolated JetKVM protocol peer.

Uses the production Manager UI, production console view/ticket handler and
production JetKVM HTTP/WS provider. Only HA framework objects and the physical
JetKVM are fixtures. This does NOT claim physical-device or full HA acceptance.
Run: python tests/browser_jetkvm.py [--browser /usr/bin/chromium]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import secrets
import time
from types import SimpleNamespace
from unittest.mock import AsyncMock

import aiohttp
from aiohttp import web
from jinja2 import Environment, FileSystemLoader
from kvm_test_support import ROOT, provider
from playwright.async_api import async_playwright
from test_jetkvm_protocol import TestLoopbackPolicy
from test_manager_inventory import load_functions

PEER_HTML = """<!doctype html><title>Test-only JetKVM protocol peer</title><canvas id="source" width="1280" height="720"></canvas><script>
window.peerErrors=[];window.rpcReports=[];
const canvas=document.getElementById('source'),ctx=canvas.getContext('2d');let frame=0;
setInterval(()=>{ctx.fillStyle='#102439';ctx.fillRect(0,0,1280,720);ctx.fillStyle='#69dbb8';ctx.fillRect((frame++*9)%1100,220,140,240);ctx.fillStyle='white';ctx.font='42px sans-serif';ctx.fillText('JetKVM protocol test · '+frame,80,100);},33);
const stream=canvas.captureStream(30);let pc,remoteICE=[];
const ws=new WebSocket(location.origin.replace(/^http/,'ws')+'/test/peer');
const send=value=>ws.send(JSON.stringify(value));let chain=Promise.resolve();
ws.onmessage=event=>{chain=chain.then(async()=>{
 const message=JSON.parse(event.data);
 if(message.type==='start'){pc?.close();pc=null;remoteICE=[];return;}
 if(message.type==='stop'){pc?.close();pc=null;return;}
 if(message.type==='offer'){
   pc=new RTCPeerConnection({iceServers:[]});window.fixturePC=pc;
   pc.onicecandidate=e=>{if(e.candidate)send({type:'new-ice-candidate',data:e.candidate.toJSON()});};
   pc.ondatachannel=e=>{if(e.channel.label!=='rpc')return;const channel=e.channel;
     channel.onmessage=event=>{const request=JSON.parse(event.data);window.rpcReports.push(request);send({type:'rpc-observed',data:{method:request.method,params:request.params}});
       const result=request.method==='getActiveExtension'?'atx-power':null;
       channel.send(JSON.stringify({jsonrpc:'2.0',id:request.id,result}));
     };
   };
   pc.addTrack(stream.getVideoTracks()[0],stream);
   await pc.setRemoteDescription(JSON.parse(atob(message.data.sd)));
   for(const ice of remoteICE.splice(0))await pc.addIceCandidate(ice);
   await pc.setLocalDescription(await pc.createAnswer());
   send({type:'answer',data:btoa(JSON.stringify(pc.localDescription))});
 }else if(message.type==='new-ice-candidate'){
   if(pc?.remoteDescription)await pc.addIceCandidate(message.data);else remoteICE.push(message.data);
 }
}).catch(error=>window.peerErrors.push(error.name+': '+error.message));};
</script>"""


class Rig:
    def __init__(self):
        self.peer = None
        self.upstream = None
        self.reports = []
        self.cookie = ""
        self.logins = 0
        self.wol = []
        self.peer_ready = asyncio.Event()
        self.password = "fixture-local-password"
        self.app = web.Application()
        self.port = 0
        self.client = None
        self.loaded = object()
        self.user = SimpleNamespace(id="test-admin", is_active=True, is_admin=True)
        self.entry = SimpleNamespace(
            entry_id="jet-device",
            domain="nanokvm_rest",
            state=self.loaded,
            data={"provider": "jetkvm"},
            title="Server-01",
        )
        self.hass = SimpleNamespace(
            data={},
            auth=SimpleNamespace(async_get_user=AsyncMock(return_value=self.user)),
            config_entries=SimpleNamespace(
                async_get_entry=lambda id: self.entry if id == "jet-device" else None
            ),
        )
        self.ns = load_functions(
            ROOT / "custom_components/nanokvm_rest/console.py",
            {
                "_sessions",
                "_loaded_coordinator",
                "websocket_console_session",
                "async_disconnect_entry",
                "NanoKVMConsoleView",
            },
            {
                "HomeAssistantView": object,
                "KEY_HASS": "test_hass",
                "web": web,
                "aiohttp": aiohttp,
                "asyncio": asyncio,
                "secrets": secrets,
                "time": time,
                "DOMAIN": "nanokvm_rest",
                "ConfigEntryState": SimpleNamespace(LOADED=self.loaded),
                "CONSOLE_PROTOCOL": "nanokvm-console",
                "CONSOLE_SESSION_TTL": 30,
                "DATA_CONSOLE_SESSIONS": "tickets",
                "DATA_ACTIVE_CONSOLES": "active",
                "runtime_provider": provider("registry").runtime_provider,
                "KVMError": provider("errors").KVMError,
                "network_error": provider("jetkvm").network_error,
                "RELAYS": provider("signaling").RELAYS,
                "_LOGGER": logging.getLogger("browser_console"),
            },
        )
        self.app["test_hass"] = self.hass
        self.app.router.add_get("/", self.index)
        self.app.router.add_static("/static/", ROOT / "nanokvm_rest/webui/static")
        self.app.router.add_get("/api/bootstrap", self.bootstrap)
        self.app.router.add_post("/api/console/session", self.ticket)
        self.app.router.add_post("/api/rpc", self.rpc)
        self.app.router.add_get("/api/nanokvm_rest/console", self.ns["NanoKVMConsoleView"]().get)
        self.app.router.add_get("/device/status", lambda _: web.json_response({"isSetup": True}))
        self.app.router.add_get("/device", self.device)
        self.app.router.add_post("/auth/login-local", self.login)
        self.app.router.add_post("/device/send-wol/{mac}", self.wake)
        self.app.router.add_get("/webrtc/signaling/client", self.signal)
        self.app.router.add_get("/test/peer", self.peer_socket)
        self.app.router.add_get(
            "/test/peer.html", lambda _: web.Response(text=PEER_HTML, content_type="text/html")
        )

    async def start(self):
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, "127.0.0.1", 0)
        await self.site.start()
        self.port = self.site._server.sockets[0].getsockname()[1]
        self.url = f"http://127.0.0.1:{self.port}"
        self.client = provider("jetkvm").JetKVMClient(
            provider("network").parse_origin(self.url), self.password, policy=TestLoopbackPolicy()
        )
        self.adapter = provider("jetkvm_provider").JetKVMProvider(self.client)
        self.entry.runtime_data = SimpleNamespace(kvm_provider=self.adapter)

    async def close(self):
        if self.client:
            await self.client.close()
        if self.peer is not None and not self.peer.closed:
            await self.peer.close()
        await self.runner.cleanup()

    async def index(self, _):
        env = Environment(
            loader=FileSystemLoader(ROOT / "nanokvm_rest/webui/templates"), autoescape=True
        )
        return web.Response(
            text=env.get_template("index.html").render(version="test"), content_type="text/html"
        )

    async def bootstrap(self, _):
        return web.json_response(
            {
                "ok": True,
                "devices": {
                    "devices": [
                        {
                            "entry_id": "jet-device",
                            "title": "Server-01",
                            "provider": "jetkvm",
                            "base_url": self.url,
                            "loaded": True,
                            "available": True,
                            "capabilities": self.adapter.get_capabilities(),
                            "last_seen_at": "2026-09-29T00:00:00Z",
                            "last_latency_ms": 1.5,
                        }
                    ]
                },
                "warnings": [],
                "operations": {},
                "updates": {},
            }
        )

    async def ticket(self, request):
        data = await request.json()
        result = {}

        def done(_, payload):
            result.update(payload)

        def fail(_, code, message):
            result.update(error=message, code=code)

        connection = SimpleNamespace(user=self.user, send_result=done, send_error=fail)
        await self.ns["websocket_console_session"](
            self.hass, connection, {"id": 1, "entry_id": data["entry_id"]}
        )
        return web.json_response({"ok": "error" not in result, **result})

    async def rpc(self, request):
        body = await request.json()
        operation = body.get("operation")
        payload = body.get("payload", {})
        if operation == "wol":
            await self.adapter.wake_on_lan(payload["mac"])
            result = {"ok": True, "sent": True}
        elif operation == "disconnect":
            result = {
                "ok": True,
                "closed_sessions": await self.ns["async_disconnect_entry"](self.hass, "jet-device"),
            }
        elif operation == "test":
            result = {"ok": True, **await self.adapter.test_connection()}
        else:
            result = {
                "ok": False,
                "error": {
                    "code": "unsupported",
                    "message": "This test only exercises live KVM, not mocked device CRUD.",
                },
            }
        return web.json_response({"ok": True, "result": result})

    async def device(self, request):
        if request.cookies.get("authToken") != self.cookie or not self.cookie:
            return web.json_response({"error": "Unauthorized"}, status=401)
        return web.json_response(
            {"deviceId": "fixture-jet-01", "authMode": "password", "loopbackOnly": False}
        )

    async def login(self, request):
        if (await request.json()).get("password") != self.password:
            return web.json_response({"error": "Invalid password"}, status=401)
        self.logins += 1
        self.cookie = f"cookie-{self.logins}"
        response = web.json_response({"message": "Login successful"})
        response.set_cookie("authToken", self.cookie, httponly=True)
        return response

    async def wake(self, request):
        if request.cookies.get("authToken") != self.cookie:
            return web.Response(status=401)
        self.wol.append(request.match_info["mac"])
        return web.Response(text="WOL sent")

    async def signal(self, request):
        if request.cookies.get("authToken") != self.cookie:
            return web.Response(status=401)
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        await self.peer_ready.wait()
        self.upstream = ws
        await self.peer.send_json({"type": "start"})
        await ws.send_json(
            {"type": "device-metadata", "data": {"deviceVersion": "protocol-fixture"}}
        )
        try:
            async for message in ws:
                if message.type == aiohttp.WSMsgType.TEXT:
                    if message.data == "ping":
                        await ws.send_str("pong")
                    else:
                        await self.peer.send_str(message.data)
        finally:
            if self.upstream is ws:
                self.upstream = None
                if self.peer is not None and not self.peer.closed:
                    await self.peer.send_json({"type": "stop"})
        return ws

    async def peer_socket(self, request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        self.peer = ws
        self.peer_ready.set()
        async for message in ws:
            if message.type == aiohttp.WSMsgType.TEXT:
                packet = json.loads(message.data)
                if packet["type"] == "rpc-observed":
                    self.reports.append(packet["data"])
                elif self.upstream is not None and not self.upstream.closed:
                    await self.upstream.send_json(packet)
        return ws


async def wait_for(predicate, timeout=5):
    async with asyncio.timeout(timeout):
        while not predicate():
            await asyncio.sleep(0.025)


async def main(browser_path=None):
    rig = Rig()
    await rig.start()
    output = ROOT / "test-results"
    output.mkdir(exist_ok=True)
    browser = None
    errors = []
    try:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(
                executable_path=browser_path,
                headless=True,
                args=["--no-sandbox", "--disable-features=WebRtcHideLocalIpsWithMdns"],
            )
            peer = await browser.new_page()
            await peer.goto(rig.url + "/test/peer.html")
            await rig.peer_ready.wait()
            page = await browser.new_page(viewport={"width": 1500, "height": 1000})
            page.on("pageerror", lambda error: errors.append(str(error)))
            await page.goto(rig.url)
            await page.get_by_role("button", name="Live KVM", exact=True).last.click()
            await page.wait_for_function(
                'document.getElementById("console-state")?.textContent === "CONNECTED"',
                timeout=30000,
            )
            await page.wait_for_function(
                'document.getElementById("console-video")?.getVideoPlaybackQuality().totalVideoFrames > 8',
                timeout=15000,
            )
            codecs = await peer.evaluate(
                'async()=>{const s=await fixturePC.getStats();return [...s.values()].filter(x=>x.type==="outbound-rtp"&&x.kind==="video").map(x=>s.get(x.codecId)?.mimeType);}'
            )
            assert codecs == ["video/H264"], codecs
            assert await page.evaluate("document.cookie") == ""
            assert not any(
                r["method"] == "keyboardReport" and (r["params"]["modifier"] or r["params"]["keys"])
                for r in rig.reports
            )
            await page.locator("#console-stage").focus()
            await page.keyboard.press("F2")
            await page.keyboard.press("ArrowLeft")
            await page.keyboard.press("Control+a")
            await page.get_by_role("button", name="Ctrl+Alt+Del", exact=True).click()
            await wait_for(
                lambda: any(
                    r["method"] == "keyboardReport" and r["params"] == {"modifier": 5, "keys": [76]}
                    for r in rig.reports
                )
            )
            await wait_for(
                lambda: bool(
                    [
                        r
                        for r in rig.reports
                        if r["method"] == "keyboardReport"
                        and r["params"] == {"modifier": 0, "keys": []}
                    ]
                )
            )
            box = await page.locator("#console-video").bounding_box()
            await page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
            await page.mouse.click(
                box["x"] + box["width"] / 2, box["y"] + box["height"] / 2, button="right"
            )
            await page.mouse.wheel(0, 80)
            await wait_for(
                lambda: any(
                    r["method"] == "absMouseReport" and r["params"]["buttons"] == 2
                    for r in rig.reports
                )
            )
            await wait_for(lambda: any(r["method"] == "wheelReport" for r in rig.reports))
            await page.locator("#console-mouse-mode").select_option("relative")
            await page.locator("#console-video").click()
            await page.mouse.move(760, 540)
            await wait_for(
                lambda: any(
                    r["method"] == "relMouseReport" and (r["params"]["dx"] or r["params"]["dy"])
                    for r in rig.reports
                )
            )
            await page.evaluate("document.exitPointerLock()")
            await page.locator("#console-mouse-mode").select_option("absolute")
            await page.wait_for_function('!document.getElementById("console-atx").hidden')
            page.once("dialog", lambda d: asyncio.create_task(d.accept()))
            await page.locator('[data-console-atx="reset"]').click()
            await wait_for(
                lambda: any(
                    r["method"] == "setATXPowerAction" and r["params"]["action"] == "reset"
                    for r in rig.reports
                )
            )
            page.once("dialog", lambda d: asyncio.create_task(d.accept("AA:BB:CC:DD:EE:FF")))
            await page.locator("#console-wol").click()
            await wait_for(lambda: bool(rig.wol))
            await page.screenshot(path=str(output / "jetkvm-live.png"), full_page=True)
            # Expired device auth followed by an interrupted signaling transport
            # must result in a fresh backend login and another real video track.
            rig.cookie = "expired"
            await rig.upstream.close()
            await wait_for(lambda: rig.logins == 2, timeout=12)
            await page.wait_for_function(
                'document.getElementById("console-state")?.textContent === "CONNECTED"',
                timeout=15000,
            )
            await page.wait_for_function(
                'document.getElementById("console-video")?.getVideoPlaybackQuality().totalVideoFrames > 8',
                timeout=15000,
            )
            # Explicit manager disconnect must not be mistaken for network loss.
            await rig.ns["async_disconnect_entry"](rig.hass, "jet-device")
            await page.wait_for_function(
                'document.getElementById("console-state")?.textContent === "DISCONNECTED"'
            )
            await asyncio.sleep(1.2)
            assert rig.upstream is None
            await page.locator("#console-reconnect").click()
            await page.wait_for_function(
                'document.getElementById("console-state")?.textContent === "CONNECTED"',
                timeout=15000,
            )
            await page.locator("#console-disconnect").click()
            await page.wait_for_function(
                'document.getElementById("console-state")?.textContent === "DISCONNECTED"'
            )
            assert await peer.evaluate("peerErrors") == []
            await page.get_by_role("button", name="Urządzenia", exact=True).click()
            await page.get_by_role("button", name="Lista", exact=True).click()
            await page.screenshot(path=str(output / "jetkvm-list.png"), full_page=True)
            await page.get_by_role("button", name="Dodaj urządzenie", exact=True).click()
            await page.locator("#device-provider").select_option("jetkvm")
            await page.screenshot(path=str(output / "jetkvm-add.png"), full_page=True)
            assert not await page.locator("#device-username-group").is_visible()
            assert await page.locator("#device-port").input_value() == "80"
            await page.locator("#device-protocol").select_option("https")
            assert await page.locator("#device-port").input_value() == "443"
            assert errors == [], errors
            report = {
                "result": "PASS",
                "codec": codecs[0],
                "real_webrtc_video": True,
                "keyboard": True,
                "ctrl_alt_delete": True,
                "absolute_relative_mouse": True,
                "atx_rpc": True,
                "wol_http": True,
                "reconnect_and_reauthentication": True,
                "explicit_disconnect": True,
                "ui_errors": errors,
                "physical_devices_tested": False,
            }
            (output / "jetkvm-browser.json").write_text(json.dumps(report, indent=2) + "\n")
            print(json.dumps(report))
            await browser.close()
            browser = None
    finally:
        if browser is not None:
            await browser.close()
        await rig.close()


if __name__ == "__main__":
    args = argparse.ArgumentParser()
    args.add_argument("--browser")
    parsed = args.parse_args()
    asyncio.run(main(parsed.browser))
