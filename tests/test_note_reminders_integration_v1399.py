"""App-level and disk regressions for Notes reminders before the 1.39.9 release."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch
import runpy
import tempfile
import unittest

from pocket import note_model as nm

ROOT = Path(__file__).resolve().parents[1]
APP = runpy.run_path(str(ROOT / "app.pyw"), run_name="test_import")
Desk = APP["PocketDesk"]


class NoteRemindersIntegrationTests(unittest.TestCase):
    def _note(self):
        note = nm.new_note("Task", "Keep original")
        note.update(reminder_enabled=True,
                    reminder_at=(datetime.now().astimezone() -
                                 timedelta(minutes=1)).isoformat(timespec="minutes"))
        return note

    def test_snoozed_response_survives_json_restart(self):
        note = self._note()
        nm.snooze_reminder(note, 15, "תשובה בעברית", True)
        data = APP["default_data"]()
        data["notes"] = [note]
        data["active_note"] = note["id"]
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "data.json"
            APP["save_data"](path, data)
            loaded = APP["load_data"](path)
            actual = loaded["notes"][0]
            self.assertEqual(actual["reminder_draft"], "תשובה בעברית")
            self.assertTrue(actual["reminder_add_response"])
            self.assertEqual(nm.reminder_status(actual), "Snoozed")
            self.assertEqual(actual["body"], "Keep original")
            nm.complete_reminder(actual, actual["reminder_draft"], True)
            APP["save_data"](path, loaded)
            again = APP["load_data"](path)["notes"][0]
            self.assertEqual(again["body"], "Keep original\n\nתשובה בעברית")
            self.assertEqual(nm.reminder_status(again), "Completed")

    def test_due_check_does_not_mark_reminder_handled_before_user_action(self):
        note = self._note()
        shown = []
        desk = SimpleNamespace(data={"notes": [note]},
                               _due_reminder_dialog=None,
                               _reminder_dialog=None,
                               _display_due_reminder=lambda note_id: shown.append(note_id))
        Desk._reminder_poll(desk)
        self.assertEqual(shown, [note["id"]])
        self.assertEqual(note["reminder_sent_at"], "")

    def test_popup_done_appends_after_flushing_live_editor(self):
        note = self._note()
        callbacks = {}
        desk = SimpleNamespace(
            data={"notes": [note], "active_note": note["id"]},
            current_tab="notes", _modal=False, _due_reminder_dialog=None,
            _flush_current_note=Mock(), _write_now=Mock(return_value=True),
            _load_selected_note=Mock(), _refresh_note_reminder_ui=Mock(),
            root=object())
        with patch.object(APP["reminder_ui"], "open_due_dialog",
                          side_effect=lambda root, note, done, snooze, close: (
                              callbacks.update(done=done, snooze=snooze, close=close)
                              or SimpleNamespace(winfo_exists=lambda: True))):
            Desk._display_due_reminder(desk, note["id"])
        self.assertTrue(desk._modal)
        callbacks["done"]("append at bottom", True)
        self.assertEqual(note["body"], "Keep original\n\nappend at bottom")
        desk._write_now.assert_called_once()
        desk._load_selected_note.assert_called_once()
        callbacks["close"]()
        self.assertFalse(desk._modal)
        self.assertIsNone(desk._due_reminder_dialog)

    def test_failed_save_keeps_dialog_and_original_note_content(self):
        note = self._note()
        callbacks = {}
        desk = SimpleNamespace(
            data={"notes": [note], "active_note": note["id"]},
            current_tab="clipboard", _modal=False, _due_reminder_dialog=None,
            _flush_current_note=Mock(), _write_now=Mock(return_value=False),
            _load_selected_note=Mock(), _refresh_note_reminder_ui=Mock(),
            root=object())
        with patch.object(APP["reminder_ui"], "open_due_dialog",
                          side_effect=lambda r, n, done, snooze, close: (
                              callbacks.update(done=done, close=close) or
                              SimpleNamespace(winfo_exists=lambda: True))):
            Desk._display_due_reminder(desk, note["id"])
        with self.assertRaises(OSError):
            callbacks["done"]("unsaved", True)
        self.assertEqual(note["body"], "Keep original")
        self.assertEqual(note["reminder_sent_at"], "")
        self.assertTrue(desk._modal)

    def test_mini_top_icon_layout_is_unchanged_and_reminders_use_more(self):
        app_source = (ROOT / "app.pyw").read_text(encoding="utf-8")
        section = app_source.split("    def _build_mini_shell(self):", 1)[1].split(
            "    def _style_mini_icon_tabs", 1)[0]
        self.assertIn('("clipboard", "▤", "Clip"), ("settings", "⚙", "More"),', section)
        self.assertNotIn('("reminders",', section)
        self.assertEqual(section.count("tile = tk.Frame(nav"), 1)
        settings_source = (ROOT / "pocket/settings_ui.py").read_text(encoding="utf-8")
        self.assertIn('"open_reminders"', settings_source)
        self.assertIn('app.show_tab("reminders")', settings_source)


if __name__ == "__main__":
    unittest.main()
