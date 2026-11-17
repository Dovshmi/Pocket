"""One-shot Win32 probe of the two Quick Slot prefixes (diagnostic only).

This does not press keys or intercept input. It verifies whether this runner's
Windows session accepts the exact 18 RegisterHotKey combinations. A failure
is reported clearly but not taken as a cross-machine guarantee.
"""
from __future__ import annotations

import ctypes
from ctypes import wintypes
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from pocket import quick_slots


def main():
    if os.name != "nt":
        print("SKIP: RegisterHotKey probe requires Windows")
        return
    user = ctypes.WinDLL("user32", use_last_error=True)
    user.RegisterHotKey.argtypes = [
        wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT]
    user.RegisterHotKey.restype = wintypes.BOOL
    user.UnregisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int]
    user.UnregisterHotKey.restype = wintypes.BOOL

    accepted = []
    rejected = []
    try:
        for hotkey_id, modifiers, key in quick_slots.slot_hotkeys():
            action, number = quick_slots.hotkey_action(hotkey_id)
            ctypes.set_last_error(0)
            if user.RegisterHotKey(None, hotkey_id, modifiers, key):
                accepted.append(hotkey_id)
                print(f"REGISTERED: {action} Numpad{number}")
            else:
                rejected.append((action, number, ctypes.get_last_error()))
                print(f"UNAVAILABLE: {action} Numpad{number}, Win32 error "
                      f"{ctypes.get_last_error()}")
    finally:
        for hotkey_id in accepted:
            user.UnregisterHotKey(None, hotkey_id)

    print(f"Quick Slots Windows registration probe: "
          f"{len(accepted)}/18 registered, {len(rejected)} unavailable")
    if rejected:
        print("NOTE: A reserved or occupied shortcut can vary by machine. "
              "Pocket keeps an available shortcut group active and explains "
              "when the other group is unavailable.")


if __name__ == "__main__":
    main()
