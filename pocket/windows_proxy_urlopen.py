"""User-initiated HTTPS requests using the signed-in Windows user's proxy policy.

On Windows, resolve PAC/WPAD per destination with WinHTTP and send HTTPS through
WinINet (Windows certificate store and interactive-user proxy authentication).
No proxy settings, registry values or credentials are modified. No connections
occur at import time. Other platforms retain urllib for unit tests/development.
"""
from __future__ import annotations

import ctypes
from ctypes import wintypes
from io import BytesIO
import os
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import urlopen as _stdlib_urlopen


# These are Windows SDK data structures; keep pointer fields as c_void_p so
# memory allocated by WinHTTP can always be released with GlobalFree.
class _IEProxyConfig(ctypes.Structure):
    _fields_ = [
        ("fAutoDetect", wintypes.BOOL),
        ("lpszAutoConfigUrl", ctypes.c_void_p),
        ("lpszProxy", ctypes.c_void_p),
        ("lpszProxyBypass", ctypes.c_void_p),
    ]


class _AutoProxyOptions(ctypes.Structure):
    _fields_ = [
        ("dwFlags", wintypes.DWORD),
        ("dwAutoDetectFlags", wintypes.DWORD),
        ("lpszAutoConfigUrl", wintypes.LPCWSTR),
        ("lpvReserved", ctypes.c_void_p),
        ("dwReserved", wintypes.DWORD),
        ("fAutoLogonIfChallenged", wintypes.BOOL),
    ]


class _ProxyInfo(ctypes.Structure):
    _fields_ = [
        ("dwAccessType", wintypes.DWORD),
        ("lpszProxy", ctypes.c_void_p),
        ("lpszProxyBypass", ctypes.c_void_p),
    ]


def _winfunc(dll, name, result, *args):
    fn = getattr(dll, name)
    fn.argtypes = args
    fn.restype = result
    return fn


