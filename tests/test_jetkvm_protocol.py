"""Real local HTTP/WebSocket protocol servers, never production device mocks."""

import asyncio
import base64
import json
import socket
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

import aiohttp
from aiohttp import web
from kvm_test_support import provider

network = provider("network")
jet = provider("jetkvm")
errors = provider("errors")
secrets = provider("secrets")
signaling = provider("signaling")
registry = provider("registry")


class TestLoopbackPolicy(network.LANPolicy):
    """Only a test fixture may dial the isolated in-process loopback server."""

    def validate(self, address):
        if address not in {"127.0.0.1", "::1"}:
            return super().validate(address)


class OriginTests(unittest.TestCase):
    def test_valid_origins(self):
        cases = [
            ("192.168.1.50", {}, "http://192.168.1.50"),
            ("10.0.0.55", {}, "http://10.0.0.55"),
            ("jetkvm.local", {}, "http://jetkvm.local"),
            ("JETKVM.local.", {}, "http://jetkvm.local"),
            ("192.168.50.12:8080", {}, "http://192.168.50.12:8080"),
            ("192.168.50.12:8080", {"port": 80}, "http://192.168.50.12:8080"),
            ("jetkvm.local", {"scheme": "https"}, "https://jetkvm.local"),
            ("https://jetkvm.local:8443", {}, "https://jetkvm.local:8443"),
            ("fd00::50", {}, "http://[fd00::50]"),
            ("[fd00::50]:8080", {}, "http://[fd00::50]:8080"),
            ("[fd00::50]", {"scheme": "https"}, "https://[fd00::50]"),
            ("fe80::1%eth0", {}, "http://[fe80::1%25eth0]"),
            ("http://[fe80::1%25eth0]:8080", {}, "http://[fe80::1%25eth0]:8080"),
            ("jetkvm.local", {"port": "8088"}, "http://jetkvm.local:8088"),
        ]
        for value, kwargs, expected in cases:
            with self.subTest(value=value, kwargs=kwargs):
                self.assertEqual(network.parse_origin(value, **kwargs).url, expected)
        self.assertEqual(
            network.parse_origin("https://[fd00::5]:8443").websocket_url(
                "/webrtc/signaling/client"
            ),
            "wss://[fd00::5]:8443/webrtc/signaling/client",
        )

    def test_invalid_origins(self):
        for value in [
            "",
            "ftp://host",
            "http://u:p@host",
            "http://host/a",
            "host?x=1",
            "host#x",
            "host:0",
            "host:65536",
            "host:abc",
            "http://host\\foo",
            "127.1",
            "0x7f000001",
            "0177.0.0.1",
            "http://host\n/a",
            "http://%31%32%37.0.0.1",
            "[::ffff:127.0.0.1]%bad",
            "fd00::1%eth0",
        ]:
            with self.subTest(value=value), self.assertRaises(errors.KVMError):
                network.parse_origin(value)

    def test_lan_policy_blocks_metadata_and_special_ranges(self):
        policy = network.LANPolicy(["0.0.0.0/0", "::/0"])
        for value in [
            "127.0.0.1",
            "169.254.169.254",
            "169.254.170.2",
            "0.0.0.0",
            "::1",
            "::",
            "ff02::1",
            "224.0.0.1",
            "::ffff:192.168.1.1",
            "2002:7f00:1::",
            "fd00:ec2::254",
        ]:
            with self.subTest(value=value), self.assertRaises(errors.KVMError):
                policy.validate(value)
        with self.assertRaises(errors.KVMError):
            network.LANPolicy().validate("8.8.8.8")
        for value in ["10.0.0.1", "172.16.0.10", "192.168.4.7", "fd00::50", "fe80::1%eth0"]:
            network.LANPolicy().validate(value)

    def test_provider_selection_and_capabilities(self):
        self.assertEqual(registry.provider_name({}), "nanokvm")
        spec = registry.provider_spec({"provider": "jetkvm"})
        caps = spec.adapter(None).get_capabilities()
        self.assertTrue(caps["video"] and caps["relative_mouse"] and caps["wol"])
        self.assertFalse(caps["atx"] or caps["audio"] or caps["clipboard"] or caps["virtual_media"])
        self.assertFalse(spec.native_management)
        with self.assertRaises(errors.KVMError):
            registry.provider_spec({"provider": "unknown"})

    def test_sdp_and_ice_envelopes(self):
        sd = base64.b64encode(json.dumps({"type": "offer", "sdp": "v=0\r\n"}).encode()).decode()
        packet = signaling.client_signal(
            json.dumps(
                {
                    "type": "offer",
                    "data": {"sd": sd, "iceServers": ["http://metadata"], "OidcGoogle": "secret"},
                }
            )
        )
        self.assertEqual(set(packet["data"]), {"sd"})
        self.assertEqual(
            signaling.session_description(packet["data"]["sd"], "offer")["sdp"], "v=0\r\n"
        )
        for raw in [
            "not-json",
            "[]",
            '{"type":"arbitrary-http"}',
            '{"type":"offer","data":{"sd":"bad"}}',
        ]:
            with self.subTest(raw=raw), self.assertRaises(errors.KVMError):
                signaling.client_signal(raw)
        self.assertEqual(
            signaling.ice_candidate(
                {"candidate": "candidate:1 1 UDP 1 192.168.1.50 45000 typ host", "sdpMid": "0"}
            )["sdpMid"],
            "0",
        )

    def test_vault_restart_tamper_and_missing_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "key"
            vault = secrets.CredentialVault(path)
            vault.load()
            value = vault.encrypt("private-password-Żółć")
            self.assertNotIn("private-password", value)
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            other = secrets.CredentialVault(path)
            other.load(encrypted_records_exist=True)
            self.assertEqual(other.decrypt(value), "private-password-Żółć")
            with self.assertRaises(errors.KVMError):
                other.decrypt(value[:-8] + "invalid!")
            path.unlink()
            with self.assertRaises(errors.KVMError):
                secrets.CredentialVault(path).load(encrypted_records_exist=True)
            self.assertFalse(path.exists())


