"""Nine explicit Windows Numpad clipboard slots, independent of daily history.

Slots persist only when the user deliberately assigns text. The normal RAM
history remains ephemeral, and no global keyboard hook is installed.
"""
from __future__ import annotations

SLOT_NUMBERS = tuple(range(1, 10))
MAX_TEXT_LENGTH = 20_000
# A single chord covers Numpad0 (arm) and Numpad1–9 (paste/save).
# Shift is deliberately absent: Shift changes the virtual key reported by
# some numeric keypads into a navigation key. Alt-only triggers Windows Alt
# codes; the selection below avoids it.
DEFAULT_PREFIX = "ctrl_alt"
PREFIX_CHOICES = (
    ("Ctrl+Alt", "ctrl_alt"),
    ("Ctrl", "ctrl"),
    ("Ctrl+Win", "ctrl_win"),
    ("Ctrl+Alt+Win", "ctrl_alt_win"),
)
PASTE_HOTKEY_BASE = 0xB60
ALTERNATE_HOTKEY_BASE = 0xB80
SAVE_MODE_SECONDS = 5
MOD_ALT = 0x0001
MOD_CTRL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
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


def normalize_prefix(value):
    """Reject unsupported combinations (including Shift and Alt-only)."""
    return value if value in {identifier for _, identifier in PREFIX_CHOICES} else DEFAULT_PREFIX


def prefix_label(value):
    chosen = normalize_prefix(value)
    return next(label for label, identifier in PREFIX_CHOICES if identifier == chosen)


def modifier_flags(value):
    value = normalize_prefix(value)
    mapping = {
        "ctrl_alt": MOD_CTRL | MOD_ALT,
        "ctrl": MOD_CTRL,
        "ctrl_win": MOD_CTRL | MOD_WIN,
        "ctrl_alt_win": MOD_CTRL | MOD_ALT | MOD_WIN,
    }
    return mapping[value] | MOD_NOREPEAT


def slot_hotkeys(prefix=DEFAULT_PREFIX, *, base=PASTE_HOTKEY_BASE):
    """Ten registrations: Numpad0 arms Save; Numpad1..9 select the slot.

    Numpad numbers are fixed. Only the modifier prefix is customizable.
    All bindings have an identical prefix and use VK_NUMPADN, not top-row N.
    """
    modifiers = modifier_flags(prefix)
    for number in SLOT_NUMBERS:
        yield (base + number - 1, modifiers, 0x60 + number)
    yield (base + 9, modifiers, 0x60)  # VK_NUMPAD0: one-shot Save Mode


def register_all(register, unregister, hwnd, prefix, *, base=PASTE_HOTKEY_BASE):
    """All-or-none registration; never leave an unusable partial keypad."""
    registered = set()
    for hotkey_id, modifiers, key in slot_hotkeys(prefix, base=base):
        if not register(hwnd, hotkey_id, modifiers, key):
            for earlier in registered:
                unregister(hwnd, earlier)
            return set()
        registered.add(hotkey_id)
    return registered


def hotkey_action(hotkey_id, *, base=PASTE_HOTKEY_BASE):
    offset = hotkey_id - base
    if 0 <= offset <= 8:
        return ("slot", offset + 1)
    if offset == 9:
        return ("mode", 0)
    return None


def slot_action(number, *, armed_until=0.0, now=0.0):
    """Decide between save and paste without querying the keyboard."""
    if number not in SLOT_NUMBERS:
        return None
    return "save" if armed_until > now else "paste"


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
