"""Windows native Unicode/BiDi note editor.

Tk 8.6's Text widget only supports paragraph justification; it cannot handle
Hebrew + English editing/caret order reliably on Windows. RichEdit 4.1 is a
Windows inbox control with native Unicode bidirectional editing. This module
uses it ONLY for RTL notes; the existing Tk Text remains the LTR editor.

No separate install, web component, or network access is required.
"""
from __future__ import annotations

import ctypes
import queue
import sys
import tkinter as tk
from types import SimpleNamespace

# These structures use fixed Windows-size fields, including on 64-bit Python.
DWORD = ctypes.c_uint32
WORD = ctypes.c_uint16
LONG = ctypes.c_int32
SHORT = ctypes.c_int16
BYTE = ctypes.c_uint8


class PARAFORMAT(ctypes.Structure):
    _fields_ = [
        ("cbSize", DWORD), ("dwMask", DWORD), ("wNumbering", WORD),
        ("wEffects", WORD), ("dxStartIndent", LONG), ("dxRightIndent", LONG),
        ("dxOffset", LONG), ("wAlignment", WORD), ("cTabCount", SHORT),
        ("rgxTabs", LONG * 32),
    ]


class PARAFORMAT2(ctypes.Structure):
    _fields_ = PARAFORMAT._fields_ + [
        ("dySpaceBefore", LONG), ("dySpaceAfter", LONG), ("dyLineSpacing", LONG),
        ("sStyle", SHORT), ("bLineSpacingRule", BYTE), ("bOutlineLevel", BYTE),
        ("wShadingWeight", WORD), ("wShadingStyle", WORD),
        ("wNumberingStart", WORD), ("wNumberingStyle", WORD),
        ("wNumberingTab", WORD), ("wBorderSpace", WORD),
        ("wBorderWidth", WORD), ("wBorders", WORD),
    ]


class CHARFORMATW(ctypes.Structure):
    _fields_ = [
        ("cbSize", DWORD), ("dwMask", DWORD), ("dwEffects", DWORD),
        ("yHeight", LONG), ("yOffset", LONG), ("crTextColor", DWORD),
        ("bCharSet", BYTE), ("bPitchAndFamily", BYTE),
        ("szFaceName", ctypes.c_wchar * 32),
    ]


def colorref(hex_color: str) -> int:
    """Convert Tk RGB (#RRGGBB) to a Win32 0x00BBGGRR COLORREF."""
    rgb = bytes.fromhex(hex_color.lstrip("#"))
    if len(rgb) != 3:
        raise ValueError("Expected six-digit RGB color")
    return rgb[0] | (rgb[1] << 8) | (rgb[2] << 16)


