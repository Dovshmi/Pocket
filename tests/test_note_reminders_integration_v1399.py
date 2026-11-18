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
            self.assertRegex(again["body"],
                             r"^Keep original\n\n\d{2}/\d{2}/\d{4} \d{2}:\d{2}\nתשובה בעברית$")
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
            root=object(), theme="blue")
        with patch.object(APP["reminder_ui"], "open_due_dialog",
                          side_effect=lambda root, note, done, snooze, close, **_kwargs: (
                              callbacks.update(done=done, snooze=snooze, close=close)
                              or SimpleNamespace(winfo_exists=lambda: True))):
            Desk._display_due_reminder(desk, note["id"])
        self.assertTrue(desk._modal)
        callbacks["done"]("append at bottom", True)
        self.assertRegex(note["body"],
                         r"^Keep original\n\n\d{2}/\d{2}/\d{4} \d{2}:\d{2}\nappend at bottom$")
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
            root=object(), theme="blue")
        with patch.object(APP["reminder_ui"], "open_due_dialog",
                          side_effect=lambda r, n, done, snooze, close, **_kwargs: (
                              callbacks.update(done=done, close=close) or
                              SimpleNamespace(winfo_exists=lambda: True))):
            Desk._display_due_reminder(desk, note["id"])
        with self.assertRaises(OSError):
            callbacks["done"]("unsaved", True)
        self.assertEqual(note["body"], "Keep original")
        self.assertEqual(note["reminder_sent_at"], "")
        self.assertTrue(desk._modal)

    def test_overview_snooze_does_not_erase_unsent_draft(self):
        note = self._note()
        note["reminder_draft"] = "preserve this"
        note["reminder_add_response"] = True
        desk = SimpleNamespace(
            data={"notes": [note], "active_note": note["id"]},
            _due_reminder_dialog=None, _modal=False, root=object(), theme="blue",
            _flush_current_note=Mock(), _write_now=Mock(return_value=True),
            _refresh_note_reminder_ui=Mock())
        Desk._manage_note_reminder(desk, note["id"], "snooze")
        self.assertEqual(note["body"], "Keep original")
        self.assertEqual(note["reminder_draft"], "preserve this")
        self.assertEqual(nm.reminder_status(note), "Snoozed")

    def test_overview_done_asks_before_discarding_response_draft(self):
        note = self._note()
        note["reminder_draft"] = "valuable"
        note["reminder_add_response"] = True
        desk = SimpleNamespace(
            data={"notes": [note], "active_note": note["id"]},
            _due_reminder_dialog=None, _modal=False, root=object(), theme="blue",
            _flush_current_note=Mock(), _write_now=Mock(return_value=True),
            _refresh_note_reminder_ui=Mock())
        with patch.object(APP["messagebox"], "askyesno", return_value=False):
            Desk._manage_note_reminder(desk, note["id"], "done")
        self.assertEqual(note["reminder_draft"], "valuable")
        self.assertEqual(note["reminder_sent_at"], "")
        desk._write_now.assert_not_called()
        with patch.object(APP["messagebox"], "askyesno", return_value=True):
            Desk._manage_note_reminder(desk, note["id"], "done")
        self.assertEqual(nm.reminder_status(note), "Completed")
        self.assertEqual(note["body"], "Keep original")
        self.assertEqual(note["reminder_draft"], "")

    def test_mini_top_icon_layout_is_unchanged_with_expandable_more(self):
        from pocket import mini_nav
        original = ["notes", "links", "ports", "mac", "commands",
                    "subnet", "clipboard"]
        first, overflow = mini_nav.plan_mini_icons(original)
        self.assertEqual(first, tuple(original + ["settings"]))
        self.assertEqual(overflow, ())
        first, overflow = mini_nav.plan_mini_icons(original + ["reminders"])
        self.assertEqual(first, tuple(original + ["more"]))
        self.assertEqual(overflow, (("reminders", "settings"),))
        app_source = (ROOT / "app.pyw").read_text(encoding="utf-8")
        self.assertIn('width=39, height=45', app_source)
        self.assertIn('"Less" if expanded else "More"', app_source)
        self.assertIn('self._mini_nav_separator', app_source)
        settings_source = (ROOT / "pocket/settings_ui.py").read_text(encoding="utf-8")
        self.assertNotIn('"open_reminders"', settings_source)
        self.assertIn('"reminders":', settings_source)


if __name__ == "__main__":
    unittest.main()
