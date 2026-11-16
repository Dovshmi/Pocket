"""Official IEEE CSV downloads through Windows' existing proxy/PAC credentials.

This GET-only transport is deliberately separate from the proven DashDash
POST code in windows_proxy_urlopen.py, which must retain its small-body limits.
No networking takes place until the user clicks Update IEEE DB.
"""
from __future__ import annotations

import ctypes
from ctypes import wintypes
from io import BytesIO
import os
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit

from . import windows_proxy_urlopen as corporate

_IEEE_HOST = "standards-oui.ieee.org"
_ALLOWED_PATHS = {"/oui/oui.csv", "/oui28/mam.csv",
                  "/oui36/oui36.csv", "/iab/iab.csv"}
_MAX_RESPONSE = 30_000_000


class _IEEEReply:
    def __init__(self, contents: bytes, encoding: str = ""):
        self.status = 200
        self.headers = {"Content-Encoding": encoding}
        self._stream = BytesIO(contents)

    def read(self, count=-1):
        return self._stream.read(count)

    def __enter__(self):
        return self

    def __exit__(self, *_unused):
        self._stream.close()


def _validate(request):
    uri = urlsplit(request.full_url)
    if (uri.scheme != "https" or uri.hostname != _IEEE_HOST
            or uri.path not in _ALLOWED_PATHS or uri.query or uri.fragment
            or uri.username or uri.password or uri.port not in (None, 443)
            or request.get_method() != "GET"):
        raise URLError("Only the four official HTTPS IEEE registry CSV files are allowed")
    return uri


