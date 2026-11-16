"""Incremental keyboard navigation for Pocket's existing readonly dropdowns.

Do not filter or replace their option lists. A posted ttk Combobox moves
keyboard focus into an internal Listbox: only *highlight* the matching row
while the popup is open. The stock Enter/click binding commits the choice,
keeping the list open and the user's multi-letter typing uninterrupted.
"""
from __future__ import annotations

import time
import tkinter as tk
import sys
import ctypes
from types import SimpleNamespace

TYPEAHEAD_TIMEOUT = 1.15


def find_match(values, query, *, selected=-1, cycle=False):
    """Prefer case-insensitive prefix matches, then substring matches.

    Notes keep their visual pinned-star marker; it is ignored for searching.
    """
    needle = str(query).strip().casefold()
    if not needle:
        return -1
    labels = [str(value).removeprefix("★ ").casefold() for value in values]
    for predicate in (lambda label: label.startswith(needle),
                      lambda label: needle in label):
        indices = [i for i, label in enumerate(labels) if predicate(label)]
        if indices:
            if cycle and len(needle) == 1 and selected in indices and len(indices) > 1:
                return indices[(indices.index(selected) + 1) % len(indices)]
            return indices[0]
    return -1


def _character(event):
    """Allow native Tk Unicode events and simple keysym-only fallbacks."""
    char = getattr(event, "char", "")
    if not char:
        key = str(getattr(event, "keysym", ""))
        if len(key) == 1:
            char = key
    if len(char) != 1 or not char.isprintable() or char in "\r\n\t":
        return ""
    return char


