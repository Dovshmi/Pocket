"""Small native Windows confirmation for replacing a numbered Quick Slot.

Tkinter's messagebox.askyesno uses the system MessageBox on Windows, not a
custom Tkinter Toplevel. It retains the OS styling, focus and Yes/No buttons.
"""
from __future__ import annotations

from tkinter import messagebox

from . import quick_slots


def confirmation_labels(number, old_text, new_text):
    """Use one compact left-to-right line: NEW → OLD."""
    if number not in quick_slots.SLOT_NUMBERS:
        raise ValueError("Invalid Quick Slot")
    maximum = quick_slots.REPLACEMENT_PREVIEW_LENGTH
    return {
        "title": f"Replace Quick Slot [{number}]?",
        "new": quick_slots.notification_preview(new_text, max_length=maximum),
        "old": quick_slots.notification_preview(old_text, max_length=maximum),
    }


def confirmation_message(number, old_text, new_text):
    labels = confirmation_labels(number, old_text, new_text)
    return f"NEW: {labels['new']}   →   OLD: {labels['old']}"


def confirm_replace(root, theme, number, old_text, new_text):
    """Native OS Yes/No dialog; No/Escape/close never changes the slot.

    The theme argument is kept for backward-compatible callers; the system
    chooses the message box appearance and dimensions.
    """
    labels = confirmation_labels(number, old_text, new_text)
    return messagebox.askyesno(
        labels["title"], confirmation_message(number, old_text, new_text),
        parent=root)
