"""Strict origin parsing and rebinding-resistant LAN-only device connections."""

from __future__ import annotations

import asyncio
import ipaddress
import re
import socket
from dataclasses import dataclass
from urllib.parse import urlsplit, urlunsplit

from aiohttp.abc import AbstractResolver

from .errors import KVMError

DEFAULT_LAN_NETWORKS = ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "fc00::/7", "fe80::/10")
# Never allow loopback, cloud metadata/credentials, unspecified or multicast,
# even if an administrator adds an overly broad LAN CIDR.
BLOCKED_NETWORKS = tuple(
    ipaddress.ip_network(v)
    for v in (
        "0.0.0.0/8",
        "127.0.0.0/8",
        "169.254.0.0/16",
        "224.0.0.0/4",
        "240.0.0.0/4",
        "::/128",
        "::1/128",
        "ff00::/8",
        "fd00:ec2::254/128",
    )
)
_HOST_LABEL = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", re.I)
_ZONE = re.compile(r"[A-Za-z0-9_.-]{1,32}")


@dataclass(frozen=True)
class DeviceOrigin:
    """An origin, never an arbitrary request URL."""

    scheme: str
    host: str
    port: int

    @property
    def authority(self) -> str:
        host = f"[{self.host.replace('%', '%25')}]" if ":" in self.host else self.host
        return (
            host if self.port == (443 if self.scheme == "https" else 80) else f"{host}:{self.port}"
        )

    @property
    def url(self) -> str:
        return f"{self.scheme}://{self.authority}"

    def websocket_url(self, path: str) -> str:
        return urlunsplit(("wss" if self.scheme == "https" else "ws", self.authority, path, "", ""))


def parse_origin(value: str, scheme: str = "http", port: int | str | None = None) -> DeviceOrigin:
    """Support raw IPv6 (no port), bracketed IPv6:port and host:port.

    A port written in the address takes precedence over a separate default port.
    Paths, credentials, controls, encoded hostnames and ambiguous malformed
    URLs are rejected rather than silently turned into requests.
    """
    if not isinstance(value, str) or not 0 < len(value) <= 512:
        raise KVMError("invalid_url")
    value = value.strip()
    if any(ord(c) < 33 or ord(c) == 127 for c in value) or "\\" in value:
        raise KVMError("invalid_url")
    if (
        not isinstance(scheme, str)
        or scheme not in {"http", "https"}
        or isinstance(port, (bool, float))
        or (isinstance(port, str) and port and not port.isdecimal())
    ):
        raise KVMError("invalid_url")
    if "://" not in value:
        # An unbracketed IPv6 literal is always an address, never host:port.
        if value.count(":") >= 2 and not value.startswith("["):
            try:
                ipaddress.IPv6Address(value.split("%", 1)[0])
            except ValueError as err:
                raise KVMError("invalid_url") from err
            value = f"[{value}]"
        value = f"{scheme}://{value}"
    try:
        parsed = urlsplit(value)
        host = parsed.hostname or ""
        explicit_port = parsed.port
        resolved_port = (
            explicit_port
            if explicit_port is not None
            else (
                int(port) if port not in (None, "") else (443 if parsed.scheme == "https" else 80)
            )
        )
    except (ValueError, TypeError) as err:
        raise KVMError("invalid_url") from err
    if (
        parsed.scheme not in {"http", "https"}
        or not host
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
        or not 1 <= resolved_port <= 65535
        or isinstance(port, bool)
    ):
        raise KVMError("invalid_url")
    host = host.replace("%25", "%")
    if ":" in host:
        address, _, zone = host.partition("%")
        try:
            ip = ipaddress.IPv6Address(address)
        except ValueError as err:
            raise KVMError("invalid_url") from err
        if zone and (not ip.is_link_local or not _ZONE.fullmatch(zone)):
            raise KVMError("invalid_url")
        host = str(ip) + (f"%{zone}" if zone else "")
    else:
        if "%" in host:
            raise KVMError("invalid_url")
        try:
            host = str(ipaddress.IPv4Address(host))
        except ValueError:
            # Reject alternative numeric forms (127.1, hex/octal inet_aton),
            # then require ordinary IDNA DNS labels, not a free-form netloc.
            try:
                socket.inet_aton(host)
            except OSError:
                pass
            else:
                raise KVMError("invalid_url") from None
            try:
                host = host.rstrip(".").encode("idna").decode("ascii").lower()
            except UnicodeError as err:
                raise KVMError("invalid_url") from err
            if len(host) > 253 or not all(_HOST_LABEL.fullmatch(p) for p in host.split(".")):
                raise KVMError("invalid_url")
    return DeviceOrigin(parsed.scheme, host, resolved_port)


