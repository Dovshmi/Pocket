"""Embedded native Windows EDIT/RichEdit input controls for Pocket.

These wrappers preserve the original Tk Entry/Text API (geometry, variables,
callbacks, selections) while hosting a real Win32 text control over the Tk
widget on Windows. Non-Windows platforms use Tk controls unchanged.

The Win32 subclass procedure NEVER calls into Tk. Native changes are pulled
into the Tk model by a lightweight timer on the Tcl event loop.
"""
from __future__ import annotations

import ctypes
import sys
import tkinter as tk
import weakref

_NATIVE_WIDGETS = weakref.WeakSet()
IS_WINDOWS = sys.platform == "win32"

# Control and message constants from the Windows API.
WS_CHILD, WS_VISIBLE, WS_TABSTOP = 0x40000000, 0x10000000, 0x00010000
ES_AUTOHSCROLL, ES_MULTILINE = 0x0080, 0x0004
ES_AUTOVSCROLL, ES_WANTRETURN, ES_NOHIDESEL = 0x0040, 0x1000, 0x0100
WM_SETTEXT, WM_GETTEXT, WM_GETTEXTLENGTH, WM_SETFONT = 0x000C, 0x000D, 0x000E, 0x0030
WM_CTLCOLOREDIT, WM_CTLCOLORSTATIC = 0x0133, 0x0138
WM_KEYDOWN, WM_SYSKEYDOWN, WM_SETFOCUS = 0x0100, 0x0104, 0x0007
WM_COPY, WM_CUT, WM_PASTE, WM_UNDO = 0x0301, 0x0300, 0x0302, 0x0304
EM_GETSEL, EM_SETSEL, EM_REDO, EM_SETREADONLY = 0x00B0, 0x00B1, 0x0454, 0x00CF
EM_SETBKGNDCOLOR = 0x0443
VK_CONTROL, VK_SHIFT = 0x11, 0x10
CALLBACK_TYPE = (ctypes.WINFUNCTYPE if IS_WINDOWS else None)


def _rgb(value, fallback):
    try:
        raw = str(value).lstrip("#")
        if len(raw) != 6:
            raise ValueError
        r, g, b = bytes.fromhex(raw)
        return r | (g << 8) | (b << 16)
    except (ValueError, TypeError):
        return _rgb(fallback, fallback) if value != fallback else 0


def has_native_focus():
    """True if any embedded Win32 input (including an in-app Toplevel) owns focus."""
    if not IS_WINDOWS:
        return False
    for widget in list(_NATIVE_WIDGETS):
        try:
            if widget.winfo_exists() and widget.has_native_focus():
                return True
        except (tk.TclError, RuntimeError):
            pass
    return False


def sync_all_native():
    """Flush pending Win32 text into StringVar before Tk button callbacks."""
    for widget in list(_NATIVE_WIDGETS):
        try:
            if widget.winfo_exists():
                widget.sync_native()
        except (tk.TclError, RuntimeError):
            pass


