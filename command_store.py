"""Editable single-file Pocket command library with manual backups.

The commands.json document is the only command reference library. Notes, settings
and command favorites continue to be stored separately in app data.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import tempfile


def resolve_library(install_dir: Path, appdata_dir: Path, bundle_dir: Path) -> Path:
    """Use one writable sidecar or user-data file, never a frozen EXE resource.

    Legacy ZIP uploads and bundled data can seed the sidecar once; the original
    source is preserved. If the install directory is not writable, use AppData.
    """
    install_dir = Path(install_dir)
    appdata_dir = Path(appdata_dir)
    bundle_dir = Path(bundle_dir)
    sidecar = install_dir / "commands" / "commands.json"
    appdata = appdata_dir / "commands.json"
    if sidecar.is_file():
        return sidecar
    if appdata.is_file():
        return appdata
    candidates = (
        install_dir / "commands.json",
        install_dir / "Pocket_Commands_One_Library" / "commands" / "commands.json",
        bundle_dir / "commands" / "commands.json",
        bundle_dir / "commands" / "example_commands.json",
    )
    source = next((p for p in candidates if p.is_file()), None)
    if source is None:
        return sidecar  # No library found: don't silently invent a replacement.
    for target in (sidecar, appdata):
        if source.resolve() == target.resolve():
            return target
        created = False
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            with source.open("rb") as stream, target.open("xb") as output:
                created = True
                shutil.copyfileobj(stream, output)
                output.flush()
                os.fsync(output.fileno())
            return target
        except FileExistsError:
            return target
        except OSError:
            if created:
                try:
                    target.unlink()
                except OSError:
                    pass
            continue
    raise OSError("Cannot create a writable commands.json in the application or AppData directory")


def read_document(path: Path) -> dict:
    """Fail rather than overwrite corrupt or missing reference data."""
    path = Path(path)
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(doc, dict) or not isinstance(doc.get("commands"), list):
        raise ValueError("commands.json must contain an object with a commands list")
    ids = set()
    for row in doc["commands"]:
        if not isinstance(row, dict) or any(not isinstance(row.get(k), str) for k in
                                            ("id", "machine", "category", "description", "command")):
            raise ValueError("commands.json contains a malformed command entry")
        if not row["id"] or row["id"] in ids:
            raise ValueError("commands.json contains duplicate or empty command IDs")
        ids.add(row["id"])
    return doc


def _atomic_write(path: Path, doc: dict) -> Path:
    """Replace commands.json atomically, WITHOUT making any automatic backup."""
    path = Path(path)
    original = path.stat()
    encoded = (json.dumps(doc, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    temp_name = None
    try:
        with tempfile.NamedTemporaryFile(mode="wb", prefix=".commands-", suffix=".tmp",
                                         dir=path.parent, delete=False) as out:
            temp_name = out.name
            out.write(encoded)
            out.flush()
            os.fsync(out.fileno())
        try:
            os.chmod(temp_name, original.st_mode)
        except OSError:
            pass
        os.replace(temp_name, path)
    finally:
        if temp_name and os.path.exists(temp_name):
            os.unlink(temp_name)
    return path


def create_backup(path: Path) -> Path:
    """User-triggered only: save a timestamped copy of the current valid library."""
    path = Path(path)
    read_document(path)
    backup_dir = path.parent / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
    backup = backup_dir / f"commands-{stamp}.json"
    with path.open("rb") as source, backup.open("xb") as target:
        shutil.copyfileobj(source, target)
        target.flush()
        os.fsync(target.fileno())
    return backup


def restore_backup(path: Path, backup: Path) -> Path:
    """Restore a manually selected valid backup with NO implicit extra backup."""
    path, backup = Path(path), Path(backup)
    if path.resolve() == backup.resolve():
        raise ValueError("Choose a backup file, not the active commands.json.")
    read_document(path)  # Never silently overwrite a corrupt active file.
    snapshot = read_document(backup)
    return _atomic_write(path, snapshot)


def _find(doc: dict, command_id: str) -> int:
    for index, row in enumerate(doc["commands"]):
        if row["id"] == command_id:
            return index
    raise KeyError("Command no longer exists in commands.json")


def _check_expected(row: dict, expected: dict | None):
    if expected is None:
        return
    for key in ("machine", "category", "description", "command"):
        if row.get(key) != expected.get(key):
            raise ValueError("The command was changed outside Pocket. Reload before editing it.")


def save_command(path: Path, entry: dict, *, original: dict | None = None) -> Path:
    """Add or edit a command while preserving its ID and other JSON metadata."""
    doc = read_document(path)
    if original is None:
        if any(row["id"] == entry["id"] for row in doc["commands"]):
            raise ValueError("This command ID already exists")
        doc["commands"].append(dict(entry))
    else:
        index = _find(doc, original["id"])
        _check_expected(doc["commands"][index], original)
        saved = dict(doc["commands"][index])
        saved.update({k: entry[k] for k in ("machine", "category", "description", "command")})
        doc["commands"][index] = saved
    return _atomic_write(path, doc)


def save_template(path: Path, entry: dict, template: dict | None) -> Path:
    """Explicit user action: configure/remove one template, no automatic backup.

    Optimistic comparison prevents overwriting a different command's edits.
    Metadata remains next to the original row and is included in manual backups.
    """
    from smart_templates import validate_template
    doc = read_document(path)
    index = _find(doc, entry["id"])
    current = doc["commands"][index]
    _check_expected(current, entry)
    if current.get("template") != entry.get("template"):
        raise ValueError("This template was edited elsewhere. Reload before saving.")
    updated = dict(current)
    if template is None:
        updated.pop("template", None)
    else:
        updated["template"] = validate_template(template, current["command"])
    doc["commands"][index] = updated
    return _atomic_write(path, doc)


def delete_command(path: Path, entry: dict) -> Path:
    doc = read_document(path)
    index = _find(doc, entry["id"])
    _check_expected(doc["commands"][index], entry)
    del doc["commands"][index]
    return _atomic_write(path, doc)


def migrate_custom(path: Path, entries: list[dict]) -> tuple[int, Path | None]:
    """Idempotently merge legacy data.json custom commands. Caller clears them only on success."""
    doc = read_document(path)
    existing_ids = {row["id"] for row in doc["commands"]}
    existing_syntax = {(row["machine"].casefold(), row["command"].strip().casefold())
                       for row in doc["commands"]}
    added = 0
    for entry in entries:
        key = (entry["machine"].casefold(), entry["command"].strip().casefold())
        if entry["id"] in existing_ids or key in existing_syntax:
            continue
        doc["commands"].append(dict(entry))
        existing_ids.add(entry["id"])
        existing_syntax.add(key)
        added += 1
    if added:
        return added, _atomic_write(path, doc)
    return 0, None