class ResolverTests(unittest.IsolatedAsyncioTestCase):
    async def test_mixed_dns_answers_block_rebinding(self):
        records = [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("192.168.1.50", 80)),
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 80)),
        ]
        with patch.object(
            asyncio.get_running_loop(), "getaddrinfo", new=AsyncMock(return_value=records)
        ):
            with self.assertRaises(errors.KVMError) as caught:
                await network.LANResolver(network.LANPolicy()).resolve("jetkvm.local", 80)
            self.assertEqual(caught.exception.code, "forbidden_target")

    async def test_dns_failure(self):
        with patch.object(
            asyncio.get_running_loop(), "getaddrinfo", new=AsyncMock(side_effect=socket.gaierror())
        ):
            with self.assertRaises(errors.KVMError) as caught:
                await network.LANResolver(network.LANPolicy()).resolve("missing.local", 80)
            self.assertEqual(caught.exception.code, "dns_error")


class JetProtocolTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.password = ""
        self.cookie = ""
        self.setup = True
        self.login_count = 0
        self.wol = []
        self.ws_count = 0
        self.status_delay = 0
        self.redirect = False
        self.large = False
        self.chunked = False
        self.app = web.Application()
        self.app.router.add_get("/device/status", self.status)
        self.app.router.add_get("/device", self.device)
        self.app.router.add_post("/auth/login-local", self.login)
        self.app.router.add_post("/device/send-wol/{mac}", self.wake)
        self.app.router.add_get("/webrtc/signaling/client", self.signal)
        self.app.router.add_get("/forbidden-redirect", self.redirect_target)
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, "127.0.0.1", 0)
        await self.site.start()
        port = self.site._server.sockets[0].getsockname()[1]
        self.origin = network.parse_origin(f"127.0.0.1:{port}")
        self.clients = []
        self.redirect_hits = 0

    def client(self, password=""):
        client = jet.JetKVMClient(self.origin, password, policy=TestLoopbackPolicy())
        self.clients.append(client)
        return client

    async def asyncTearDown(self):
        await asyncio.gather(*(client.close() for client in self.clients))
        await self.runner.cleanup()

    def authorized(self, request):
        return not self.password or (
            self.cookie and request.cookies.get("authToken") == self.cookie
        )

    async def status(self, request):
        await asyncio.sleep(self.status_delay)
        if self.large:
            return web.Response(body=b"x" * (jet.MAX_JSON + 1))
        if self.chunked:
            response = web.StreamResponse(headers={"Content-Type": "application/json"})
            await response.prepare(request)
            for piece in [b'{"is', b'Setup":', b"true}"]:
                await response.write(piece)
                await asyncio.sleep(0.005)
            await response.write_eof()
            return response
        return web.json_response({"isSetup": self.setup})

    async def device(self, request):
        if not self.authorized(request):
            return web.json_response({"error": "Unauthorized"}, status=401)
        return web.json_response(
            {
                "deviceId": "test-device-123",
                "authMode": "password" if self.password else "noPassword",
                "loopbackOnly": False,
            }
        )

    async def login(self, request):
        self.login_count += 1
        if (await request.json()).get("password") != self.password:
            return web.json_response({"error": "Invalid password"}, status=401)
        self.cookie = f"valid-cookie-{self.login_count}"
        response = web.json_response({"message": "Logged in"})
        response.set_cookie("authToken", self.cookie, httponly=True)
        return response

    async def wake(self, request):
        if not self.authorized(request):
            return web.Response(status=401)
        self.wol.append(request.match_info["mac"])
        return web.Response(text="WOL sent")

    async def redirect_target(self, request):
        self.redirect_hits += 1
        return web.Response()

    async def signal(self, request):
        if self.redirect:
            raise web.HTTPFound("/forbidden-redirect")
        if not self.authorized(request):
            return web.Response(status=401)
        self.ws_count += 1
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        await ws.send_json({"type": "device-metadata", "data": {"deviceVersion": "test-version"}})
        async for message in ws:
            if message.type == aiohttp.WSMsgType.TEXT:
                if message.data == "ping":
                    await ws.send_str("pong")
                    continue
                packet = json.loads(message.data)
                if packet["type"] == "offer":
                    self.last_offer = packet
                    answer = base64.b64encode(
                        json.dumps({"type": "answer", "sdp": "v=0\r\n"}).encode()
                    ).decode()
                    await ws.send_json({"type": "answer", "data": answer})
        return ws

    async def test_no_password_device_and_http_wol(self):
        client = self.client()
        info = await client.test_connection()
        self.assertEqual(info["auth_mode"], "noPassword")
        self.assertGreaterEqual(info["latency_ms"], 0)
        await client.wake_on_lan("aa-bb-cc-dd-ee-ff")
        self.assertEqual(self.wol, ["AA:BB:CC:DD:EE:FF"])
        self.assertEqual(self.login_count, 0)
        self.assertEqual(self.ws_count, 0)

    async def test_password_auth_cookie_expiry_and_reauthentication(self):
        self.password = "correct"
        client = self.client("correct")
        await client.test_connection()
        await client.test_connection()
        self.assertEqual(self.login_count, 1)
        self.cookie = "expired"
        await client.test_connection()
        self.assertEqual(self.login_count, 2)
        self.assertEqual(client._cookie, self.cookie)

    async def test_wrong_or_missing_password(self):
        self.password = "correct"
        for password, code in [("", "authentication_required"), ("wrong", "invalid_password")]:
            with self.subTest(password=password), self.assertRaises(errors.KVMError) as caught:
                await self.client(password).test_connection()
            self.assertEqual(caught.exception.code, code)

    async def test_invalid_password_poll_is_rate_bounded(self):
        self.password = "correct"
        client = self.client("wrong")
        for _ in range(3):
            with self.assertRaises(errors.KVMError) as caught:
                await client.test_connection()
            self.assertEqual(caught.exception.code, "invalid_password")
        self.assertEqual(self.login_count, 1)

    async def test_setup_required(self):
        self.setup = False
        with self.assertRaises(errors.KVMError) as caught:
            await self.client().test_connection()
        self.assertEqual(caught.exception.code, "setup_required")

    async def test_chunked_status_and_oversize(self):
        self.chunked = True
        await self.client().test_connection()
        self.large = True
        with self.assertRaises(errors.KVMError) as caught:
            await self.client().test_connection()
        self.assertEqual(caught.exception.code, "protocol_error")

    async def test_timeout_and_connection_refused(self):
        self.status_delay = 0.15
        client = self.client()
        session = client._http()
        session._timeout = aiohttp.ClientTimeout(total=0.025)
        with self.assertRaises(errors.KVMError) as caught:
            await client.test_connection()
        self.assertEqual(caught.exception.code, "timeout")
        await self.site.stop()
        with self.assertRaises(errors.KVMError) as caught:
            await self.client().test_connection()
        self.assertEqual(caught.exception.code, "connection_refused")

    async def test_real_websocket_and_redirect_block(self):
        self.password = "correct"
        client = self.client("correct")
        ws = await client.open_signaling()
        self.assertEqual((await ws.receive_json())["type"], "device-metadata")
        await ws.send_str("ping")
        self.assertEqual((await ws.receive()).data, "pong")
        await client.close_signaling(ws)
        self.assertTrue(ws.closed)
        self.redirect = True
        with self.assertRaises(errors.KVMError) as caught:
            await client.open_signaling()
        self.assertEqual(caught.exception.code, "protocol_error")
        self.assertEqual(self.redirect_hits, 0)

    async def test_full_signaling_relay_lifecycle(self):
        client = self.client()
        adapter = provider("jetkvm_provider").JetKVMProvider(client)
        closed = asyncio.Event()

        async def bridge(request):
            browser = web.WebSocketResponse()
            await browser.prepare(request)
            upstream = await adapter.open_kvm_session()
            try:
                await signaling.relay_jetkvm(adapter, upstream, browser)
            finally:
                await adapter.close_kvm_session(upstream)
                await browser.close()
                closed.set()
            return browser

        app = web.Application()
        app.router.add_get("/bridge", bridge)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "127.0.0.1", 0)
        await site.start()
        try:
            async with aiohttp.ClientSession() as session:
                port = site._server.sockets[0].getsockname()[1]
                async with session.ws_connect(f"http://127.0.0.1:{port}/bridge") as ws:
                    self.assertEqual((await ws.receive_json())["type"], "device-metadata")
                    sd = base64.b64encode(
                        json.dumps({"type": "offer", "sdp": "v=0\r\n"}).encode()
                    ).decode()
                    await ws.send_json(
                        {"type": "offer", "data": {"sd": sd, "OidcGoogle": "must-not-forward"}}
                    )
                    answer = await ws.receive_json()
                    self.assertEqual(answer["type"], "answer")
                    self.assertNotIn("OidcGoogle", self.last_offer["data"])
                    await ws.send_json({"type": "manager-state", "state": "connected"})
                await asyncio.wait_for(closed.wait(), 2)
            self.assertFalse(client._websockets)
        finally:
            await runner.cleanup()


