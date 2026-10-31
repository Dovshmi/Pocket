"""Pure, offline data model for Pocket's three-page Extra Mini launcher.

This module never executes CLI, opens URLs, or reads personal files. It stores
only references (kind and record ID), short optional display labels, and an
explicit copy/open preference for plain commands.
"""
from __future__ import annotations

from copy import deepcopy
import command_helper as ch
import smart_templates as smart

PAGE_COUNT = 3
SLOT_COUNT = 4
PAGE_TITLES = ("Tools", "Commands", "Notes")
KINDS = ("tool", "command", "template", "note", "shortcut")
TOOLS = ("notes", "links", "ports", "mac", "commands", "subnet", "clipboard")
TOOL_NAMES = {
    "notes": "Notes", "links": "Shortcuts", "ports": "TCP Ports",
    "mac": "MAC Lookup", "commands": "Commands",
    "subnet": "Subnet", "clipboard": "Clipboard",
}
KIND_ICONS = {"tool": "⌘", "command": ">_", "template": "{}", "note": "✎", "shortcut": "↗"}


def safe_name(raw, fallback):
    if not isinstance(raw, str):
        return fallback
    # Users may name pages and tiles, but cannot inject newlines/control codes.
    title = " ".join(raw.split())[:28]
    return title if title and all(ord(c) >= 32 for c in title) else fallback


def page_index(raw):
    return raw if type(raw) is int and 0 <= raw < PAGE_COUNT else 0


def clean_tile(raw):
    """Keep a valid, bounded reference, otherwise a non-destructive empty slot."""
    if raw is None:
        return None
    if isinstance(raw, str):
        return {"kind": "tool", "id": raw} if raw in TOOLS else None
    if not isinstance(raw, dict):
        return None
    kind, ident = raw.get("kind"), raw.get("id")
    if kind not in KINDS or not isinstance(ident, str) or not 1 <= len(ident) <= 160:
        return None
    if any(ord(c) < 32 for c in ident):
        return None
    if kind == "tool" and ident not in TOOLS:
        return None
    tile = {"kind": kind, "id": ident}
    if isinstance(raw.get("label"), str):
        label = safe_name(raw["label"], "")
        if label:
            tile["label"] = label
    if kind == "command" and raw.get("action") == "copy":
        tile["action"] = "copy"
    return tile


def default_pages(legacy_tiles=None):
    base = legacy_tiles if isinstance(legacy_tiles, (tuple, list)) else (
        "commands", "notes", "clipboard", "subnet")
    first = [clean_tile(base[i]) if i < len(base) else None for i in range(SLOT_COUNT)]
    return [
        {"name": "Tools", "tiles": first},
        {"name": "Commands", "tiles": [None] * SLOT_COUNT},
        {"name": "Notes", "tiles": [None] * SLOT_COUNT},
    ]


def normalize_pages(raw, legacy_tiles=None):
    """Lossless migration from the former four saved tool slots.

    Once pages exist, the new multi-page model is authoritative. The old
    extra_mini_tiles setting is maintained only for older code/tests.
    """
    if not isinstance(raw, list) or len(raw) != PAGE_COUNT:
        return default_pages(legacy_tiles)
    result = []
    for i in range(PAGE_COUNT):
        source = raw[i] if isinstance(raw[i], dict) else {}
        items = source.get("tiles")
        if not isinstance(items, list):
            items = [None] * SLOT_COUNT
        result.append({
            "name": safe_name(source.get("name"), PAGE_TITLES[i]),
            "tiles": [clean_tile(items[j]) if j < len(items) else None
                      for j in range(SLOT_COUNT)],
        })
    return result


def legacy_first_page(pages):
    """Backwards-compatible four string slots; specific items have no tool key."""
    first = normalize_pages(pages)[0]["tiles"]
    return [t["id"] if t is not None and t["kind"] == "tool" else None for t in first]


def put(pages, page, slot, tile):
    state = normalize_pages(pages)
    if not valid_slot(page, slot):
        return state
    new_item = clean_tile(tile)
    slots = state[page]["tiles"]
    if new_item is not None and new_item["kind"] == "tool":
        for i, previous in enumerate(slots):
            if i != slot and previous is not None and previous.get("kind") == "tool" and previous.get("id") == new_item["id"]:
                # Preserve the legacy first-page behavior: moving an already
                # assigned tool swaps the two positions, never duplicates it.
                slots[i] = slots[slot]
                break
    slots[slot] = new_item
    return state


def remove(pages, page, slot):
    return put(pages, page, slot, None)


def rename(pages, page, slot, label):
    state = normalize_pages(pages)
    if not valid_slot(page, slot):
        return state
    item = state[page]["tiles"][slot]
    if item is None:
        return state
    item.pop("label", None)
    label = safe_name(label, "")
    if label:
        item["label"] = label
    return state


