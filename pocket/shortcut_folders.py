"""Persistent, one-level collapsible shortcut folders and deterministic reordering.

An organizer folder is ONLY a Pocket UI category: it never changes filesystem
directories and never launches the folder-type shortcut. All existing links
retain their IDs, targets, types and original order during migration.
"""
from __future__ import annotations

from uuid import uuid4

MAX_FOLDERS = 100
MAX_TITLE = 64


def clean_title(raw):
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError("Enter a name for the Pocket folder.")
    title = " ".join(raw.split())
    if len(title) > MAX_TITLE:
        raise ValueError(f"Folder names must be {MAX_TITLE} characters or shorter.")
    return title


def link_key(ident):
    return "l:" + ident


def folder_key(ident):
    return "f:" + ident


def normalize(raw, links):
    """Sanitize order/children and collect unassigned items without data loss."""
    if not isinstance(raw, dict):
        raw = {}
    folders = []
    folder_ids = set()
    for item in raw.get("folders", []) if isinstance(raw.get("folders"), list) else []:
        if not isinstance(item, dict):
            continue
        ident = item.get("id")
        title = item.get("title")
        if (not isinstance(ident, str) or not ident or len(ident) > 96
                or ident in folder_ids or len(folders) >= MAX_FOLDERS):
            continue
        try:
            title = clean_title(title)
        except ValueError:
            continue
        folder_ids.add(ident)
        folders.append({"id": ident, "title": title, "expanded": item.get("expanded") is not False})

    valid_links = []
    link_ids = set()
    for link in links:
        ident = link.get("id") if isinstance(link, dict) else None
        if isinstance(ident, str) and ident and ident not in link_ids:
            valid_links.append(ident)
            link_ids.add(ident)

    seen_links = set()
    children = {fid: [] for fid in folder_ids}
    raw_children = raw.get("children")
    if not isinstance(raw_children, dict):
        raw_children = {}
    # Honor saved children before root entries, unless explicitly ungrouped.
    # Root ownership wins when a valid root link is listed there.
    raw_root = raw.get("root")
    if not isinstance(raw_root, list):
        raw_root = []
    root_owned = {key[2:] for key in raw_root
                  if isinstance(key, str) and key.startswith("l:") and key[2:] in link_ids}
    for folder in folders:
        fid = folder["id"]
        values = raw_children.get(fid, [])
        for lid in values if isinstance(values, list) else []:
            if (isinstance(lid, str) and lid in link_ids and
                    lid not in seen_links and lid not in root_owned):
                children[fid].append(lid)
                seen_links.add(lid)

    root = []
    seen_folders = set()
    for key in raw_root:
        if not isinstance(key, str):
            continue
        if key.startswith("f:"):
            fid = key[2:]
            if fid in folder_ids and fid not in seen_folders:
                root.append(key)
                seen_folders.add(fid)
        elif key.startswith("l:"):
            lid = key[2:]
            if lid in link_ids and lid not in seen_links:
                root.append(key)
                seen_links.add(lid)
    for folder in folders:
        fid = folder["id"]
        if fid not in seen_folders:
            root.append(folder_key(fid))
    for lid in valid_links:
        if lid not in seen_links:
            root.append(link_key(lid))
            seen_links.add(lid)
    return {"folders": folders, "root": root, "children": children}


def _folder(layout, ident):
    return next((item for item in layout["folders"] if item["id"] == ident), None)


def add_folder(layout, title):
    title = clean_title(title)
    if len(layout["folders"]) >= MAX_FOLDERS:
        raise ValueError("Too many Pocket folders.")
    ident = uuid4().hex
    layout["folders"].append({"id": ident, "title": title, "expanded": True})
    layout["root"].append(folder_key(ident))
    layout["children"][ident] = []
    return ident


def rename_folder(layout, ident, title):
    found = _folder(layout, ident)
    if found is None:
        return False
    title = clean_title(title)
    if found["title"] == title:
        return False
    found["title"] = title
    return True


def set_expanded(layout, ident, expanded):
    found = _folder(layout, ident)
    if found is None or found["expanded"] is bool(expanded):
        return False
    found["expanded"] = bool(expanded)
    return True


def delete_folder(layout, ident):
    """Flatten its children at the former header position; never delete links."""
    folder = _folder(layout, ident)
    if folder is None:
        return False
    key = folder_key(ident)
    index = layout["root"].index(key)
    layout["root"][index:index + 1] = [
        link_key(lid) for lid in layout["children"].get(ident, [])]
    layout["folders"] = [item for item in layout["folders"] if item["id"] != ident]
    layout["children"].pop(ident, None)
    return True


