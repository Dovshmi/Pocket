"""Local-only, temporary Tk key-chord capture for Pocket Settings.

No global keyboard hooks, polling loops, stored keystroke logs or network use.
The Toplevel only listens while Record Shortcut has focus.
"""
from __future__ import annotations
import os
import re

from . import hotkey_settings as hk

_MODIFIER_KEYSYMS = frozenset((
    "Control_L", "Control_R", "Shift_L", "Shift_R",
    "Alt_L", "Alt_R", "Meta_L", "Meta_R", "Super_L", "Super_R",
    "Win_L", "Win_R", "ISO_Level3_Shift",
))
_NUMPAD = re.compile(r"KP_([1-9])$")
_PREFIXES = {
    (True, False, True, False): "ctrl_alt",
    (True, False, False, False): "ctrl",
    (True, False, False, True): "ctrl_win",
    (True, False, True, True): "ctrl_alt_win",
}


def modifiers(state, keysym="", async_mods=None):
    """Honor Tk masks; Windows native state fills Win/Alt gaps."""
    flags = {
        "ctrl": bool(state & 0x0004),
        "shift": bool(state & 0x0001),
        "alt": bool(state & 0x0008),
        "win": bool(state & 0x0040),
    }
    # Tk keysyms may not expose the Win state on some Windows builds.
    if async_mods is None and os.name == "nt":
        try:
            import ctypes
            win = ctypes.WinDLL("user32")
            win.GetAsyncKeyState.argtypes = [ctypes.c_int]
            win.GetAsyncKeyState.restype = ctypes.c_short
            async_mods = {
                "ctrl": any(win.GetAsyncKeyState(n) & 0x8000
                            for n in (0x11, 0xA2, 0xA3)),
                "shift": any(win.GetAsyncKeyState(n) & 0x8000
                             for n in (0x10, 0xA0, 0xA1)),
                "alt": any(win.GetAsyncKeyState(n) & 0x8000
                           for n in (0x12, 0xA4, 0xA5)),
                "win": any(win.GetAsyncKeyState(n) & 0x8000
                           for n in (0x5B, 0x5C)),
            }
        except (OSError, AttributeError):
            async_mods = {}
    for key in flags:
        if async_mods and async_mods.get(key):
            flags[key] = True
    if keysym.startswith("Control"):
        flags["ctrl"] = True
    elif keysym.startswith("Shift"):
        flags["shift"] = True
    elif keysym.startswith("Alt"):
        flags["alt"] = True
    elif keysym.startswith(("Meta", "Super", "Win")):
        flags["win"] = True
    return flags


def key_from_event(keysym, char=""):
    if keysym in _MODIFIER_KEYSYMS:
        return None
    if keysym in ("asterisk", "KP_Multiply"):
        return "*"
    if keysym in ("space", "Space"):
        return "Space"
    if re.fullmatch(r"F(?:[1-9]|1[0-2])", keysym):
        return keysym
    if len(keysym) == 1 and keysym.upper() in hk.KEYS:
        return keysym.upper()
    if len(char) == 1 and char.upper() in hk.KEYS:
        return char.upper()
    return None


def hotkey_from_event(keysym, char="", state=0, *, async_mods=None):
    """Returns None for modifier-only input, raises for unsupported chords."""
    if keysym in _MODIFIER_KEYSYMS:
        return None
    key = key_from_event(keysym, char)
    if key is None:
        raise ValueError("Unsupported key. Use a letter, digit, F1–F12, Space or *.")
    flags = modifiers(state, keysym, async_mods)
    if not (flags["ctrl"] or flags["alt"] or flags["win"]):
        raise ValueError("Include Ctrl, Alt or Win in the shortcut.")
    return {**flags, "key": key}


def quick_slot_prefix_from_event(keysym, state=0, *, async_mods=None):
    """Numpad1–9 is mandatory: capture only its modifiers."""
    if keysym in _MODIFIER_KEYSYMS:
        return None
    if not _NUMPAD.fullmatch(keysym):
        raise ValueError("Press modifiers together with Numpad1–9 (Num Lock ON).")
    flags = modifiers(state, keysym, async_mods)
    value = (flags["ctrl"], flags["shift"], flags["alt"], flags["win"])
    prefix = _PREFIXES.get(value)
    if prefix is None:
        raise ValueError("Use Ctrl, Ctrl+Alt, Ctrl+Win or Ctrl+Alt+Win; no Shift.")
    return prefix