class _NativeMixin:
    """Win32 child lifetime, focus, font, color and model synchronization."""

    def _native_init(self, *, multiline=False, textvariable=None):
        self._native_hwnd = None
        self._native_active = False
        self._native_after = None
        self._native_last_focus = False
        self._native_last_text = ""
        self._native_multiline = multiline
        self._native_var = textvariable if isinstance(textvariable, tk.Variable) else None
        self._native_trace = None
        self._native_busy = False
        self._native_brush = None
        self._native_font = None
        self._native_parent_proc = None
        self._native_child_proc = None

        if not IS_WINDOWS:
            return
        try:
            self._u = ctypes.WinDLL("user32", use_last_error=True)
            self._g = ctypes.WinDLL("gdi32", use_last_error=True)
            self._cc = ctypes.WinDLL("comctl32", use_last_error=True)
            if multiline:
                self._richedit = ctypes.WinDLL("msftedit", use_last_error=True)
            self._configure_api()
            self._native_fg = _rgb(self.cget("fg"), "#F3F4FA")
            self._native_bg = _rgb(self.cget("bg"), "#161923")
            self._native_brush = self._g.CreateSolidBrush(self._native_bg)

            style = WS_CHILD | WS_VISIBLE | WS_TABSTOP | ES_NOHIDESEL
            if multiline:
                style |= ES_MULTILINE | ES_AUTOVSCROLL | ES_WANTRETURN
                if str(self.cget("wrap")) == "none":
                    style |= ES_AUTOHSCROLL
            else:
                style |= ES_AUTOHSCROLL

            cls = "RICHEDIT50W" if multiline else "EDIT"
            self._native_hwnd = self._u.CreateWindowExW(
                0, cls, "", style, 0, 0, 1, 1,
                ctypes.c_void_p(self.winfo_id()), None, None, None)
            if not self._native_hwnd:
                raise ctypes.WinError(ctypes.get_last_error())

            self._native_parent_proc = CALLBACK_TYPE(self._parent_message)
            self._native_child_proc = CALLBACK_TYPE(self._child_message)
            if not self._cc.SetWindowSubclass(
                    ctypes.c_void_p(self.winfo_id()),
                    self._native_parent_proc, 202, 0):
                raise ctypes.WinError(ctypes.get_last_error())
            self._native_parent_subclassed = True
            if not self._cc.SetWindowSubclass(
                    ctypes.c_void_p(self._native_hwnd),
                    self._native_child_proc, 203, 0):
                raise ctypes.WinError(ctypes.get_last_error())
            self._native_child_subclassed = True

            font_spec = self.cget("font")
            try:
                from tkinter import font as tkfont
                font = tkfont.Font(font=font_spec)
                face = font.actual("family")
                pixels = max(12, font.metrics("linespace"))
                weight = 700 if font.actual("weight") == "bold" else 400
            except (ValueError, tk.TclError, TypeError):
                face, pixels, weight = "Segoe UI", 16, 400
            self._native_font = self._g.CreateFontW(
                -pixels, 0, 0, 0, weight, 0, 0, 0, 1,
                0, 0, 0, 0, face)
            if self._native_font:
                self._send(WM_SETFONT, self._native_font, 1)
            if multiline:
                self._send(EM_SETBKGNDCOLOR, 0, self._native_bg)
            self._native_last_text = self._tk_value()
            self._write_native(self._native_last_text)
            self._native_active = True
            self.bind("<Configure>", self._native_resize, add="+")
            self.bind("<Destroy>", self._native_destroy, add="+")
            _NATIVE_WIDGETS.add(self)
            if self._native_var is not None:
                self._native_trace = self._native_var.trace_add(
                    "write", self._native_from_variable)
            self._native_after = self.after(45, self._native_tick)
        except (OSError, RuntimeError, tk.TclError, AttributeError) as exc:
            self._native_cleanup()
            # Keep the original working Tk control rather than aborting Pocket.
            print(f"Pocket native input unavailable; using Tk: {exc}", file=sys.stderr)

    def _configure_api(self):
        self._u.CreateWindowExW.argtypes = (
            ctypes.c_uint32, ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint32,
            ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
            ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p)
        self._u.CreateWindowExW.restype = ctypes.c_void_p
        self._u.SendMessageW.argtypes = (
            ctypes.c_void_p, ctypes.c_uint32, ctypes.c_size_t, ctypes.c_ssize_t)
        self._u.SendMessageW.restype = ctypes.c_ssize_t
        self._u.GetFocus.restype = ctypes.c_void_p
        self._u.SetFocus.argtypes = (ctypes.c_void_p,)
        self._u.SetFocus.restype = ctypes.c_void_p
        self._u.MoveWindow.argtypes = (
            ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int,
            ctypes.c_int, ctypes.c_int)
        self._u.DestroyWindow.argtypes = (ctypes.c_void_p,)
        self._g.CreateSolidBrush.argtypes = (ctypes.c_uint32,)
        self._g.CreateSolidBrush.restype = ctypes.c_void_p
        self._g.SetBkColor.argtypes = (ctypes.c_void_p, ctypes.c_uint32)
        self._g.SetTextColor.argtypes = (ctypes.c_void_p, ctypes.c_uint32)
        self._g.DeleteObject.argtypes = (ctypes.c_void_p,)
        self._g.CreateFontW.argtypes = (
            ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
            ctypes.c_int, ctypes.c_uint, ctypes.c_uint, ctypes.c_uint,
            ctypes.c_uint, ctypes.c_uint, ctypes.c_uint, ctypes.c_uint,
            ctypes.c_uint, ctypes.c_wchar_p)
        self._g.CreateFontW.restype = ctypes.c_void_p
        PROC = CALLBACK_TYPE(
            ctypes.c_ssize_t, ctypes.c_void_p, ctypes.c_uint32,
            ctypes.c_size_t, ctypes.c_ssize_t, ctypes.c_size_t, ctypes.c_size_t)
        self._PROC = PROC
        self._cc.SetWindowSubclass.argtypes = (
            ctypes.c_void_p, PROC, ctypes.c_size_t, ctypes.c_size_t)
        self._cc.SetWindowSubclass.restype = ctypes.c_int
        self._cc.RemoveWindowSubclass.argtypes = (
            ctypes.c_void_p, PROC, ctypes.c_size_t)
        self._cc.DefSubclassProc.argtypes = (
            ctypes.c_void_p, ctypes.c_uint32, ctypes.c_size_t, ctypes.c_ssize_t)
        self._cc.DefSubclassProc.restype = ctypes.c_ssize_t

    def _parent_message(self, hwnd, msg, wp, lp, sid, ref):
        """GDI calls only; no Tk from a Win32 window procedure."""
        if (msg in (WM_CTLCOLOREDIT, WM_CTLCOLORSTATIC)
                and lp == self._native_hwnd and self._native_brush):
            self._g.SetTextColor(ctypes.c_void_p(wp), self._native_fg)
            self._g.SetBkColor(ctypes.c_void_p(wp), self._native_bg)
            return int(self._native_brush)
        return self._cc.DefSubclassProc(hwnd, msg, wp, lp)

    def _child_message(self, hwnd, msg, wp, lp, sid, ref):
        """Win32 Ctrl+A is explicit; all other shortcuts remain OS-native."""
        if msg == WM_KEYDOWN and wp == ord("A"):
            if self._u.GetKeyState(VK_CONTROL) & 0x8000:
                self._u.SendMessageW(hwnd, EM_SETSEL, 0, -1)
                return 0
        return self._cc.DefSubclassProc(hwnd, msg, wp, lp)

    def _send(self, msg, wp=0, lp=0):
        if not self._native_hwnd:
            return 0
        return self._u.SendMessageW(
            ctypes.c_void_p(self._native_hwnd), msg, wp, lp)

    def _read_native(self):
        if not self._native_hwnd:
            return self._tk_value()
        size = self._send(WM_GETTEXTLENGTH)
        buffer = ctypes.create_unicode_buffer(max(64, min(size * 2 + 64, 2_100_000)))
        self._send(WM_GETTEXT, len(buffer), ctypes.addressof(buffer))
        return buffer.value.replace("\r\n", "\n") if self._native_multiline else buffer.value

    def _write_native(self, value):
        if not self._native_hwnd:
            return
        buffer = ctypes.create_unicode_buffer(value)
        self._send(WM_SETTEXT, 0, ctypes.addressof(buffer))
        self._native_last_text = value

    def _native_from_variable(self, *_):
        if not self._native_busy:
            self._sync_native_from_tk()

    def _sync_native_from_tk(self):
        if self._native_active and not self._native_busy:
            value = self._tk_value()
            if value != self._read_native():
                self._write_native(value)

    def has_native_focus(self):
        return bool(self._native_hwnd and
                    self._u.GetFocus() == self._native_hwnd)

    @property
    def native_hwnd(self):
        return self._native_hwnd if self._native_active else None

    def _native_resize(self, _event=None):
        if not self._native_active or not self._native_hwnd:
            return
        inset = max(0, int(self.cget("highlightthickness")))
        width = max(1, self.winfo_width() - inset * 2)
        height = max(1, self.winfo_height() - inset * 2)
        self._u.MoveWindow(
            ctypes.c_void_p(self._native_hwnd), inset, inset,
            width, height, True)

    def sync_native(self):
        if not self._native_active or self._native_busy:
            return
        value = self._read_native()
        if value == self._native_last_text and value == self._tk_value():
            return
        self._native_last_text = value
        if value != self._tk_value():
            self._native_busy = True
            try:
                self._put_tk_value(value)
            finally:
                self._native_busy = False

    def _native_tick(self):
        self._native_after = None
        if not self._native_active or not self.winfo_exists():
            return
        focused = self.has_native_focus()
        if focused or self._native_last_focus:
            self.sync_native()
        if focused != self._native_last_focus:
            self._native_last_focus = focused
            try:
                if focused:
                    # Preserve Pocket's Tk focus callbacks for search fields.
                    tk.Misc.focus_force(self)
                    self._u.SetFocus(ctypes.c_void_p(self._native_hwnd))
                    self.event_generate("<FocusIn>")
                else:
                    self.event_generate("<FocusOut>")
            except tk.TclError:
                pass
        self._native_after = self.after(45, self._native_tick)

    def _native_cleanup(self):
        self._native_active = False
        _NATIVE_WIDGETS.discard(self)
        job, self._native_after = self._native_after, None
        if job is not None:
            try:
                self.after_cancel(job)
            except (tk.TclError, RuntimeError):
                pass
        if self._native_trace and self._native_var is not None:
            try:
                self._native_var.trace_remove("write", self._native_trace)
            except (tk.TclError, RuntimeError):
                pass
            self._native_trace = None
        if getattr(self, "_native_child_subclassed", False) and self._native_hwnd:
            self._cc.RemoveWindowSubclass(
                ctypes.c_void_p(self._native_hwnd), self._native_child_proc, 203)
            self._native_child_subclassed = False
        if getattr(self, "_native_parent_subclassed", False):
            try:
                self._cc.RemoveWindowSubclass(
                    ctypes.c_void_p(self.winfo_id()), self._native_parent_proc, 202)
            except tk.TclError:
                pass
            self._native_parent_subclassed = False
        if self._native_hwnd:
            self._u.DestroyWindow(ctypes.c_void_p(self._native_hwnd))
            self._native_hwnd = None
        if self._native_font:
            self._g.DeleteObject(ctypes.c_void_p(self._native_font))
            self._native_font = None
        if self._native_brush:
            self._g.DeleteObject(ctypes.c_void_p(self._native_brush))
            self._native_brush = None

    def _native_destroy(self, event):
        if event.widget is self:
            self._native_cleanup()

    def focus_set(self):
        tk.Misc.focus_set(self)
        if self._native_active:
            self._u.SetFocus(ctypes.c_void_p(self._native_hwnd))

    def focus_force(self):
        tk.Misc.focus_force(self)
        if self._native_active:
            self._u.SetFocus(ctypes.c_void_p(self._native_hwnd))