class _Win32PopupKeys:
    """Capture real WM_CHAR on Tk's private dropdown Listbox HWND.

    Tcl synthetic <KeyPress> tests do not exercise Windows' real keyboard
    messages. A Native Win32 RichEdit child can leave actual Windows keyboard
    routing different from Tk focus; the listbox HWND needs a direct handler.

    Never call Tk inside a Windows subclass procedure. Capture only Unicode
    characters and deliver them from the regular Tk event loop.
    """

    WM_CHAR = 0x0102
    WM_KEYDOWN = 0x0100
    VK_BACK = 0x08
    VK_CONTROL = 0x11
    VK_MENU = 0x12

    def __init__(self, widget, listing, callback):
        self.widget = widget
        self.listing = listing
        self.callback = callback
        self.pending = []
        self.installed = False
        self._after = None
        self._posted = False
        self._child = None
        self._proc = None
        self._tag = id(self) & 0xFFFFFFFF

        if sys.platform != "win32":
            return
        try:
            self._u = ctypes.WinDLL("user32", use_last_error=True)
            self._cc = ctypes.WinDLL("comctl32", use_last_error=True)
            self._u.GetKeyState.argtypes = (ctypes.c_int,)
            self._u.GetKeyState.restype = ctypes.c_short
            self._u.GetFocus.restype = ctypes.c_void_p
            self._u.SetFocus.argtypes = (ctypes.c_void_p,)
            self._u.SetFocus.restype = ctypes.c_void_p
            proc_type = ctypes.WINFUNCTYPE(
                ctypes.c_ssize_t, ctypes.c_void_p, ctypes.c_uint32,
                ctypes.c_size_t, ctypes.c_ssize_t, ctypes.c_size_t,
                ctypes.c_size_t)
            self._PROC = proc_type
            self._cc.SetWindowSubclass.argtypes = (
                ctypes.c_void_p, proc_type, ctypes.c_size_t, ctypes.c_size_t)
            self._cc.SetWindowSubclass.restype = ctypes.c_int
            self._cc.RemoveWindowSubclass.argtypes = (
                ctypes.c_void_p, proc_type, ctypes.c_size_t)
            self._cc.DefSubclassProc.argtypes = (
                ctypes.c_void_p, ctypes.c_uint32, ctypes.c_size_t,
                ctypes.c_ssize_t)
            self._cc.DefSubclassProc.restype = ctypes.c_ssize_t
            self._child = ctypes.c_void_p(
                int(str(widget.tk.call("winfo", "id", listing)), 0))
            self._proc = proc_type(self._window_proc)
            if not self._cc.SetWindowSubclass(self._child, self._proc,
                                              self._tag, 0):
                return
            self.installed = True
            self._after = widget.after(25, self._poll)
        except (ValueError, RuntimeError, AttributeError, OSError, tk.TclError):
            self.installed = False

    def _popup_visible(self):
        try:
            return bool(int(self.widget.tk.call(
                "winfo", "ismapped", self.listing)))
        except (RuntimeError, tk.TclError, ValueError):
            return False

    def _ensure_keyboard_focus(self):
        # Tcl's focus command can succeed while Windows GetFocus still
        # points to the previous Win32 RichEdit child. Real keyboard input
        # then never arrives at the popup even though the dropdown is visible.
        # SetFocus must run in the window-owning Tk/UI thread, never from the
        # Windows subclass procedure.
        if self.installed and self._popup_visible():
            if self._u.GetFocus() != self._child.value:
                self._u.SetFocus(self._child)

    def on_map(self, _event=None):
        if self.installed:
            self.widget.after_idle(self._ensure_keyboard_focus)

    def _window_proc(self, hwnd, msg, wp, lp, sid, ref):
        if msg == self.WM_CHAR:
            # Do not swallow shortcut chords or nonprintable control chars.
            control = bool(self._u.GetKeyState(self.VK_CONTROL) & 0x8000)
            alt = bool(self._u.GetKeyState(self.VK_MENU) & 0x8000)
            if (not control or alt) and wp >= 32 and wp != 127:
                try:
                    self.pending.append(chr(wp))
                    # Prevent Tcl's Listbox keyboard binding from acting on
                    # the same character a second time.
                    return 0
                except (ValueError, OverflowError):
                    pass
        elif msg == self.WM_KEYDOWN and wp == self.VK_BACK:
            self.pending.append("\b")
            return 0
        return self._cc.DefSubclassProc(hwnd, msg, wp, lp)

    def _poll(self):
        self._after = None
        try:
            if not self.widget.winfo_exists():
                return
            posted = self._popup_visible()
            if posted and not self._posted:
                self._ensure_keyboard_focus()
            self._posted = posted
            todo, self.pending = self.pending, []
            for char in todo:
                if char == "\b":
                    self.callback(SimpleNamespace(char="", keysym="BackSpace",
                                                  state=0))
                else:
                    self.callback(SimpleNamespace(char=char, keysym=char,
                                                  state=0))
            self._after = self.widget.after(25, self._poll)
        except (RuntimeError, tk.TclError):
            return

    def close(self):
        if self._after is not None:
            try:
                self.widget.after_cancel(self._after)
            except (RuntimeError, tk.TclError):
                pass
            self._after = None
        if self.installed:
            self._cc.RemoveWindowSubclass(self._child, self._proc, self._tag)
            self.installed = False


