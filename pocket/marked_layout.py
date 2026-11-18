"""Convert currently selected Windows text using the EN/HE keyboard mapping.

Mark mode is entirely local. It borrows the clipboard only during Ctrl+C /
Ctrl+V and uses OLE's IDataObject to preserve *all clipboard formats* (rather
than preserving only plain text and inadvertently deleting copied images).
No keyboard hook, dependency or persistent background clipboard monitor.
"""
from __future__ import annotations

from contextlib import contextmanager
import ctypes
from ctypes import wintypes
from dataclasses import dataclass
import os
import time


@dataclass(frozen=True)
class MarkResult:
    changed: bool
    message: str


class MarkError(RuntimeError):
    pass


class _KeyInput(ctypes.Structure):
    _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD),
                ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD),
                ("dwExtraInfo", ctypes.c_void_p)]


class _MouseInput(ctypes.Structure):
    _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG),
                ("mouseData", wintypes.DWORD), ("dwFlags", wintypes.DWORD),
                ("time", wintypes.DWORD), ("dwExtraInfo", ctypes.c_void_p)]


class _HardwareInput(ctypes.Structure):
    _fields_ = [("uMsg", wintypes.DWORD), ("wParamL", wintypes.WORD),
                ("wParamH", wintypes.WORD)]


class _InputUnion(ctypes.Union):
    _fields_ = [("ki", _KeyInput), ("mi", _MouseInput),
                ("hi", _HardwareInput)]


class _Input(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("value", _InputUnion)]


