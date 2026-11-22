"""Pure validation and explicit launch helpers for PocketDesk shortcuts.

Website shortcuts are restricted to HTTPS/HTTP; file and folder shortcuts launch
only when explicitly clicked, using the operating system's normal file opener.
"""
from __future__ import annotations

import os
from pathlib import Path
import re
import subprocess
import sys
import webbrowser
from urllib.parse import urlsplit

VALID_KINDS = ("url", "file", "folder")
TRUECALLER_LOOKUP_URL = "https://www.truecaller.com/reverse-phone-number-lookup"


def normalize_url(raw: str) -> str:
    raw = raw.strip()
    if not raw:
        raise ValueError("Enter a website address.")
    if raw.lower().startswith(("javascript:", "file:", "data:", "mailto:", "ftp:", "about:", "blob:")):
        raise ValueError("Only HTTP and HTTPS websites can be saved.")
    if "://" not in raw:
        raw = "https://" + raw
    parts = urlsplit(raw)
    if parts.scheme not in ("http", "https") or not parts.netloc or any(c.isspace() for c in raw):
        raise ValueError("Enter a valid http:// or https:// address.")
    return raw


def normalize_shortcut(kind: str, target: str) -> str:
    if kind not in VALID_KINDS:
        raise ValueError("Choose Website, File, or Folder.")
    if kind == "url":
        return normalize_url(target)
    target = target.strip().strip('"')
    if not target:
        raise ValueError(f"Choose a {kind} to open.")
    path = Path(os.path.expandvars(target)).expanduser()
    if not path.exists():
        raise ValueError(f"This {kind} does not exist: {path}")
    if kind == "file" and not path.is_file():
        raise ValueError("Selected path is not a file.")
    if kind == "folder" and not path.is_dir():
        raise ValueError("Selected path is not a folder.")
    return str(path.resolve())


def validate_phone_number(value: str) -> str:
    """Accept formatted phone numbers; preserve local 0 or leading + country code.

    Clipboard-only: this function never contacts a phone lookup provider.
    """
    raw = value.strip()
    if not raw or len(raw) > 40 or not re.fullmatch(r"\+?[\d\s()\-.]+", raw):
        raise ValueError("Enter a phone number (digits, spaces, +, hyphens or parentheses).")
    digits = re.sub(r"\D", "", raw)
    if not 7 <= len(digits) <= 15:
        raise ValueError("Enter a phone number containing 7 to 15 digits.")
    return ("+" if raw.startswith("+") else "") + digits


EXCEL_WORKBOOK_SUFFIXES = frozenset({
    ".xlsx", ".xls", ".xlsm", ".xlsb", ".xltx", ".xltm", ".xlam", ".xla",
})


def _same_excel_file(a, b):
    """Compare the *complete* local path, case-insensitively on Windows."""
    try:
        return os.path.normpath(os.path.abspath(str(a))).casefold() == (
            os.path.normpath(os.path.abspath(str(b))).casefold())
    except (TypeError, ValueError, OSError):
        return False


def _focus_excel_workbook(workbook):
    """Bring exactly this Excel workbook to the front; do not reopen or save."""
    workbook.Activate()
    excel = workbook.Application
    excel.Visible = True
    try:
        # Workbooks can live in different Excel processes. Hwnd belongs to the
        # particular application that owns the matching open workbook.
        import win32gui
        import win32con
        handle = int(excel.Hwnd)
        if win32gui.IsIconic(handle):
            win32gui.ShowWindow(handle, win32con.SW_RESTORE)
        win32gui.SetForegroundWindow(handle)
    except Exception:
        # Foreground activation is best effort: Office and Windows can reject
        # SetForegroundWindow even after Workbook.Activate succeeds.
        # Activation already succeeded; Windows foreground restrictions are
        # independent of whether the workbook was correctly selected.
        pass


def _find_open_excel_workbook(target, client):
    """Find the exact workbook in an active Excel app or the COM running table.

    GetObject(path) is deliberately NOT used: on some Office installations it
    can create/open a new workbook when no matching object is registered.
    """
    try:
        active = client.GetActiveObject("Excel.Application")
        for workbook in active.Workbooks:
            if _same_excel_file(workbook.FullName, target):
                return workbook
    except Exception:
        pass

    try:
        import pythoncom
        running = pythoncom.GetRunningObjectTable()
        items = running.EnumRunning()
        bind = pythoncom.CreateBindCtx(0)
        while True:
            batch = items.Next(1)
            if not batch:
                break
            moniker = batch[0]
            try:
                name = moniker.GetDisplayName(bind, None)
                if not _same_excel_file(name, target):
                    continue
                workbook = client.Dispatch(running.GetObject(moniker))
                # Never activate an unrelated workbook because a COM moniker
                # happened to have a similar display name.
                if _same_excel_file(workbook.FullName, target):
                    return workbook
            except Exception:
                continue
    except Exception:
        # The ROT is optional and may be restricted by Office policy.
        pass
    return None


def _open_excel_workbook(target: str) -> bool:
    """Reuse the exact open workbook, otherwise open the requested *other* file.

    This is invoked only after the user clicks a Shortcut. Prefer an existing
    Excel instance for a different workbook; create a separate instance only
    if no usable Excel application is running. Existing windows are never
    closed, saved or modified. Return False for Windows shell fallback when
    the Office COM interface is unavailable.
    """
    try:
        import win32com.client
    except ImportError:
        return False
    client = win32com.client
    existing = _find_open_excel_workbook(target, client)
    if existing is not None:
        _focus_excel_workbook(existing)
        return True

    created = False
    try:
        try:
            excel = client.GetActiveObject("Excel.Application")
        except Exception:
            excel = client.DispatchEx("Excel.Application")
            created = True
    except Exception:
        return False

    try:
        excel.Visible = True
        workbook = excel.Workbooks.Open(Filename=target)
        _focus_excel_workbook(workbook)
        return True
    except Exception as exc:
        if created:
            try:
                excel.Quit()  # Close ONLY the empty instance we just created.
            except Exception:
                pass
        raise OSError(
            "Excel could not open the requested workbook. "
            "Check its permissions and Office security prompts."
        ) from exc


def launch_shortcut(kind: str, target: str) -> None:
    """Only invoke when the user clicks a stored shortcut (never on app startup)."""
    target = normalize_shortcut(kind, target)
    if kind == "url":
        if not webbrowser.open(target):
            raise OSError("Your default browser could not be opened.")
    elif sys.platform == "win32":
        if kind == "file" and Path(target).name.casefold() == "excel.exe":
            # Excel's /x starts a separate process instead of silently
            # activating a workbook already open in another Excel window.
            subprocess.Popen([target, "/x"])
        elif (kind == "file" and Path(target).suffix.casefold()
              in EXCEL_WORKBOOK_SUFFIXES and _open_excel_workbook(target)):
            return
        else:
            os.startfile(target)  # type: ignore[attr-defined]  # Shell association
    elif sys.platform == "darwin":
        subprocess.Popen(["open", target])
    else:
        subprocess.Popen(["xdg-open", target])
