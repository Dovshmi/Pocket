"""Nine explicit Windows Numpad clipboard slots, independent of daily history.

Slots persist only when the user deliberately assigns text. The normal RAM
history remains ephemeral, and no global keyboard hook is installed.
"""
from __future__ import annotations

SLOT_NUMBERS = tuple(range(1, 10))
MAX_TEXT_LENGTH = 20_000
# Each slot has two direct Windows hotkeys with distinct modifiers.
# Num Lock must be ON; Numpad1–9 are fixed and never customizable.
# Shift is intentionally excluded because it can remap Numpad digits into
# navigation key events on Windows.
DEFAULT_PREFIX = "ctrl_alt"  # Backward compatible name for paste.
DEFAULT_PASTE_PREFIX = "ctrl_alt"
DEFAULT_COPY_PREFIX = "ctrl_win"
DEFAULT_PASTE_MODE = "auto"
PASTE_MODE_CHOICES = (("Auto Paste", "auto"), ("Copy to Clipboard", "clipboard"))
PREFIX_CHOICES = (
    ("Ctrl+Alt", "ctrl_alt"),
    ("Ctrl", "ctrl"),
    ("Ctrl+Win", "ctrl_win"),
    ("Ctrl+Alt+Win", "ctrl_alt_win"),
)
PASTE_HOTKEY_BASE = 0xB60
SAVE_HOTKEY_BASE = 0xB70
ALTERNATE_HOTKEY_BASE = 0xB80
MOD_ALT = 0x0001
MOD_CTRL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000


def valid_text(value):
    return (isinstance(value, str) and bool(value.strip())
            and len(value) <= MAX_TEXT_LENGTH)


def normalize_paste_mode(value):
    """An existing profile must keep its automatic-paste behavior."""
    return value if value in ("auto", "clipboard") else DEFAULT_PASTE_MODE


def normalize_slots(raw):
    """Only accept plain text values for keys '1'..'9'; no custom labels."""
    if not isinstance(raw, dict):
        return {}
    return {str(number): raw[str(number)] for number in SLOT_NUMBERS
            if valid_text(raw.get(str(number)))}


def normalize_prefix(value, *, default=DEFAULT_PASTE_PREFIX):
    """Only the modifier prefix is user-editable, not the numeric keys."""
    allowed = {identifier for _, identifier in PREFIX_CHOICES}
    return value if isinstance(value, str) and value in allowed else default


def normalized_prefix_pair(paste, copy):
    """Migrate old profiles without accidentally assigning both actions one key."""
    paste = normalize_prefix(paste, default=DEFAULT_PASTE_PREFIX)
    copy = normalize_prefix(copy, default=DEFAULT_COPY_PREFIX)
    if copy == paste:
        copy = (DEFAULT_PASTE_PREFIX if paste != DEFAULT_PASTE_PREFIX
                else DEFAULT_COPY_PREFIX)
    return paste, copy


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


def distinct_prefixes(paste_prefix, copy_prefix):
    """A pair of actions cannot claim the same global chord."""
    return normalize_prefix(paste_prefix) != normalize_prefix(
        copy_prefix, default=DEFAULT_COPY_PREFIX)


def slot_hotkeys(paste_prefix=DEFAULT_PASTE_PREFIX,
                 copy_prefix=DEFAULT_COPY_PREFIX, *,
                 base=PASTE_HOTKEY_BASE):
    """Register direct Paste and Copy-to-slot keys for Numpad1–9 only."""
    if not distinct_prefixes(paste_prefix, copy_prefix):
        raise ValueError("Copy and paste must use different modifier combinations")
    for number in SLOT_NUMBERS:
        key = 0x60 + number
        yield (base + number - 1, modifier_flags(paste_prefix), key)
        yield (base + 0x10 + number - 1, modifier_flags(copy_prefix), key)


def group_hotkeys(action, prefix, *, base):
    """One 9-key group, addressable independently for conflict-safe swaps."""
    if action not in ("paste", "save"):
        raise ValueError("Invalid Quick Slot action")
    for number in SLOT_NUMBERS:
        yield (base + number - 1, modifier_flags(prefix), 0x60 + number)


def register_group(register, unregister, hwnd, action, prefix, *, base):
    """All-or-none single action registration; old group remains active."""
    registered = set()
    for hotkey_id, mods, key in group_hotkeys(action, prefix, base=base):
        if not register(hwnd, hotkey_id, mods, key):
            for previous in registered:
                unregister(hwnd, previous)
            return set()
        registered.add(hotkey_id)
    return registered