class NativeEntry(_NativeMixin, tk.Entry):
    """Real Windows EDIT backed by the same StringVar and Entry API."""

    def __init__(self, master=None, **kwargs):
        var = kwargs.get("textvariable")
        super().__init__(master, **kwargs)
        self._native_init(multiline=False, textvariable=var)

    def _tk_value(self):
        return tk.Entry.get(self)

    def _put_tk_value(self, value):
        if self._native_var is not None:
            self._native_var.set(value)
        else:
            tk.Entry.delete(self, 0, tk.END)
            tk.Entry.insert(self, 0, value)

    def get(self):
        return self._read_native() if self._native_active else tk.Entry.get(self)

    def insert(self, index, string):
        result = tk.Entry.insert(self, index, string)
        self._sync_native_from_tk()
        return result

    def delete(self, first, last=None):
        result = tk.Entry.delete(self, first, last)
        self._sync_native_from_tk()
        return result

    def selection_range(self, start, end):
        tk.Entry.selection_range(self, start, end)
        if self._native_active:
            last = -1 if end == tk.END else int(end)
            self._send(EM_SETSEL, int(start), last)

    def selection_present(self):
        if not self._native_active:
            return tk.Entry.selection_present(self)
        start, end = ctypes.c_uint32(), ctypes.c_uint32()
        self._send(EM_GETSEL, ctypes.addressof(start), ctypes.addressof(end))
        return start.value != end.value

    def configure(self, cnf=None, **kwargs):
        result = tk.Entry.configure(self, cnf, **kwargs)
        if getattr(self, "_native_active", False):
            self._sync_native_from_tk()
            self._native_resize()
        return result

    config = configure