class WindowsMarkBackend:
    def __init__(self, owner_hwnd):
        if os.name != "nt":
            raise MarkError("Mark mode requires Windows.")
        self.owner_hwnd = owner_hwnd
        self.user = ctypes.WinDLL("user32", use_last_error=True)
        self.kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        self.ole = ctypes.OleDLL("ole32")
        self._configure()

    def _configure(self):
        user = self.user
        user.GetForegroundWindow.restype = ctypes.c_void_p
        user.GetClipboardSequenceNumber.restype = wintypes.DWORD
        user.GetAsyncKeyState.argtypes = [ctypes.c_int]
        user.GetAsyncKeyState.restype = ctypes.c_short
        user.SendInput.argtypes = [wintypes.UINT, ctypes.POINTER(_Input),
                                   ctypes.c_int]
        user.SendInput.restype = wintypes.UINT
        user.OpenClipboard.argtypes = [ctypes.c_void_p]
        user.OpenClipboard.restype = wintypes.BOOL
        user.CloseClipboard.restype = wintypes.BOOL
        user.CountClipboardFormats.restype = ctypes.c_int
        user.EmptyClipboard.restype = wintypes.BOOL
        user.GetClipboardData.argtypes = [wintypes.UINT]
        user.GetClipboardData.restype = ctypes.c_void_p
        user.SetClipboardData.argtypes = [wintypes.UINT, ctypes.c_void_p]
        user.SetClipboardData.restype = ctypes.c_void_p
        self.kernel.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
        self.kernel.GlobalAlloc.restype = ctypes.c_void_p
        self.kernel.GlobalLock.argtypes = [ctypes.c_void_p]
        self.kernel.GlobalLock.restype = ctypes.c_void_p
        self.kernel.GlobalUnlock.argtypes = [ctypes.c_void_p]
        self.kernel.GlobalUnlock.restype = wintypes.BOOL
        self.kernel.GlobalFree.argtypes = [ctypes.c_void_p]
        self.kernel.GlobalFree.restype = ctypes.c_void_p
        self.ole.OleGetClipboard.argtypes = [ctypes.POINTER(ctypes.c_void_p)]
        self.ole.OleGetClipboard.restype = ctypes.c_long
        self.ole.OleSetClipboard.argtypes = [ctypes.c_void_p]
        self.ole.OleSetClipboard.restype = ctypes.c_long
        self.ole.OleFlushClipboard.argtypes = []
        self.ole.OleFlushClipboard.restype = ctypes.c_long

    def foreground(self):
        return self.user.GetForegroundWindow()

    def sequence(self):
        return self.user.GetClipboardSequenceNumber()

    def wait_keys_up(self, timeout=1.2):
        deadline = time.monotonic() + timeout
        # Never send Ctrl+C while the original Ctrl+Alt+V is held.
        while time.monotonic() < deadline:
            if not any(self.user.GetAsyncKeyState(key) & 0x8000
                       for key in (0x11, 0x12, 0x56, 0x10, 0x5B, 0x5C, *range(0x60, 0x6A))):
                return True
            time.sleep(0.025)
        return False

    def settle_hotkey_release(self):
        """Let Ctrl+Win key-up events reach the focused app before Ctrl+C."""
        time.sleep(0.10)

    @contextmanager
    def preserve_clipboard(self):
        # A private COM apartment is used only for this single hotkey action.
        hr = self.ole.OleInitialize(None)
        if hr not in (0, 1):
            raise MarkError("Windows could not initialize clipboard preservation.")
        original = ctypes.c_void_p()
        try:
            try:
                snapshot_status = self.ole.OleGetClipboard(ctypes.byref(original))
            except OSError:
                snapshot_status = -1
            if snapshot_status != 0 or not original.value:
                # A genuinely empty clipboard needs no OLE data object. Mark
                # should still work on a machine without previous copied text.
                # Check while holding the clipboard lock. A failed format
                # count must not be mistaken for an empty clipboard.
                with self._opened():
                    if self.user.CountClipboardFormats() != 0:
                        raise MarkError("The current clipboard cannot be preserved safely.")

                def clear_empty_clipboard():
                    with self._opened(owner=True):
                        if not self.user.EmptyClipboard():
                            raise MarkError("Could not restore an empty clipboard.")
                yield clear_empty_clipboard
                return
            try:
                def restore():
                    if self.ole.OleSetClipboard(original) != 0:
                        raise MarkError("Could not restore the original clipboard.")
                    # Make the restored multi-format data independent of this
                    # worker's short-lived COM apartment before it exits.
                    if self.ole.OleFlushClipboard() != 0:
                        raise MarkError("Windows could not finalize clipboard restoration.")
                yield restore
            finally:
                # Release the IDataObject reference returned by OleGetClipboard.
                vtable = ctypes.cast(
                    original, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
                release = ctypes.WINFUNCTYPE(ctypes.c_ulong, ctypes.c_void_p)(
                    vtable[2])
                release(original)
        finally:
            self.ole.OleUninitialize()

    def send_key(self, letter):
        vk = ord(letter.upper())
        # Ctrl down, key down, key up, Ctrl up. One atomic SendInput batch.
        steps = (_KeyInput(0x11, 0, 0, 0, None),
                 _KeyInput(vk, 0, 0, 0, None),
                 _KeyInput(vk, 0, 2, 0, None),
                 _KeyInput(0x11, 0, 2, 0, None))
        batch = (_Input * len(steps))(
            *(_Input(1, _InputUnion(ki=step)) for step in steps))
        if self.user.SendInput(len(batch), batch, ctypes.sizeof(_Input)) != len(batch):
            raise MarkError("Windows did not allow the keyboard shortcut to reach the application.")

    def wait_for_sequence_change(self, baseline, timeout=1.0):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.sequence() != baseline:
                return True
            time.sleep(0.025)
        return False

    @contextmanager
    def _opened(self, owner=None):
        # Clipboard can be temporarily busy while the foreground app copies.
        hwnd = self.owner_hwnd if owner else None
        for _ in range(15):
            if self.user.OpenClipboard(hwnd):
                break
            time.sleep(0.025)
        else:
            raise MarkError("Clipboard is busy; try again.")
        try:
            yield
        finally:
            self.user.CloseClipboard()

    def read_text(self):
        with self._opened():
            handle = self.user.GetClipboardData(13)  # CF_UNICODETEXT
            if not handle:
                return None
            pointer = self.kernel.GlobalLock(handle)
            if not pointer:
                return None
            try:
                return ctypes.wstring_at(pointer)
            finally:
                self.kernel.GlobalUnlock(handle)

    def put_text(self, text):
        raw = (text + "\0").encode("utf-16-le")
        memory = self.kernel.GlobalAlloc(0x0002, len(raw))  # GMEM_MOVEABLE
        if not memory:
            raise MarkError("Windows cannot allocate clipboard memory.")
        try:
            pointer = self.kernel.GlobalLock(memory)
            if not pointer:
                raise MarkError("Windows could not write converted text.")
            try:
                ctypes.memmove(pointer, raw, len(raw))
            finally:
                self.kernel.GlobalUnlock(memory)
            with self._opened(owner=True):
                if not self.user.EmptyClipboard():
                    raise MarkError("Windows could not clear the temporary clipboard.")
                if not self.user.SetClipboardData(13, memory):
                    raise MarkError("Windows could not install converted text.")
                memory = None  # The Windows clipboard now owns this memory.
        finally:
            if memory:
                self.kernel.GlobalFree(memory)

    def send_text(self, text, *, target_hwnd=None):
        """Fallback: type UTF-16 text directly without touching the clipboard.

        KEYEVENTF_UNICODE enters text in most Windows edit controls. It is only
        used when the OLE clipboard snapshot failed *before* any paste or write.
        Protected or elevated targets may reject SendInput.
        """
        if not isinstance(text, str):
            raise MarkError("No text to insert.")
        utf16 = text.encode("utf-16-le")
        # SendInput preserves order within a batch; limit per-call allocation.
        for offset in range(0, len(utf16), 256):
            if target_hwnd and self.foreground() != target_hwnd:
                raise MarkError("The active window changed; stopped inserting text.")
            chunk = utf16[offset:offset + 256]
            inputs = []
            for index in range(0, len(chunk), 2):
                code_unit = int.from_bytes(chunk[index:index + 2], "little")
                inputs.extend((
                    _Input(1, _InputUnion(ki=_KeyInput(
                        0, code_unit, 0x0004, 0, None))),
                    _Input(1, _InputUnion(ki=_KeyInput(
                        0, code_unit, 0x0004 | 0x0002, 0, None))),
                ))
            batch = (_Input * len(inputs))(*inputs)
            sent = self.user.SendInput(
                len(batch), batch, ctypes.sizeof(_Input))
            if sent != len(batch):
                raise MarkError(
                    "Windows blocked direct text input; use Clipboard Only "
                    "in Settings, then press Ctrl+V.")

    def pause_after_paste(self):
        # Let the foreground program finish consuming text before restoring OLE.
        time.sleep(0.22)


def convert_selection(converter, *, target_hwnd, owner_hwnd=0, backend=None):
    """Copy selection, correct layout, replace it, restore original OLE clipboard.

    Abort without pasting when no fresh selection arrives, when focus moves, or
    when the mapping did not change the copied text. Never use the clipboard's
    old value as a substitute for a missing selection.
    """
    if backend is None:
        backend = WindowsMarkBackend(owner_hwnd)
    if not target_hwnd or backend.foreground() != target_hwnd:
        raise MarkError("The original text window is no longer active.")
    if not backend.wait_keys_up():
        raise MarkError("Release the shortcut keys and try again.")

    with backend.preserve_clipboard() as restore:
        copied_sequence = None
        own_sequence = None
        result = None
        try:
            before = backend.sequence()
            backend.send_key("C")
            if not backend.wait_for_sequence_change(before):
                result = MarkResult(False, "Select text first; no fresh copy was detected.")
            else:
                copied_sequence = own_sequence = backend.sequence()
                selected = backend.read_text()
                if not isinstance(selected, str) or not selected.strip():
                    result = MarkResult(False, "No selected text was found.")
                elif backend.foreground() != target_hwnd:
                    result = MarkResult(False, "The active window changed; text was not replaced.")
                else:
                    converted = converter(selected)
                    if converted == selected:
                        result = MarkResult(False, "Selected text needs no keyboard-layout correction.")
                    else:
                        # Avoid replacing the wrong field if another app wrote
                        # into the clipboard after Ctrl+C.
                        if backend.sequence() != copied_sequence:
                            result = MarkResult(False, "Clipboard changed during selection; paste cancelled.")
                        else:
                            backend.put_text(converted)
                            own_sequence = backend.sequence()
                            if backend.foreground() != target_hwnd:
                                result = MarkResult(False, "Active window changed; paste cancelled.")
                            else:
                                backend.send_key("V")
                                backend.pause_after_paste()
                                result = MarkResult(True, "Selected text corrected and pasted.")
        finally:
            # Do not overwrite a clipboard write from another application.
            if own_sequence is not None and backend.sequence() == own_sequence:
                restore()
        return result
