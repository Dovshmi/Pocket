"""Windows integration: actual Quick Slot auto paste and clipboard-only flow.

Run against a real foreground Tk text control on a Windows CI desktop.
"""
from __future__ import annotations

import ctypes
import os
from pathlib import Path
import sys
import threading
import time
import tkinter as tk

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from pocket import quick_slots, marked_layout, keyboard_layout, native_inputs


def run_on_worker(root, action):
    complete = threading.Event()
    result = {}

    def worker():
        try:
            result["return"] = action()
        except Exception as exc:
            result["error"] = repr(exc)
        finally:
            complete.set()

    threading.Thread(target=worker, daemon=True).start()
    limit = time.monotonic() + 8

    def poll():
        if complete.is_set() or time.monotonic() >= limit:
            root.quit()
        else:
            root.after(15, poll)

    root.after(15, poll)
    # The GUI thread must pump messages while Windows clipboard data is
    # rendered and SendInput reaches the actual entry widget.
    root.mainloop()
    if not complete.is_set():
        raise AssertionError("Timed out on Windows Quick Slot paste")
    if "error" in result:
        raise AssertionError("Windows Quick Slot paste failed: " + result["error"])


def run(*, mark_diagnostic=False):
    if os.name != "nt":
        print("SKIP: requires real Windows clipboard and input")
        return
    root = tk.Tk()
    root.title("Pocket 1.39.3 independent Quick Slot modes")
    root.geometry("560x190+140+140")
    entry = tk.Entry(root, width=48, font=("Segoe UI", 13))
    entry.pack(padx=14, pady=24)
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
        target = user.GetAncestor(root.winfo_id(), 2)  # GA_ROOT
        user.SetForegroundWindow(target)
        root.update()
        assert user.GetForegroundWindow() == target, "Test foreground changed"

        entry.delete(0, tk.END)
        entry.focus_force()
        root.clipboard_clear()
        root.clipboard_append("PREVIOUS_CLIPBOARD_CONTENT")
        root.update()
        run_on_worker(root, lambda: quick_slots.paste_slot_text(
            "PASTED_1391", target_hwnd=target, owner_hwnd=root.winfo_id()))
        root.update()
        assert entry.get() == "PASTED_1391", entry.get()
        assert root.clipboard_get() == "PREVIOUS_CLIPBOARD_CONTENT", (
            "Auto paste must preserve the previous clipboard")
        print("PASS: real Windows ASCII Auto Paste inserts and preserves clipboard")

        # Some enterprise and remote controls replace KEYEVENTF_UNICODE
        # Hebrew with '?' instead of text. Non-ASCII must use CF_UNICODETEXT
        # and actual Ctrl+V, without OLE clipboard preservation.
        for multilingual in ("שלום עולם 123 English", "עברית עברית — مرحبا"):
            entry.delete(0, tk.END)
            entry.focus_force()
            root.clipboard_clear()
            root.clipboard_append("PREVIOUS_BEFORE_UNICODE")
            root.update()
            run_on_worker(root, lambda value=multilingual: quick_slots.paste_slot_text(
                value, target_hwnd=target, owner_hwnd=root.winfo_id()))
            root.update()
            assert entry.get() == multilingual, (
                f"Unicode auto-paste changed text: {entry.get()!r}")
            assert root.clipboard_get() == multilingual, (
                "Unicode copy must remain on clipboard for normal Ctrl+V")
        print("PASS: real Windows Hebrew/Arabic Unicode clipboard auto-paste")

        entry.delete(0, tk.END)
        entry.focus_force()
        root.update()
        run_on_worker(root, lambda: quick_slots.copy_slot_to_clipboard(
            "MANUAL_1391", owner_hwnd=root.winfo_id()))
        assert entry.get() == "", "Clipboard-only mode must not auto-paste"
        assert root.clipboard_get() == "MANUAL_1391", (
            "Clipboard-only must stage actual Windows clipboard text")
        print("PASS: real Windows clipboard-only stages text without pasting")

        # Save behavior: existing clipboard is read directly; never inject
        # Ctrl+C or alter the target field (useful for protected apps).
        entry.delete(0, tk.END)
        root.clipboard_clear()
        root.clipboard_append("שלום מהקליפבורד 123")
        root.update()
        capture = {}
        def save_from_clipboard():
            capture["text"] = quick_slots.read_existing_clipboard(
                owner_hwnd=root.winfo_id())
        run_on_worker(root, save_from_clipboard)
        assert capture["text"] == "שלום מהקליפבורד 123", capture
        assert root.clipboard_get() == capture["text"]
        assert entry.get() == "", "Use Current Clipboard must not auto-copy"
        print("PASS: manual Save reads existing Hebrew clipboard without Ctrl+C")

        if not mark_diagnostic:
            return

        # Real selected-text conversion in both ordinary Tk and Pocket's
        # embedded Win32 EDIT control. The clipboard must survive, the
        # original foreground window must remain active, and Quick Slots
        # must still paste after the conversion returns.
        native_entry = native_inputs.Entry(root, width=48)
        native_entry.pack(padx=14, pady=4)
        root.update()
        assert native_entry.native_hwnd, "Expected native Pocket edit control"
        user.GetFocus.restype = ctypes.c_void_p
        for field in (entry, native_entry):
            for original in ("akuo", "שלום"):
                field.delete(0, tk.END)
                field.insert(0, original)
                field.focus_force()
                field.selection_range(0, tk.END)
                root.clipboard_clear()
                root.clipboard_append("KEEP_ORIGINAL_CLIPBOARD")
                root.update()
                assert user.GetForegroundWindow() == target
                original_focus = user.GetFocus()
                assert original_focus, "No active edit control"
                result = {}
                def correct():
                    result["mark"] = marked_layout.convert_selection(
                        keyboard_layout.convert, target_hwnd=target,
                        owner_hwnd=owner_hwnd)
                owner_hwnd = root.winfo_id()
                run_on_worker(root, correct)
                root.update()
                assert result["mark"].changed, result["mark"]
                assert field.get() == keyboard_layout.convert(original), field.get()
                assert root.clipboard_get() == "KEEP_ORIGINAL_CLIPBOARD"
                assert user.GetForegroundWindow() == target, "Conversion changed foreground"
                assert user.GetFocus() == original_focus, "Conversion changed focused control"

                field.delete(0, tk.END)
                field.focus_force()
                root.update()
                run_on_worker(root, lambda: quick_slots.paste_slot_text(
                    "AFTER_MARK", target_hwnd=target, owner_hwnd=owner_hwnd))
                root.update()
                assert field.get() == "AFTER_MARK", field.get()
        print("PASS: real Windows Mark conversion preserves focus and clipboard; Quick Slots still paste")
    finally:
        root.destroy()


if __name__ == "__main__":
    run(mark_diagnostic="--mark-diagnostic" in sys.argv[1:])
