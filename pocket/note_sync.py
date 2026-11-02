"""Local Windows Notepad bridge for Pocket notes.

Persistent per-note working files make saved Notepad edits detectable. No network,
background service, or third-party watcher is required.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
import os
import uuid


def note_path(folder: Path, note_id: str) -> Path:
    """Opaque filename: never use titles or user-supplied path components."""
    if not isinstance(note_id, str) or len(note_id) != 32:
        raise ValueError("Invalid note identifier")
    try:
        int(note_id, 16)
    except ValueError as exc:
        raise ValueError("Invalid note identifier") from exc
    return folder / f"note_{note_id}.txt"


def read_text(path: Path) -> str:
    """Read Notepad UTF-8 files, including files with a UTF-8 BOM."""
    return path.read_text(encoding="utf-8-sig")


def write_text(path: Path, body: str) -> None:
    """Replace a working file atomically, keeping existing content on errors."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("w", encoding="utf-8-sig", newline="") as stream:
            stream.write(body)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def preserve_conflict(path: Path, external_text: str) -> Path:
    """Keep a recoverable external copy before Pocket overwrites a conflict."""
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    recovery = path.with_name(f"{path.stem}_notepad_conflict_{stamp}_{uuid.uuid4().hex[:6]}.txt")
    with recovery.open("x", encoding="utf-8-sig") as stream:
        stream.write(external_text)
    return recovery
