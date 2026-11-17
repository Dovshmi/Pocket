"""Offline, selective, versioned Pocket backups.

The archive is never extracted: every name, size and SHA-256 is validated
before any data is applied. Quick Slot contents and Quick Slot settings are
deliberately excluded, including from full/settings backups.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path, PurePosixPath
import json
import os
import re
import tempfile
from zipfile import ZipFile, ZIP_DEFLATED, BadZipFile

from . import clipboard_database as cdb
from . import command_store as cs
from . import data_recovery
from . import shortcut_folders

VERSION = 1
CATEGORIES = ("notes", "links", "cli", "settings", "clipboard_text", "clipboard_images")
RECOMMENDED = ("notes", "links", "cli", "settings")
LABELS = {
    "notes": "Notes and reminders",
    "links": "Links and folders",
    "cli": "CLI commands, templates and favorites",
    "settings": "Settings and keyboard shortcuts (not Quick Slots)",
    "clipboard_text": "Clipboard DATABASE: text history",
    "clipboard_images": "Clipboard DATABASE: saved screenshots",
}
MAX_ARCHIVE = 350 * 1024 * 1024
MAX_MEMBER = 110 * 1024 * 1024
MAX_FILES = 3500
MAX_JSON = 100 * 1024 * 1024
QUICK_SLOT_KEYS = frozenset(("quick_slots_enabled",
                             "quick_slots_paste_prefix", "quick_slots_copy_prefix",
                             "quick_slots_prefix"))
_IMAGE_NAME = re.compile(
    r"\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}(?:-\d{6})?_[0-9a-f]{32}\.png"
)
_IMAGE_SIG = b"\x89PNG\r\n\x1a\n"


def select_categories(selected):
    if not isinstance(selected, (set, tuple, list)):
        raise ValueError("Select at least one category")
    categories = tuple(group for group in CATEGORIES if group in selected)
    if not categories or len(set(selected) - set(CATEGORIES)):
        raise ValueError("Invalid or empty Pocket backup selection")
    return categories


def filtered_settings(raw):
    if not isinstance(raw, dict):
        raise ValueError("Invalid settings in backup")
    return {key: deepcopy(value) for key, value in raw.items()
            if key not in QUICK_SLOT_KEYS}


def _encode(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")


def _items(value, field, required):
    if not isinstance(value, list) or len(value) > 100_000:
        raise ValueError("Invalid " + field + " list")
    ids = set()
    for item in value:
        if not isinstance(item, dict) or any(
                not isinstance(item.get(k), str) for k in required):
            raise ValueError("Malformed " + field + " entry")
        identifier = item["id"]
        if not identifier or len(identifier) > 150 or identifier in ids:
            raise ValueError("Duplicate or invalid " + field + " ID")
        ids.add(identifier)
    return deepcopy(value)


def _valid_commands(doc):
    if not isinstance(doc, dict) or not isinstance(doc.get("commands"), list):
        raise ValueError("Invalid CLI command document")
    _items(doc["commands"], "CLI", ("id", "machine", "category",
                                     "description", "command"))
    return deepcopy(doc)


def _get_clipboard(profile_dir, kind):
    database = cdb.ClipboardDatabase(profile_dir)
    if kind == "text":
        return {day: database.load_text(day) for day in database.days("text")}
    result = {}
    folder = database.image_dir
    if folder.is_symlink():
        raise ValueError("Clipboard image directory is a symbolic link")
    if folder.is_dir():
        for file in folder.iterdir():
            if not _IMAGE_NAME.fullmatch(file.name) or not file.is_file():
                continue
            if file.is_symlink():
                raise ValueError("Clipboard image cannot be a symbolic link")
            content = file.read_bytes()
            if not content.startswith(_IMAGE_SIG) or len(content) > 15 * 1024 * 1024:
                raise ValueError("Invalid clipboard image " + file.name)
            result[file.name] = content
    return result


def _archive_data(profile, groups, commands_path, profile_dir):
    data = {}
    media = {}
    if "notes" in groups:
        data["notes"] = {"notes": _items(profile["notes"], "notes",
                                        ("id", "title", "body")),
                         "active_note": profile.get("active_note")}
    if "links" in groups:
        data["links"] = {"links": _items(profile["links"], "links",
                                        ("id", "title", "url")),
                         "shortcut_folders": deepcopy(profile.get("shortcut_folders"))}
    if "settings" in groups:
        data["settings"] = {
            "settings": filtered_settings(profile.get("settings", {})),
            "theme": profile.get("theme", "blue"),
            "hotkey": deepcopy(profile.get("hotkey")),
            "convert_hotkey": deepcopy(profile.get("convert_hotkey")),
            "extra_mini_pages": deepcopy(profile.get("extra_mini_pages")),
        }
    if "cli" in groups:
        if not commands_path:
            raise ValueError("CLI library is unavailable on this machine")
        data["cli"] = {
            "command_state": deepcopy(profile.get("command_state", {})),
            "custom_commands": deepcopy(profile.get("custom_commands", [])),
        }
        media["cli/commands.json"] = _encode(
            cs.read_document(Path(commands_path)))
    if "clipboard_text" in groups:
        data["clipboard_text"] = _get_clipboard(profile_dir, "text")
    if "clipboard_images" in groups:
        images = _get_clipboard(profile_dir, "images")
        data["clipboard_images"] = sorted(images)
        for name, binary in images.items():
            media["clipboard/images/" + name] = binary
    return data, media


def make_backup(destination, profile, *, commands_path=None,
                profile_dir=None, selected=RECOMMENDED):
    """Write a validated, single ZIP backup; no implicit scheduled backups."""
    groups = select_categories(selected)
    data_recovery.validate_payload(profile)
    root = Path(profile_dir) if profile_dir else Path.cwd()
    payload, media = _archive_data(profile, groups, commands_path, root)
    media["payload.json"] = _encode(payload)
    if len(media) > MAX_FILES or sum(len(b) for b in media.values()) > MAX_ARCHIVE:
        raise ValueError("Selected backup is too large")
    manifest = {
        "format": "PocketBackup", "version": VERSION,
        "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "categories": list(groups),
        "files": {name: {"size": len(b), "sha256": sha256(b).hexdigest()}
                  for name, b in media.items()},
    }
    target = Path(destination)
    target.parent.mkdir(parents=True, exist_ok=True)
    staged = None
    try:
        with tempfile.NamedTemporaryFile(prefix=".pocket-backup-", suffix=".tmp",
                                         dir=target.parent, delete=False) as tmp:
            staged = Path(tmp.name)
        with ZipFile(staged, mode="w", compression=ZIP_DEFLATED,
                     compresslevel=6, allowZip64=True) as archive:
            archive.writestr("manifest.json", _encode(manifest))
            for name, blob in media.items():
                archive.writestr(name, blob)
        # Verify what was written before replacing any existing backup.
        read_backup(staged)
        os.replace(staged, target)
        staged = None
    finally:
        if staged is not None:
            staged.unlink(missing_ok=True)
    return target


def read_backup(source):
    """Reject ZIP-slip, bombs, duplicates, tampered bytes and unknown versions."""
    try:
        with ZipFile(source) as archive:
            infos = archive.infolist()
            if len(infos) > MAX_FILES + 2:
                raise ValueError("Backup contains too many entries")
            names = [i.filename for i in infos]
            if len(names) != len(set(names)) or "manifest.json" not in names:
                raise ValueError("Invalid backup member list")
            total = 0
            for entry in infos:
                name = entry.filename
                path = PurePosixPath(name)
                if (not name or "\\" in name or path.is_absolute()
                        or ".." in path.parts or name.endswith("/")
                        or entry.is_dir()
                        or (entry.external_attr >> 16) & 0o170000 == 0o120000):
                    raise ValueError("Unsafe path in Pocket backup")
                if entry.file_size > MAX_MEMBER or entry.file_size < 0:
                    raise ValueError("Backup member is too large")
                total += entry.file_size
                if total > MAX_ARCHIVE:
                    raise ValueError("Backup expands beyond size limit")
            raw_manifest = archive.read("manifest.json")
            if len(raw_manifest) > 50_000:
                raise ValueError("Invalid manifest")
            manifest = json.loads(raw_manifest)
            if (not isinstance(manifest, dict)
                    or manifest.get("format") != "PocketBackup"
                    or manifest.get("version") != VERSION):
                raise ValueError("Unsupported Pocket backup version")
            categories = select_categories(manifest.get("categories"))
            if list(categories) != manifest["categories"]:
                raise ValueError("Invalid category ordering")
            checks = manifest.get("files")
            if not isinstance(checks, dict) or set(names) != (set(checks) | {"manifest.json"}):
                raise ValueError("Unexpected or missing backup files")
            files = {}
            for name, expected in checks.items():
                if not isinstance(expected, dict):
                    raise ValueError("Malformed backup checksum")
                raw = archive.read(name)
                if (len(raw) != expected.get("size") or
                        sha256(raw).hexdigest() != expected.get("sha256")):
                    raise ValueError("Backup failed integrity verification")
                files[name] = raw
    except (BadZipFile, OSError, KeyError, UnicodeDecodeError,
            json.JSONDecodeError) as exc:
        raise ValueError("Not a valid Pocket backup: " + str(exc)) from exc
    if "payload.json" not in files or len(files["payload.json"]) > MAX_JSON:
        raise ValueError("Backup payload is missing or too large")
    try:
        payload = json.loads(files.pop("payload.json"))
    except (UnicodeError, ValueError) as exc:
        raise ValueError("Malformed backup payload") from exc
    if not isinstance(payload, dict) or set(payload) != set(categories):
        raise ValueError("Backup categories do not match its contents")
    for category in categories:
        group = payload[category]
        if category == "notes":
            if not isinstance(group, dict) or "notes" not in group:
                raise ValueError("Invalid notes backup")
            _items(group["notes"], "notes", ("id", "title", "body"))
        elif category == "links":
            if not isinstance(group, dict) or "links" not in group:
                raise ValueError("Invalid links backup")
            _items(group["links"], "links", ("id", "title", "url"))
        elif category == "settings":
            if not isinstance(group, dict):
                raise ValueError("Invalid settings backup")
            group["settings"] = filtered_settings(group.get("settings", {}))
        elif category == "cli":
            if not isinstance(group, dict) or "cli/commands.json" not in files:
                raise ValueError("CLI library missing from backup")
            _valid_commands(json.loads(files["cli/commands.json"]))
        elif category == "clipboard_text":
            if not isinstance(group, dict) or len(group) > 3660:
                raise ValueError("Invalid clipboard text backup")
            for day, rows in group.items():
                if not cdb.valid_day(day):
                    raise ValueError("Invalid clipboard date")
                if not isinstance(rows, list):
                    raise ValueError("Invalid clipboard entries")
                for row in rows:
                    cdb._check_record(row)
        elif category == "clipboard_images":
            if not isinstance(group, list) or len(group) > MAX_FILES:
                raise ValueError("Invalid clipboard image index")
            for name in group:
                if not isinstance(name, str) or not _IMAGE_NAME.fullmatch(name):
                    raise ValueError("Unsafe clipboard image name")
                raw = files.get("clipboard/images/" + name)
                if raw is None or not raw.startswith(_IMAGE_SIG) or len(raw) > 15*1024*1024:
                    raise ValueError("Invalid clipboard screenshot")
    expected_files = {"cli/commands.json"} if "cli" in categories else set()
    if "clipboard_images" in categories:
        expected_files.update("clipboard/images/" + n
                              for n in payload["clipboard_images"])
    if set(files) != expected_files:
        raise ValueError("Backup contains unexpected content")
    return {"manifest": manifest, "payload": payload, "files": files}


def _merge_items(existing, incoming):
    """Non-destructive: collisions keep the local row and report conflicts."""
    old = _items(existing, "existing", ("id",))
    fresh = _items(incoming, "incoming", ("id",))
    ids = {row["id"]: row for row in old}
    added = same = conflicts = 0
    for row in fresh:
        old_row = ids.get(row["id"])
        if old_row is None:
            old.append(row)
            ids[row["id"]] = row
            added += 1
        elif old_row == row:
            same += 1
        else:
            conflicts += 1
    return old, {"added": added, "unchanged": same, "conflicts": conflicts}


def plan_restore(bundle, current, *, selected, mode="merge", current_commands=None):
    """Pure preflight for UI and tests; no writes, never restores Quick Slots."""
    groups = select_categories(selected)
    if not set(groups).issubset(bundle["payload"]):
        raise ValueError("Backup does not contain the selected categories")
    if mode not in ("merge", "replace"):
        raise ValueError("Choose Merge or Replace")
    profile = deepcopy(current)
    data_recovery.validate_payload(profile)
    report = {}
    for group in groups:
        incoming = bundle["payload"][group]
        if group == "notes":
            existing = profile["notes"]
            source = _items(incoming["notes"], "notes", ("id", "title", "body"))
            updated, counts = (_merge_items(existing, source) if mode == "merge"
                               else (source, {"added": len(source), "unchanged": 0,
                                              "conflicts": 0}))
            if not updated:
                raise ValueError("Cannot restore an empty notes list")
            profile["notes"] = updated
            old_active = profile.get("active_note")
            wanted_active = incoming.get("active_note")
            profile["active_note"] = (old_active if mode == "merge" and
                old_active in {n["id"] for n in updated} else
                wanted_active if wanted_active in {n["id"] for n in updated}
                else updated[0]["id"])
            report[group] = counts
        elif group == "links":
            source = _items(incoming["links"], "links", ("id", "title", "url"))
            updated, counts = (_merge_items(profile["links"], source)
                               if mode == "merge" else
                               (source, {"added": len(source), "unchanged": 0, "conflicts": 0}))
            profile["links"] = updated
            if mode == "replace":
                profile["shortcut_folders"] = shortcut_folders.normalize(
                    incoming.get("shortcut_folders"), updated)
            else:
                # Existing folder ownership is authoritative. Imported folders
                # with distinct IDs are appended, and new links are placed in
                # the matching imported folder when possible.
                layout = deepcopy(profile.get("shortcut_folders") or {})
                other = shortcut_folders.normalize(
                    incoming.get("shortcut_folders"), source)
                layout = shortcut_folders.normalize(layout, current["links"])
                old_folders = {f["id"] for f in layout["folders"]}
                old_links = {l["id"] for l in current["links"]}
                for folder in other["folders"]:
                    if folder["id"] not in old_folders:
                        layout["folders"].append(folder)
                        layout["root"].append("f:" + folder["id"])
                        layout["children"][folder["id"]] = [
                            lid for lid in other["children"].get(folder["id"], [])
                            if lid not in old_links]
                        old_folders.add(folder["id"])
                assigned = {lid for members in layout["children"].values()
                            for lid in members}
                for key in other["root"]:
                    if key.startswith("l:") and key[2:] not in old_links:
                        layout["root"].append(key)
                        assigned.add(key[2:])
                profile["shortcut_folders"] = shortcut_folders.normalize(layout, updated)
            report[group] = counts
        elif group == "settings":
            base = deepcopy(profile.get("settings", {}))
            imported = filtered_settings(incoming.get("settings", {}))
            # Applying settings means applying the selected settings values,
            # even in Merge; Quick Slot preferences remain local.
            base.update(imported)
            profile["settings"] = base
            for key in ("theme", "hotkey", "convert_hotkey", "extra_mini_pages"):
                if key in incoming and incoming[key] is not None:
                    profile[key] = deepcopy(incoming[key])
            report[group] = {"applied": len(imported), "conflicts": 0}
        elif group == "cli":
            imported = _valid_commands(json.loads(bundle["files"]["cli/commands.json"]))
            existing = _valid_commands(current_commands or {"commands": []})
            incoming_commands = imported["commands"]
            if mode == "replace":
                doc = imported
                counts = {"added": len(incoming_commands), "unchanged": 0,
                          "conflicts": 0}
            else:
                combined, counts = _merge_items(existing["commands"], incoming_commands)
                doc = deepcopy(existing)
                doc["commands"] = combined
            profile["_restore_cli_document"] = doc
            if mode == "replace":
                profile["command_state"] = deepcopy(incoming.get("command_state", {}))
                profile["custom_commands"] = deepcopy(incoming.get("custom_commands", []))
            else:
                profile["command_state"] = deepcopy({
                    **current.get("command_state", {}),
                    "favorites": list(dict.fromkeys(
                        current.get("command_state", {}).get("favorites", []) +
                        incoming.get("command_state", {}).get("favorites", []))),
                })
                merged_custom, custom_report = _merge_items(
                    current.get("custom_commands", []),
                    incoming.get("custom_commands", []))
                profile["custom_commands"] = merged_custom
                counts["conflicts"] += custom_report["conflicts"]
            report[group] = counts
        elif group in ("clipboard_text", "clipboard_images"):
            report[group] = {"items": sum(len(v) for v in incoming.values())
                             if isinstance(incoming, dict) else len(incoming),
                             "conflicts": 0}
    profile["clipboard_slots"] = deepcopy(current.get("clipboard_slots", {}))
    # The preview CLI document is intentionally not part of data.json.
    cli_document = profile.pop("_restore_cli_document", None)
    data_recovery.validate_payload(profile)
    return {"profile": profile, "commands": cli_document,
            "report": report, "groups": groups, "mode": mode}


def apply_restore(bundle, current, *, selected, mode, profile_path,
                  commands_path=None):
    """Validate, save a recovery ZIP, then apply only explicitly chosen data.

    A pre-restore ZIP is retained even if a later disk operation fails. This
    offers recovery from cross-file failures (not a cross-file atomic commit).
    The caller should close Pocket afterward to reload all preferences/hooks.
    """
    from . import clipboard_database as cdb
    root = Path(profile_path).parent
    cmds = cs.read_document(commands_path) if commands_path else None
    plan = plan_restore(bundle, current, selected=selected, mode=mode,
                        current_commands=cmds)
    if "cli" in plan["groups"] and not commands_path:
        raise ValueError("Cannot restore CLI without a writable commands library")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
    safety = root / "backups" / ("Pocket-before-restore-" + stamp + ".zip")
    safety_categories = tuple(x for x in plan["groups"] if x != "cli" or commands_path)
    make_backup(safety, current, commands_path=commands_path,
                profile_dir=root, selected=safety_categories)

    # All archive content and group-level profile changes are prevalidated.
    # Only regular, recognized database files may be changed.
    database = cdb.ClipboardDatabase(root)
    if "clipboard_text" in plan["groups"]:
        database.ensure_folders()
        for day, incoming in bundle["payload"]["clipboard_text"].items():
            if plan["mode"] == "merge":
                original = database.load_text(day)
                updated, _ = _merge_items(original, incoming)
            else:
                updated = incoming
            database.save_text(day, updated, days=0)
        if plan["mode"] == "replace":
            new_days = set(bundle["payload"]["clipboard_text"])
            for day in database.days("text"):
                if day not in new_days:
                    database.save_text(day, [], days=0)
    if "clipboard_images" in plan["groups"]:
        database.ensure_folders()
        wanted = set(bundle["payload"]["clipboard_images"])
        for name in wanted:
            target = database.image_dir / name
            content = bundle["files"]["clipboard/images/" + name]
            if target.exists() and target.read_bytes() != content and plan["mode"] == "merge":
                continue  # Keep the local conflicting screenshot.
            data_recovery._write_atomic(target, content)
        if plan["mode"] == "replace":
            for file in database.image_dir.iterdir():
                if (file.is_file() and not file.is_symlink() and
                        _IMAGE_NAME.fullmatch(file.name) and file.name not in wanted):
                    file.unlink()
    if plan["commands"] is not None:
        cs._atomic_write(Path(commands_path), plan["commands"])
    data_recovery.save_profile(Path(profile_path), plan["profile"])
    return safety, plan["report"]