def _windows_ieee_get(request, timeout=25, *, use_windows_proxy=True):
    """WinINet HTTPS GET. Direct mode uses Windows TLS without PAC/WPAD."""
    uri = _validate(request)
    if use_windows_proxy:
        # Keep the already-working corporate PAC resolver unchanged.
        access, proxy, bypass = corporate._resolve_user_proxy(request.full_url)
    else:
        # INTERNET_OPEN_TYPE_DIRECT = 1. Crucially, this is not PRECONFIG (0)
        # and does not resolve or silently fall back to a Windows proxy.
        # WinINet still performs TLS validation against Windows' trust store.
        access, proxy, bypass = 1, None, None
    wininet = ctypes.WinDLL("wininet", use_last_error=True)
    winfunc = corporate._winfunc
    open_root = winfunc(wininet, "InternetOpenW", ctypes.c_void_p,
                        wintypes.LPCWSTR, wintypes.DWORD, wintypes.LPCWSTR,
                        wintypes.LPCWSTR, wintypes.DWORD)
    connect = winfunc(wininet, "InternetConnectW", ctypes.c_void_p,
                      ctypes.c_void_p, wintypes.LPCWSTR, wintypes.WORD,
                      wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD,
                      wintypes.DWORD, ctypes.c_size_t)
    open_request = winfunc(wininet, "HttpOpenRequestW", ctypes.c_void_p,
                           ctypes.c_void_p, wintypes.LPCWSTR, wintypes.LPCWSTR,
                           wintypes.LPCWSTR, wintypes.LPCWSTR, ctypes.c_void_p,
                           wintypes.DWORD, ctypes.c_size_t)
    send = winfunc(wininet, "HttpSendRequestW", wintypes.BOOL,
                   ctypes.c_void_p, wintypes.LPCWSTR, wintypes.DWORD,
                   ctypes.c_void_p, wintypes.DWORD)
    query = winfunc(wininet, "HttpQueryInfoW", wintypes.BOOL,
                    ctypes.c_void_p, wintypes.DWORD, ctypes.c_void_p,
                    ctypes.POINTER(wintypes.DWORD), ctypes.c_void_p)
    read = winfunc(wininet, "InternetReadFile", wintypes.BOOL,
                   ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD,
                   ctypes.POINTER(wintypes.DWORD))
    set_option = winfunc(wininet, "InternetSetOptionW", wintypes.BOOL,
                         ctypes.c_void_p, wintypes.DWORD, ctypes.c_void_p,
                         wintypes.DWORD)
    close = winfunc(wininet, "InternetCloseHandle", wintypes.BOOL, ctypes.c_void_p)

    handles = []

    def checked(value, stage):
        if not value:
            code = ctypes.get_last_error()
            if code in (12037, 12038, 12045, 12055, 12056, 12057, 12169, 12170, 12175):
                # Never disable certificate checks or ignore invalid CA names.
                raise URLError(
                    f"Windows certificate validation failed (WinINet {code}) "
                    "while downloading IEEE. The certificate may be replaced "
                    "by workplace HTTPS inspection. Ask IT to verify the "
                    "trusted root certificate; TLS checks were not bypassed.")
            raise URLError(f"Windows IEEE HTTPS {stage} failed (WinINet {code})")
        return value

    try:
        root = checked(open_root("PocketDesk IEEE update (manual)", access,
                                 proxy, bypass, 0), "initialization")
        handles.append(root)
        ms = wintypes.DWORD(max(1000, min(int(timeout * 1000), 60000)))
        for option in (2, 5, 6):  # connect/send/receive timeout, milliseconds
            set_option(root, option, ctypes.byref(ms), ctypes.sizeof(ms))
        connection = checked(connect(root, _IEEE_HOST, 443,
                                     None, None, 3, 0, 0), "connection")
        handles.append(connection)
        # Same secure/no-redirect/cert-validation flags as DashDash POST.
        flags = (0x00800000 | 0x80000000 | 0x04000000 |
                 0x00200000 | 0x00000200)
        handle = checked(open_request(connection, "GET", uri.path, None,
                                      None, None, flags, 0), "request creation")
        handles.append(handle)
        headers = ("Accept: text/csv,*/*;q=0.7\r\n"
                   "Accept-Encoding: identity\r\n")
        checked(send(handle, headers, len(headers), None, 0), "request")
        status = wintypes.DWORD()
        size = wintypes.DWORD(ctypes.sizeof(status))
        checked(query(handle, 19 | 0x20000000, ctypes.byref(status),
                      ctypes.byref(size), None), "status")

        # WinINet may return gzip/deflate despite Accept-Encoding: identity;
        # the caller already validates/decompresses official registry bodies.
        encoding = ""
        length = wintypes.DWORD(128 * ctypes.sizeof(wintypes.WCHAR))
        buffer = ctypes.create_unicode_buffer(128)
        if query(handle, 29, buffer, ctypes.byref(length), None):
            encoding = buffer.value.lower().strip()

        chunks, total = [], 0
        while True:
            block = ctypes.create_string_buffer(8192)
            received = wintypes.DWORD()
            checked(read(handle, block, len(block), ctypes.byref(received)),
                    "response read")
            if not received.value:
                break
            total += received.value
            if total > _MAX_RESPONSE:
                raise ValueError("IEEE registry file exceeds 30 MB safety limit")
            chunks.append(block.raw[:received.value])
        body = b"".join(chunks)
        if status.value != 200:
            raise HTTPError(request.full_url, status.value,
                            "IEEE HTTPS download failed", {}, BytesIO(body))
        return _IEEEReply(body, encoding)
    finally:
        for handle in reversed(handles):
            close(handle)


def open_ieee(request, timeout=25, *, use_windows_proxy=True):
    """Trusted native Windows HTTPS with explicit proxy selection for IEEE.

    On non-Windows, use urllib for development; Windows alone has WinINet's
    OS-backed certificate validation and InternetOpenW direct-access flag.
    """
    _validate(request)
    if os.name != "nt":
        if use_windows_proxy:
            return corporate._stdlib_urlopen(request, timeout=timeout)
        return corporate.direct_urlopen(request, timeout=timeout)
    return _windows_ieee_get(
        request, timeout=timeout, use_windows_proxy=use_windows_proxy)
