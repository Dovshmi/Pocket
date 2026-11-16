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
from tkinter import font as tkfont
from types import SimpleNamespace

from .native_bidi import CHARFORMATW

_NATIVE_WIDGETS = weakref.WeakSet()
IS_WINDOWS = sys.platform == "win32"

# Control and message constants from the Windows API.
WS_CHILD, WS_VISIBLE, WS_TABSTOP = 0x40000000, 0x10000000, 0x00010000
ES_AUTOHSCROLL, ES_MULTILINE = 0x0080, 0x0004
ES_AUTOVSCROLL, ES_WANTRETURN, ES_NOHIDESEL = 0x0040, 0x1000, 0x0100
WM_SETTEXT, WM_GETTEXT, WM_GETTEXTLENGTH, WM_SETFONT = 0x000C, 0x000D, 0x000E, 0x0030
WM_CTLCOLOREDIT, WM_CTLCOLORSTATIC = 0x0133, 0x0138
WM_KEYDOWN, WM_CHAR, WM_SYSKEYDOWN, WM_SETFOCUS = 0x0100, 0x0102, 0x0104, 0x0007
WM_CONTEXTMENU, WM_KILLFOCUS, WM_MOUSEWHEEL = 0x007B, 0x0008, 0x020A
EM_SETCHARFORMAT, CFM_COLOR, SCF_ALL = 0x0444, 0x40000000, 0x0004
WM_COPY, WM_CUT, WM_PASTE, WM_UNDO = 0x0301, 0x0300, 0x0302, 0x0304
WM_CLEAR = 0x0303
EM_CANUNDO, EM_CANREDO = 0x00C6, 0x0455
EM_GETSEL, EM_SETSEL, EM_REDO, EM_SETREADONLY = 0x00B0, 0x00B1, 0x0454, 0x00CF
EM_SETBKGNDCOLOR = 0x0443
EM_EXLIMITTEXT = 0x0435  # WM_USER + 53; match Pocket's large-note editor
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
        self._native_pending_ctrl_return = False
        self._native_skip_ctrl_return_char = False
        self._native_var = textvariable if isinstance(textvariable, tk.Variable) else None
        self._native_trace = None
        self._native_busy = False
        self._native_brush = None
        self._native_font = None
        self._native_parent_proc = None
        self._native_child_proc = None
        self._native_parent_subclassed = False
        self._native_child_subclassed = False
        self._native_context_point = None
        self._native_font_key = None
        self._native_pending_focus = None
        self._native_menu_requested = False
        self._native_placeholder = None
        self._native_focus_callback = None

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

            self._native_parent_proc = self._PROC(self._parent_message)
            self._native_child_proc = self._PROC(self._child_message)
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

            face, pixels, weight = self._native_font_metrics()
            self._native_font = self._g.CreateFontW(
                -pixels, 0, 0, 0, weight, 0, 0, 0, 1,
                0, 0, 0, 0, face)
            self._native_font_key = str(self.cget("font"))
            if self._native_font:
                self._send(WM_SETFONT, self._native_font, 1)
            if multiline:
                # Default RichEdit limits can truncate pasted switch MAC tables.
                self._send(EM_EXLIMITTEXT, 0, 2_000_000)
                self._send(EM_SETBKGNDCOLOR, 0, self._native_bg)
                self._native_set_rich_foreground()
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
        """Native callback: marshal context requests; never enter Tk here."""
        if msg == WM_CONTEXTMENU:
            # No Windows default menu: Pocket's compact Tk menu is shown from
            # _native_tick, outside the Win32 subclass callback.
            x = ctypes.c_short(lp & 0xFFFF).value
            y = ctypes.c_short((lp >> 16) & 0xFFFF).value
            self._native_context_point = (x, y)
            self._native_menu_requested = True
            return 0
        if msg == WM_SETFOCUS:
            self._native_pending_focus = True
            # Clear placeholder inside the native control before the first
            # keystroke. The deferred Tk FocusIn callback may come too late.
            if (self._native_placeholder is not None
                    and self._read_native() == self._native_placeholder):
                self._write_native("")
        elif msg == WM_KILLFOCUS:
            self._native_pending_focus = False
        if msg == WM_KEYDOWN and self._u.GetKeyState(VK_CONTROL) & 0x8000:
            if wp == ord("A"):
                self._u.SendMessageW(hwnd, EM_SETSEL, 0, -1)
                return 0
            if wp == 0x0D and self._native_multiline:
                # Command editor Ctrl+Enter: marshal to the Tk event loop.
                self._native_pending_ctrl_return = True
                self._native_skip_ctrl_return_char = True
                return 0
        if msg == WM_CHAR and self._native_skip_ctrl_return_char:
            self._native_skip_ctrl_return_char = False
            if wp in (10, 13):
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

    def _native_font_metrics(self):
        """CreateFontW needs character height, not Tk's taller line spacing.

        Tk's positive font sizes are points; negative sizes are pixels.
        Matching the actual Tk pixel size preserves the original compact UI.
        """
        try:
            ft = tkfont.Font(root=self, font=self.cget("font"))
            size = int(ft.actual("size"))
            pixels = (round(size * self.winfo_fpixels("1p"))
                      if size > 0 else abs(size))
            return (ft.actual("family"), max(9, pixels),
                    700 if ft.actual("weight") == "bold" else 400)
        except (ValueError, tk.TclError, TypeError):
            return ("Segoe UI", 13, 400)

    def _native_set_rich_foreground(self):
        """RichEdit does not honor WM_CTLCOLOREDIT's text color.

        Use CHARFORMATW for the entire document, as Pocket's note editor does.
        """
        if not self._native_multiline or not self._native_hwnd:
            return
        fmt = CHARFORMATW()
        fmt.cbSize = ctypes.sizeof(fmt)
        fmt.dwMask = CFM_COLOR
        fmt.crTextColor = self._native_fg
        self._send(EM_SETCHARFORMAT, SCF_ALL, ctypes.addressof(fmt))

    def set_native_placeholder(self, text, on_focus=None):
        """Track an existing search hint and its real Windows focus callback.

        Win32 child focus does not reliably appear in Tk's focus_get(); the
        callback is invoked from the Tcl timer, never the Win32 subclass.
        """
        self._native_placeholder = str(text) if text is not None else None
        self._native_focus_callback = on_focus

    def _native_clear_placeholder_on_focus(self):
        if (self._native_focus_callback is not None
                and self._native_var is not None
                and self._native_placeholder is not None
                and self._native_var.get() == self._native_placeholder):
            self._native_focus_callback()

    def native_has_selection(self):
        if not self._native_active:
            return False
        first, last = ctypes.c_uint32(), ctypes.c_uint32()
        self._send(EM_GETSEL, ctypes.addressof(first), ctypes.addressof(last))
        return first.value != last.value

    def native_can_undo(self):
        return bool(self._native_active and self._send(EM_CANUNDO))

    def native_can_redo(self):
        return bool(self._native_active and self._native_multiline
                    and self._send(EM_CANREDO))

    def native_action(self, operation):
        """Edit through the real Win32 control, not the hidden Tk backing field."""
        if not self._native_active:
            return False
        commands = {"copy": WM_COPY, "cut": WM_CUT, "paste": WM_PASTE,
                    "undo": WM_UNDO, "redo": EM_REDO, "delete": WM_CLEAR}
        if operation == "select_all":
            self._send(EM_SETSEL, 0, -1)
            return True
        if operation not in commands:
            return False
        if operation not in ("copy",) and str(self.cget("state")) in ("disabled", "readonly"):
            return False
        self._send(commands[operation])
        if operation in ("cut", "paste", "undo", "redo", "delete"):
            self.sync_native()
        return True

    def _native_refresh_style(self):
        """Honor runtime theme, font and read-only changes on the Win32 HWND."""
        if not self._native_active or not self._native_hwnd:
            return
        fg = _rgb(self.cget("fg"), "#F3F4FA")
        bg = _rgb(self.cget("bg"), "#161923")
        if fg != self._native_fg or bg != self._native_bg:
            self._native_fg, self._native_bg = fg, bg
            if self._native_brush:
                self._g.DeleteObject(ctypes.c_void_p(self._native_brush))
            self._native_brush = self._g.CreateSolidBrush(bg)
            if self._native_multiline:
                self._send(EM_SETBKGNDCOLOR, 0, bg)
                self._native_set_rich_foreground()
            self._u.InvalidateRect(ctypes.c_void_p(self._native_hwnd), None, True)
        new_font_key = str(self.cget("font"))
        if new_font_key != self._native_font_key:
            try:
                face, pixels, weight = self._native_font_metrics()
                new_font = self._g.CreateFontW(
                    -pixels, 0, 0, 0, weight, 0, 0, 0, 1,
                    0, 0, 0, 0, face)
                if new_font:
                    self._send(WM_SETFONT, new_font, 1)
                    if self._native_font:
                        self._g.DeleteObject(ctypes.c_void_p(self._native_font))
                    self._native_font = new_font
                    self._native_font_key = new_font_key
            except (ValueError, TypeError, tk.TclError):
                pass
        state = str(self.cget("state"))
        self._send(EM_SETREADONLY, int(state in ("disabled", "readonly")), 0)
        self._u.EnableWindow(
            ctypes.c_void_p(self._native_hwnd), state != "disabled")

    def _native_from_variable(self, *_):
        # Tcl variable traces may run before the underlying Tk Entry's own
        # trace. Read StringVar directly: tk.Entry.get() can still be stale.
        if not self._native_busy and self._native_active and self._native_var is not None:
            value = self._native_var.get()
            if value != self._read_native():
                self._write_native(value)

    def _sync_native_from_tk(self):
        if self._native_active and not self._native_busy:
            # A StringVar trace may run before Tk's internal Entry trace.
            # Never copy a stale hidden Tk Entry value back over a newer
            # native value (the cause of the sticky CLI search placeholder).
            value = (self._native_var.get() if self._native_var is not None
                     else self._tk_value())
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
        # Tk Text uses padx/pady *inside* its border; the Win32 child needs
        # the same inset instead of covering the padding and labels.
        if self._native_multiline:
            px, py = int(self.cget("padx")), int(self.cget("pady"))
        else:
            px, py = 0, 0
        x, y = inset + px, inset + py
        width = max(1, self.winfo_width() - 2 * x)
        height = max(1, self.winfo_height() - 2 * y)
        self._u.MoveWindow(
            ctypes.c_void_p(self._native_hwnd), x, y,
            width, height, True)

    def sync_native(self):
        if not self._native_active or self._native_busy:
            return
        value = self._read_native()
        current = (self._native_var.get() if self._native_var is not None
                   else self._tk_value())
        if value == self._native_last_text and value == current:
            return
        self._native_last_text = value
        if value != current:
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
        if focused:
            self._native_clear_placeholder_on_focus()
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
        if self._native_pending_ctrl_return:
            self._native_pending_ctrl_return = False
            # Never enter Tk from the native window subclass callback.
            self.event_generate("<Control-Return>")
        if self._native_menu_requested:
            self._native_menu_requested = False
            point, self._native_context_point = self._native_context_point, None
            if point is not None:
                x, y = point
                if x == -1 and y == -1:
                    x, y = self.winfo_rootx() + 16, self.winfo_rooty() + 12
                try:
                    self.event_generate(
                        "<Button-3>", x=x - self.winfo_rootx(),
                        y=y - self.winfo_rooty(),
                        rootx=x, rooty=y, when="tail")
                except tk.TclError:
                    pass
        if self._native_active and self.winfo_exists():
            self._native_after = self.after(35, self._native_tick)

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
            self._native_clear_placeholder_on_focus()

    def focus_force(self):
        tk.Misc.focus_force(self)
        if self._native_active:
            self._u.SetFocus(ctypes.c_void_p(self._native_hwnd))
            self._native_clear_placeholder_on_focus()


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
            self._native_refresh_style()
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

    def tag_add(self, tag_name, index1, *indices):
        result = tk.Text.tag_add(self, tag_name, index1, *indices)
        if (self._native_active and tag_name == "sel" and
                index1 == "1.0" and indices and indices[0] in ("end-1c", tk.END)):
            self._send(EM_SETSEL, 0, -1)
        return result

    def mark_set(self, mark_name, index):
        result = tk.Text.mark_set(self, mark_name, index)
        if self._native_active and mark_name == "insert" and index in ("end-1c", tk.END):
            self._send(EM_SETSEL, -1, -1)
        return result

    def configure(self, cnf=None, **kwargs):
        result = tk.Text.configure(self, cnf, **kwargs)
        if getattr(self, "_native_active", False):
            self._sync_native_from_tk()
            self._native_refresh_style()
            self._native_resize()
        return result

    config = configure


Entry = NativeEntry if IS_WINDOWS else tk.Entry
Text = NativeText if IS_WINDOWS else tk.Text
