"""Verify actual Windows input routing, not merely Tk's focus_get()."""
import ctypes
from pathlib import Path
import sys
import time
import tkinter as tk
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from pocket import command_palette_ui, native_inputs, native_bidi


def run():
    if sys.platform != "win32":
        return
    root = tk.Tk()
    root.geometry("600x450+100+100")
    root.attributes("-topmost", True)
    app = SimpleNamespace(root=root, theme="blue", _modal=False,
                          data={"notes": [], "links": []}, command_library=[],
                          settings={"visible_tabs": ["notes", "extra", "ports"]},
                          _screen_work_area=lambda x, y: (0, 0, 1200, 900))
    root._pocket_palette_callback = lambda: command_palette_ui.open_palette(app)
    user = ctypes.WinDLL("user32", use_last_error=True)
    user.GetFocus.restype = ctypes.c_void_p
    user.GetAncestor.argtypes = (ctypes.c_void_p, ctypes.c_uint)
    user.GetAncestor.restype = ctypes.c_void_p
    user.keybd_event.argtypes = (ctypes.c_ubyte, ctypes.c_ubyte, ctypes.c_uint32, ctypes.c_size_t)

    def pump(seconds=.15):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            root.update()
            time.sleep(.01)

    def test_source(source, getter, hwnd, send):
        print("Testing source:", type(source).__name__, flush=True)
        source.focus_force() if hasattr(source, "native_hwnd") else source.focus_set()
        pump()
        assert user.GetFocus() == hwnd, "Source must have real Windows focus"
        before = getter()
        state = (ctypes.c_ubyte * 256)()
        assert user.GetKeyboardState(state)
        ctrl = (ctypes.c_ubyte * 256)(*state)
        ctrl[0x11] |= 0x80
        try:
            assert user.SetKeyboardState(ctrl)
            send(0x0100, ord("K"), 0)
            send(0x0102, 11, 0)
        finally:
            user.SetKeyboardState(state)
        pump(.25)
        dialog = app._quick_search_dialog
        assert dialog is not None and dialog.winfo_exists(), "Ctrl+K did not open palette"
        entry = app._palette_entry
        assert entry.native_hwnd, "Palette must use a real Windows EDIT"
        assert user.GetFocus() == entry.native_hwnd, f"Keyboard focus {user.GetFocus()} is not palette HWND {entry.native_hwnd}"
        assert user.GetFocus() != hwnd, "Source still owns actual keyboard focus"
        assert user.GetAncestor(user.GetFocus(), 2) == user.GetAncestor(dialog.winfo_id(), 2), "Keyboard not in palette window"
        # Actual keyboard input (not entry.insert or a widget-targeted Tk event).
        user.keybd_event(ord("Q"), 0, 0, 0)
        user.keybd_event(ord("Q"), 0, 2, 0)
        pump()
        assert entry.get(), "Real keystroke did not reach search field"
        assert getter() == before, "Search typing changed the original field"
        user.keybd_event(0x1B, 0, 0, 0)
        user.keybd_event(0x1B, 0, 2, 0)
        pump()
        assert app._quick_search_dialog is None
        assert root._pocket_palette_target is None

    try:
        entry = native_inputs.Entry(root)
        entry.pack(fill="x")
        entry.insert(0, "Original entry")
        multi = native_inputs.Text(root, height=3)
        multi.pack(fill="x")
        multi.insert("1.0", "Original multiline")
        bidi = native_bidi.NativeBidiEditor(root, background="#161923", foreground="#F3F4FA")
        bidi.pack(fill="both", expand=True)
        app.bidi_editor = bidi
        pump()
        bidi.set_text("Original note")
        for source, getter, hwnd, send in (
            (entry, entry.get, entry.native_hwnd, entry._send),
            (multi, lambda: multi.get("1.0", "end-1c"), multi.native_hwnd, multi._send),
            (bidi, bidi.get_text, bidi._hwnd, bidi._send),
        ):
            assert hwnd, "Expected real native control"
            test_source(source, getter, hwnd, send)
        print("PASS: Ctrl+K transfers real keyboard input from EDIT, RichEdit and Notes")
    finally:
        root.destroy()


if __name__ == "__main__":
    run()
