"""Manual TCP input and the compact favorite + last-scan quick list.

Port names below are labels only: NONE are shown automatically as default
Quick Port Selection items. Only favorites and the last completed scan appear.
This module is pure, does no network I/O and does not write persistent data.
"""
from __future__ import annotations

from . import network_tools as net

MAX_SELECTED_PORTS = 16
MAX_FAVORITES = 128


# All presets are TCP services; never imply UDP reachability from a TCP check.
PORT_SERVICE_CATALOG = (
    (21, "FTP"), (22, "SSH"), (23, "Telnet"), (25, "SMTP"),
    (53, "DNS"), (80, "HTTP"), (110, "POP3"), (143, "IMAP"),
    (443, "HTTPS"), (445, "SMB"), (3389, "RDP"), (5900, "VNC"),
    (8080, "HTTP Alt"), (8443, "HTTPS Alt"), (8291, "WinBox"),
    (8728, "RouterOS API"), (465, "SMTPS"), (587, "SMTP Send"),
    (993, "IMAPS"), (995, "POP3S"), (389, "LDAP"), (636, "LDAPS"),
    (139, "NetBIOS"), (1433, "MSSQL"), (1521, "Oracle"),
    (3306, "MySQL"), (5432, "Postgres"), (6379, "Redis"),
    (27017, "MongoDB"), (8000, "HTTP Dev"), (9200, "Elastic"),
    (1883, "MQTT"), (5672, "AMQP"), (6443, "K8s API"),
)


PORT_SERVICE_NAMES = dict(PORT_SERVICE_CATALOG)


def port_usage(port: int) -> str:
    """Human-readable TCP service, or Custom for an unrecognized port."""
    return PORT_SERVICE_NAMES.get(port, "Custom")


def normalize_favorites(raw, *, maximum: int = MAX_FAVORITES) -> list[int]:
    """Load old/invalid profile values defensively without inserting defaults."""
    if not isinstance(raw, list):
        return []
    result = []
    seen = set()
    for port in raw:
        if type(port) is int and 1 <= port <= 65535 and port not in seen:
            seen.add(port)
            result.append(port)
            if len(result) == maximum:
                break
    return result


def toggle_favorite(favorites: list[int], port: int) -> list[int]:
    """Add/remove one star. Never change recent ports or typed input."""
    if type(port) is not int or not 1 <= port <= 65535:
        raise ValueError("Invalid TCP port for favorites.")
    current = normalize_favorites(favorites)
    if port in current:
        return [p for p in current if p != port]
    if len(current) >= MAX_FAVORITES:
        raise ValueError(f"You can save up to {MAX_FAVORITES} favorite ports.")
    return [*current, port]


def quick_ports(favorites: list[int], last_scan: list[int]) -> list[int]:
    """One list: starred ports first, then non-starred ports from last scan."""
    stored = normalize_favorites(favorites)
    seen = set(stored)
    result = list(stored)
    for port in last_scan if isinstance(last_scan, (list, tuple)) else ():
        if type(port) is int and 1 <= port <= 65535 and port not in seen:
            result.append(port)
            seen.add(port)
    return result


def parse_manual_ports(raw: str, *, limit: int = MAX_SELECTED_PORTS,
                       allow_empty: bool = False) -> list[int]:
    """Parse comma-separated TCP port numbers, preserving first appearance."""
    if not isinstance(raw, str) or len(raw) > 512:
        raise ValueError("Enter comma-separated port numbers (up to 16).")
    if not raw.strip():
        if allow_empty:
            return []
        raise ValueError("Enter at least one TCP port.")
    tokens = raw.split(",")
    # Allow a trailing comma while the user is composing a list.
    if tokens[-1].strip() == "":
        tokens.pop()
    if not tokens or any(not token.strip() for token in tokens):
        raise ValueError("Separate ports with commas (e.g. 22,80,443).")
    values = []
    seen = set()
    for token in tokens:
        token = token.strip()
        if not token.isascii() or not token.isdecimal() or not 1 <= int(token) <= 65535:
            raise ValueError(f"Invalid TCP port: {token[:32]}. Use 1–65535.")
        port = int(token)
        if port not in seen:
            values.append(port)
            seen.add(port)
            if len(values) > limit:
                raise ValueError(f"Maximum {limit} unique TCP ports per check.")
    return values


def toggle_quick_port(raw: str, port: int) -> str:
    """Add a preset to the existing input or remove only that preset.

    Other manually entered ports are always preserved, including their order.
    Invalid text is never silently overwritten.
    """
    if type(port) is not int or not 1 <= port <= 65535:
        raise ValueError("Invalid quick-select port.")
    ports = parse_manual_ports(raw, limit=65535, allow_empty=True)
    if port in ports:
        ports.remove(port)
    else:
        if len(ports) >= MAX_SELECTED_PORTS:
            raise ValueError("Maximum 16 TCP ports. Remove a port before adding another.")
        ports.append(port)
    return ",".join(map(str, ports))


def migrate_port_input(tools: dict) -> str:
    """Keep existing saved port choices when upgrading older Pocket profiles."""
    if isinstance(tools.get("ports_input"), str):
        return tools["ports_input"][:512]
    if tools.get("mode") == "selected":
        values = []
        for port in tools.get("selected_ports", []):
            if type(port) is int and 1 <= port <= 65535 and port not in values:
                values.append(port)
        custom = tools.get("custom_ports", "")
        if isinstance(custom, str) and custom.strip():
            try:
                values.extend(net.parse_ports(custom))
            except ValueError:
                # Never discard a saved manual entry just because a legacy
                # custom field contained invalid text.
                return (",".join(map(str, values)) + ("," if values else "") + custom)[:512]
        return ",".join(map(str, dict.fromkeys(values)))
    single = tools.get("single_port", "443")
    return single[:512] if isinstance(single, str) else "443"
