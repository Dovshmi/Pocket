"""Explicit, on-demand remote TCP checks through the DashDash API.

No connection is made on import. The desktop app calls this only when the user
selects DashDash and presses Run TCP check. No third-party dependencies.
"""
from __future__ import annotations

import ipaddress
import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

DASHDASH_PORT_CHECK_URL = "https://dashdash-tau.vercel.app/api/port-check"
REMOTE_MAX_PORTS = 16
REMOTE_TIMEOUT_SECONDS = 12
MAX_RESPONSE_BYTES = 65536
VALID_STATUSES = {"OPEN", "CLOSED", "TIMEOUT"}


def validate_remote_check(ip: str, ports: list[int]) -> tuple[str, list[int]]:
    """DashDash only accepts one globally routable public IPv4 and <=16 ports."""
    try:
        address = ipaddress.IPv4Address(ip.strip())
    except (ValueError, AttributeError) as exc:
        raise ValueError("DashDash remote checks require a public IPv4 address.") from exc
    # Match DashDash's explicit SSRF blocks, including ranges that some
    # Python versions classify as globally routable.
    excluded = (ipaddress.IPv4Network("192.0.0.0/24"),
                ipaddress.IPv4Network("192.88.99.0/24"))
    if not address.is_global or any(address in network for network in excluded):
        raise ValueError("DashDash cannot test private, local, or reserved IP addresses.")
    if not isinstance(ports, list) or not ports:
        raise ValueError("Select at least one TCP port.")
    if any(type(port) is not int or not 1 <= port <= 65535 for port in ports):
        raise ValueError("TCP ports must be integers between 1 and 65535.")
    unique = sorted(set(ports))
    if len(unique) > REMOTE_MAX_PORTS:
        raise ValueError("DashDash allows up to 16 TCP ports per check. Select fewer ports.")
    return str(address), unique


def _error_detail(body: bytes) -> str:
    try:
        payload = json.loads(body.decode("utf-8"))
        detail = payload.get("error") if isinstance(payload, dict) else None
        return str(detail)[:160] if isinstance(detail, str) else ""
    except (UnicodeError, ValueError):
        return ""


def check_remote_ports(ip: str, ports: list[int]) -> list[dict]:
    """Request a server-side TCP connect scan and validate the returned results.

    This does not discover hosts or start background scans. Call from a worker
    thread so the Tkinter UI stays responsive.
    """
    ip, ports = validate_remote_check(ip, ports)
    payload = json.dumps({"ip": ip, "ports": ",".join(map(str, ports))}).encode("utf-8")
    request = Request(
        DASHDASH_PORT_CHECK_URL, data=payload, method="POST",
        headers={"Content-Type": "application/json", "Accept": "application/json",
                 "User-Agent": "PocketDesk/1.32 (manual DashDash check)"},
    )
    try:
        with urlopen(request, timeout=REMOTE_TIMEOUT_SECONDS) as response:
            if response.status != 200:
                raise ValueError(f"DashDash returned HTTP {response.status}.")
            body = response.read(MAX_RESPONSE_BYTES + 1)
    except HTTPError as exc:
        detail = _error_detail(exc.read(2048))
        if exc.code == 429:
            raise ValueError("DashDash is limiting requests. Try again later.") from exc
        raise ValueError(f"DashDash HTTP {exc.code}" + (f": {detail}" if detail else ".")) from exc
    except (URLError, TimeoutError, OSError) as exc:
        raise ValueError("Could not contact DashDash. Check your internet access or try Local.") from exc
    if len(body) > MAX_RESPONSE_BYTES:
        raise ValueError("DashDash returned an unexpectedly large response.")
    try:
        data = json.loads(body.decode("utf-8"))
    except (UnicodeError, ValueError) as exc:
        raise ValueError("DashDash returned invalid JSON.") from exc
    if not isinstance(data, dict) or data.get("ip") != ip or not isinstance(data.get("results"), list):
        raise ValueError("DashDash returned an unexpected response.")
    items = data["results"]
    if len(items) != len(ports):
        raise ValueError("DashDash returned an incomplete port check.")
    checked, results = set(), []
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("DashDash returned an invalid port result.")
        port, status, ms = item.get("port"), item.get("status"), item.get("ms")
        if (type(port) is not int or port not in ports or port in checked or
                status not in VALID_STATUSES or type(ms) not in (int, float) or
                not 0 <= ms <= 120000):
            raise ValueError("DashDash returned an invalid port result.")
        checked.add(port)
        service = item.get("service", "—")
        results.append({"port": port,
                        "service": service if isinstance(service, str) and len(service) <= 32 else "—",
                        "status": status, "ms": int(ms)})
    return sorted(results, key=lambda item: item["port"])
