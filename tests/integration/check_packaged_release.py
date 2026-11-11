"""Verify final Windows Portable ZIP in a new directory with a space in its path."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import tempfile
import time
import zipfile

from package_portable import check_native_extensions, verify_manifest

def check_release(version: str) -> None:
    if os.name != "nt":
        raise RuntimeError("Windows runner required")
    archive = Path(__file__).resolve().parents[2] / "dist" / f"Pocket-Portable-{version}.zip"
    if not archive.is_file():
        raise FileNotFoundError(archive)
    with tempfile.TemporaryDirectory(prefix="Pocket clean extracted ") as scratch:
        temp = Path(scratch)
        with zipfile.ZipFile(archive) as z:
            if z.testzip() is not None:
                raise AssertionError("ZIP corruption")
            z.extractall(temp)
        folder = temp / "Pocket-Portable"
        exe = folder / "PocketDesk.exe"
        if not exe.is_file() or not (folder / "portable.flag").is_file():
            raise AssertionError("Portable app or marker missing")
        check_native_extensions(folder)
        verify_manifest(folder)
        environment = dict(os.environ)
        environment["APPDATA"] = str(temp / "clean AppData")
        Path(environment["APPDATA"]).mkdir()
        environment.pop("PYTHONPATH", None)
        environment.pop("PYTHONHOME", None)
        diagnostic = temp / "diagnostic.log"
        tested = subprocess.run([str(exe), "--self-test-deps",
                                  f"--deps-log={diagnostic}"], env=environment,
                                 capture_output=True, text=True, timeout=90)
        if tested.returncode:
            details = diagnostic.read_text(encoding="utf-8") if diagnostic.exists() else "No traceback: possible bootloader/policy block"
            raise AssertionError(f"Missing/blocked DLL: {details}; {tested.stderr}")
        process = subprocess.Popen([str(exe), "--preview"], env=environment,
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            time.sleep(7)
            if process.poll() is not None:
                raise AssertionError(f"Packaged UI exited prematurely: {process.returncode}")
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=10)
        print("PASS: extracted Windows Portable ZIP, native DLLs, Pillow/Tk and GUI startup")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", required=True)
    parser.add_argument("--portable-only", action="store_true",
                        help="Compatibility with existing CI invocation")
    arguments = parser.parse_args()
    check_release(arguments.version)
