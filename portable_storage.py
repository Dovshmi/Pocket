"""Choose Pocket's data location without changing the standard installation.

Standard: %APPDATA%/PocketDesk/data.json (as in v1.27).
Portable: <Pocket folder>/data/data.json when portable.flag is beside app.pyw/EXE.

Never silently fall back to AppData in portable mode: that would leave personal
data on the host computer and break the promise of portability.
"""
from __future__ import annotations

import os
from pathlib import Path
import sys
import tempfile


PORTABLE_MARKER = "portable.flag"


def application_directory(*, frozen: bool | None = None,
                          executable: str | Path | None = None,
                          source: str | Path | None = None) -> Path:
    if frozen is None:
        frozen = bool(getattr(sys, "frozen", False))
    if frozen:
        return Path(executable if executable is not None else sys.executable).resolve().parent
    return Path(source if source is not None else __file__).resolve().parent


def is_portable(root: Path | None = None) -> bool:
    root = Path(root) if root is not None else application_directory()
    return (root / PORTABLE_MARKER).is_file()


def data_directory(app_name: str = "PocketDesk", *, root: Path | None = None,
                   appdata: str | Path | None = None) -> Path:
    root = Path(root) if root is not None else application_directory()
    if is_portable(root):
        return root / "data"
    base = appdata if appdata is not None else os.environ.get("APPDATA")
    if not base:
        base = Path.home() / ".local" / "share"
    return Path(base) / app_name


def data_file(app_name: str = "PocketDesk", *, root: Path | None = None,
              appdata: str | Path | None = None) -> Path:
    return data_directory(app_name, root=root, appdata=appdata) / "data.json"


def require_writable_portable_data(root: Path | None = None) -> None:
    """Check storage without overwriting anything or opening user data."""
    root = Path(root) if root is not None else application_directory()
    if not is_portable(root):
        return
    folder = root / "data"
    try:
        folder.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryFile(dir=folder):
            pass
    except OSError as exc:
        raise OSError(
            f"Pocket Portable cannot write to {folder}. "
            "Move the extracted Pocket folder to a writable location. "
            "Your notes will NOT be saved to AppData as a fallback."
        ) from exc

def resolve_portable_library(data_dir: Path, bundle_dir: Path) -> Path:
    """Copy only the public example library into writable portable storage."""
    import shutil
    from command_store import read_document
    data_dir = Path(data_dir)
    target = data_dir / "commands.json"
    if target.is_file():
        return target
    source = Path(bundle_dir) / "commands" / "example_commands.json"
    if not source.is_file():
        raise FileNotFoundError("Pocket Portable is missing its bundled example commands")
    read_document(source)
    data_dir.mkdir(parents=True, exist_ok=True)
    try:
        with source.open("rb") as reader, target.open("xb") as writer:
            shutil.copyfileobj(reader, writer)
            writer.flush()
            os.fsync(writer.fileno())
    except FileExistsError:
        pass
    return target