class LANPolicy:
    """Fixed safe defaults plus explicitly configured local routable subnets."""

    def __init__(self, extra_cidrs: list[str] | tuple[str, ...] = ()):
        if len(extra_cidrs) > 32:
            raise KVMError("invalid_data")
        try:
            self.networks = tuple(
                ipaddress.ip_network(v, strict=False) for v in (*DEFAULT_LAN_NETWORKS, *extra_cidrs)
            )
        except ValueError as err:
            raise KVMError("invalid_data", "Invalid LAN CIDR") from err

    def validate(self, address: str) -> None:
        try:
            ip = ipaddress.ip_address(address.split("%", 1)[0])
        except ValueError as err:
            raise KVMError("forbidden_target") from err
        # Do not permit IPv4-mapped or translation/tunnel addresses to escape
        # checks by presenting an otherwise harmless-looking IPv6 prefix.
        if isinstance(ip, ipaddress.IPv6Address) and (ip.ipv4_mapped or ip.sixtofour or ip.teredo):
            raise KVMError("forbidden_target")
        if any(ip.version == net.version and ip in net for net in BLOCKED_NETWORKS):
            raise KVMError("forbidden_target")
        if not any(ip.version == net.version and ip in net for net in self.networks):
            raise KVMError("forbidden_target")

    def validate_literal(self, host: str) -> None:
        try:
            ipaddress.ip_address(host.split("%", 1)[0])
        except ValueError:
            return
        self.validate(host)


class LANResolver(AbstractResolver):
    """Resolve AND validate the addresses that aiohttp will actually dial.

    No preflight-only DNS check: returned addresses are pinned to this connect
    attempt, and aiohttp's DNS cache is disabled. All answers must satisfy the
    policy. Literal targets are separately checked before client construction.
    """

    def __init__(self, policy: LANPolicy):
        self.policy = policy

    async def resolve(self, host: str, port: int = 0, family: int = socket.AF_INET) -> list[dict]:
        try:
            async with asyncio.timeout(3):
                records = await asyncio.get_running_loop().getaddrinfo(
                    host,
                    port,
                    family=family,
                    type=socket.SOCK_STREAM,
                )
        except TimeoutError as err:
            raise KVMError("dns_error", "DNS lookup timeout") from err
        except (socket.gaierror, OSError) as err:
            raise KVMError("dns_error", "DNS lookup failed") from err
        result = []
        seen = set()
        for af, _, proto, _, sockaddr in records:
            ip = sockaddr[0]
            self.policy.validate(ip)
            # getaddrinfo returns the scope separately for link-local IPv6.
            if af == socket.AF_INET6 and len(sockaddr) > 3 and sockaddr[3]:
                ip = f"{ip}%{sockaddr[3]}"
            if (af, ip) in seen:
                continue
            seen.add((af, ip))
            result.append(
                {
                    "hostname": host,
                    "host": ip,
                    "port": port,
                    "family": af,
                    "proto": proto,
                    "flags": socket.AI_NUMERICHOST,
                }
            )
        if not result:
            raise KVMError("dns_error", "No usable DNS addresses")
        return result

    async def close(self) -> None:
        """No sockets or background workers are owned by this resolver."""
