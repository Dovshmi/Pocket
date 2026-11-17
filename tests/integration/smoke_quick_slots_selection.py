"""Windows integration: select text in a real Tk widget and save to Quick Slot.

Tests actual Win32 SendInput Ctrl+C, OLE clipboard preservation and the
foreground-window check, not just a mocked clipboard backend.
"""
from __future__ import annotations

from pathlib import Path
import ctypes
import os
import sys
import threading
import time
import tkinter as tk

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from pocket import quick_slots


def capture_while_ui_pumps(root, target_hwnd, *, timeout=5.0):
    finished = threading.Event()
    answer = {}
    def worker():
        try:
            answer["value"] = quick_slots.capture_selection_or_clipboard(
                target_hwnd=target_hwnd, owner_hwnd=root.winfo_id())
        except Exception as exc:
            answer["error"] = str(exc)
        finally:
            finished.set()
    thread = threading.Thread(target=worker, daemon=True)
    thread.start()
    end = time.monotonic() + timeout
    def poll():
        if finished.is_set() or time.monotonic() >= end:
            root.quit()
        else:
            root.after(15, poll)
    root.after(15, poll)
    # Tk clipboard formats can be rendered lazily from this UI thread.
    # A real mainloop is required; repeated update() alone is insufficient.
    root.mainloop()
    if not finished.is_set():
        raise AssertionError("Timed out waiting for Quick Slot selection capture")
    if "error" in answer:
        raise AssertionError("Quick Slot copy failed: " + answer["error"])
    return answer["value"]


def run():
    if os.name != "nt":
        print("SKIP: native Windows selection integration")
        return
    root = tk.Tk()
    root.geometry("530x200+150+150")
    root.title("Pocket Quick Slots selected text integration")
    entry = tk.Entry(root, font=("Segoe UI", 13), width=42)
    entry.pack(padx=18, pady=18)
    entry.insert(0, "POCKET_SELECTED_TEXT_1942")
    try:
        root.update()
        root.deiconify()
        root.lift()
        root.focus_force()
        entry.focus_force()
        root.update()
        user = ctypes.WinDLL("user32", use_last_error=True)
        user.GetForegroundWindow.restype = ctypes.c_void_p
        user.GetAncestor.argtypes = [ctypes.c_void_p, ctypes.c_uint]
        user.GetAncestor.restype = ctypes.c_void_p
        user.SetForegroundWindow.argtypes = [ctypes.c_void_p]
        user.SetForegroundWindow.restype = ctypes.c_int
        target_hwnd = user.GetAncestor(root.winfo_id(), 2)  # GA_ROOT
        user.SetForegroundWindow(target_hwnd)
        root.update()
        foreground = user.GetForegroundWindow()
        assert foreground == target_hwnd, (foreground, target_hwnd, root.winfo_id())

        root.clipboard_clear()
        root.clipboard_append("PREVIOUS_CLIPBOARD")
        root.update()

        entry.selection_range(0, len(entry.get()))
        entry.icursor(len(entry.get()))
        entry.focus_force()
        root.update()
        assert entry.selection_present(), "Entry must have active selection"
        captured = capture_while_ui_pumps(root, target_hwnd)
        assert captured == "POCKET_SELECTED_TEXT_1942", (captured, "selected")
        assert root.clipboard_get() == "PREVIOUS_CLIPBOARD"
        print("PASS: selected text copied through SendInput Ctrl+C and clipboard restored")

        entry.selection_clear()
        root.update()
        captured = capture_while_ui_pumps(root, target_hwnd)
        assert captured == "PREVIOUS_CLIPBOARD", (captured, "fallback")
        print("PASS: without selection, original clipboard remains the fallback")
    finally:
        root.destroy()


if __name__ == "__main__":
    run()
