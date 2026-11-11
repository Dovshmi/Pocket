"""Create the complete, privacy-safe, Windows portable Pocket release."""
from __future__ import annotations

from hashlib import sha256
import os
from pathlib import Path
import re
import shutil
import sys
import zipfile

ROOT = Path(__file__).resolve().parent
APP_DIR = ROOT / "build" / "portable-binaries" / "PocketDesk"
PACKAGE_DIR = ROOT / "build" / "portable-package" / "Pocket-Portable"
RELEASE_VERSION = os.environ.get("POCKET_RELEASE_VERSION", "v1.30.0")
if not re.fullmatch(r"v[0-9]+\\.[0-9]+\\.[0-9]+(?:-[A-Za-z0-9.]+)?", RELEASE_VERSION):
    raise ValueError("Invalid release version")
OUTPUT = ROOT / "dist" / f"Pocket-Portable-{RELEASE_VERSION}.zip"

REQUIRED_NATIVE = ("PIL/_imaging*.pyd", "_ctypes*.pyd",
                   "_tkinter*.pyd", "unicodedata*.pyd")

def check_native_extensions(folder: Path) -> None:
    internal = folder / "_internal"
    if not internal.is_dir():
        raise FileNotFoundError("Missing bundled _internal runtime directory")
    for pattern in REQUIRED_NATIVE:
        if not list(internal.glob(pattern)):
            raise FileNotFoundError(f"Required Windows extension missing: {pattern}")

def write_manifest(folder: Path) -> None:
    manifest = folder / "bundle-manifest.sha256"
    entries = []
    for path in sorted(folder.rglob("*")):
        if path.is_file() and path != manifest:
            digest = sha256(path.read_bytes()).hexdigest()
            entries.append(f"{digest}  {path.relative_to(folder).as_posix()}")
    manifest.write_text("\\n".join(entries) + "\\n", encoding="utf-8")

def verify_manifest(folder: Path) -> None:
    manifest = folder / "bundle-manifest.sha256"
    if not manifest.is_file():
        raise AssertionError("Missing SHA256 integrity manifest")
    checked = set()
    for line in manifest.read_text(encoding="utf-8").splitlines():
        match = re.fullmatch(r"([0-9a-f]{64})  (.+)", line)
        if not match:
            raise AssertionError(f"Invalid manifest line: {line!r}")
        digest, relative = match.groups()
        path = Path(relative)
        if path.is_absolute() or ".." in path.parts or relative in checked:
            raise AssertionError(f"Unsafe or duplicate entry: {relative}")
        checked.add(relative)
        target = folder / path
        if not target.is_file() or sha256(target.read_bytes()).hexdigest() != digest:
            raise AssertionError(f"Missing or modified file: {relative}")
    files = {p.relative_to(folder).as_posix()
             for p in folder.rglob("*") if p.is_file() and p != manifest}
    if files != checked:
        raise AssertionError(f"Untracked or missing entries: {files ^ checked}")

def package() -> Path:
    if os.name != "nt":
        raise OSError("Windows distribution must be built on Windows")
    if not (APP_DIR / "PocketDesk.exe").is_file():
        raise FileNotFoundError("Build the onedir PocketDesk.exe first")
    check_native_extensions(APP_DIR)
    safe_commands = APP_DIR / "_internal" / "commands" / "example_commands.json"
    if not safe_commands.is_file():
        raise FileNotFoundError("Missing public example command library")
    from pocket.command_store import read_document
    read_document(safe_commands)

    if PACKAGE_DIR.exists():
        shutil.rmtree(PACKAGE_DIR)
    PACKAGE_DIR.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(APP_DIR, PACKAGE_DIR, ignore=shutil.ignore_patterns(
        "data", "data.json", "data-recovery.json", "data-corrupt-*.json",
        "vendors.json", "commands.json", "notepad", "notepad_exports",
        "backups", "*.log", ".env", ".env.*"))
    (PACKAGE_DIR / "portable.flag").write_text(
        "Pocket Portable: user data lives in the adjacent data directory.\\n",
        encoding="utf-8")
    (PACKAGE_DIR / "README.txt").write_text(
        f"Pocket Portable {RELEASE_VERSION}\\n\\n"
        "1. Extract the complete ZIP to a NEW LOCAL writable folder.\\n"
        "2. Double-click PocketDesk.exe. Python and internet are not needed.\\n"
        "3. Keep _internal in place; it contains required Windows DLLs.\\n"
        "4. Save and move notes by copying the complete data folder.\\n"
        "5. Do not run from inside the ZIP or from a mapped network drive.\\n"
        "6. If blocked, ask IT to check corporate application-control logs.\\n"
        "7. Optional offline check (IT-approved only): Verify-Pocket.ps1\\n",
        encoding="utf-8")
    script = ROOT / "scripts" / "Verify-Pocket.ps1"
    shutil.copy2(script, PACKAGE_DIR / "Verify-Pocket.ps1")
    check_native_extensions(PACKAGE_DIR)
    write_manifest(PACKAGE_DIR)
    verify_manifest(PACKAGE_DIR)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(OUTPUT, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for path in sorted(PACKAGE_DIR.rglob("*")):
            if path.is_file():
                z.write(path, path.relative_to(PACKAGE_DIR.parent))
    with zipfile.ZipFile(OUTPUT) as z:
        corrupt = z.testzip()
        if corrupt:
            raise OSError(f"Invalid ZIP member: {corrupt}")
    print(f"Packaged tested Pocket Windows ZIP: {OUTPUT}")
    return OUTPUT

if __name__ == "__main__":
    try:
        package()
    except (OSError, ValueError, ImportError, AssertionError) as error:
        print(f"Portable packaging failed: {error}", file=sys.stderr)
        sys.exit(1)