def add_link(layout, ident, *, group=None):
    """New shortcuts are unfiled by default, never silently placed in a folder."""
    key = link_key(ident)
    if key in layout["root"] or any(ident in child for child in layout["children"].values()):
        return False
    if group is not None and _folder(layout, group) is not None:
        layout["children"][group].insert(0, ident)
        set_expanded(layout, group, True)
    else:
        layout["root"].insert(0, key)
    return True


def remove_link(layout, ident):
    key = link_key(ident)
    removed = False
    if key in layout["root"]:
        layout["root"].remove(key)
        removed = True
    for ids in layout["children"].values():
        if ident in ids:
            ids.remove(ident)
            removed = True
    return removed


def link_folder(layout, ident):
    for fid, children in layout["children"].items():
        if ident in children:
            return fid
    return None


def move(layout, source, target, position="before"):
    """Move a folder or link before/after any root row, or into a folder.

    Keys: "f:<folder-id>", "l:<link-id>" or target="root".
    A folder cannot be nested. A shortcut can enter/leave folders or be
    positioned relative to another shortcut, preserving deterministic order.
    Invalid requests leave data untouched.
    """
    if not isinstance(source, str) or not source.startswith(("l:", "f:")):
        return False
    is_folder = source.startswith("f:")
    source_id = source[2:]
    origin = None
    if source in layout["root"]:
        origin = layout["root"]
    elif not is_folder:
        fid = link_folder(layout, source_id)
        if fid is not None:
            origin = layout["children"][fid]
    if origin is None:
        return False
    origin_value = source if origin is layout["root"] else source_id
    if target == "root" and not is_folder:
        dest = layout["root"]
        insert = 0
    elif isinstance(target, str) and target.startswith("f:"):
        fid = target[2:]
        if _folder(layout, fid) is None or source == target:
            return False
        if position == "inside" and not is_folder:
            dest = layout["children"][fid]
            insert = len(dest)
        elif position in ("before", "after"):
            dest = layout["root"]
            insert = dest.index(target) + (position == "after")
        else:
            return False
    elif isinstance(target, str) and target.startswith("l:") and source != target:
        tid = target[2:]
        if target in layout["root"]:
            dest = layout["root"]
            lookup = target
        else:
            fid = link_folder(layout, tid)
            if fid is None or is_folder:
                return False
            dest = layout["children"][fid]
            lookup = tid
        if position not in ("before", "after"):
            return False
        insert = dest.index(lookup) + (position == "after")
    else:
        return False
    if is_folder and dest is not layout["root"]:
        return False
    output = source if dest is layout["root"] else source_id
    if origin is dest:
        old = origin.index(origin_value)
        if old < insert:
            insert -= 1
        if old == insert:
            return False
    origin.remove(origin_value)
    dest.insert(insert, output)
    if dest is not layout["root"]:
        fid = next(fid for fid, values in layout["children"].items() if values is dest)
        set_expanded(layout, fid, True)
    return True


def visible_rows(layout, links, *, query="", kind="all"):
    """Produce presentation rows, showing collapsed folders without card content.

    Search temporarily expands matching folder items (without saving the
    expansion state); folder-title matching includes all matching kinds.
    """
    by_id = {link["id"]: link for link in links}
    folders = {item["id"]: item for item in layout["folders"]}
    query = query.strip().casefold()
    def allowed(link):
        if kind != "all" and link.get("kind", "url") != kind:
            return False
        return (not query or query in link.get("title", "").casefold()
                or query in link.get("url", "").casefold())
    output = []
    for key in layout["root"]:
        if key.startswith("l:"):
            link = by_id.get(key[2:])
            if link is not None and allowed(link):
                output.append({"type": "link", "link": link})
        elif key.startswith("f:"):
            fid = key[2:]
            folder = folders.get(fid)
            if folder is None:
                continue
            title_hit = bool(query and query in folder["title"].casefold())
            children = [by_id[lid] for lid in layout["children"].get(fid, []) if lid in by_id]
            showing = [link for link in children
                       if (kind == "all" or link.get("kind", "url") == kind)
                       and (not query or title_hit or allowed(link))]
            # In unfiltered view, keep even empty/collapsed folders visible.
            if (query or kind != "all") and not showing and not title_hit:
                continue
            output.append({"type": "folder", "folder": folder, "links": showing,
                           "expanded": bool(query) or folder["expanded"],
                           "total": len(children)})
    return output
