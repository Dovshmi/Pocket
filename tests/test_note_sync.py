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


    def test_named_files_and_duplicate_numbering(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            first = note_sync.named_note_path(folder, "Network")
            self.assertEqual(first.name, "Network.txt")
            note_sync.create_text(first, "first")
            second = note_sync.named_note_path(folder, "Network")
            self.assertEqual(second.name, "Network (1).txt")
            note_sync.create_text(second, "second")
            self.assertEqual(note_sync.named_note_path(folder, "Network").name,
                             "Network (2).txt")
            self.assertEqual(note_sync.read_text(first), "first")
            self.assertEqual(note_sync.read_text(second), "second")
            with self.assertRaises(FileExistsError):
                note_sync.create_text(first, "should never overwrite")
            self.assertEqual(note_sync.read_text(first), "first")

    def test_legal_unicode_names_and_windows_reserved_filenames(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            self.assertEqual(note_sync.named_note_path(folder, "דו״ח רשת").name,
                             "דו״ח רשת.txt")
            self.assertEqual(note_sync.named_note_path(folder, "My note: / test").name,
                             "My note_ _ test.txt")
            self.assertEqual(note_sync.named_note_path(folder, "CON").name, "_CON.txt")
            self.assertEqual(note_sync.named_note_path(folder, "LPT1.log").name,
                             "_LPT1.log.txt")
            self.assertEqual(note_sync.named_note_path(folder, "..").name,
                             "Untitled note.txt")
            self.assertEqual(note_sync.named_note_path(folder, "..\\secrets").name,
                             "_secrets.txt")
            self.assertEqual(note_sync.named_note_path(folder, "").name,
                             "Untitled note.txt")

    def test_saved_name_persists_and_other_notes_reserve_it(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            original = note_sync.named_note_path(folder, "Router")
            note_sync.create_text(original, "v1")
            reopened = note_sync.named_note_path(
                folder, "Router renamed", saved_filename="Router.txt")
            self.assertEqual(reopened, original)
            # A second note must not claim another note's filename, even if the
            # original file has since been moved outside the folder.
            original.unlink()
            newer = note_sync.named_note_path(
                folder, "Router", reserved_names={"Router.txt"})
            self.assertEqual(newer.name, "Router (1).txt")
            self.assertEqual(note_sync.named_note_path(
                folder, "Router", saved_filename="../escape.txt").name, "Router.txt")
            self.assertEqual(note_sync.named_note_path(
                folder, "Router", saved_filename="CON.txt").name, "Router.txt")

    def test_windows_case_insensitive_collisions(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            note_sync.create_text(folder / "network.TXT", "exists")
            self.assertEqual(note_sync.named_note_path(folder, "Network").name,
                             "Network (1).txt")


if __name__ == "__main__":
    unittest.main()
