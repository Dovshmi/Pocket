"""Offline command palette: explicit allowlisted actions, never shell execution."""
from __future__ import annotations

import ipaddress
import re
from datetime import datetime, timedelta

from . import quick_search, icon_themes, adaptive_window, network_tools, port_presets
from . import compact_dashboard as compact

ACTIONS = (
    ("new_note", "New note", "notes", "new note create note"),
    ("reminder", "Create reminder", "reminders", "reminder remind"),
    ("backup", "Create Pocket backup", "settings", "backup export backup"),
    ("pin", "Pin window", None, "pin"),
    ("unpin", "Unpin window", None, "unpin"),
    ("clip_pause", "Pause clipboard capture", "clipboard", "clipboard pause"),
    ("clip_resume", "Resume clipboard capture", "clipboard", "clipboard resume"),
    ("mac_update", "Update IEEE database", "mac", "mac update ieee"),
    ("extra_database", "Open Extranet Database", "extra", "extranet database extra database"),
    ("extra_local", "Open Extranet Local", "extra", "extranet local extra local"),
)

def action(key, title, destination=None, args=(), subtitle="Action"):
    return {"kind": "action", "id": key, "title": title, "destination": destination,
            "args": tuple(args), "subtitle": subtitle}

def allowed(hit, enabled):
    return hit.get("destination") in (None, "settings") or hit["destination"] in enabled

def catalog(settings):
    items = [action(key, title, dest) for key, title, dest, _ in ACTIONS]
    items += [action("theme", "Theme · " + icon_themes.THEMES[key]["name"],
                     "settings", (key,)) for key in icon_themes.THEME_ORDER]
    items += [action("size", "Size · " + name, "settings", (name,))
              for name in adaptive_window.profiles(settings.get("window_profiles"))]
    return items

def command(raw, settings):
    """Parse an exact internal command, or return None for ordinary searches."""
    q = raw.strip()
    low = q.casefold()
    for key, title, dest, aliases in ACTIONS:
        exact = {"new_note":"new note", "reminder":"reminder", "backup":"backup",
                 "pin":"pin", "unpin":"unpin", "clip_pause":"clipboard pause",
                 "clip_resume":"clipboard resume", "mac_update":"mac update",
                 "extra_database":"extranet database", "extra_local":"extranet local"}
        if low == exact[key]:
            return action(key, title, dest)
    verb, _, arg = q.partition(" ")
    arg = arg.strip()
    verb = verb.casefold()
    if not arg:
        return None
    if verb == "open":
        if arg.casefold() == "dashboard":
            return action("size", "Open Dashboard", "settings", ("Dashboard",))
        for key, _, label in compact.NAVIGATION:
            if key != "home" and arg.casefold() in (key.casefold(), label.casefold()):
                return {"kind":"tool", "id":key, "destination":key,
                        "title":label, "subtitle":"Open tool"}
    if verb == "theme":
        for key in icon_themes.THEME_ORDER:
            if arg.casefold().replace(" ", "_") == key:
                return action("theme", "Theme · " + icon_themes.THEMES[key]["name"], "settings", (key,))
    if verb == "size":
        for name in adaptive_window.profiles(settings.get("window_profiles")):
            if name.casefold() == arg.casefold():
                return action("size", "Size · " + name, "settings", (name,))
    if verb in ("port", "ports"):
        target, _, ports = arg.partition(" ")
        try:
            ip = network_tools.parse_target(target)
            if ports.strip():
                port_presets.parse_manual_ports(ports)
        except ValueError:
            return None
        return action("ports", "Prepare TCP check · " + ip, "ports", (ip, ports.strip()), "Review & run")
    if verb == "mac":
        try:
            network_tools.parse_mac_input(arg)
        except ValueError:
            return None
        return action("mac", "Prepare MAC lookup", "mac", (arg,), "Review & run")
    if verb == "subnet":
        try:
            ip = ipaddress.IPv4Interface(arg)
            if "/" not in arg:
                return action("subnet", "Open subnet · " + str(ip.ip), "subnet", (str(ip.ip), ""))
        except ValueError:
            return None
        return action("subnet", "Calculate · " + str(ip), "subnet", (str(ip.ip), str(ip.network.prefixlen)), "Local calculation")
    if verb in ("extra", "extranet") and len(arg) >= 2:
        return action("extra", "Search Extranet · " + arg, "extra", (arg,), "Local search")
    if verb == "cli":
        return action("cli", "Search CLI · " + arg, "commands", (arg,))
    if verb == "note":
        return action("new_note", "Create note · " + arg, "notes", (arg,))
    if verb == "remind":
        match = re.fullmatch(r"([0-9]{2}):([0-9]{2})\s+(.+)", arg)
        if match and int(match[1]) < 24 and int(match[2]) < 60:
            return action("timed_reminder", "Prepare reminder · " + match[3], "reminders",
                          (match[1]+":"+match[2], match[3]), "Confirm time")
    return None

