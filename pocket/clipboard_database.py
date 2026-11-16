"""Optional *local* Clipboard history, isolated from Pocket's RAM-only mode.

One UTF-8 .txt file (JSON-lines records) per calendar date; one screenshot
folder per date containing PNGs. All paths live below the *current Pocket
profile* directory. No SQLite, networking, registry writes, or background
service. Clipboard contents are personal data: database mode is opt-in.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
import json
import os
from pathlib import Path
import re
import uuid

ROOT_NAME = "ClipboardDatabase"
TEXT_FOLDER = "ClipboardText"
IMAGE_FOLDER = "ClipboardScreenshots"
_RETENTION = (1, 2, 3, 4, 5)
_TEXT_FILE = re.compile(
    r"^(?P<day>\d{4}-\d{2}-\d{2})_(?P<created>\d{2}-\d{2}-\d{2})_to_(?P<expires>\d{4}-\d{2}-\d{2})\.txt$")
_IMAGE_FILE = re.compile(r"^\d{2}-\d{2}-\d{2}_[0-9a-f]{32}\.png$")
_MAX_IMAGE = 12 * 1024 * 1024


def normalize_days(value):
    return value if type(value) is int and value in _RETENTION else 1


def today():
    return date.today().isoformat()


def valid_day(value):
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return False
    try:
        return date.fromisoformat(value).isoformat() == value
    except ValueError:
        return False


def expire_date(day: str, days: int) -> str:
    # N calendar days means today is day 1: the oldest allowed date is
    # today - (N-1), and expiry is the start of date + N.
    if not valid_day(day):
        raise ValueError("Invalid history date")
    return (date.fromisoformat(day) + timedelta(days=normalize_days(days))).isoformat()


class ClipboardDatabase:
    def __init__(self, profile_dir):
        self.root = Path(profile_dir) / ROOT_NAME
        self.text_dir = self.root / TEXT_FOLDER
        self.image_dir = self.root / IMAGE_FOLDER

    def _day_folder(self, day):
        if not valid_day(day):
            raise ValueError("Invalid history date")
        return self.image_dir / day

    def _text_file(self, day):
        if not valid_day(day):
            raise ValueError("Invalid history date")
        if not self.text_dir.is_dir() or self.text_dir.is_symlink():
            return None
        for file in sorted(self.text_dir.iterdir()):
            if file.is_symlink() or not file.is_file():
                continue
            parsed = _TEXT_FILE.fullmatch(file.name)
            if parsed and parsed.group("day") == day:
                return file
        return None

    def days(self, kind, *, days=5, on=None):
        """Show only retained dates; never traverse unexpected filenames."""
        now = date.fromisoformat(on or today())
        cutoff = now - timedelta(days=normalize_days(days) - 1)
        matches = set()
        if kind == "text":
            folder = self.text_dir
            if folder.is_dir() and not folder.is_symlink():
                for file in folder.iterdir():
                    m = _TEXT_FILE.fullmatch(file.name)
                    if m and file.is_file() and not file.is_symlink():
                        matches.add(m.group("day"))
        elif kind == "images":
            folder = self.image_dir
            if folder.is_dir() and not folder.is_symlink():
                for child in folder.iterdir():
                    if child.is_dir() and not child.is_symlink() and valid_day(child.name):
                        matches.add(child.name)
        else:
            raise ValueError("Invalid history type")
        return sorted((day for day in matches if valid_day(day) and
                       cutoff <= date.fromisoformat(day) <= now), reverse=True)

    def prune(self, days=1, *, on=None):
        """Delete Pocket-created expired daily data only, never arbitrary files."""
        now = date.fromisoformat(on or today())
        cutoff = now - timedelta(days=normalize_days(days) - 1)
        if self.text_dir.is_dir() and not self.text_dir.is_symlink():
            for file in self.text_dir.iterdir():
                m = _TEXT_FILE.fullmatch(file.name)
                if (m and file.is_file() and not file.is_symlink() and
                        valid_day(m.group("day")) and
                        date.fromisoformat(m.group("day")) < cutoff):
                    file.unlink()
        if self.image_dir.is_dir() and not self.image_dir.is_symlink():
            for folder in self.image_dir.iterdir():
                if (not folder.is_dir() or folder.is_symlink()
                        or not valid_day(folder.name)
                        or date.fromisoformat(folder.name) >= cutoff):
                    continue
                for file in folder.iterdir():
                    if (file.is_file() and not file.is_symlink()
                            and _IMAGE_FILE.fullmatch(file.name)):
                        file.unlink()
                # Retain any unexpected files rather than deleting user data.
                if not any(folder.iterdir()):
                    folder.rmdir()

    def load_text(self, day):
        file = self._text_file(day)
        if file is None:
            return []
        if file.stat().st_size > 100_000_000:
            raise ValueError("Daily clipboard text file exceeds 100 MB")
        items = []
        with file.open("r", encoding="utf-8") as handle:
            for raw in handle:
                if not raw.strip():
                    continue
                row = json.loads(raw)
                if not isinstance(row, dict):
                    raise ValueError("Invalid clipboard history record")
                if (not isinstance(row.get("id"), str) or
                        not re.fullmatch(r"[0-9a-f]{32}", row["id"]) or
                        not isinstance(row.get("text"), str) or
                        len(row["text"]) > 20_000 or
                        not isinstance(row.get("time"), str)):
                    raise ValueError("Invalid clipboard history record")
                items.append({
                    "id": row["id"], "text": row["text"], "time": row["time"],
                    "pinned": row.get("pinned") is True})
        return items

    def save_text(self, day, items, *, days=1, on=None):
        """Atomically replace one date file; preserve a readable .txt format."""
        if not valid_day(day):
            raise ValueError("Invalid history date")
        if self.text_dir.is_symlink():
            raise OSError("Clipboard text directory must not be a symbolic link")
        self.text_dir.mkdir(parents=True, exist_ok=True)
        target = self._text_file(day)
        # A date's file carries its actual creation time and current intended
        # expiry date in its filename. Update expiry after retention changes.
        if target is None:
            stamp = (on or datetime.now()).strftime("%H-%M-%S")
        else:
            stamp = _TEXT_FILE.fullmatch(target.name).group("created")
        wanted = self.text_dir / f"{day}_{stamp}_to_{expire_date(day, days)}.txt"
        if wanted.exists() and wanted != target:
            raise FileExistsError(f"Clipboard history filename is already used: {wanted.name}")
        if not items:
            if target is not None:
                target.unlink()
            return
        temporary = self.text_dir / f".pocket-{uuid.uuid4().hex}.tmp"
        try:
            with temporary.open("x", encoding="utf-8", newline="\n") as handle:
                for item in items:
                    handle.write(json.dumps({
                        "id": item["id"], "text": item["text"],
                        "time": item["time"], "pinned": bool(item.get("pinned"))
                    }, ensure_ascii=False, separators=(",", ":")) + "\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, wanted)
            if target is not None and target != wanted and target.exists():
                target.unlink()
        finally:
            if temporary.exists():
                temporary.unlink()

    def load_images(self, day):
        folder = self._day_folder(day)
        if not folder.is_dir() or folder.is_symlink():
            return []
        result = []
        for file in sorted(folder.iterdir(), reverse=True):
            if (file.is_symlink() or not file.is_file()
                    or not _IMAGE_FILE.fullmatch(file.name)):
                continue
            if file.stat().st_size > _MAX_IMAGE:
                continue
            payload = file.read_bytes()
            if not payload.startswith(b"\x89PNG\r\n\x1a\n"):
                continue
            from hashlib import sha256
            from .clipboard_images import decode_image
            try:
                image = decode_image(payload)
                result.append({
                    "id": file.stem.split("_")[-1], "data": payload,
                    "digest": sha256(payload).hexdigest(),
                    "time": file.name[:8].replace("-", ":"),
                    "width": image.width, "height": image.height,
                    "file_name": file.name})
            except (OSError, ValueError, MemoryError):
                continue
        return result

    def save_image(self, day, item):
        """Save all accepted screenshots for the day, not RAM's 20-item cap."""
        folder = self._day_folder(day)
        if folder.is_symlink():
            raise OSError("Clipboard screenshot directory must not be a symbolic link")
        folder.mkdir(parents=True, exist_ok=True)
        identifier = item["id"]
        payload = item["data"]
        if not re.fullmatch(r"[0-9a-f]{32}", identifier):
            raise ValueError("Invalid screenshot id")
        if (not isinstance(payload, bytes) or len(payload) > _MAX_IMAGE or
                not payload.startswith(b"\x89PNG\r\n\x1a\n")):
            raise ValueError("Invalid screenshot image")
        timestamp = item["time"].replace(":", "-")
        if not re.fullmatch(r"\d{2}-\d{2}-\d{2}", timestamp):
            raise ValueError("Invalid screenshot timestamp")
        name = f"{timestamp}_{identifier}.png"
        with (folder / name).open("xb") as output:
            output.write(payload)
        item["file_name"] = name

    def delete_image(self, day, item):
        name = item.get("file_name", "")
        if not isinstance(name, str) or not _IMAGE_FILE.fullmatch(name):
            raise ValueError("Invalid screenshot filename")
        file = self._day_folder(day) / name
        if file.is_symlink():
            raise ValueError("Unsafe screenshot path")
        file.unlink(missing_ok=True)

    def clear_images(self, day):
        for item in self.load_images(day):
            self.delete_image(day, item)
