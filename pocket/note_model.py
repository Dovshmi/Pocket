"""Pure note operations shared by Normal, Mini and Dashboard.

No Tk widgets or network calls; keeps note identity, reminder and direction
behavior testable without opening a desktop.
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from pathlib import Path
import ipaddress
import uuid

def new_note(title="Untitled note", body="", phone="") -> dict:
    return {"id": uuid.uuid4().hex, "title": title, "body": body, "phone": phone,
            "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "pinned": False, "direction": "ltr",
            "reminder_enabled": False, "reminder_at": "", "reminder_sent_at": "",
            "reminder_snoozed": False, "reminder_draft": "",
            "reminder_add_response": False}


def ordered_notes(notes: list[dict]) -> list[dict]:
    """Pinned notes first; preserve the original order within both groups."""
    return sorted(notes, key=lambda note: not (note.get("pinned") is True))


def duplicate_note(original: dict) -> dict:
    """Copy the content but use a fresh note ID and creation time. Pin is not inherited."""
    # The UI allocates the next available Windows-style title, e.g. (1).
    # Do not bake "(copy)" into the user's eventual TXT filename.
    copy = new_note(original.get('title', 'Untitled note'),
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
    """Create a numbered, never-overwriting UTF-8 snapshot for Notepad.

    Unlike Pocket's live Notepad working file, snapshots do not sync edits
    back into the application's data.
    """
    from . import note_sync

    target = note_sync.named_note_path(output_dir, note.get("title", "Note"))
    note_sync.create_text(target, note.get("body", ""))
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
    note["reminder_snoozed"] = valid and note.get("reminder_snoozed") is True
    note["reminder_draft"] = (note.get("reminder_draft", "")[:4000]
                              if isinstance(note.get("reminder_draft"), str) else "")
    note["reminder_add_response"] = note.get("reminder_add_response") is True
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




SNOOZE_MINUTES = (5, 15, 30, 60)


def reminder_status(note):
    """Status of a Note's optional Reminder, for the overview."""
    if not note.get("reminder_enabled"):
        return None
    if note.get("reminder_sent_at"):
        return "Completed"
    return "Snoozed" if note.get("reminder_snoozed") else "Upcoming"


def append_reminder_response(body, response, add_response):
    """Append only to the bottom; never reflow or replace existing note text."""
    prior = body if isinstance(body, str) else ""
    if not add_response or not isinstance(response, str) or not response.strip():
        return prior
    new_text = response.strip()
    if len(new_text) > 4000:
        raise ValueError("Reminder response is too long")
    separator = "" if not prior else ("\\n" if prior.endswith("\\n") else "\\n\\n")
    return prior + separator + new_text


def complete_reminder(note, response="", add_response=False, *, now=None):
    """Mark delivered notification as handled and optionally append once."""
    prior = note.get("body", "")
    updated = append_reminder_response(prior, response, add_response)
    note["body"] = updated
    instant = now or datetime.now(timezone.utc)
    note["reminder_sent_at"] = instant.astimezone(timezone.utc).isoformat(timespec="seconds")
    note["reminder_snoozed"] = False
    note["reminder_draft"] = ""
    note["reminder_add_response"] = False
    return updated != prior


def snooze_reminder(note, minutes, response="", add_response=False, *, now=None):
    """Postpone delivery without writing any draft to the Note."""
    if type(minutes) is not int or minutes not in SNOOZE_MINUTES:
        raise ValueError("Select a supported Snooze interval")
    instant = (now or datetime.now().astimezone()).astimezone()
    note["reminder_at"] = (instant + timedelta(minutes=minutes)).isoformat(timespec="minutes")
    note["reminder_enabled"] = True
    note["reminder_sent_at"] = ""
    note["reminder_snoozed"] = True
    note["reminder_add_response"] = add_response is True
    note["reminder_draft"] = response[:4000] if add_response and isinstance(response, str) else ""