def register_all(register, unregister, hwnd, paste_prefix,
                 copy_prefix=DEFAULT_COPY_PREFIX, *, base=PASTE_HOTKEY_BASE):
    """Atomic 18-key registration; undo partial success on a conflict."""
    registered = set()
    try:
        bindings = tuple(slot_hotkeys(paste_prefix, copy_prefix, base=base))
    except ValueError:
        return set()
    for hotkey_id, modifiers, key in bindings:
        if not register(hwnd, hotkey_id, modifiers, key):
            for earlier in registered:
                unregister(hwnd, earlier)
            return set()
        registered.add(hotkey_id)
    return registered


def hotkey_action(hotkey_id, *, base=PASTE_HOTKEY_BASE):
    offset = hotkey_id - base
    if 0 <= offset < 9:
        return ("paste", offset + 1)
    if 0x10 <= offset < 0x19:
        return ("save", offset - 0x10 + 1)
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
    """Copy the selected text into the slot, using ordinary Windows Ctrl+C.

    Do not obtain/restore the old clipboard via OLE for *copy*. Some Windows
    applications expose delayed-rendered clipboard data that causes
    OleGetClipboard/CloseClipboard to fail while text is selected. A copy
    shortcut should behave like normal Ctrl+C: if text is selected it also
    becomes the current clipboard content; otherwise the previous clipboard
    text is the fallback. The separate *paste* action still preserves the
    user's original multi-format clipboard through OLE.
    """
    if backend is None:
        from .marked_layout import WindowsMarkBackend
        backend = WindowsMarkBackend(owner_hwnd)
    from .marked_layout import MarkError
    if not target_hwnd or backend.foreground() != target_hwnd:
        raise MarkError("The original window is no longer active.")
    if not backend.wait_keys_up():
        raise MarkError("Release the shortcut keys and try again.")

    # Ctrl+Win+NumpadN has just been released. Allow the foreground app to
    # process the released Win modifier before injecting a plain Ctrl+C.
    backend.settle_hotkey_release() if hasattr(backend, "settle_hotkey_release") else None
    if backend.foreground() != target_hwnd:
        raise MarkError("The active window changed before the text was copied.")

    before_text = backend.read_text()
    baseline = backend.sequence()
    backend.send_key("C")
    if backend.wait_for_sequence_change(baseline, timeout=1.0):
        copied_text = backend.read_text()
        if valid_text(copied_text):
            return copied_text
        raise MarkError("The selection was copied, but it is not usable text.")
    # No new copy occurred: the previous clipboard text remains available.
    if valid_text(before_text):
        return before_text
    raise MarkError("No selected text or existing text clipboard to save.")


def copy_slot_to_clipboard(value, *, owner_hwnd=0, backend=None):
    """Stage the slot as the current Windows copy, for ordinary manual Ctrl+V.

    Clipboard-only mode deliberately does not snapshot or restore OLE formats
    and does not send Ctrl+V or require focus to remain in the same window.
    """
    if not valid_text(value):
        raise ValueError("Quick Slot is empty.")
    if backend is None:
        from .marked_layout import WindowsMarkBackend
        backend = WindowsMarkBackend(owner_hwnd)
    from .marked_layout import MarkError
    if not backend.wait_keys_up():
        raise MarkError("Release the shortcut keys and try again.")
    if hasattr(backend, "settle_hotkey_release"):
        backend.settle_hotkey_release()
    backend.put_text(value)


def paste_slot_text(value, *, target_hwnd, owner_hwnd=0, backend=None):
    """Auto-paste, preserving the original clipboard when the OLE snapshot works.

    Some corporate apps provide an OLE clipboard object that cannot be read.
    If the snapshot fails *before touching the clipboard*, use native Unicode
    input instead; never silently discard the prior clipboard or paste twice.
    """
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
    if hasattr(backend, "settle_hotkey_release"):
        backend.settle_hotkey_release()
    if backend.foreground() != target_hwnd:
        raise MarkError("The active window changed; paste cancelled.")

    snapshot_ready = False
    try:
        with backend.preserve_clipboard() as restore:
            snapshot_ready = True
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
    except (MarkError, OSError):
        if snapshot_ready:
            # A failure after clipboard replacement or Ctrl+V is not safe to
            # retry: doing so might paste twice or clobber another app's copy.
            raise
        if backend.foreground() != target_hwnd:
            raise MarkError("The active window changed; paste cancelled.")
        # This path never calls put_text or Ctrl+V, so the existing
        # multi-format clipboard survives even when OleGetClipboard fails.
        backend.send_text(value)
