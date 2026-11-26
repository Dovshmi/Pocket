"""Local command palette preferences and monitor-safe geometry."""
from __future__ import annotations

DEFAULT_OPACITY = 95


def opacity(raw):
    if type(raw) is not int:
        return DEFAULT_OPACITY
    return max(60, min(100, raw))


def position(raw):
    if not isinstance(raw, dict):
        return None
    x, y = raw.get("x"), raw.get("y")
    if type(x) is not int or type(y) is not int or max(abs(x), abs(y)) > 100000:
        return None
    return {"x": x, "y": y}


def normalize(raw):
    raw = raw if isinstance(raw, dict) else {}
    remember = raw.get("palette_remember_position") is not False
    return {"palette_opacity": opacity(raw.get("palette_opacity")),
            "palette_remember_position": remember,
            "palette_position": position(raw.get("palette_position")) if remember else None}


def clamp(x, y, width, height, area):
    left, top, right, bottom = area
    return (max(left + 5, min(x, max(left + 5, right - width - 5))),
            max(top + 5, min(y, max(top + 5, bottom - height - 5))))


def dimensions(area, count):
    left, top, right, bottom = area
    width = min(550, max(180, right - left - 18))
    # Two-line rows, capped at six, plus the grip, search and footer.
    height = min(132 + 48 * max(1, min(6, count)), max(150, bottom - top - 18))
    return width, height


def window_xy(window):
    """Actual outer-window position, including negative monitor coordinates."""
    import sys
    if sys.platform == "win32":
        import ctypes
        from ctypes import wintypes
        user = ctypes.WinDLL("user32", use_last_error=True)
        user.GetAncestor.argtypes = (ctypes.c_void_p, ctypes.c_uint)
        user.GetAncestor.restype = ctypes.c_void_p
        user.GetWindowRect.argtypes = (ctypes.c_void_p, ctypes.POINTER(wintypes.RECT))
        user.GetWindowRect.restype = ctypes.c_int
        hwnd = user.GetAncestor(window.winfo_id(), 2) or window.winfo_id()
        rect = wintypes.RECT()
        if user.GetWindowRect(hwnd, ctypes.byref(rect)):
            return rect.left, rect.top
    return window.winfo_x(), window.winfo_y()


def move(window, x, y):
    """Tk negative geometry offsets are edge-relative, not absolute on Win32."""
    import sys
    if sys.platform == "win32" and window.winfo_ismapped():
        import ctypes
        user = ctypes.WinDLL("user32", use_last_error=True)
        user.GetAncestor.argtypes = (ctypes.c_void_p, ctypes.c_uint)
        user.GetAncestor.restype = ctypes.c_void_p
        user.SetWindowPos.argtypes = (ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int,
                                     ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_uint)
        user.SetWindowPos.restype = ctypes.c_int
        hwnd = user.GetAncestor(window.winfo_id(), 2) or window.winfo_id()
        if user.SetWindowPos(hwnd, None, x, y, 0, 0, 0x0001 | 0x0004 | 0x0010):
            return
    window.geometry(f"{x:+d}{y:+d}")


def apply_opacity(window, value):
    import tkinter as tk
    try:
        window.attributes("-alpha", opacity(value) / 100)
    except tk.TclError:
        pass


def remove_window_chrome(window):
    """Hide Win32 nonclient chrome without changing Tk window management.

    Keep the managed tool window and its activation semantics; do not switch
    the Windows palette to override-redirect or add WS_EX_NOACTIVATE.
    """
    import sys
    if sys.platform != "win32":
        return True
    import ctypes
    user = ctypes.WinDLL("user32", use_last_error=True)
    user.GetAncestor.argtypes = (ctypes.c_void_p, ctypes.c_uint)
    user.GetAncestor.restype = ctypes.c_void_p
    user.GetWindowLongW.argtypes = (ctypes.c_void_p, ctypes.c_int)
    user.GetWindowLongW.restype = ctypes.c_long
    user.SetWindowLongW.argtypes = (ctypes.c_void_p, ctypes.c_int, ctypes.c_long)
    user.SetWindowLongW.restype = ctypes.c_long
    user.SetWindowPos.argtypes = (ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int,
                                 ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_uint)
    user.SetWindowPos.restype = ctypes.c_int
    hwnd = user.GetAncestor(window.winfo_id(), 2) or window.winfo_id()
    # WS_CAPTION | WS_THICKFRAME | WS_SYSMENU | WS_MINIMIZEBOX | WS_MAXIMIZEBOX
    chrome = 0x00C00000 | 0x00040000 | 0x00080000 | 0x00020000 | 0x00010000
    style = user.GetWindowLongW(hwnd, -16)
    if style & chrome:
        user.SetWindowLongW(hwnd, -16, style & ~chrome)
        # SWP_FRAMECHANGED | NOMOVE | NOSIZE | NOZORDER | NOACTIVATE
        user.SetWindowPos(hwnd, None, 0, 0, 0, 0, 0x0020 | 0x0002 | 0x0001 | 0x0004 | 0x0010)
    return not bool(user.GetWindowLongW(hwnd, -16) & chrome)
