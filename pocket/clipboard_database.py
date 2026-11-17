"""Offline, opt-in daily text archive and flat PNG screenshot library for Pocket.

RAM mode never calls this module's write paths. Database files live strictly
within Pocket's writable profile. Automatic deletion is OFF unless the user
explicitly chooses 7–30 calendar days. Previous daily PNG folders are migrated
non-destructively and only recognized Pocket files are managed.
"""
from __future__ import annotations

from collections import deque
from datetime import date, datetime, timedelta
from hashlib import sha256
import heapq
import json
import os
from pathlib import Path
import re
import struct
import uuid

ROOT_NAME = "ClipboardDatabase"
TEXT_FOLDER = "ClipboardText"
IMAGE_FOLDER = "ClipboardScreenshots"
_MAX_IMAGE = 12 * 1024 * 1024
_TEXT_FILE = re.compile(
    r"^(?P<day>\d{4}-\d{2}-\d{2})_(?P<created>\d{2}-\d{2}-\d{2})_to_(?P<expires>\d{4}-\d{2}-\d{2}|saved)\.txt$")
_IMAGE_FILE = re.compile(
    r"^(?P<day>\d{4}-\d{2}-\d{2})_(?P<clock>\d{2}-\d{2}-\d{2})(?:-(?P<us>\d{6}))?_(?P<id>[0-9a-f]{32})\.png$")
_LEGACY_IMAGE = re.compile(r"^(?P<clock>\d{2}-\d{2}-\d{2})_(?P<id>[0-9a-f]{32})\.png$")
_PNG_HEADER = b"\x89PNG\r\n\x1a\n"


def normalize_days(value):
    """Legacy explicit archive retention API (supports existing 1–5 callers)."""
    return value if type(value) is int and 1 <= value <= 30 else 1


def normalize_autodelete_days(value):
    """0 means keep until deleted; other values are 7 through 30 inclusive."""
    return value if type(value) is int and 7 <= value <= 30 else 0


TEXT_DISPLAY_CHOICES = (100, 300, 500, 800, 1000, 1200, 1500)


def normalize_display_limit(value, default=30):
    """Image DB options; kept independent from the text history limit."""
    return value if type(value) is int and value in range(10, 101, 10) else default


def normalize_text_display_limit(value):
    """v1.38 text-page choices, safely upgrading saved 1.37 preferences."""
    if type(value) is not int or value < 1:
        return 100
    # Previously available 10–100 counts upgrade to 100. Other persisted
    # integer counts round upward so a larger setting does not lose entries.
    return next((count for count in TEXT_DISPLAY_CHOICES if value <= count), 1500)


def today():
    return date.today().isoformat()


def valid_day(value):
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return False
    try:
        return date.fromisoformat(value).isoformat() == value
    except ValueError:
        return False