class NativeText(_NativeMixin, tk.Text):
    """Real Windows RichEdit for regular multiline input (MAC CLI output)."""

    def __init__(self, master=None, **kwargs):
        super().__init__(master, **kwargs)
        self._native_init(multiline=True)

    def _tk_value(self):
        return tk.Text.get(self, "1.0", "end-1c")

    def _put_tk_value(self, value):
        tk.Text.delete(self, "1.0", tk.END)
        tk.Text.insert(self, "1.0", value)

    def get(self, start, end=None):
        if self._native_active and start == "1.0" and end in ("end-1c", tk.END):
            value = self._read_native()
            return value + ("\n" if end == tk.END else "")
        return tk.Text.get(self, start, end)

    def insert(self, index, chars, *tags):
        result = tk.Text.insert(self, index, chars, *tags)
        self._sync_native_from_tk()
        return result

    def delete(self, index1, index2=None):
        result = tk.Text.delete(self, index1, index2)
        self._sync_native_from_tk()
        return result

    def configure(self, cnf=None, **kwargs):
        result = tk.Text.configure(self, cnf, **kwargs)
        if getattr(self, "_native_active", False):
            self._sync_native_from_tk()
            self._native_resize()
        return result

    config = configure


Entry = NativeEntry if IS_WINDOWS else tk.Entry
Text = NativeText if IS_WINDOWS else tk.Text
