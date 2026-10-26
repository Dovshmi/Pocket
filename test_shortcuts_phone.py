"""Phone and new file/folder shortcuts; no real browser/network calls."""
from pathlib import Path
import json
import runpy
import tempfile
import unittest
from unittest import mock
import shortcut_utils as tools

app = runpy.run_path(str(Path(__file__).parent / "app.pyw"), run_name="test_import")


class PhoneAndShortcutsTests(unittest.TestCase):
    def test_caller_lookup_removed(self):
        """The app must not expose any of the abandoned caller integrations."""
        cls = app["PocketDesk"]
        for old in ("_open_caller_browser", "_lookup_phone", "_configure_caller_lookup",
                    "_import_contacts", "_show_cached_lookup"):
            self.assertFalse(hasattr(cls, old), old)

    def test_phone_validation(self):
        self.assertEqual(tools.validate_phone_number("+972 (50) 123-4567"), "+972501234567")
        self.assertEqual(tools.validate_phone_number("050-123-4567"), "0501234567")
        for number in ("", "123", "1234567890123456", "1; echo evil", "abcd", "tel:0501234567"):
            with self.subTest(number=number):
                with self.assertRaises(ValueError):
                    tools.validate_phone_number(number)

    def test_file_folder_shortcuts_and_bad_types(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            test_file = folder / "example.txt"
            test_file.write_text("test", encoding="utf-8")
            self.assertEqual(tools.normalize_shortcut("file", str(test_file)), str(test_file.resolve()))
            self.assertEqual(tools.normalize_shortcut("folder", str(folder)), str(folder.resolve()))
            for kind, target in (("file", str(folder)), ("folder", str(test_file)),
                                 ("file", str(folder / "absent.txt")), ("exec", str(test_file))):
                with self.subTest(kind=kind, target=target):
                    with self.assertRaises(ValueError):
                        tools.normalize_shortcut(kind, target)

    def test_windows_startfile_called_only_after_click(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.pdf"
            path.touch()
            with mock.patch.object(tools.sys, "platform", "win32"), mock.patch.object(tools.os, "startfile", create=True) as startfile:
                tools.launch_shortcut("file", str(path))
                startfile.assert_called_once_with(str(path.resolve()))

    def test_legacy_storage_migration_and_persist_new_data(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "data.json"
            legacy = {"notes": [{"id": "n1", "title": "Call", "body": "Legacy note"}],
                      "active_note": "n1", "links": [{"id": "l1", "title": "Home", "url": "https://example.com"}]}
            path.write_text(json.dumps(legacy), encoding="utf-8")
            loaded = app["load_data"](path)
            self.assertEqual(loaded["notes"][0]["phone"], "")
            self.assertEqual(loaded["links"][0]["kind"], "url")
            loaded["notes"][0]["phone"] = "+972501234567"
            loaded["links"].append(app["new_link"]("Documents", str(Path(directory)), "folder"))
            app["save_data"](path, loaded)
            reopened = app["load_data"](path)
            self.assertEqual(reopened["notes"][0]["phone"], "+972501234567")
            self.assertEqual(reopened["links"][-1]["kind"], "folder")


if __name__ == "__main__":
    unittest.main()
