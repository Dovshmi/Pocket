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
                # Second note also persists its newly numbered Title.
                self.assertEqual(len(saves), 3)
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


class TitleFileSyncTests(unittest.TestCase):
    @staticmethod
    def make_app(directory, notes, index=0):
        path = Path(directory) / "data.json"
        data = {"notes": notes, "active_note": notes[index]["id"]}
        events = []
        app = SimpleNamespace(
            data=data, path=path, root=None, current_tab="background",
            _title_job=None, _title_job_note_id=None,
            _notepad_sessions={}, _loading_note=False,
            _flush_current_note=lambda: events.append("flush"),
            schedule_save=lambda: events.append("save"),
            refresh_note_list=lambda: events.append("refresh"),
            _load_selected_note=lambda: events.append("load"),
            title_entry=_Entry())
        app._unique_note_path = lambda note, title: PocketDesk._unique_note_path(app, note, title)
        app._commit_note_title = lambda note_id=None: PocketDesk._commit_note_title(app, note_id)
        app.active_note = lambda: next(
            n for n in data["notes"] if n["id"] == data["active_note"])
        return app, events

    def test_new_note_titles_number_before_any_notepad_file_exists(self):
        with tempfile.TemporaryDirectory() as folder:
            notes = [new_note("Untitled note"), new_note("Untitled note (1)")]
            app, _events = self.make_app(folder, notes)
            app.current_tab = "notes"
            PocketDesk.add_note(app)
            self.assertEqual(notes[-1]["title"], "Untitled note (2)")
            self.assertEqual(app.data["active_note"], notes[-1]["id"])
            self.assertEqual(sorted(Path(folder).glob("notepad/*.txt")), [])

    def test_duplicate_note_uses_numbered_title_not_copy(self):
        with tempfile.TemporaryDirectory() as folder:
            original = new_note("Router", "show version")
            app, _events = self.make_app(folder, [original])
            PocketDesk._duplicate_note(app, original["id"])
            self.assertEqual(app.data["notes"][1]["title"], "Router (1)")
            self.assertEqual(app.data["notes"][1]["body"], "show version")
            PocketDesk._duplicate_note(app, original["id"])
            self.assertEqual(app.data["notes"][1]["title"], "Router (2)")

    def test_rename_title_moves_file_and_updates_session(self):
        with tempfile.TemporaryDirectory() as folder:
            note = new_note("Router", "initial")
            app, _events = self.make_app(folder, [note])
            with patch.object(api["sys"], "platform", "win32"), \
                 patch.object(api["subprocess"], "Popen"):
                PocketDesk.open_notepad(app)
                original = Path(folder) / "notepad" / "Router.txt"
                self.assertTrue(original.is_file())
                note["title"] = "Switch"
                app._commit_note_title()
                target = original.with_name("Switch.txt")
                self.assertFalse(original.exists())
                self.assertEqual(note["title"], "Switch")
                self.assertEqual(note["notepad_filename"], "Switch.txt")
                self.assertEqual(app._notepad_sessions[note["id"]]["path"], target)
                self.assertEqual(note_sync.read_text(target), "initial")
                PocketDesk.open_notepad(app)
                self.assertEqual(app._notepad_sessions[note["id"]]["path"], target)
                self.assertEqual(len(list(target.parent.glob("*.txt"))), 1)

    def test_collision_existing_note_and_disk_is_numbered_in_both(self):
        with tempfile.TemporaryDirectory() as folder:
            base, other = new_note("Router"), new_note("Switch", "content")
            app, _events = self.make_app(folder, [base, other], index=1)
            occupied = Path(folder) / "notepad" / "Router (1).txt"
            note_sync.create_text(occupied, "not related")
            with patch.object(api["sys"], "platform", "win32"), \
                 patch.object(api["subprocess"], "Popen"):
                PocketDesk.open_notepad(app)
                source = Path(folder) / "notepad" / "Switch.txt"
                other["title"] = "router"
                app._commit_note_title()
                self.assertEqual(other["title"], "router (2)")
                self.assertEqual(other["notepad_filename"], "router (2).txt")
                self.assertFalse(source.exists())
                self.assertEqual(note_sync.read_text(
                    Path(folder) / "notepad" / "router (2).txt"), "content")
                self.assertEqual(note_sync.read_text(occupied), "not related")
                self.assertEqual(base["title"], "Router")

    def test_title_sanitization_reuses_same_name_as_file(self):
        with tempfile.TemporaryDirectory() as folder:
            note = new_note("Original")
            app, _events = self.make_app(folder, [note])
            note["title"] = "Report: / status.txt"
            app._commit_note_title()
            self.assertEqual(note["title"], "Report_ _ status")
            with patch.object(api["sys"], "platform", "win32"), \
                 patch.object(api["subprocess"], "Popen"):
                PocketDesk.open_notepad(app)
            self.assertEqual(note["notepad_filename"], "Report_ _ status.txt")

    def test_case_only_rename_changes_filename_without_data_loss(self):
        with tempfile.TemporaryDirectory() as folder:
            note = new_note("Router", "data")
            app, _events = self.make_app(folder, [note])
            with patch.object(api["sys"], "platform", "win32"), \
                 patch.object(api["subprocess"], "Popen"):
                PocketDesk.open_notepad(app)
                note["title"] = "ROUTER"
                app._commit_note_title()
            self.assertEqual(note["title"], "ROUTER")
            self.assertEqual(note["notepad_filename"], "ROUTER.txt")
            self.assertEqual(note_sync.read_text(
                Path(folder) / "notepad" / "ROUTER.txt"), "data")

    def test_locked_file_rolls_title_back_instead_of_diverging(self):
        with tempfile.TemporaryDirectory() as folder:
            note = new_note("Router", "data")
            app, _events = self.make_app(folder, [note])
            with patch.object(api["sys"], "platform", "win32"), \
                 patch.object(api["subprocess"], "Popen"):
                PocketDesk.open_notepad(app)
            note["title"] = "Switch"
            with patch.object(note_sync, "rename_text_file", side_effect=PermissionError("locked")), \
                 patch.object(api["messagebox"], "showwarning") as warning:
                app._commit_note_title()
            self.assertEqual(note["title"], "Router")
            self.assertEqual(note["notepad_filename"], "Router.txt")
            self.assertTrue((Path(folder) / "notepad" / "Router.txt").exists())
            warning.assert_called_once()

    def test_title_name_stays_numbered_after_restart(self):
        with tempfile.TemporaryDirectory() as folder:
            notes = [new_note("Router"), new_note("Router")]
            app, _events = self.make_app(folder, notes, index=1)
            app._commit_note_title()
            self.assertEqual(notes[1]["title"], "Router (1)")
            api["save_data"](app.path, {**api["default_data"](),
                                        "notes": notes,
                                        "active_note": notes[1]["id"]})
            recovered = api["load_data"](app.path)
            self.assertEqual(recovered["notes"][1]["title"], "Router (1)")



if __name__ == "__main__":
    unittest.main()
