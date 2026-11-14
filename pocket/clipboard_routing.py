"""Safe, explicit handoff from Clipboard history to existing Pocket tools.

Only exact IP/MAC/CIDR literals are routable. Merely opening a tool never
starts a TCP check, remote MAC lookup or any network request.
"""
from __future__ import annotations

import ipaddress

from . import network_tools
from .note_model import new_note


def destination_values(text):
    """Return validated destinations for a single copied text entry.

    Ports accepts literal IPv4/IPv6. Subnet accepts IPv4 or IPv4/prefix and
    keeps the calculator's currently selected prefix for plain IPv4.
    MAC accepts one complete EUI-48, never arbitrary text or a partial OUI.
    """
    result = {}
    if not isinstance(text, str):
        return result
    value = text.strip()
    if not value:
        return result
    try:
        result["ports"] = network_tools.parse_target(value)
    except ValueError:
        pass
    try:
        mac = network_tools.normalize_mac(value)
        result["mac"] = ":".join(mac[i:i+2] for i in range(0, 12, 2))
    except ValueError:
        pass
    try:
        interface = ipaddress.IPv4Interface(value)
        address = str(interface.ip)
        prefix = str(interface.network.prefixlen) if "/" in value else None
        result["subnet"] = (address, prefix)
    except (ValueError, ipaddress.AddressValueError, ipaddress.NetmaskValueError):
        pass
    # Taking text into Notes is an intentional, persisted user action.
    result["notes"] = value
    return result


def send_to_tool(app, destination, text):
    """Populate an enabled existing tool, but never run a check implicitly."""
    values = destination_values(text)
    if destination not in values:
        return False
    if destination not in app.settings["visible_tabs"]:
        return False
    if destination == "notes":
        # Save a new note instead of overwriting existing user notes.
        app.data["notes"].insert(0, new_note(title="From Clipboard", body=values["notes"]))
        app.data["active_note"] = app.data["notes"][0]["id"]
        app.show_tab("notes")
        app.schedule_save()
        return True
    if destination == "ports":
        app.show_tab("ports")
        app.host_var.set(values["ports"])
    elif destination == "mac":
        app.mac_draft = values["mac"]
        app.show_tab("mac")
    elif destination == "subnet":
        address, prefix = values["subnet"]
        app.show_tab("subnet")
        app.subnet_ip_var.set(address)
        if prefix is not None:
            app.subnet_prefix_var.set(prefix)
        app._calculate_subnet()  # Local calculation only, no network I/O.
    else:
        return False
    return True
