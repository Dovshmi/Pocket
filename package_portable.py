"""Package the public onedir build without importing any personal data."""
from pathlib import Path
import shutil
import zipfile
import sys

ROOT = Path(__file__).resolve().parent
APP_DIR = ROOT / "build" / "portable-binaries" / "PocketDesk"
PACKAGE_DIR = ROOT / "build" / "portable-package" / "Pocket-Portable"
OUTPUT = ROOT / "dist" / "Pocket-Portable-v1.30.0-beta.1.zip"

def package():
    if not (APP_DIR / "PocketDesk.exe").is_file():
        raise FileNotFoundError("Build the PocketDesk onedir EXE first.")
    bundled = APP_DIR / "_internal" / "commands" / "example_commands.json"
    if not bundled.is_file():
        raise FileNotFoundError("Safe example command library not bundled.")
    from command_store import read_document
    read_document(bundled)
    # Generated staging only. Exclude any local data, private commands,
    # backups, cached vendors and application notes from the distributable.
    if PACKAGE_DIR.exists():
        shutil.rmtree(PACKAGE_DIR)
    PACKAGE_DIR.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(APP_DIR, PACKAGE_DIR,
                    ignore=shutil.ignore_patterns(
                        "data", "data.json", "vendors.json", "commands.json",
                        "notepad", "notepad_exports", "backups", "*.log"))
    (PACKAGE_DIR / "portable.flag").write_text(
        "Pocket Portable: store all application data inside the data folder.\n",
        encoding="utf-8")
    (PACKAGE_DIR / "README.txt").write_text(
        "Pocket Portable v1.30.0-beta.1\n"
        "1. Extract the entire ZIP to a writable folder on Windows.\n"
        "2. Launch PocketDesk.exe; Python is not needed on this PC.\n"
        "3. Personal data stays inside the data folder beside the EXE.\n"
        "4. To move Pocket, close it and copy the whole folder.\n"
        "5. Never edit or delete _internal; it holds application libraries.\n"
        "6. Do not run directly inside the ZIP; extract it first.\n",
        encoding="utf-8")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(OUTPUT, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in sorted(PACKAGE_DIR.rglob("*")):
            if p.is_file():
                zf.write(p, p.relative_to(PACKAGE_DIR.parent))
    print(f"Created {OUTPUT}")
    return OUTPUT

if __name__ == "__main__":
    try:
        package()
    except (OSError, ValueError) as exc:
        print(f"Portable packaging failed: {exc}", file=sys.stderr)
        sys.exit(1)