def smart(q):
    items = []
    try:
        ip = ipaddress.ip_address(q)
    except ValueError:
        ip = None
    if ip is not None:
        items.append(action("ports", "Check TCP ports · " + q, "ports", (q, ""), "Review & run"))
        if ip.version == 4:
            items.append(action("subnet", "Calculate subnet · " + q, "subnet", (q, "")))
        items.append(action("extra", "Search Extranet · " + q, "extra", (q,)))
        items.append(action("copy", "Copy IP address", None, (q,)))
    elif "/" in q:
        try:
            iface = ipaddress.IPv4Interface(q)
            items.append(action("subnet", "Calculate · " + q, "subnet",
                                (str(iface.ip), str(iface.network.prefixlen))))
        except ValueError:
            pass
    if re.fullmatch(r"(?:[0-9a-fA-F]{2}[:-]){5}[0-9a-fA-F]{2}|[0-9a-fA-F]{12}|(?:[0-9a-fA-F]{4}\.){2}[0-9a-fA-F]{4}", q):
        items.append(action("mac", "Look up MAC · " + q, "mac", (q,), "Review & run"))
        items.append(action("copy", "Copy MAC address", None, (q,)))
    if re.match(r"^https?://\S+$", q, re.I):
        items.append(action("copy", "Copy URL", None, (q,)))
    if re.fullmatch(r"\+?[0-9][0-9 ()-]{6,18}", q):
        items.append(action("copy", "Copy phone / number", None, (q,)))
    if re.fullmatch(r"[0-9,\s-]+", q) and ("," in q or "-" in q):
        try:
            port_presets.parse_manual_ports(q)
            items.append(action("ports", "Prepare port selection · " + q, "ports", ("", q), "Review & run"))
        except ValueError:
            pass
    return items

def results(data, commands, raw, enabled, settings, limit=18):
    q = raw.strip()[:1024]
    mode = q.startswith(">")
    if mode:
        q = q[1:].strip()
    exact = command(q, settings)
    found = [exact] if exact else []
    if mode and q:
        found += [{"kind":"tool", "id":key, "destination":key, "title":label,
                   "subtitle":"Open tool"} for key, _, label in compact.NAVIGATION
                  if key != "home" and q.casefold() in (key.casefold(), label.casefold())]
    if not mode:
        found += smart(q)
    if not q:
        found += [{"kind":"tool", "id":key, "destination":key, "title":label,
                   "subtitle":"Open tool"} for key, _, label in compact.NAVIGATION if key != "home"]
    for hit in catalog(settings):
        aliases = next((a for key, _, _, a in ACTIONS if key == hit["id"]), "")
        hay = (hit["title"] + " " + aliases).casefold()
        if not q or all(word in hay for word in q.casefold().split()):
            found.append(hit)
    if not mode:
        if q:
            found += quick_search.results(data, commands, q, enabled, limit=limit)

    seen = set()
    out = []
    for hit in found:
        key = (hit["kind"], hit["id"], hit.get("args", ()))
        if key not in seen and allowed(hit, enabled):
            seen.add(key)
            out.append(hit)
    return out[:limit]