class JetTLSTests(unittest.IsolatedAsyncioTestCase):
    asyncSetUp = JetProtocolTests.asyncSetUp
    asyncTearDown = JetProtocolTests.asyncTearDown
    client = JetProtocolTests.client
    authorized = JetProtocolTests.authorized
    status = JetProtocolTests.status
    device = JetProtocolTests.device
    login = JetProtocolTests.login
    wake = JetProtocolTests.wake
    signal = JetProtocolTests.signal
    redirect_target = JetProtocolTests.redirect_target

    # Reuse actual HTTP handlers without duplicating the whole plain-HTTP suite.
    async def test_per_device_tls_verification_and_pin(self):
        import datetime
        import hashlib
        import ipaddress
        import ssl

        from cryptography import x509
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.x509.oid import NameOID

        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "JetKVM protocol fixture")])
        now = datetime.datetime.now(datetime.timezone.utc)
        certificate = (
            x509.CertificateBuilder()
            .subject_name(name)
            .issuer_name(name)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - datetime.timedelta(days=1))
            .not_valid_after(now + datetime.timedelta(days=1))
            .add_extension(
                x509.SubjectAlternativeName([x509.IPAddress(ipaddress.ip_address("127.0.0.1"))]),
                critical=False,
            )
            .sign(key, hashes.SHA256())
        )
        with tempfile.TemporaryDirectory() as tmp:
            cert_path = Path(tmp) / "cert.pem"
            key_path = Path(tmp) / "key.pem"
            cert_path.write_bytes(certificate.public_bytes(serialization.Encoding.PEM))
            key_path.write_bytes(
                key.private_bytes(
                    serialization.Encoding.PEM,
                    serialization.PrivateFormat.PKCS8,
                    serialization.NoEncryption(),
                )
            )
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            context.load_cert_chain(cert_path, key_path)
            site = web.TCPSite(self.runner, "127.0.0.1", 0, ssl_context=context)
            await site.start()
            origin = network.parse_origin(
                f"https://127.0.0.1:{site._server.sockets[0].getsockname()[1]}"
            )

            async def attempt(**options):
                client = jet.JetKVMClient(origin, policy=TestLoopbackPolicy(), **options)
                self.clients.append(client)
                await client.test_connection()
                ws = await client.open_signaling()
                await ws.receive_json()
                await client.close_signaling(ws)

            with self.assertRaises(errors.KVMError) as caught:
                await attempt()
            self.assertEqual(caught.exception.code, "tls_error")
            await attempt(verify_ssl=False)
            # Device-local bypass must not weaken a newly created strict client.
            with self.assertRaises(errors.KVMError) as caught:
                await attempt()
            self.assertEqual(caught.exception.code, "tls_error")
            digest = hashlib.sha256(
                certificate.public_bytes(serialization.Encoding.DER)
            ).hexdigest()
            await attempt(certificate_sha256=digest)
            with self.assertRaises(errors.KVMError) as caught:
                await attempt(certificate_sha256="00" * 32)
            self.assertEqual(caught.exception.code, "tls_error")
            await site.stop()

    async def test_real_ipv6_http(self):
        try:
            site = web.TCPSite(self.runner, "::1", 0)
            await site.start()
        except OSError:
            self.skipTest("IPv6 loopback unavailable on this test runner")
        origin = network.parse_origin(f"[::1]:{site._server.sockets[0].getsockname()[1]}")
        client = jet.JetKVMClient(origin, policy=TestLoopbackPolicy())
        self.clients.append(client)
        self.assertEqual((await client.test_connection())["device_id"], "test-device-123")
        await site.stop()

    async def test_not_jetkvm_and_unknown_http_methods(self):
        self.client()._http()  # Ensure session ownership/cleanup is exercised.
        with self.assertRaises(errors.KVMError):
            await self.client()._json("GET", "/arbitrary-proxy-path")
        self.large = True
        with self.assertRaises(errors.KVMError):
            await self.client().test_connection()