def install(widget, *, time_source=time.monotonic):
    """Add non-destructive type-to-jump to a ttk.Combobox.

    The entry remains readonly and its full options remain intact. When the
    dropdown is open, typeahead moves only the visible Listbox highlight and
    scrolls to it. Enter or clicking an item uses Tk's existing selection
    bindings and triggers Pocket's usual <<ComboboxSelected>> handler.
    """
    typed = ""
    last_key = None
    last_at = -float("inf")
    listing = None

    # The Tcl popdown is created on demand; ensure it exists at install time.
    # On non-Aqua systems its listbox path is the same on Windows and Linux.
    try:
        popdown = widget.tk.call("ttk::combobox::PopdownWindow", str(widget))
        candidate = str(popdown) + ".f.l"
        if widget.tk.call("winfo", "exists", candidate):
            listing = candidate
    except (AttributeError, RuntimeError, tk.TclError):
        pass

    def popup_open():
        if not listing:
            return False
        try:
            return bool(int(widget.tk.call("winfo", "ismapped", listing)))
        except (ValueError, RuntimeError, tk.TclError):
            return False

    def popup_selection():
        if not listing:
            return widget.current()
        try:
            indices = widget.tk.splitlist(widget.tk.call(listing, "curselection"))
            return int(indices[0]) if indices else widget.current()
        except (ValueError, RuntimeError, tk.TclError):
            return widget.current()

    def highlight(index):
        if not listing:
            return False
        try:
            widget.tk.call(listing, "selection", "clear", 0, "end")
            widget.tk.call(listing, "selection", "set", index)
            widget.tk.call(listing, "activate", index)
            widget.tk.call(listing, "see", index)
        except (ValueError, RuntimeError, tk.TclError):
            return False
        return True

    def on_key(event):
        nonlocal typed, last_key, last_at
        # AltGr sends Ctrl+Alt on Windows. Do not commandeer accelerators.
        if getattr(event, "state", 0) & 0x000C:
            return None
        key = str(getattr(event, "keysym", ""))
        if key in ("Escape", "Return", "Tab", "Up", "Down", "Left", "Right"):
            if key == "Escape":
                typed = ""
                last_key = None
            return None
        if key == "BackSpace":
            if typed:
                typed = typed[:-1]
                last_at = time_source()
                if typed:
                    values = widget["values"]
                    if isinstance(values, str):
                        values = widget.tk.splitlist(values)
                    match = find_match(values, typed)
                    if match >= 0:
                        if popup_open():
                            highlight(match)
                        elif match != widget.current():
                            widget.current(match)
                            widget.event_generate("<<ComboboxSelected>>")
                return "break"
            return None
        char = _character(event)
        if not char:
            return None

        now = time_source()
        if now - last_at > TYPEAHEAD_TIMEOUT:
            typed = ""
            last_key = None
        values = widget["values"]
        if isinstance(values, str):
            values = widget.tk.splitlist(values)
        opened = popup_open()
        selected = popup_selection() if opened else widget.current()
        repeated = typed == char and char == last_key
        tentative = char if repeated else typed + char
        match = find_match(values, tentative, selected=selected, cycle=repeated)
        if match < 0:
            tentative = char
            match = find_match(values, tentative, selected=selected)
        typed = tentative
        last_key = char
        last_at = now
        if match >= 0:
            if opened:
                # Crucial: never call current() or generate ComboboxSelected
                # while the popdown is posted. Doing so changes Notes/Commands
                # and steals popup focus before the rest of the name is typed.
                highlight(match)
            elif match != selected:
                widget.current(match)
                widget.event_generate("<<ComboboxSelected>>")
        return "break"

    # The main widget receives keys while the dropdown is closed.
    widget.bind("<KeyPress>", on_key, add="+")
    if listing:
        try:
            # This is a real Tcl Listbox owned by ttk; also listen to Windows
            # character messages from its HWND, not only synthetic Tk events.
            bridge = _Win32PopupKeys(widget, listing, on_key)
            widget._pocket_typeahead_win32 = bridge
            widget._pocket_typeahead_popdown = listing

            def popup_key(event):
                if bridge.installed:
                    # Actual Windows printable characters are delivered by
                    # WM_CHAR. Keep Tcl keyboard events for other keys.
                    if _character(event):
                        return "break"
                    if str(getattr(event, "keysym", "")) == "BackSpace":
                        return "break"
                return on_key(event)

            widget._bind(("bind", listing), "<KeyPress>", popup_key, add="+")
            # The Tcl Listbox <Map> class binding sets Tk focus but may leave
            # the actual OS keyboard focus on an embedded native edit HWND.
            widget._bind(("bind", listing), "<Map>", bridge.on_map, add="+")

            def cleanup(event):
                if event.widget is widget:
                    bridge.close()

            widget.bind("<Destroy>", cleanup, add="+")
        except (AttributeError, RuntimeError, tk.TclError):
            pass

    widget._pocket_typeahead = on_key
    return widget
