"""Nine explicit Windows Numpad clipboard slots, independent of daily history.

Slots persist only when the user deliberately assigns text. The normal RAM
history remains ephemeral, and no global keyboard hook is installed.
"""
from __future__ import annotations

SLOT_NUMBERS = tuple(range(1, 10))
MAX_TEXT_LENGTH = 20_000
PASTE_HOTKEY_BASE = 0xB60
SAVE_HOTKEY_BASE = 0xB70
MOD_ALT = 0x0001
MOD_CTRL = 0x0002
MOD_SHIFT = 0x0004
MOD_NOREPEAT = 0x4000


def valid_text(value):
    return (isinstance(value, str) and bool(value.strip())
            and len(value) <= MAX_TEXT_LENGTH)


def normalize_slots(raw):
    """Only accept plain text values for keys '1'..'9'; no custom labels."""
    if not isinstance(raw, dict):
        return {}
    return {str(number): raw[str(number)] for number in SLOT_NUMBERS
            if valid_text(raw.get(str(number)))}


def slot_hotkeys():
    """Separate Ctrl+Alt+NumpadN paste and Ctrl+Alt+Shift+NumpadN save."""
    for number in SLOT_NUMBERS:
        key = 0x60 + number  # VK_NUMPAD1..9, not top-row digit keys.
        yield (PASTE_HOTKEY_BASE + number - 1,
               MOD_CTRL | MOD_ALT | MOD_NOREPEAT, key)
        yield (SAVE_HOTKEY_BASE + number - 1,
               MOD_CTRL | MOD_ALT | MOD_SHIFT | MOD_NOREPEAT, key)


def hotkey_action(hotkey_id):
    if PASTE_HOTKEY_BASE <= hotkey_id < PASTE_HOTKEY_BASE + 9:
        return ("paste", hotkey_id - PASTE_HOTKEY_BASE + 1)
    if SAVE_HOTKEY_BASE <= hotkey_id < SAVE_HOTKEY_BASE + 9:
        return ("save", hotkey_id - SAVE_HOTKEY_BASE + 1)
    return None


def merged_rows(slots, history, query=""):
    """View-only order: [1]..[9], regular pins, then ordinary history.

    A matching historical row is shown once, at the slot position. Removing
    or overwriting the slot does not create an extra pinned historical row.
    """
    needle = query.casefold()
    entries = []
    assigned = set()
    for number in SLOT_NUMBERS:
        value = slots.get(str(number))
        if not valid_text(value):
            continue
        assigned.add(value)
        if needle in value.casefold():
            entries.append({
                "id": "quick-slot:" + str(number), "slot": number,
                "text": value, "pinned": True, "time": "",
            })
    remaining = [row for row in history
                 if row.get("text") not in assigned
                 and needle in row.get("text", "").casefold()]
    entries.extend(sorted(remaining, key=lambda row: not row.get("pinned", False)))
    return entries


def capture_selection_or_clipboard(*, target_hwnd, owner_hwnd=0, backend=None):
    """Prefer selected Windows text; otherwise use the previous clipboard.

    The user's full OLE clipboard is restored after a temporary Ctrl+C, even
    when it contains images. Never substitute stale clipboard text for a
    selection *if* copying has actually produced fresh selected text.
    """
    if backend is None:
        from .marked_layout import WindowsMarkBackend
        backend = WindowsMarkBackend(owner_hwnd)
    from .marked_layout import MarkError
    if not target_hwnd or backend.foreground() != target_hwnd:
        raise MarkError("The original window is no longer active.")
    if not backend.wait_keys_up():
        raise MarkError("Release the shortcut keys and try again.")

    with backend.preserve_clipboard() as restore:
        before_text = backend.read_text()
        baseline = backend.sequence()
        changed_by_us = None
        try:
            backend.send_key("C")
            if backend.wait_for_sequence_change(baseline, timeout=0.5):
                changed_by_us = backend.sequence()
                selected_text = backend.read_text()
                value = selected_text if valid_text(selected_text) else before_text
            else:
                # Ctrl+C had no effect: use the original clipboard contents.
                value = before_text
            if not valid_text(value):
                raise MarkError("No selected text or existing text clipboard to save.")
            return value
        finally:
            # Do not overwrite newer clipboard changes made by another app.
            if changed_by_us is not None and backend.sequence() == changed_by_us:
                restore()


def paste_slot_text(value, *, target_hwnd, owner_hwnd=0, backend=None):
    """Paste into the original foreground window; preserve original formats."""
    if not valid_text(value):
        raise ValueError("Quick Slot is empty.")
    if backend is None:
        from .marked_layout import WindowsMarkBackend
        backend = WindowsMarkBackend(owner_hwnd)
    from .marked_layout import MarkError
    if not target_hwnd or backend.foreground() != target_hwnd:
        raise MarkError("The original window is no longer active.")
    if not backend.wait_keys_up():
        raise MarkError("Release the shortcut keys and try again.")

    with backend.preserve_clipboard() as restore:
        changed_by_us = None
        try:
            if backend.foreground() != target_hwnd:
                raise MarkError("The original window is no longer active.")
            backend.put_text(value)
            changed_by_us = backend.sequence()
            if backend.foreground() != target_hwnd:
                raise MarkError("The active window changed; paste cancelled.")
            backend.send_key("V")
            backend.pause_after_paste()
        finally:
            if changed_by_us is not None and backend.sequence() == changed_by_us:
                restore()
