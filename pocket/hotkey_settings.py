"""Persisted, button-configurable Windows global hotkeys for Pocket.

Keep validation independent of Tk/Win32 so the mapping can be unit tested.
"""
from __future__ import annotations

DEFAULT_HOTKEY = {"ctrl": True, "shift": True, "alt": False, "win": False, "key": "*"}
# Keyboard-layout conversion is configurable in Pocket Settings.
DEFAULT_CONVERT_HOTKEY = {"ctrl": True, "shift": False, "alt": True, "win": False, "key": "V"}
_LEGACY_CONVERT_DEFAULT = {"ctrl": True, "shift": False, "alt": True, "win": False, "key": "F9"}
KEYS = tuple("ABCDEFGHIJKLMNOPQRSTUVWXYZ") + tuple("0123456789") + ("*", "Space") + tuple(f"F{i}" for i in range(1, 13))
MOD_ALT, MOD_CTRL, MOD_SHIFT, MOD_WIN, MOD_NOREPEAT = 0x0001, 0x0002, 0x0004, 0x0008, 0x4000
HOTKEY_ID = 0xB10
NUMPAD_HOTKEY_ID = 0xB11


def normalize_hotkey(value) -> dict:
    """Treat incomplete/unsafe persisted combinations as the legacy default."""
    if not isinstance(value, dict) or value.get("key") not in KEYS:
        return DEFAULT_HOTKEY.copy()
    if any(type(value.get(k)) is not bool for k in ("ctrl", "shift", "alt", "win")):
        return DEFAULT_HOTKEY.copy()
    if not (value["ctrl"] or value["alt"] or value["win"]):
        # Never register bare letters, numbers or Shift+letter system-wide.
        return DEFAULT_HOTKEY.copy()
    return {k: value[k] for k in ("ctrl", "shift", "alt", "win")} | {"key": value["key"]}


def hotkey_label(value) -> str:
    item = normalize_hotkey(value)
    names = [label for field, label in (
        ("ctrl", "Ctrl"), ("alt", "Alt"), ("shift", "Shift"), ("win", "Win")
    ) if item[field]]
    names.append(item["key"])
    return "+".join(names)


def key_code(key: str) -> int:
    if key == "*":
        return 0x38  # Standard Shift+8. Numpad multiply is registered separately.
    if key == "Space":
        return 0x20
    if key.startswith("F") and key[1:].isdigit():
        return 0x70 + int(key[1:]) - 1
    return ord(key)


def bindings(value, start_id: int = HOTKEY_ID) -> tuple[tuple[int, int, int], ...]:
    item = normalize_hotkey(value)
    modifiers = MOD_NOREPEAT
    for field, flag in (("ctrl", MOD_CTRL), ("shift", MOD_SHIFT),
                        ("alt", MOD_ALT), ("win", MOD_WIN)):
        if item[field]:
            modifiers |= flag
    result = [(start_id, modifiers, key_code(item["key"]))]
    if item["key"] == "*":
        result.append((start_id + 1, modifiers, 0x6A))
    return tuple(result)


def collides(left, right) -> bool:
    """Detect actual Win32 hotkey collisions, including '*' and Shift+8."""
    a = {(mods, key) for _, mods, key in bindings(left)}
    b = {(mods, key) for _, mods, key in bindings(right)}
    return not a.isdisjoint(b)


def normalize_convert_hotkey(value, *, popup=None) -> dict:
    """Migrate legacy data and never register both Pocket actions on one key."""
    if (isinstance(value, dict) and value.get("key") in KEYS
            and all(type(value.get(k)) is bool for k in ("ctrl", "shift", "alt", "win"))
            and any(value[k] for k in ("ctrl", "alt", "win"))):
        candidate = normalize_hotkey(value)
    else:
        candidate = DEFAULT_CONVERT_HOTKEY.copy()
    # Old profiles stored Ctrl+Alt+F9 even when the user never customized it.
    # Upgrade that former factory combination to the new default.
    if candidate == _LEGACY_CONVERT_DEFAULT:
        candidate = DEFAULT_CONVERT_HOTKEY.copy()
    other = normalize_hotkey(popup)
    if collides(candidate, other):
        candidate = DEFAULT_CONVERT_HOTKEY.copy()
        # A user can configure the popup to the converter's default too.
        if collides(candidate, other):
            candidate["key"] = "F8"
            if collides(candidate, other):
                candidate["key"] = "F7"
    return candidate


def filter_shortcuts(items, query: str):
    """Case-insensitive search across shortcut title, target and kind."""
    needle = query.strip().casefold()
    if not needle:
        return list(items)
    return [item for item in items if needle in " ".join(
        str(item.get(field, "")) for field in ("title", "url", "kind")
    ).casefold()]