def _resolve_user_proxy(url):
    """Return (WinINet access type, proxy name, bypass) for *this* HTTPS URL.

    A configured PAC that cannot be evaluated is an error, never an excuse to
    silently attempt an unrestricted direct connection.
    """
    winhttp = ctypes.WinDLL("winhttp", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    get_settings = _winfunc(winhttp, "WinHttpGetIEProxyConfigForCurrentUser",
                            wintypes.BOOL, ctypes.POINTER(_IEProxyConfig))
    global_free = _winfunc(kernel32, "GlobalFree", ctypes.c_void_p, ctypes.c_void_p)
    config = _IEProxyConfig()
    if not get_settings(ctypes.byref(config)):
        # No per-user settings: use the normal Windows preconfigured settings.
        return 0, None, None
    try:
        pac = ctypes.wstring_at(config.lpszAutoConfigUrl) if config.lpszAutoConfigUrl else None
        manual = ctypes.wstring_at(config.lpszProxy) if config.lpszProxy else None
        bypass = ctypes.wstring_at(config.lpszProxyBypass) if config.lpszProxyBypass else None
        if not pac and not config.fAutoDetect:
            return (3, manual, bypass) if manual else (1, None, None)

        open_http = _winfunc(winhttp, "WinHttpOpen", ctypes.c_void_p,
                             wintypes.LPCWSTR, wintypes.DWORD, wintypes.LPCWSTR,
                             wintypes.LPCWSTR, wintypes.DWORD)
        close_http = _winfunc(winhttp, "WinHttpCloseHandle", wintypes.BOOL,
                              ctypes.c_void_p)
        resolve = _winfunc(winhttp, "WinHttpGetProxyForUrl", wintypes.BOOL,
                           ctypes.c_void_p, wintypes.LPCWSTR,
                           ctypes.POINTER(_AutoProxyOptions), ctypes.POINTER(_ProxyInfo))
        session = open_http("PocketDesk PAC lookup", 1, None, None, 0)
        if not session:
            raise URLError("Windows could not initialize the corporate PAC resolver")
        info = _ProxyInfo()
        try:
            # 2 = explicitly configured PAC URL, 1 = WPAD autodetection.
            options = _AutoProxyOptions(2 if pac else 1, 0 if pac else 3,
                                        pac, None, 0, True)
            if not resolve(session, url, ctypes.byref(options), ctypes.byref(info)):
                code = ctypes.get_last_error()
                raise URLError(f"Windows PAC resolution failed (WinHTTP {code}); "
                               "direct access was not attempted")
            proxy = ctypes.wstring_at(info.lpszProxy) if info.lpszProxy else None
            proxy_bypass = (ctypes.wstring_at(info.lpszProxyBypass)
                            if info.lpszProxyBypass else None)
            # WINHTTP_ACCESS_TYPE_NAMED_PROXY = 3; NO_PROXY = 1.
            if info.dwAccessType == 3 and proxy:
                return 3, proxy, proxy_bypass
            if info.dwAccessType == 1:
                return 1, None, None
            raise URLError("Windows PAC returned an unsupported proxy configuration")
        finally:
            for pointer in (info.lpszProxy, info.lpszProxyBypass):
                if pointer:
                    global_free(pointer)
            close_http(session)
    finally:
        for pointer in (config.lpszAutoConfigUrl, config.lpszProxy,
                        config.lpszProxyBypass):
            if pointer:
                global_free(pointer)


class _Response:
    """Minimal urlopen-compatible response; the network handles are closed."""
    def __init__(self, status, content):
        self.status = status
        self._body = BytesIO(content)

    def read(self, count=-1):
        return self._body.read(count)

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self._body.close()


def _windows_urlopen(request, timeout):
    uri = urlsplit(request.full_url)
    if uri.scheme.lower() != "https" or not uri.hostname or uri.username or uri.password:
        raise URLError("Only HTTPS URLs without embedded credentials are permitted")
    if request.get_method() != "POST":
        raise URLError("Only explicit DashDash POST requests are supported")
    body = request.data or b""
    if not isinstance(body, bytes) or len(body) > 32_768:
        raise URLError("Invalid or oversized HTTPS request body")
    access, proxy, bypass = _resolve_user_proxy(request.full_url)
    wininet = ctypes.WinDLL("wininet", use_last_error=True)
    open_root = _winfunc(wininet, "InternetOpenW", ctypes.c_void_p,
                         wintypes.LPCWSTR, wintypes.DWORD, wintypes.LPCWSTR,
                         wintypes.LPCWSTR, wintypes.DWORD)
    connect = _winfunc(wininet, "InternetConnectW", ctypes.c_void_p,
                       ctypes.c_void_p, wintypes.LPCWSTR, wintypes.WORD,
                       wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD,
                       wintypes.DWORD, ctypes.c_size_t)
    open_request = _winfunc(wininet, "HttpOpenRequestW", ctypes.c_void_p,
                            ctypes.c_void_p, wintypes.LPCWSTR, wintypes.LPCWSTR,
                            wintypes.LPCWSTR, wintypes.LPCWSTR, ctypes.c_void_p,
                            wintypes.DWORD, ctypes.c_size_t)
    send = _winfunc(wininet, "HttpSendRequestW", wintypes.BOOL,
                    ctypes.c_void_p, wintypes.LPCWSTR, wintypes.DWORD,
                    ctypes.c_void_p, wintypes.DWORD)
    query = _winfunc(wininet, "HttpQueryInfoW", wintypes.BOOL,
                     ctypes.c_void_p, wintypes.DWORD, ctypes.c_void_p,
                     ctypes.POINTER(wintypes.DWORD), ctypes.c_void_p)
    read = _winfunc(wininet, "InternetReadFile", wintypes.BOOL,
                    ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD,
                    ctypes.POINTER(wintypes.DWORD))
    set_option = _winfunc(wininet, "InternetSetOptionW", wintypes.BOOL,
                          ctypes.c_void_p, wintypes.DWORD, ctypes.c_void_p,
                          wintypes.DWORD)
    close = _winfunc(wininet, "InternetCloseHandle", wintypes.BOOL, ctypes.c_void_p)

    handles = []
    def checked(value, stage):
        if not value:
            raise URLError(f"Windows HTTPS {stage} failed (WinINet "
                           f"{ctypes.get_last_error()})")
        return value
    try:
        root = checked(open_root("PocketDesk/1.33 (manual DashDash request)",
                                 access, proxy, bypass, 0), "initialization")
        handles.append(root)
        milliseconds = wintypes.DWORD(max(1000, min(int(timeout * 1000), 60000)))
        for option in (2, 5, 6):  # connect, send, receive timeout
            set_option(root, option, ctypes.byref(milliseconds),
                       ctypes.sizeof(milliseconds))
        connection = checked(connect(root, uri.hostname, uri.port or 443,
                                     None, None, 3, 0, 0), "connection")
        handles.append(connection)
        path = (uri.path or "/") + ("?" + uri.query if uri.query else "")
        flags = (0x00800000 | 0x80000000 | 0x04000000 |
                 0x00200000 | 0x00000200)  # secure, reload, no-cache, no-redirect, no-UI
        handle = checked(open_request(connection, "POST", path, None, None,
                                      None, flags, 0), "request creation")
        handles.append(handle)
        headers = "Content-Type: application/json\r\nAccept: application/json\r\n"
        post_buffer = ctypes.create_string_buffer(body, len(body)) if body else None
        checked(send(handle, headers, len(headers),
                     post_buffer, len(body)), "request")
        status = wintypes.DWORD()
        size = wintypes.DWORD(ctypes.sizeof(status))
        checked(query(handle, 19 | 0x20000000, ctypes.byref(status),
                      ctypes.byref(size), None), "status")
        chunks = []
        total = 0
        while True:
            chunk = ctypes.create_string_buffer(8192)
            received = wintypes.DWORD()
            checked(read(handle, chunk, len(chunk), ctypes.byref(received)),
                    "response read")
            if not received.value:
                break
            chunks.append(chunk.raw[:received.value])
            total += received.value
            if total > 65_537:
                raise URLError("DashDash response exceeds the permitted limit")
        data = b"".join(chunks)
        if status.value >= 400:
            raise HTTPError(request.full_url, status.value,
                            "DashDash API error", {}, BytesIO(data))
        return _Response(status.value, data)
    finally:
        for handle in reversed(handles):
            close(handle)


def urlopen(request, timeout=12):
    """urlopen replacement: uses corporate PAC only on Windows, on demand."""
    if os.name != "nt":
        return _stdlib_urlopen(request, timeout=timeout)
    return _windows_urlopen(request, timeout)
