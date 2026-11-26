"""Safe, explicit handoff from Clipboard history to existing Pocket tools.

Only exact IP/MAC/CIDR literals are routable. Merely opening a tool never
starts a TCP check, remote MAC lookup or any network request.
"""
from __future__ import annotations

import ipaddress
import re
from urllib.parse import urlsplit

from . import network_tools, port_presets
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


# Keep the original routing API stable; suggestions add only explicit actions.
def suggestions(text, enabled):
    """Pure, bounded classification of the selected text; never run a tool."""
    if not isinstance(text, str) or not text.strip():
        return []
    enabled = set(enabled)
    value = text.strip()
    items = []
    # Avoid expensive parsing, giant menu labels or accidental actions on logs.
    values = destination_values(value) if len(value) <= 2048 else {"notes": value}

    def add(key, label, destination, payload):
        if destination is None or destination in enabled:
            items.append((key, label, destination, payload))

    for destination, label in (
        ("ports", "Prepare TCP port check"),
        ("mac", "Open MAC lookup with address"),
        ("subnet", "Open Subnet Calculator"),
    ):
        if destination in values:
            add(destination, label, destination, value)

    single_line = len(value) <= 2048 and not any(c in value for c in "\r\n\t")
    if single_line:
        # A line ID is not a TCP port range. Prefer the group-code form
        # when the suffix is at least six digits.
        line_code = re.fullmatch(r"[0-9]{1,5}\s*-\s*[0-9]{6,12}", value)
        phone = re.fullmatch(r"\+?[0-9][0-9 ()-]{6,18}", value)
        phone_digits = re.sub(r"\D", "", value)
        is_phone = bool(phone and 7 <= len(phone_digits) <= 15 and
                        (value.startswith(("+", "0")) or value.isdecimal() or "(" in value))
        if "ports" in values or "mac" in values or line_code or is_phone:
            add("extra", "Search in EXTRA", "extra", value)
        if not line_code and not is_phone and re.fullmatch(r"[0-9,\s-]+", value) and ("," in value or "-" in value):
            try:
                ports = port_presets.parse_manual_ports(value)
            except ValueError:
                pass
            else:
                add("port_list", "Prepare TCP port selection", "ports",
                    ",".join(str(port) for port in ports))
        if re.match(r"^https?://", value, re.I) and not re.search(r"\s|[\x00-\x1f\x7f\\]", value):
            try:
                url = urlsplit(value)
                valid_url = bool(url.hostname and not url.username and not url.password)
                _ = url.port  # rejects malformed/out-of-range ports
            except ValueError:
                valid_url = False
            if valid_url:
                add("url", "Open URL in browser", None, value)

    add("notes", "Create a new Note from text", "notes", value)
    add("translate", "TRANSLATE EN/HE", None, text)
    return items


def run_suggestion(app, suggestion):
    """Dispatch only after the user chooses a menu item."""
    key, _label, destination, value = suggestion
    if destination is not None and destination not in app.settings["visible_tabs"]:
        return False
    if key in ("ports", "mac", "subnet", "notes"):
        return send_to_tool(app, key, value)
    if key in ("extra", "port_list"):
        # Reuse the palette's existing dispatch. Extra's database lookup is
        # local; live Excel is only prefilled, requiring an explicit Search.
        action = ("extra", (value,)) if key == "extra" else ("ports", ("", value))
        app._run_palette_action({"kind": "action", "id": action[0],
                                 "destination": destination, "args": action[1]})
        return True
    if key == "translate":
        return app._convert_clipboard_text(value)
    if key == "url":
        # An explicit click is the only event that may open a web page.
        import webbrowser
        return webbrowser.open(value)
    return False
