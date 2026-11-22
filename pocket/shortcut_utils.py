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


def _open_excel_in_new_instance(target: str) -> bool:
    """Launch a real, separate Microsoft Excel window for workbook shortcuts.

    ShellExecute's ordinary Excel file association can re-use an already open
    Excel instance (DDE), occasionally leaving the requested workbook unopened.
    DispatchEx explicitly creates a NEW Excel automation server independent of
    any existing workbook. This is only invoked by a user-clicked file shortcut.

    Return False only when Excel COM cannot be initialized; callers then retain
    the original Windows file association as a graceful fallback.
    """
    try:
        import win32com.client
    except ImportError:
        return False
    try:
        excel = win32com.client.DispatchEx("Excel.Application")
    except Exception:
        # Machine without registered Excel, or Office policy blocks COM.
        return False
    try:
        excel.Visible = True
        # Do not suppress Office security dialogs, force a read-only session,
        # save data, or interfere with any previously open Excel instances.
        excel.Workbooks.Open(Filename=target)
        return True
    except Exception as exc:
        try:
            excel.Quit()  # Only the new instance we created.
        except Exception:
            pass
        raise OSError(
            "Excel started but could not open this workbook. "
            "Check the file permissions and any Excel prompt."
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
              in EXCEL_WORKBOOK_SUFFIXES and _open_excel_in_new_instance(target)):
            return
        else:
            os.startfile(target)  # type: ignore[attr-defined]  # Shell association
    elif sys.platform == "darwin":
        subprocess.Popen(["open", target])
    else:
        subprocess.Popen(["xdg-open", target])
