"""Regression: append Notes after any selection; Notepad filenames stay readable."""
from pathlib import Path
import runpy
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from pocket import note_sync

api = runpy.run_path(str(Path(__file__).resolve().parents[1] / "app.pyw"),
                     run_name="test_import")
PocketDesk = api["PocketDesk"]
new_note = api["new_note"]
ordered_notes = api["ordered_notes"]


class _Entry:
    def __init__(self):
        self.focused = False
        self.selected = False

    def focus_set(self):
        self.focused = True

    def selection_range(self, *_):
        self.selected = True


class NoteCreationOrderTests(unittest.TestCase):
    def test_new_note_is_last_from_any_selected_position(self):
        for selected in (0, 1, 2):
            with self.subTest(selected=f"{selected+1}/3"):
                notes = [new_note("First"), new_note("Second"), new_note("Third")]
                entry = _Entry()
                calls = []
                fake = SimpleNamespace(
                    data={"notes": notes, "active_note": notes[selected]["id"]},
                    current_tab="notes", title_entry=entry,
                    path=Path(tempfile.gettempdir()) / "pocket-note-test-no-files" / "data.json",
                    _unique_note_path=lambda note, title: Path("notepad") / (title + ".txt"),
                    _flush_current_note=lambda: calls.append("flush"),
                    refresh_note_list=lambda: calls.append("refresh"),
                    _load_selected_note=lambda: calls.append("load"),
                    schedule_save=lambda: calls.append("save"))
                previous_ids = [n["id"] for n in notes]
                PocketDesk.add_note(fake)
                self.assertEqual([n["id"] for n in notes[:3]], previous_ids)
                self.assertEqual(len(notes), 4)
                self.assertEqual(fake.data["active_note"], notes[3]["id"])
                rows = ordered_notes(notes)
                self.assertEqual(rows[-1]["id"], fake.data["active_note"])
                self.assertEqual(f"{len(rows)}/{len(rows)}", "4/4")
                self.assertEqual(calls, ["flush", "refresh", "load", "save"])
                self.assertTrue(entry.focused and entry.selected)

    def test_new_note_is_last_even_if_older_notes_are_pinned(self):
        notes = [new_note("First"), new_note("Pinned"), new_note("Third")]
        notes[1]["pinned"] = True
        fake = SimpleNamespace(
            data={"notes": notes, "active_note": notes[0]["id"]},
            current_tab="notes", title_entry=_Entry(),
            path=Path(tempfile.gettempdir()) / "pocket-note-test-no-files" / "data.json",
            _unique_note_path=lambda note, title: Path("notepad") / (title + ".txt"),
            _flush_current_note=lambda: None,
            refresh_note_list=lambda: None,
            _load_selected_note=lambda: None,
            schedule_save=lambda: None)
        PocketDesk.add_note(fake)
        rows = ordered_notes(notes)
        self.assertEqual(rows[0]["id"], notes[1]["id"])
        self.assertEqual(rows[-1]["id"], fake.data["active_note"])


class NotepadWorkingFileTests(unittest.TestCase):
    def _fake_app(self, directory, notes, index=0):
        data = {"notes": notes, "active_note": notes[index]["id"]}
        saves = []
        app = SimpleNamespace(
            data=data,
            path=Path(directory) / "data.json",
            root=None,
            _modal=False,
            _notepad_sessions={},
            current_tab="background",
            _title_job=None,
            _flush_current_note=lambda: None,
            schedule_save=lambda: saves.append(True),
            _import_notepad_body=lambda note, text: note.update(body=text))
        app._unique_note_path = lambda note, title: PocketDesk._unique_note_path(app, note, title)
        app._commit_note_title = lambda note_id=None: PocketDesk._commit_note_title(app, note_id)
        app.active_note = lambda: next(
            n for n in data["notes"] if n["id"] == data["active_note"])
        return app, saves

    def test_live_working_files_have_titles_and_reopen_stably(self):
        with tempfile.TemporaryDirectory() as folder:
            notes = [new_note("Network", "a"), new_note("Network", "b")]
            app, saves = self._fake_app(folder, notes)
            with patch.object(api["sys"], "platform", "win32"), \
                 patch.object(api["subprocess"], "Popen") as popen:
                PocketDesk.open_notepad(app)
                self.assertEqual(notes[0]["notepad_filename"], "Network.txt")
                path = Path(folder) / "notepad" / "Network.txt"
                self.assertEqual(note_sync.read_text(path), "a")
                note_sync.write_text(path, "saved in Notepad")
                PocketDesk.open_notepad(app)
                self.assertEqual(notes[0]["notepad_filename"], "Network.txt")
                self.assertEqual(note_sync.read_text(path), "saved in Notepad")
                app.data["active_note"] = notes[1]["id"]
                PocketDesk.open_notepad(app)
                self.assertEqual(notes[1]["notepad_filename"], "Network (1).txt")
                self.assertEqual(note_sync.read_text(
                    Path(folder) / "notepad" / "Network (1).txt"), "b")
                self.assertEqual(popen.call_count, 3)
                self.assertEqual(len(saves), 2)
            # The note-to-file mapping survives a full data.json round trip.
            api["save_data"](app.path, {**api["default_data"](),
                                        "notes": notes,
                                        "active_note": notes[1]["id"]})
            recovered = api["load_data"](app.path)
            self.assertEqual(recovered["notes"][0]["notepad_filename"],
                             "Network.txt")
            self.assertEqual(recovered["notes"][1]["notepad_filename"],
                             "Network (1).txt")

    def test_legacy_opaque_file_migrates_without_deleting_original(self):
        with tempfile.TemporaryDirectory() as folder:
            note = new_note("דו״ח רשת", "from Pocket")
            app, _saves = self._fake_app(folder, [note])
            old_path = note_sync.note_path(Path(folder) / "notepad", note["id"])
            note_sync.create_text(old_path, "from old Notepad")
            with patch.object(api["sys"], "platform", "win32"), \
                 patch.object(api["subprocess"], "Popen"), \
                 patch.object(api["messagebox"], "askyesnocancel", return_value=True):
                PocketDesk.open_notepad(app)
            self.assertEqual(note["body"], "from old Notepad")
            new_path = Path(folder) / "notepad" / "דו״ח רשת.txt"
            self.assertEqual(note["notepad_filename"], new_path.name)
            self.assertEqual(note_sync.read_text(new_path), "from old Notepad")
            self.assertEqual(note_sync.read_text(old_path), "from old Notepad")

    def test_cancel_legacy_conflict_does_not_claim_a_filename(self):
        with tempfile.TemporaryDirectory() as folder:
            note = new_note("Network", "from Pocket")
            app, saves = self._fake_app(folder, [note])
            old_path = note_sync.note_path(Path(folder) / "notepad", note["id"])
            note_sync.create_text(old_path, "different")
            with patch.object(api["sys"], "platform", "win32"), \
                 patch.object(api["subprocess"], "Popen") as popen, \
                 patch.object(api["messagebox"], "askyesnocancel", return_value=None):
                PocketDesk.open_notepad(app)
            popen.assert_not_called()
            self.assertNotIn("notepad_filename", note)
            self.assertFalse(saves)
            self.assertFalse((Path(folder) / "notepad" / "Network.txt").exists())


if __name__ == "__main__":
    unittest.main()