def _calendar_day(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    result = date.fromisoformat(value or today())
    return result


def _expiry(days, day):
    if not days:
        return "saved"
    return (date.fromisoformat(day) + timedelta(days=normalize_days(days))).isoformat()


def expire_date(day: str, days: int) -> str:
    if not valid_day(day):
        raise ValueError("Invalid history date")
    return _expiry(days, day)


def _cutoff(days, on):
    if not days:
        return None
    return _calendar_day(on) - timedelta(days=normalize_days(days) - 1)


def _record(item):
    return {
        "id": item["id"], "text": item["text"], "time": item["time"],
        "pinned": item.get("pinned") is True
    }


def _check_record(row):
    if (not isinstance(row, dict) or not isinstance(row.get("id"), str) or
            not re.fullmatch(r"[0-9a-f]{32}", row["id"]) or
            not isinstance(row.get("text"), str) or len(row["text"]) > 20_000 or
            not isinstance(row.get("time"), str)):
        raise ValueError("Invalid clipboard history record")
    return _record(row)


class ClipboardDatabase:
    def __init__(self, profile_dir):
        self.root = Path(profile_dir) / ROOT_NAME
        self.text_dir = self.root / TEXT_FOLDER
        self.image_dir = self.root / IMAGE_FOLDER

    def ensure_folders(self):
        for folder in (self.root, self.text_dir, self.image_dir):
            if folder.is_symlink():
                raise OSError("Clipboard archive cannot use symbolic link directories")
            folder.mkdir(parents=True, exist_ok=True)

    def _day_folder(self, day):
        if not valid_day(day):
            raise ValueError("Invalid history date")
        return self.image_dir / day  # Only used for legacy migration.

    def _text_file(self, day):
        if not valid_day(day):
            raise ValueError("Invalid history date")
        if not self.text_dir.is_dir() or self.text_dir.is_symlink():
            return None
        candidates = []
        for file in self.text_dir.iterdir():
            parsed = _TEXT_FILE.fullmatch(file.name)
            if (parsed and parsed.group("day") == day and file.is_file()
                    and not file.is_symlink()):
                candidates.append(file)
        # Interrupted upgrades can temporarily leave both a legacy expiry
        # name and an upgraded _to_saved file. Prefer the most recently
        # committed file; never delete or overwrite the other candidate.
        return max(candidates, key=lambda file: (file.stat().st_mtime_ns, file.name)) if candidates else None

    def migrate_screenshots(self):
        """Move valid old YYYY-MM-DD/HH-MM-SS_ID.png to one flat folder.

        Files are never overwritten or deleted on collision/error. Unknown
        files or links remain in the old folder for manual inspection.
        Running again after interruption is safe; moved files stay moved.
        """
        if not self.image_dir.exists():
            return 0
        if self.image_dir.is_symlink():
            raise OSError("Clipboard screenshot folder cannot be a link")
        moved = 0
        for folder in sorted(self.image_dir.iterdir()):
            if (not folder.is_dir() or folder.is_symlink()
                    or not valid_day(folder.name)):
                continue
            for source in sorted(folder.iterdir()):
                if source.is_symlink() or not source.is_file():
                    continue
                old = _LEGACY_IMAGE.fullmatch(source.name)
                if not old:
                    continue
                target = self.image_dir / f"{folder.name}_{source.name}"
                if target.exists() or target.is_symlink():
                    # Never overwrite the destination or remove the source.
                    if target.is_file() and target.read_bytes() == source.read_bytes():
                        # Still retain the original to avoid any hidden deletion.
                        continue
                    continue
                source.rename(target)
                moved += 1
            if not any(folder.iterdir()):
                folder.rmdir()
        return moved

    def days(self, kind, *, days=0, on=None):
        """Dates with content. OFF (0) lists all dates without a cutoff."""
        cutoff = _cutoff(days, on)
        now = _calendar_day(on)
        matches = set()
        if kind == "text":
            if self.text_dir.is_dir() and not self.text_dir.is_symlink():
                for file in self.text_dir.iterdir():
                    m = _TEXT_FILE.fullmatch(file.name)
                    if m and file.is_file() and not file.is_symlink():
                        matches.add(m.group("day"))
        elif kind == "images":
            if self.image_dir.is_dir() and not self.image_dir.is_symlink():
                for file in self.image_dir.iterdir():
                    m = _IMAGE_FILE.fullmatch(file.name)
                    if m and file.is_file() and not file.is_symlink():
                        matches.add(m.group("day"))
        else:
            raise ValueError("Invalid clipboard history type")
        return sorted(
            (day for day in matches if valid_day(day) and
             (cutoff is None or date.fromisoformat(day) >= cutoff) and
             date.fromisoformat(day) <= now),
            reverse=True)

    def prune(self, days=0, *, on=None):
        """Delete only recognized expired Pocket data when explicitly enabled."""
        cutoff = _cutoff(days, on)
        if cutoff is None:
            return
        if self.text_dir.is_dir() and not self.text_dir.is_symlink():
            for file in self.text_dir.iterdir():
                m = _TEXT_FILE.fullmatch(file.name)
                if (m and valid_day(m.group("day")) and file.is_file()
                        and not file.is_symlink() and
                        date.fromisoformat(m.group("day")) < cutoff):
                    file.unlink()
        if self.image_dir.is_dir() and not self.image_dir.is_symlink():
            for file in self.image_dir.iterdir():
                m = _IMAGE_FILE.fullmatch(file.name)
                if (m and valid_day(m.group("day")) and file.is_file()
                        and not file.is_symlink() and
                        date.fromisoformat(m.group("day")) < cutoff):
                    file.unlink()

    def update_retention(self, days=0, *, on=None):
        """Re-label the daily TXT expiry and optionally prune archived days."""
        self.prune(days, on=on)
        if not self.text_dir.is_dir() or self.text_dir.is_symlink():
            return
        cutoff = _cutoff(days, on)
        now = _calendar_day(on)
        for file in tuple(self.text_dir.iterdir()):
            matched = _TEXT_FILE.fullmatch(file.name)
            if not matched or file.is_symlink() or not file.is_file():
                continue
            day = matched.group("day")
            if not valid_day(day) or date.fromisoformat(day) > now:
                continue
            if cutoff is not None and date.fromisoformat(day) < cutoff:
                continue
            wanted = self.text_dir / (
                f"{day}_{matched.group('created')}_to_{_expiry(days, day)}.txt")
            if wanted != file:
                if wanted.exists() or wanted.is_symlink():
                    raise FileExistsError("Clipboard history filename is already used")
                file.rename(wanted)

    def load_text(self, day, *, limit=None, offset=0):
        """Newest-first items; only keep a bounded page in RAM when requested.

        v1.37 files are newest-first. New journal files are appended in
        chronological order with v=2; a deque holds only the most recent page.
        """
        file = self._text_file(day)
        if file is None:
            return []
        if file.stat().st_size > 100_000_000:
            raise ValueError("Daily clipboard text file exceeds 100 MB")
        if limit is not None and (type(limit) is not int or limit < 1 or limit > 1500):
            raise ValueError("Invalid text page limit")
        if type(offset) is not int or offset < 0:
            raise ValueError("Invalid text page offset")
        needed = None if limit is None else limit + offset
        records = deque(maxlen=needed) if needed else []
        chronological = None
        with file.open("r", encoding="utf-8") as handle:
            for raw in handle:
                if not raw.strip():
                    continue
                row = json.loads(raw)
                item = _check_record(row)
                if chronological is None:
                    chronological = row.get("v") == 2
                if chronological:
                    records.append(item)
                elif needed is None or len(records) < needed:
                    records.append(item)
                elif not chronological:
                    break
        result = list(reversed(records)) if chronological else list(records)
        return result[offset:offset + limit if limit is not None else None]

    def _filename(self, day, days, *, on=None):
        old = self._text_file(day)
        if old:
            created = _TEXT_FILE.fullmatch(old.name).group("created")
        else:
            created = (on or datetime.now()).strftime("%H-%M-%S")
        return (self.text_dir / f"{day}_{created}_to_{_expiry(days, day)}.txt", old)

    def save_text(self, day, items, *, days=0, on=None):
        """Atomic rewrite for infrequent pin/delete or one-time migration."""
        if not valid_day(day):
            raise ValueError("Invalid history date")
        self.ensure_folders()
        target, previous = self._filename(day, days, on=on)
        if target.exists() and target != previous:
            raise FileExistsError("Clipboard text target already exists")
        if not items:
            if previous:
                previous.unlink()
            return
        temporary = self.text_dir / f".pocket-{uuid.uuid4().hex}.tmp"
        try:
            with temporary.open("x", encoding="utf-8", newline="\n") as out:
                for item in reversed(items):
                    row = {**_check_record(item), "v": 2}
                    out.write(json.dumps(row, ensure_ascii=False,
                                         separators=(",", ":")) + "\n")
                out.flush()
                os.fsync(out.fileno())
            os.replace(temporary, target)
            if previous and target != previous and previous.exists():
                previous.unlink()
        finally:
            if temporary.exists():
                temporary.unlink()

    def append_text(self, day, item, *, days=0):
        """Append one new line, never rewrite a full day's growing history."""
        if not valid_day(day):
            raise ValueError("Invalid history date")
        self.ensure_folders()
        target, old = self._filename(day, days)
        if old:
            with old.open("r", encoding="utf-8") as src:
                first = next((x for x in src if x.strip()), None)
            if first and json.loads(first).get("v") != 2:
                # Convert existing v1.37 newest-first files once.
                self.save_text(day, self.load_text(day), days=days)
                target, old = self._filename(day, days)
            elif old != target:
                if target.exists():
                    raise FileExistsError("Clipboard text target already exists")
                old.rename(target)
        row = {**_check_record(item), "v": 2}
        with target.open("a", encoding="utf-8", newline="\n") as output:
            output.write(json.dumps(row, ensure_ascii=False,
                                    separators=(",", ":")) + "\n")
            output.flush()
            os.fsync(output.fileno())

    def last_text(self, day):
        """Get the most recent record without scanning a growing daily TXT.

        The new append journal is chronological, so its last JSON line is the
        newest capture. Legacy newest-first files use their first JSON line.
        The per-clip 20,000-character cap bounds the tail read to 256 KiB.
        """
        file = self._text_file(day)
        if file is None:
            return None
        with file.open("rb") as handle:
            first = handle.readline()
            if not first.strip():
                return None
            first_row = json.loads(first.decode("utf-8"))
            if first_row.get("v") != 2:
                return _check_record(first_row)
            handle.seek(0, os.SEEK_END)
            size = handle.tell()
            handle.seek(max(0, size - 262144))
            tail = handle.read()
            final = tail.splitlines()[-1]
            return _check_record(json.loads(final.decode("utf-8")))

    def _image_paths(self, day, *, take=None):
        if not valid_day(day):
            raise ValueError("Invalid history date")
        if not self.image_dir.is_dir() or self.image_dir.is_symlink():
            return []

        def images():
            for file in self.image_dir.iterdir():
                match = _IMAGE_FILE.fullmatch(file.name)
                if (match is not None and match.group("day") == day
                        and file.is_file() and not file.is_symlink()):
                    yield file

        def sort_key(file):
            matched = _IMAGE_FILE.fullmatch(file.name)
            return (matched.group("clock"), int(matched.group("us") or 0),
                    matched.group("id"))

        # Keep only the requested display page in memory, even with tens of
        # thousands of saved PNG filenames in the flat folder.
        if take is not None:
            return heapq.nlargest(take, images(), key=sort_key)
        return sorted(images(), key=sort_key, reverse=True)

    def load_images(self, day, *, limit=None, offset=0, metadata_only=False):
        """Only fetch the selected visible page; avoid eager PNG bytes in RAM."""
        if limit is not None and (type(limit) is not int or limit < 1 or limit > 1000):
            raise ValueError("Invalid screenshot display limit")
        if type(offset) is not int or offset < 0:
            raise ValueError("Invalid screenshot page offset")
        selected = self._image_paths(day, take=(offset + limit) if limit else None)[
            offset:offset + limit if limit is not None else None]
        result = []
        for file in selected:
            if file.stat().st_size > _MAX_IMAGE:
                continue
            try:
                with file.open("rb") as handle:
                    header = handle.read(24)
                if not header.startswith(_PNG_HEADER) or len(header) < 24:
                    continue
                width, height = struct.unpack(">II", header[16:24])
                if not (0 < width <= 25000 and 0 < height <= 25000
                        and width * height <= 16_000_000):
                    continue
                item = {
                    "id": _IMAGE_FILE.fullmatch(file.name).group("id"),
                    "file_name": file.name,
                    "file_path": str(file),
                    "time": _IMAGE_FILE.fullmatch(file.name).group("clock").replace("-", ":"),
                    "width": width, "height": height
                }
                if not metadata_only:
                    data = file.read_bytes()
                    item["data"] = data
                    item["digest"] = sha256(data).hexdigest()
                result.append(item)
            except (OSError, ValueError, MemoryError):
                continue
        return result

    def image_data(self, item):
        name = item.get("file_name", "")
        if not isinstance(name, str) or not _IMAGE_FILE.fullmatch(name):
            raise ValueError("Invalid stored screenshot name")
        file = self.image_dir / name
        if file.is_symlink() or not file.is_file() or file.stat().st_size > _MAX_IMAGE:
            raise ValueError("Screenshot file is missing or unsafe")
        payload = file.read_bytes()
        if not payload.startswith(_PNG_HEADER) or len(payload) < 24:
            raise ValueError("Invalid screenshot content")
        width, height = struct.unpack(">II", payload[16:24])
        if not (0 < width <= 25000 and 0 < height <= 25000
                and width * height <= 16_000_000):
            raise ValueError("Screenshot dimensions exceed the safe limit")
        return payload

    def save_image(self, day, item):
        if not valid_day(day):
            raise ValueError("Invalid history date")
        self.ensure_folders()
        identifier = item["id"]
        payload = item["data"]
        if not re.fullmatch(r"[0-9a-f]{32}", identifier):
            raise ValueError("Invalid screenshot id")
        if (not isinstance(payload, bytes) or len(payload) > _MAX_IMAGE
                or not payload.startswith(_PNG_HEADER)):
            raise ValueError("Invalid screenshot image")
        timestamp = item["time"].replace(":", "-")
        if not re.fullmatch(r"\d{2}-\d{2}-\d{2}", timestamp):
            raise ValueError("Invalid screenshot timestamp")
        name = f"{day}_{timestamp}-{datetime.now().microsecond:06d}_{identifier}.png"
        with (self.image_dir / name).open("xb") as output:
            output.write(payload)
        item["file_name"] = name

    def delete_image(self, day, item):
        if not valid_day(day):
            raise ValueError("Invalid history date")
        name = item.get("file_name", "")
        match = _IMAGE_FILE.fullmatch(name) if isinstance(name, str) else None
        if not match or match.group("day") != day:
            raise ValueError("Invalid screenshot filename")
        file = self.image_dir / name
        if file.is_symlink():
            raise ValueError("Unsafe screenshot path")
        file.unlink(missing_ok=True)

    def clear_images(self, day):
        if not valid_day(day):
            raise ValueError("Invalid history date")
        for file in self._image_paths(day):
            file.unlink()
