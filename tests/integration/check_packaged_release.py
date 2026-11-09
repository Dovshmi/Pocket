"""Verify FINAL packaged Pocket binaries on a clean Windows extraction.

This check is deliberately stronger than a bare process-alive smoke test:
--self-test-deps must load Pillow's compiled _imaging and ImageTk inside Tk.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import tempfile
import time
import zipfile


def run_dependency_test(exe: Path, env: dict[str, str]) -> None:
    result = subprocess.run(
        [str(exe), "--self-test-deps"], env=env, capture_output=True,
        text=True, timeout=90, check=False,
    )
    if result.returncode != 0:
        raise AssertionError(
            f"{exe.name}: bundled Pillow/Tk self-test failed "
            f"(exit code {result.returncode}).\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )
    print(f"PASS: compiled Pillow + ImageTk + Tk from {exe.name}", flush=True)


def run_startup(exe: Path, env: dict[str, str]) -> None:
    process = subprocess.Popen(
        [str(exe), "--preview"], env=env, stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        time.sleep(7)
        if process.poll() is not None:
            raise AssertionError(
                f"{exe.name}: Pocket GUI terminated during startup "
                f"(exit code {process.returncode})"
            )
        print(f"PASS: {exe.name} starts in GUI preview mode", flush=True)
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=10)


def check_release(version: str, portable_only: bool) -> None:
    if os.name != "nt":
        raise RuntimeError("Packaged release smoke checks require Windows")
    dist = Path(__file__).resolve().parents[2] / "dist"
    zip_path = dist / f"Pocket-Portable-{version}.zip"
    if not zip_path.is_file():
        raise FileNotFoundError(zip_path)
    with tempfile.TemporaryDirectory(prefix="Pocket clean test ") as temp_dir:
        temp = Path(temp_dir)
        with zipfile.ZipFile(zip_path) as archive:
            if archive.testzip() is not None:
                raise AssertionError("Corrupted portable release ZIP")
            archive.extractall(temp / "extracted")
        folder = temp / "extracted" / "Pocket-Portable"
        exe = folder / "PocketDesk.exe"
        if not exe.is_file():
            raise AssertionError("Portable EXE missing after extraction")
        if not (folder / "portable.flag").is_file():
            raise AssertionError("Portable marker is missing")
        internal = folder / "_internal"
        imaging = list((internal / "PIL").glob("_imaging*.pyd"))
        if not imaging:
            raise AssertionError(
                "Pillow _imaging compiled extension is missing from extracted ZIP"
            )
        print(f"PASS: extracted compiled extension: {imaging[0].name}", flush=True)
        env = dict(os.environ)
        env["APPDATA"] = str(temp / "clean AppData")
        Path(env["APPDATA"]).mkdir(parents=True, exist_ok=True)
        env.pop("PYTHONPATH", None)
        env.pop("PYTHONHOME", None)
        run_dependency_test(exe, env)
        run_startup(exe, env)
        if not portable_only:
            standalone = dist / f"Pocket-{version}.exe"
            if not standalone.is_file():
                raise FileNotFoundError(standalone)
            run_dependency_test(standalone, env)
            run_startup(standalone, env)
        print("PASS: all packaged release runtime checks completed", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", required=True)
    parser.add_argument("--portable-only", action="store_true")
    args = parser.parse_args()
    check_release(args.version, args.portable_only)
