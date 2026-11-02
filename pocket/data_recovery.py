"""Guard Pocket's personal data.json without touching manual command backups.

A single rolling, validated *previous version* is retained as
data-recovery.json beside data.json. All writes are atomic and local.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import uuid


def snapshot_path(path: Path) -> Path:
    return Path(path).with_name("data-recovery.json")


def validate_payload(value) -> None:
    """Structural validation only: preserve legacy fields for load migrations."""
    if not isinstance(value, dict):
        raise ValueError("Pocket data must be a JSON object")
    for key in ("notes", "links"):
        if not isinstance(value.get(key), list):
            raise ValueError(f"Pocket data needs a {key} list")
    for item in value["notes"]:
        if not isinstance(item, dict) or any(
            not isinstance(item.get(field), str) for field in ("id", "title", "body")
        ):
            raise ValueError("Invalid note in Pocket data")
    for item in value["links"]:
        if not isinstance(item, dict) or any(
            not isinstance(item.get(field), str) for field in ("id", "title", "url")
        ):
            raise ValueError("Invalid shortcut in Pocket data")


def _write_atomic(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    staged = None
    try:
        with tempfile.NamedTemporaryFile(prefix=f".{path.stem}-", suffix=".tmp",
                                         dir=path.parent, delete=False) as stream:
            staged = Path(stream.name)
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(staged, path)
        staged = None
    finally:
        if staged is not None:
            try:
                staged.unlink()
            except FileNotFoundError:
                pass


def save_profile(path: Path, data: dict) -> None:
    """Validate, retain one last-good previous state, then replace atomically."""
    path = Path(path)
    validate_payload(data)
    content = (json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    if path.is_file():
        previous = path.read_bytes()
        if previous == content:
            return  # Don't churn disk or recovery snapshot if nothing changed.
        try:
            validate_payload(json.loads(previous))
        except (ValueError, TypeError, UnicodeError):
            # Never overwrite a usable last-good snapshot with damaged data.
            raise ValueError("Existing Pocket data is invalid; use recovery before saving")
        _write_atomic(snapshot_path(path), previous)
    _write_atomic(path, content)


def quarantine(path: Path) -> Path:
    """Preserve damaged data with an unpredictable unique name; never overwrite."""
    path = Path(path)
    archived = path.with_name(f"data-corrupt-{uuid.uuid4().hex}.json")
    path.rename(archived)  # Propagate failures; don't risk overwriting the original.
    return archived
