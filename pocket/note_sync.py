"""Local Windows Notepad bridge for Pocket notes.

Persistent per-note working files make saved Notepad edits detectable. No network,
background service, or third-party watcher is required.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
import os
import re
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


# Windows-friendly, readable names for new Notepad working files. The note ID
# remains the identity inside Pocket; the chosen filename is persisted in
# data.json so reopening the same note never creates an accidental copy.
_INVALID_WINDOWS_NAME = re.compile(r'[<>:"/\\|?*\x00-\x1f\x7f]')
_RESERVED_WINDOWS_NAMES = (
    {"CON", "PRN", "AUX", "NUL"} |
    {f"{kind}{number}" for kind in ("COM", "LPT") for number in (*range(1, 10), "¹", "²", "³")}
)


def _safe_title_stem(title: str) -> str:
    """Keep Hebrew/Unicode, while avoiding invalid or reserved Windows names."""
    stem = _INVALID_WINDOWS_NAME.sub("_", title if isinstance(title, str) else "")
    stem = stem.strip(" .")[:96].rstrip(" .") or "Untitled note"
    # A title already ending in .txt should not produce "Title.txt.txt".
    if stem.casefold().endswith(".txt"):
        stem = stem[:-4].rstrip(" .") or "Untitled note"
    if stem.split(".")[0].rstrip(" ").upper() in _RESERVED_WINDOWS_NAMES:
        stem = "_" + stem[:95]
    return stem


def _valid_saved_filename(filename) -> bool:
    """Stored filenames must be one safe .txt basename, never a path."""
    if not isinstance(filename, str) or not 5 <= len(filename) <= 240:
        return False
    if _INVALID_WINDOWS_NAME.search(filename) or filename != filename.strip(" ."):
        return False
    if not filename.casefold().endswith(".txt"):
        return False
    stem = filename[:-4]
    return bool(stem and stem not in (".", "..") and
                stem.split(".")[0].rstrip(" ").upper() not in _RESERVED_WINDOWS_NAMES)


def named_note_path(folder: Path, title: str, *, saved_filename=None,
                    reserved_names=()) -> Path:
    """Choose Title.txt, Title (1).txt, etc., without overwriting another note.

    A saved filename is reused for the same note across launches and title edits;
    it is never assigned to a different note, even if that note's file was moved.
    Existing files are compared case-insensitively, like Windows Explorer.
    """
    folder = Path(folder)
    reserved = {name.casefold() for name in reserved_names if isinstance(name, str)}
    if (_valid_saved_filename(saved_filename) and
            saved_filename.casefold() not in reserved):
        path = folder / saved_filename
        if not path.is_symlink() and not path.is_dir():
            return path

    occupied = set(reserved)
    if folder.exists():
        occupied.update(item.name.casefold() for item in folder.iterdir())
    stem = _safe_title_stem(title)
    number = 0
    while True:
        suffix = f" ({number})" if number else ""
        filename = f"{stem[:96 - len(suffix)].rstrip(' .')}{suffix}.txt"
        if filename.casefold() not in occupied:
            return folder / filename
        number += 1


def create_text(path: Path, body: str) -> None:
    """Create a new text file exclusively; never replace a name that just appeared."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8-sig", newline="") as stream:
        stream.write(body)



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
