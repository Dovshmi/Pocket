"""Pure-Python tests for release integrity, without Windows or Python executable."""
from __future__ import annotations
from pathlib import Path
import tempfile
import unittest
from package_portable import check_native_extensions, write_manifest, verify_manifest

class PortableBundleIntegrityTests(unittest.TestCase):
    def create_package(self, root):
        for name in ("_internal/PIL/_imaging.cp311-win_amd64.pyd",
                     "_internal/_ctypes.pyd", "_internal/_tkinter.pyd",
                     "_internal/unicodedata.pyd", "PocketDesk.exe"):
            p = root / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(b"synthetic test file")

    def test_detect_changed_file(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.create_package(root)
            check_native_extensions(root)
            write_manifest(root)
            verify_manifest(root)
            (root / "_internal" / "_ctypes.pyd").write_bytes(b"tampered")
            with self.assertRaisesRegex(AssertionError, "modified"):
                verify_manifest(root)

    def test_detect_missing_module(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.create_package(root)
            (root / "_internal" / "unicodedata.pyd").unlink()
            with self.assertRaisesRegex(FileNotFoundError, "unicodedata"):
                check_native_extensions(root)

    def test_detect_unlisted_file(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.create_package(root)
            write_manifest(root)
            (root / "unexpected.txt").write_text("extra")
            with self.assertRaisesRegex(AssertionError, "Untracked"):
                verify_manifest(root)
