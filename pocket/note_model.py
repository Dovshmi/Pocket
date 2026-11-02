"""Pure note operations shared by Normal, Mini and Dashboard.

No Tk widgets or network calls; keeps note identity, reminder and direction
behavior testable without opening a desktop.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import ipaddress
import re
import uuid

def new_note(title="Untitled note", body="", phone="") -> dict:
    return {"id": uuid.uuid4().hex, "title": title, "body": body, "phone": phone,
            "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "pinned": False, "direction": "ltr",
            "reminder_enabled": False, "reminder_at": "", "reminder_sent_at": ""}


def ordered_notes(notes: list[dict]) -> list[dict]:
    """Pinned notes first; preserve the original order within both groups."""
    return sorted(notes, key=lambda note: not (note.get("pinned") is True))


def duplicate_note(original: dict) -> dict:
    """Copy the content but use a fresh note ID and creation time. Pin is not inherited."""
    copy = new_note(f"{original.get('title', 'Untitled note')} (copy)",
                    original.get('body', ''), original.get('phone', ''))
    copy["direction"] = normalize_note_direction(original.get("direction"))
    return copy


def normalize_note_direction(value) -> str:
    """Existing notes remain left-aligned; only explicit RTL is accepted."""
    return "rtl" if value == "rtl" else "ltr"


def display_created_at(value: str) -> str:
    """Show genuine creation timestamps in local time; never invent legacy dates."""
    if not value:
        return "Created: unknown (older note)"
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            return "Created: unknown"
        return "Created: " + parsed.astimezone().strftime("%d %b %Y, %H:%M")
    except (ValueError, TypeError, OverflowError):
        return "Created: unknown"


def export_note_for_notepad(note: dict, output_dir: Path) -> Path:
    """Save a one-off UTF-8 copy of the selected note for Windows Notepad.

    A fresh snapshot avoids overwriting previous edits made in Notepad.
    Notepad snapshots do not synchronize edits back to the application's data.
    """
    title = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", note.get("title", "Note"))
    title = title.strip(" .")[:40] or "Note"
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"PocketDesk_{title}_{stamp}_{uuid.uuid4().hex[:8]}.txt"
    target = output_dir / filename
    with target.open("x", encoding="utf-8-sig", newline="") as stream:
        stream.write(note.get("body", ""))
    return target


def note_selection_ip(selected: str) -> str | None:
    """Return a literal selected IP, with no hostname resolution or network call."""
    selected = selected.strip()
    try:
        return str(ipaddress.ip_address(selected))
    except ValueError:
        return None


def note_command_query(selected: str) -> str:
    """Compact a selection for Commands search, avoiding accidental huge queries."""
    return " ".join(selected.split())[:250]


def parse_reminder_time(date_text, time_text, now=None):
    """Validate a future local time, stored with the local UTC offset."""
    try:
        scheduled = datetime.strptime(f"{date_text.strip()} {time_text.strip()}",
                                      "%Y-%m-%d %H:%M").astimezone()
    except (ValueError, AttributeError) as exc:
        raise ValueError("Use a valid date YYYY-MM-DD and time HH:MM.") from exc
    if scheduled <= (now or datetime.now().astimezone()):
        raise ValueError("Choose a future date and time.")
    return scheduled.isoformat(timespec="minutes")


def normalize_note_reminder(note):
    """Migrate previous note records without inventing reminder times."""
    raw = note.get("reminder_at")
    try:
        when = datetime.fromisoformat(raw) if isinstance(raw, str) and raw else None
    except ValueError:
        when = None
    valid = when is not None and when.tzinfo is not None
    note["reminder_at"] = raw if valid else ""
    note["reminder_enabled"] = valid and note.get("reminder_enabled") is True
    note["reminder_sent_at"] = (note.get("reminder_sent_at", "")
                                if isinstance(note.get("reminder_sent_at", ""), str) else "")
    return note


def reminder_is_due(note, now=None):
    if not note.get("reminder_enabled") or note.get("reminder_sent_at"):
        return False
    try:
        scheduled = datetime.fromisoformat(note["reminder_at"])
        return scheduled.tzinfo is not None and scheduled <= (now or datetime.now().astimezone())
    except (ValueError, TypeError, KeyError):
        return False


def format_reminder(note):
    if not note.get("reminder_enabled"):
        return "No reminder"
    try:
        when = datetime.fromisoformat(note["reminder_at"]).astimezone()
        return when.strftime("%d %b %Y · %H:%M") + (" · sent" if note.get("reminder_sent_at") else "")
    except (ValueError, TypeError, KeyError):
        return "No reminder"