def rename_page(pages, page, name):
    state = normalize_pages(pages)
    if type(page) is int and 0 <= page < PAGE_COUNT:
        state[page]["name"] = safe_name(name, PAGE_TITLES[page])
    return state


def move(pages, origin_page, origin_slot, dest_page, dest_slot):
    """Swap references, never duplicate or delete a note/command/shortcut."""
    state = normalize_pages(pages)
    if not valid_slot(origin_page, origin_slot) or not valid_slot(dest_page, dest_slot):
        return state
    a = state[origin_page]["tiles"]
    b = state[dest_page]["tiles"]
    a[origin_slot], b[dest_slot] = b[dest_slot], a[origin_slot]
    return state


def valid_slot(page, slot):
    return (type(page) is int and 0 <= page < PAGE_COUNT and
            type(slot) is int and 0 <= slot < SLOT_COUNT)


def lookup(tile, data, commands, visible_tabs):
    """Resolve a live tile without ever substituting a different saved item.

    Returns visible status with no side effects. Hidden tools or deleted IDs
    stay stored but render as disabled tiles until restored/replaced.
    """
    item = clean_tile(tile)
    if item is None:
        return {"status": "empty", "title": "Add", "detail": "Choose item",
                "icon": "+"}
    kind, ident = item["kind"], item["id"]
    title, detail = "", ""
    destination = {"tool": ident, "command": "commands", "template": "commands",
                   "note": "notes", "shortcut": "links"}[kind]
    visible = set(visible_tabs)
    if destination not in visible:
        status = "hidden"
        detail = "Menu hidden"
    else:
        status = "ready"
    record = None
    if kind == "tool":
        title, detail = TOOL_NAMES.get(ident, "Tool"), "Open tool"
    elif kind in ("command", "template"):
        record = next((r for r in commands if isinstance(r, dict) and r.get("id") == ident), None)
        title = str(record.get("description") or record.get("machine") or "Command") if record else "Missing command"
        detail = "Fill template" if kind == "template" else ("Copy CLI" if item.get("action") == "copy" else "Open CLI")
        if record is None:
            status, detail = "missing", "Command deleted"
        elif kind == "template" and smart.template_state(record) != "configured":
            status, detail = "needs_review", "Review template"
    elif kind == "note":
        record = next((r for r in data.get("notes", []) if isinstance(r, dict) and r.get("id") == ident), None)
        title = str(record.get("title") or "Untitled note") if record else "Missing note"
        detail = "Open note" if record else "Note deleted"
        if record is None:
            status = "missing"
    elif kind == "shortcut":
        record = next((r for r in data.get("links", []) if isinstance(r, dict) and r.get("id") == ident), None)
        title = str(record.get("title") or "Shortcut") if record else "Missing shortcut"
        detail = "Open shortcut" if record else "Shortcut deleted"
        if record is None:
            status = "missing"
    if status == "hidden":
        detail = "Menu hidden"
    title = item.get("label") or title
    return {"status": status, "title": title[:35], "detail": detail,
            "icon": KIND_ICONS[kind], "kind": kind, "id": ident,
            "destination": destination, "action": item.get("action", "open")}


def candidates(data, commands, enabled, kind, query="", limit=100):
    """Searchable, bounded local picker; nothing is executed or auto-selected."""
    if kind not in KINDS:
        return []
    allowed = set(enabled)
    target = {"tool": None, "command": "commands", "template": "commands",
              "note": "notes", "shortcut": "links"}[kind]
    if target is not None and target not in allowed:
        return []
    entries = []
    if kind == "tool":
        for key, label in TOOL_NAMES.items():
            if key in allowed:
                entries.append(({"kind": kind, "id": key}, label, "Pocket menu"))
    elif kind in ("command", "template"):
        for row in commands:
            if not isinstance(row, dict) or not isinstance(row.get("id"), str):
                continue
            if kind == "template" and smart.template_state(row) != "configured":
                continue
            title = str(row.get("description") or row.get("command") or "Command")
            entries.append(({"kind": kind, "id": row["id"]}, title,
                            str(row.get("machine", "")) + " · " +
                            str(row.get("command", ""))[:60]))
    elif kind == "note":
        for row in data.get("notes", []):
            if isinstance(row, dict) and isinstance(row.get("id"), str):
                entries.append(({"kind": kind, "id": row["id"]},
                                str(row.get("title") or "Untitled note"), "Saved note"))
    else:
        for row in data.get("links", []):
            if isinstance(row, dict) and isinstance(row.get("id"), str):
                entries.append(({"kind": kind, "id": row["id"]},
                                str(row.get("title") or "Shortcut"),
                                str(row.get("kind", "url")).upper()))
    tokens = ch.normalize(query).split()
    found = []
    for tile, title, detail in entries:
        text = ch.normalize(title + " " + detail)
        if all(term in text for term in tokens):
            found.append({"tile": tile, "title": title[:110], "detail": detail[:100]})
            if len(found) >= max(1, min(250, limit)):
                break
    return found
