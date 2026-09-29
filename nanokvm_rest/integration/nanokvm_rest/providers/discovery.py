"""Opt-in passive-neighbour discovery with real, bounded HTTP fingerprints.

No subnet sweeps, port ranges, shell interpolation, credentials or invented
mDNS/SSDP services. A cold neighbour table will not discover every LAN device.
"""

from __future__ import annotations

import asyncio
import ipaddress
import json
import shutil
from pathlib import Path

import aiohttp

from .errors import KVMError
from .network import LANPolicy, LANResolver, parse_origin

MAX_CANDIDATES = 32


def arp_candidates() -> set[str]:
    try:
        with Path("/proc/net/arp").open(encoding="ascii") as source:
            lines = source.read(65536).splitlines()[1:]
    except (OSError, UnicodeError):
        return set()
    result = set()
    for line in lines:
        parts = line.split()
        if len(parts) >= 4 and parts[3] != "00:00:00:00:00:00":
            result.add(parts[0])
    return result


async def neighbour_candidates() -> set[str]:
    result = await asyncio.to_thread(arp_candidates)
    executable = shutil.which("ip")
    if not executable:
        return result
    process = None
    try:
        async with asyncio.timeout(2):
            process = await asyncio.create_subprocess_exec(
                executable,
                "-j",
                "neigh",
                "show",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
                limit=65536,
            )
            # Stop oversized output before buffering an unbounded neighbour table.
            output = bytearray()
            while chunk := await process.stdout.read(8192):
                output.extend(chunk)
                if len(output) > 65536:
                    return result
            await process.wait()
            for record in json.loads(output):
                host = record.get("dst", "")
                try:
                    ip = ipaddress.ip_address(host)
                except ValueError:
                    continue
                if ip.version == 6 and ip.is_link_local:
                    host += "%" + str(record.get("dev", ""))
                result.add(host)
    except (OSError, TimeoutError, ValueError, TypeError, AttributeError):
        pass
    finally:
        if process and process.returncode is None:
            process.kill()
            await process.wait()
    return result


async def fingerprint(session, host: str) -> dict | None:
    origin = parse_origin(host)

    async def get(path):
        async with session.get(origin.url + path, allow_redirects=False) as response:
            body = bytearray()
            async for chunk in response.content.iter_chunked(16384):
                body.extend(chunk)
                if len(body) > 128 * 1024:
                    return response.status, None, ""
            text = body.decode("utf-8", errors="replace")
            try:
                data = json.loads(text)
            except ValueError:
                data = None
            return response.status, data, text

    status, data, _ = await get("/device/status")
    if status == 200 and isinstance(data, dict) and type(data.get("isSetup")) is bool:
        status, identity, _ = await get("/device")
        if (
            status == 200
            and isinstance(identity, dict)
            and identity.get("authMode") in {"password", "noPassword"}
            and isinstance(identity.get("deviceId"), str)
        ):
            return {"provider": "jetkvm", "host": host, "auth_mode": identity["authMode"]}
        _, _, html = await get("/")
        if "jetkvm" in html.lower():
            return {"provider": "jetkvm", "host": host, "requires_auth": status == 401}
        return None
    # A protected endpoint alone is not evidence of a NanoKVM. Only a real
    # NanoKVM info payload is accepted; password-protected devices can be added
    # manually instead of trying credentials during discovery.
    status, data, _ = await get("/api/vm/info")
    if status == 200 and isinstance(data, dict) and data.get("code") == 0:
        info = data.get("data")
        if isinstance(info, dict) and isinstance(info.get("deviceKey"), str) and info["deviceKey"]:
            return {"provider": "nanokvm", "host": host}
    return None


async def async_discover(hass) -> dict:
    policy = LANPolicy()
    candidates = []
    for host in sorted(await neighbour_candidates()):
        try:
            origin = parse_origin(host)
            policy.validate(origin.host)
        except KVMError:
            continue
        candidates.append(origin.host)
        if len(candidates) == MAX_CANDIDATES:
            break
    slots = asyncio.Semaphore(4)
    timeout = aiohttp.ClientTimeout(total=2, connect=1, sock_read=1)
    async with aiohttp.ClientSession(
        connector=aiohttp.TCPConnector(resolver=LANResolver(policy), use_dns_cache=False, limit=4),
        timeout=timeout,
        cookie_jar=aiohttp.DummyCookieJar(),
        trust_env=False,
    ) as session:

        async def probe(host):
            async with slots:
                try:
                    async with asyncio.timeout(3):
                        return await fingerprint(session, host)
                except (aiohttp.ClientError, KVMError, TimeoutError, OSError):
                    return None

        devices = [d for d in await asyncio.gather(*(probe(host) for host in candidates)) if d]
    return {
        "devices": devices,
        "checked": len(candidates),
        "note": "Odczytano tablicę ARP/neighbour Home Assistant i sprawdzono API na porcie 80 (maks. 32 adresy). Brak wpisu, niestandardowy port lub wymagane logowanie NanoKVM mogą wymagać ręcznego dodania.",
    }