class NativeBidiEditor(tk.Frame):
    """A Tk container for a Windows RichEdit control (logical Unicode text)."""

    WM_USER = 0x0400
    WM_SETTEXT, WM_GETTEXT, WM_GETTEXTLENGTH, WM_SETFONT = 0x000C, 0x000D, 0x000E, 0x0030
    WM_CONTEXTMENU, WM_NCDESTROY = 0x007B, 0x0082
    WM_COPY, WM_CUT, WM_PASTE, WM_UNDO = 0x0301, 0x0300, 0x0302, 0x0304
    EM_GETSEL, EM_SETSEL, EM_REPLACESEL = 0x00B0, 0x00B1, 0x00C2
    EM_GETSELTEXT = WM_USER + 62
    EM_REDO = WM_USER + 84
    EM_CANREDO = WM_USER + 85
    EM_SETPARAFORMAT = WM_USER + 71
    EM_SETBKGNDCOLOR = WM_USER + 67
    EM_SETCHARFORMAT = WM_USER + 68
    EM_EXLIMITTEXT = WM_USER + 53
    PFM_ALIGNMENT, PFM_RTLPARA = 0x00000008, 0x00010000

    def __init__(self, parent, *, background: str, foreground: str,
                 context_menu=None):
        if sys.platform != "win32":
            raise OSError("Native RichEdit requires Windows")
        super().__init__(parent, bg=background, highlightthickness=0, bd=0)
        self._context_menu = context_menu
        # Windows calls SUBCLASSPROC synchronously from its own message loop.
        # Do not enter Tcl/Tk from that ctypes callback: queue the coordinates
        # and let a normal Tk timer construct/post the existing context menu.
        self._context_menu_events = queue.SimpleQueue()
        self._menu_timer = None
        self._user = ctypes.WinDLL("user32", use_last_error=True)
        self._gdi = ctypes.WinDLL("gdi32", use_last_error=True)
        self._comctl = ctypes.WinDLL("comctl32", use_last_error=True)
        # Registers the inbox RICHEDIT50W class.
        self._msftedit = ctypes.WinDLL("msftedit", use_last_error=True)

        self._user.CreateWindowExW.argtypes = (
            ctypes.c_uint32, ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint32,
            ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
            ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p)
        self._user.CreateWindowExW.restype = ctypes.c_void_p
        self._user.SendMessageW.argtypes = (ctypes.c_void_p, ctypes.c_uint32,
                                           ctypes.c_size_t, ctypes.c_ssize_t)
        self._user.SendMessageW.restype = ctypes.c_ssize_t
        self._user.MoveWindow.argtypes = (ctypes.c_void_p, ctypes.c_int, ctypes.c_int,
                                         ctypes.c_int, ctypes.c_int, ctypes.c_int)
        self._user.DestroyWindow.argtypes = (ctypes.c_void_p,)
        self._user.GetWindowTextLengthW.argtypes = (ctypes.c_void_p,)
        self._user.GetWindowTextLengthW.restype = ctypes.c_int
        self._user.GetFocus.restype = ctypes.c_void_p
        self._user.SetFocus.argtypes = (ctypes.c_void_p,)
        self._gdi.CreateFontW.argtypes = (ctypes.c_int, ctypes.c_int, ctypes.c_int,
                                         ctypes.c_int, ctypes.c_int, ctypes.c_uint,
                                         ctypes.c_uint, ctypes.c_uint, ctypes.c_uint,
                                         ctypes.c_uint, ctypes.c_uint, ctypes.c_uint,
                                         ctypes.c_uint, ctypes.c_wchar_p)
        self._gdi.CreateFontW.restype = ctypes.c_void_p
        self._gdi.DeleteObject.argtypes = (ctypes.c_void_p,)

        WS_CHILD, WS_VISIBLE, WS_VSCROLL = 0x40000000, 0x10000000, 0x00200000
        ES_MULTILINE, ES_AUTOVSCROLL, ES_WANTRETURN = 0x0004, 0x0040, 0x1000
        WS_TABSTOP = 0x00010000
        style = (WS_CHILD | WS_VISIBLE | WS_VSCROLL | WS_TABSTOP |
                 ES_MULTILINE | ES_AUTOVSCROLL | ES_WANTRETURN)
        self._hwnd = self._user.CreateWindowExW(
            0, "RICHEDIT50W", "", style, 0, 0, 1, 1,
            self.winfo_id(), None, None, None)
        if not self._hwnd:
            raise ctypes.WinError(ctypes.get_last_error())
        self._send(self.EM_EXLIMITTEXT, 0, 2_000_000)
        self._send(self.EM_SETBKGNDCOLOR, 0, colorref(background))

        self._font = self._gdi.CreateFontW(
            -15, 0, 0, 0, 400, 0, 0, 0, 1, 0, 0, 0, 0, "Segoe UI")
        if self._font:
            self._send(self.WM_SETFONT, self._font, 1)
        fmt = CHARFORMATW()
        fmt.cbSize = ctypes.sizeof(fmt)
        fmt.dwMask = 0x40000000  # CFM_COLOR
        fmt.crTextColor = colorref(foreground)
        self._send(self.EM_SETCHARFORMAT, 0, ctypes.addressof(fmt))

        # Subclass only for Pocket's existing right-click menu. Keep a strong
        # Python reference and remove the subclass before HWND destruction.
        PROC = ctypes.WINFUNCTYPE(ctypes.c_ssize_t, ctypes.c_void_p,
                                 ctypes.c_uint32, ctypes.c_size_t,
                                 ctypes.c_ssize_t, ctypes.c_size_t, ctypes.c_size_t)
        self._callback = PROC(self._subclass_proc)
        self._comctl.SetWindowSubclass.argtypes = (
            ctypes.c_void_p, PROC, ctypes.c_size_t, ctypes.c_size_t)
        self._comctl.SetWindowSubclass.restype = ctypes.c_int
        self._comctl.RemoveWindowSubclass.argtypes = (ctypes.c_void_p, PROC, ctypes.c_size_t)
        self._comctl.DefSubclassProc.argtypes = (ctypes.c_void_p, ctypes.c_uint32,
                                                ctypes.c_size_t, ctypes.c_ssize_t)
        self._comctl.DefSubclassProc.restype = ctypes.c_ssize_t
        self._subclass_id = 101
        if not self._comctl.SetWindowSubclass(self._hwnd, self._callback, self._subclass_id, 0):
            self._user.DestroyWindow(self._hwnd)
            self._hwnd = None
            raise ctypes.WinError(ctypes.get_last_error())
        self.bind("<Configure>", self._resize, add="+")
        self.bind("<Destroy>", self._on_destroy, add="+")
        self._menu_timer = self.after(25, self._dispatch_context_menus)

    def _send(self, message: int, wparam=0, lparam=0) -> int:
        return self._user.SendMessageW(self._hwnd, message, wparam, lparam)

    def _resize(self, event):
        if self._hwnd:
            self._user.MoveWindow(self._hwnd, 0, 0,
                                  max(1, event.width), max(1, event.height), True)

    def _subclass_proc(self, hwnd, message, wp, lp, subclass_id, ref_data):
        """Win32 callback: no Tk calls, no exceptions across the ctypes boundary.

        Entering Tk from a native window procedure may re-enter its event loop
        during mouse/focus handling and terminate the whole Python process.
        Only marshal screen coordinates; the Tk timer does the actual work.
        """
        if message == self.WM_CONTEXTMENU and self._context_menu is not None:
            try:
                # LPARAM is two signed 16-bit desktop coordinates. -1/-1 is
                # the keyboard context-menu key, handled by the Tk side.
                x = ctypes.c_short(lp & 0xffff).value
                y = ctypes.c_short((lp >> 16) & 0xffff).value
                self._context_menu_events.put((x, y))
                return 0
            except Exception:
                # A ctypes callback must always return an LRESULT.
                return 0
        return self._comctl.DefSubclassProc(hwnd, message, wp, lp)

    def _dispatch_context_menus(self):
        """Show Pocket's context menu only from the normal Tk event loop."""
        self._menu_timer = None
        event_coords = None
        try:
            # Collapse duplicate WM_CONTEXTMENU messages for the same click.
            while True:
                event_coords = self._context_menu_events.get_nowait()
        except queue.Empty:
            pass
        if event_coords is not None and self._context_menu is not None and self._hwnd:
            x, y = event_coords
            if x == -1 and y == -1:
                x = self.winfo_rootx() + 25
                y = self.winfo_rooty() + 25
            try:
                self._context_menu(SimpleNamespace(x_root=x, y_root=y))
            except (tk.TclError, RuntimeError) as exc:
                # Tk errors must never escape a callback into Windows.
                print(f"Pocket note menu error: {exc}", file=sys.stderr)
        if self._hwnd and self.winfo_exists():
            self._menu_timer = self.after(25, self._dispatch_context_menus)

    def _on_destroy(self, event):
        if event.widget is not self:
            return
        if self._menu_timer is not None:
            try:
                self.after_cancel(self._menu_timer)
            except tk.TclError:
                pass
            self._menu_timer = None
        if self._hwnd:
            self._comctl.RemoveWindowSubclass(self._hwnd, self._callback, self._subclass_id)
            self._user.DestroyWindow(self._hwnd)
            self._hwnd = None
        if self._font:
            self._gdi.DeleteObject(self._font)
            self._font = None

    def has_focus(self) -> bool:
        return bool(self._hwnd and self._user.GetFocus() == self._hwnd)

    def focus_set(self):
        if self._hwnd:
            self._user.SetFocus(self._hwnd)

    def release_focus_to(self, widget):
        """Explicitly transfer native keyboard focus to a Tk navigation control.

        RichEdit has its own child HWND, outside Tk's widget focus machinery.
        Calling Tk.focus_set() alone does not always clear GetFocus() for this
        HWND. Transfer focus from the Tk event loop (never a Win32 subclass
        callback) so arrow keys reach Pocket's normal Tk bindings again.
        """
        if self._hwnd and widget.winfo_exists():
            self._user.SetFocus(ctypes.c_void_p(widget.winfo_id()))

    def get_text(self) -> str:
        if not self._hwnd:
            return ""
        # Room for CRLF conversion plus Unicode surrogates.
        length = self._user.GetWindowTextLengthW(self._hwnd)
        buffer = ctypes.create_unicode_buffer(max(64, length * 2 + 64))
        self._send(self.WM_GETTEXT, len(buffer), ctypes.addressof(buffer))
        return buffer.value.replace("\r\n", "\n").replace("\r", "\n")

    def set_text(self, text: str):
        buffer = ctypes.create_unicode_buffer(text.replace("\r\n", "\n"))
        self._send(self.WM_SETTEXT, 0, ctypes.addressof(buffer))

    def selection_range(self) -> tuple[int, int]:
        start, end = DWORD(), DWORD()
        self._send(self.EM_GETSEL, ctypes.addressof(start), ctypes.addressof(end))
        return start.value, end.value

    def get_selected(self) -> str:
        start, end = self.selection_range()
        if start == end:
            return ""
        buffer = ctypes.create_unicode_buffer(max(64, (end - start) * 2 + 64))
        self._send(self.EM_GETSELTEXT, 0, ctypes.addressof(buffer))
        return buffer.value.replace("\r\n", "\n").replace("\r", "\n")

    def select_all(self):
        self._send(self.EM_SETSEL, 0, -1)

    def replace_selection(self, text: str):
        buffer = ctypes.create_unicode_buffer(text)
        self._send(self.EM_REPLACESEL, 1, ctypes.addressof(buffer))

    def edit_action(self, operation: str):
        messages = {"undo": self.WM_UNDO, "redo": self.EM_REDO,
                    "cut": self.WM_CUT, "copy": self.WM_COPY,
                    "paste": self.WM_PASTE}
        self._send(messages[operation])

    def set_direction(self, direction: str):
        """Set actual Unicode paragraph flow, not merely right justification."""
        start, end = self.selection_range()
        self.select_all()
        para = PARAFORMAT2()
        para.cbSize = ctypes.sizeof(para)
        para.dwMask = self.PFM_ALIGNMENT | self.PFM_RTLPARA
        para.wAlignment = 2 if direction == "rtl" else 1  # PFA_RIGHT/LEFT
        para.wEffects = 1 if direction == "rtl" else 0  # PFE_RTLPARA
        if not self._send(self.EM_SETPARAFORMAT, 0, ctypes.addressof(para)):
            raise RuntimeError("Could not set RichEdit paragraph direction")
        self._send(self.EM_SETSEL, start, end)
