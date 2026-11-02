"""Regression tests for note alignment persistence and local Notepad file handling."""
from pathlib import Path
import runpy
import tempfile
import unittest

from pocket import note_sync

m = runpy.run_path(str(Path(__file__).resolve().parents[1] / "app.pyw"), run_name="test_import")


class NoteDirectionTests(unittest.TestCase):
    def test_default_and_invalid_values(self):
        self.assertEqual(m["new_note"]()["direction"], "ltr")
        self.assertEqual(m["normalize_note_direction"]("rtl"), "rtl")
        self.assertEqual(m["normalize_note_direction"]("RTL"), "ltr")
        self.assertEqual(m["normalize_note_direction"](["rtl"]), "ltr")

    def test_direction_survives_save_and_load(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "data.json"
            data = m["default_data"]()
            data["notes"][0]["direction"] = "rtl"
            m["save_data"](path, data)
            self.assertEqual(m["load_data"](path)["notes"][0]["direction"], "rtl")

    def test_legacy_defaults_and_duplicate_preserves_direction(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "data.json"
            data = m["default_data"]()
            data["notes"][0].pop("direction", None)
            m["save_data"](path, data)
            self.assertEqual(m["load_data"](path)["notes"][0]["direction"], "ltr")
        original = m["new_note"]("עברית", "English / עברית")
        original["direction"] = "rtl"
        duplicate = m["duplicate_note"](original)
        self.assertEqual(duplicate["direction"], "rtl")
        self.assertEqual(duplicate["body"], original["body"])
        self.assertNotEqual(duplicate["id"], original["id"])


class NotepadBridgeTests(unittest.TestCase):
    def test_working_path_is_stable_and_rejects_bad_ids(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            ident = "a" * 32
            self.assertEqual(note_sync.note_path(folder, ident), note_sync.note_path(folder, ident))
            self.assertEqual(note_sync.note_path(folder, ident).name, "note_" + ident + ".txt")
            for bad in ["../../secrets", "", "a" * 31, "z" * 32]:
                with self.subTest(bad=bad), self.assertRaises(ValueError):
                    note_sync.note_path(folder, bad)

    def test_heb_eng_unicode_and_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            path = note_sync.note_path(Path(directory), "b" * 32)
            note_sync.write_text(path, "עברית\nEnglish\n10.0.0.1")
            self.assertEqual(note_sync.read_text(path), "עברית\nEnglish\n10.0.0.1")
            note_sync.write_text(path, "Changed in Notepad ✨")
            self.assertEqual(note_sync.read_text(path), "Changed in Notepad ✨")

    def test_conflict_backup_is_recoverable(self):
        with tempfile.TemporaryDirectory() as directory:
            path = note_sync.note_path(Path(directory), "c" * 32)
            external = "Saved by Notepad"
            backup = note_sync.preserve_conflict(path, external)
            self.assertNotEqual(path, backup)
            self.assertEqual(note_sync.read_text(backup), external)


if __name__ == "__main__":
    unittest.main()
