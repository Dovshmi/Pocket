"""One shared 16-port list with additive quick-selection presets.

Pure functions: no network access, UI, or persistent data writes.
"""
from __future__ import annotations

from . import network_tools as net

MAX_SELECTED_PORTS = 16

# All presets are TCP services; never imply UDP reachability from a TCP check.
QUICK_PORTS = (
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
