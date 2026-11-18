"""Pure offline standalone reminders independent of Notes.

A standalone reminder has its own identity, optional description, due time
and response log; it is never automatically turned into a Note.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import uuid

from . import note_model

MAX_REMINDERS = 2000
MAX_TITLE = 140
MAX_DETAILS = 4000


def make_reminder(title, details="", when=None):
    title = title.strip() if isinstance(title, str) else ""
    if not title or len(title) > MAX_TITLE:
        raise ValueError("Enter a reminder title (1–140 characters).")
    if not isinstance(details, str) or len(details) > MAX_DETAILS:
        raise ValueError("Reminder details must be under 4,000 characters.")
    if not isinstance(when, str):
        raise ValueError("Choose a reminder date and time.")
    try:
        at = datetime.fromisoformat(when)
    except ValueError as exc:
        raise ValueError("Choose a valid date and time.") from exc
    if at.tzinfo is None or at <= datetime.now().astimezone():
        raise ValueError("Choose a future date and time.")
    return {
        "id": uuid.uuid4().hex, "title": title, "details": details,
        "reminder_enabled": True, "reminder_at": at.isoformat(timespec="minutes"),
        "reminder_sent_at": "", "reminder_snoozed": False,
        "reminder_draft": "", "reminder_add_response": False,
        "responses": [], "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def normalize_reminders(value):
    """Accept older profiles with no standalone list; reject malformed records."""
    if value is None:
        return []
    if not isinstance(value, list) or len(value) > MAX_REMINDERS:
        raise ValueError("Invalid standalone reminder list")
    result, ids = [], set()
    for raw in value:
        if not isinstance(raw, dict) or any(
            not isinstance(raw.get(key), str) for key in ("id", "title", "details", "reminder_at")
        ):
            raise ValueError("Invalid standalone reminder")
        if not raw["id"] or not raw["title"].strip() or len(raw["title"]) > MAX_TITLE:
            raise ValueError("Invalid standalone reminder identity/title")
        if len(raw["details"]) > MAX_DETAILS or raw["id"] in ids:
            raise ValueError("Duplicate or oversized standalone reminder")
        item = dict(raw)
        note_model.normalize_note_reminder(item)
        if not item["reminder_at"]:
            raise ValueError("Invalid standalone reminder date")
        responses = item.get("responses", [])
        if not isinstance(responses, list) or len(responses) > 200:
            raise ValueError("Invalid reminder responses")
        cleaned = []
        for response in responses:
            if not isinstance(response, dict) or not all(
                isinstance(response.get(k), str) for k in ("time", "text")
            ) or len(response["text"]) > MAX_DETAILS:
                raise ValueError("Invalid reminder response")
            cleaned.append({"time": response["time"], "text": response["text"]})
        item["responses"] = cleaned
        item["created_at"] = raw.get("created_at") if isinstance(raw.get("created_at"), str) else ""
        ids.add(item["id"])
        result.append(item)
    return result


def is_due(item, now=None):
    return note_model.reminder_is_due(item, now)


def status(item):
    return note_model.reminder_status(item)


def snooze(item, minutes, response="", checked=False, *, now=None):
    return note_model.snooze_reminder(item, minutes, response, checked, now=now)


def complete(item, response="", checked=False, *, now=None):
    """Keep optional reply on the standalone item, NOT in Notes."""
    now = now or datetime.now().astimezone()
    if checked and isinstance(response, str) and response.strip():
        if len(response.strip()) > MAX_DETAILS:
            raise ValueError("Reminder response is too long")
        item.setdefault("responses", []).append({
            "time": now.astimezone().strftime("%d/%m/%Y %H:%M"),
            "text": response.strip(),
        })
    item["reminder_sent_at"] = now.astimezone(timezone.utc).isoformat(timespec="seconds")
    item["reminder_snoozed"] = False
    item["reminder_draft"] = ""
    item["reminder_add_response"] = False
