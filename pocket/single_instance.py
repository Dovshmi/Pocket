"""Windows single-instance guard for Pocket (standard library only).

A session-local named mutex prevents two running copies of Pocket from writing
the same local data. A named auto-reset event lets a second launch reveal the
already-running tray window. No network, persistent lockfile or polling port.
"""
from __future__ import annotations

import ctypes
import sys
import threading
import time


# 'Local' keeps separate Windows logon sessions independent, but covers every
# Pocket folder and both Python and packaged EXE launches in that session.
MUTEX_NAME = "Local\\PocketDesk-SingleInstance-v1"
ACTIVATE_EVENT_NAME = "Local\\PocketDesk-Activate-v1"
ERROR_ALREADY_EXISTS = 183
EVENT_MODIFY_STATE = 0x0002
WAIT_OBJECT_0 = 0
WAIT_TIMEOUT = 0x102
WAIT_FAILED = 0xFFFFFFFF


def _win32_kernel():
    """Load properly typed Win32 HANDLE functions (64-bit safe)."""
    from ctypes import wintypes

    api = ctypes.WinDLL("kernel32", use_last_error=True)
    api.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
    api.CreateMutexW.restype = wintypes.HANDLE
    api.CreateEventW.argtypes = [ctypes.c_void_p, wintypes.BOOL,
                                 wintypes.BOOL, wintypes.LPCWSTR]
    api.CreateEventW.restype = wintypes.HANDLE
    api.OpenEventW.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.LPCWSTR]
    api.OpenEventW.restype = wintypes.HANDLE
    api.SetEvent.argtypes = [wintypes.HANDLE]
    api.SetEvent.restype = wintypes.BOOL
    api.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    api.WaitForSingleObject.restype = wintypes.DWORD
    api.CloseHandle.argtypes = [wintypes.HANDLE]
    api.CloseHandle.restype = wintypes.BOOL
    return api


class WindowsSingleInstance:
    """Acquire before reading user data or initializing Tk.

    Call start() with a thread-safe callback (e.g. Queue.put), and close()
    when the mainloop exits. Preview sessions deliberately bypass this guard
    in the app entry point.
    """

    def __init__(self, *, kernel=None, get_last_error=None, sleep=None):
        if kernel is None and sys.platform != "win32":
            raise OSError("Windows single-instance guard requires Windows")
        self._kernel = kernel if kernel is not None else _win32_kernel()
        self._get_last_error = get_last_error if get_last_error is not None else ctypes.get_last_error
        self._sleep = sleep if sleep is not None else time.sleep
        self._mutex = None
        self._activation_event = None
        self._listener = None
        self._stop = threading.Event()

    def acquire(self) -> bool:
        """True for primary, False for duplicate (which signals the primary).

        Fail closed if Windows can't create the synchronization primitives:
        allowing two unsynchronized instances could corrupt saved notes.
        """
        if self._mutex is not None:
            return True
        mutex = self._kernel.CreateMutexW(None, False, MUTEX_NAME)
        if not mutex:
            raise OSError(f"CreateMutexW failed (Windows error {self._get_last_error()})")
        if self._get_last_error() == ERROR_ALREADY_EXISTS:
            self._kernel.CloseHandle(mutex)
            self._notify_primary()
            return False

        try:
            event = self._kernel.CreateEventW(None, False, False, ACTIVATE_EVENT_NAME)
            if not event:
                raise OSError(f"CreateEventW failed (Windows error {self._get_last_error()})")
        except BaseException:
            self._kernel.CloseHandle(mutex)
            raise

        self._mutex = mutex
        self._activation_event = event
        return True

    def _notify_primary(self):
        # The second process can race with the first creating its event.
        # Retry briefly, then exit either way; never spawn a second Pocket.
        for attempt in range(12):
            event = self._kernel.OpenEventW(EVENT_MODIFY_STATE, False, ACTIVATE_EVENT_NAME)
            if event:
                try:
                    self._kernel.SetEvent(event)
                finally:
                    self._kernel.CloseHandle(event)
                return
            if attempt < 11:
                self._sleep(0.05)

    def start(self, on_activate):
        """Listen on a worker; on_activate must NOT touch tkinter directly."""
        if self._activation_event is None:
            raise RuntimeError("Acquire the single-instance mutex before listening")
        if self._listener is not None:
            return
        self._stop.clear()
        self._listener = threading.Thread(
            target=self._listen, args=(on_activate,),
            daemon=True, name="PocketInstanceActivation")
        self._listener.start()

    def _listen(self, on_activate):
        while not self._stop.is_set():
            result = self._kernel.WaitForSingleObject(self._activation_event, 200)
            if result == WAIT_OBJECT_0:
                if not self._stop.is_set():
                    on_activate()
            elif result == WAIT_FAILED:
                break

    def close(self):
        """Release the Windows objects on exit; safe to call repeatedly."""
        self._stop.set()
        if self._listener is not None:
            if self._listener is not threading.current_thread():
                self._listener.join(timeout=1.0)
            self._listener = None
        if self._activation_event is not None:
            self._kernel.CloseHandle(self._activation_event)
            self._activation_event = None
        if self._mutex is not None:
            self._kernel.CloseHandle(self._mutex)
            self._mutex = None
