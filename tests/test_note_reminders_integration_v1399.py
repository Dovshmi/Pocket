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

    def test_x_removes_note_reminder_but_never_deletes_its_note(self):
        note = self._note()
        note["reminder_draft"] = "Draft"
        desk = SimpleNamespace(
            data={"notes": [note], "active_note": note["id"]},
            _modal=False, root=object(), _flush_current_note=Mock(),
            _write_now=Mock(return_value=True),
            _refresh_note_reminder_ui=Mock())
        with patch.object(APP["messagebox"], "askyesno", return_value=False):
            Desk._delete_reminder(desk, note["id"], source="note")
        self.assertTrue(note["reminder_enabled"])
        self.assertEqual(note["reminder_draft"], "Draft")
        with patch.object(APP["messagebox"], "askyesno", return_value=True):
            Desk._delete_reminder(desk, note["id"], source="note")
        self.assertEqual(desk.data["notes"], [note])
        self.assertEqual(note["title"], "Task")
        self.assertEqual(note["body"], "Keep original")
        self.assertFalse(note["reminder_enabled"])
        self.assertEqual(note["reminder_at"], "")
        self.assertEqual(note["reminder_draft"], "")

    def test_remove_note_reminder_rolls_back_on_save_failure(self):
        note = self._note()
        original = dict(note)
        desk = SimpleNamespace(
            data={"notes": [note], "active_note": note["id"]},
            _modal=False, root=object(), _flush_current_note=Mock(),
            _write_now=Mock(return_value=False),
            _refresh_note_reminder_ui=Mock())
        with patch.object(APP["messagebox"], "askyesno", return_value=True):
            Desk._delete_reminder(desk, note["id"], source="note")
        self.assertEqual(note, original)
        desk._refresh_note_reminder_ui.assert_not_called()

    def test_hidden_reminders_menu_stops_both_notification_sources(self):
        from pocket import reminder_store
        note = self._note()
        task = reminder_store.make_reminder(
            "Independent reminder", "Keep this", (datetime.now().astimezone() +
             timedelta(minutes=5)).isoformat(timespec="minutes"))
        task["reminder_at"] = (datetime.now().astimezone() -
                               timedelta(minutes=2)).isoformat(timespec="minutes")
        delivered = []
        settings = {"visible_tabs": ["notes", "clipboard"],
                    "reminders_menu_configured": True}
        desk = SimpleNamespace(
            settings=settings, data={"notes": [note], "reminders": [task]},
            _due_reminder_dialog=None, _reminder_dialog=None, _modal=False,
            _display_due_reminder=lambda ident, source="note": delivered.append((ident, source)))
        Desk._reminder_poll(desk)
        self.assertEqual(delivered, [])
        self.assertEqual(note["reminder_sent_at"], "")
        self.assertEqual(task["reminder_sent_at"], "")
        # Restoring the menu resumes overdue reminders without data loss.
        settings["visible_tabs"].append("reminders")
        Desk._reminder_poll(desk)
        self.assertEqual(len(delivered), 1)
        self.assertEqual(note["reminder_sent_at"], "")
        self.assertEqual(task["reminder_sent_at"], "")

    def test_reminder_switch_blocks_note_actions_but_keeps_existing_dates(self):
        note = self._note()
        original = dict(note)
        desk = SimpleNamespace(
            settings={"visible_tabs": ["notes"]}, data={"notes": [note]},
            _edit_note_reminder=Mock())
        Desk._toggle_note_reminder(desk, note["id"])
        Desk._edit_note_reminder(desk, note["id"])
        self.assertEqual(note, original)
        desk._edit_note_reminder.assert_not_called()

        # The UI setting must call the active-popup suspension on disable.
        shell = SimpleNamespace(
            settings={"visible_tabs": ["notes", "reminders"]},
            _suspend_open_due_reminder=Mock(), _build_shell_refresh=Mock(),
            schedule_save=Mock())
        Desk._set_visible_tab(shell, "reminders", False)
        self.assertNotIn("reminders", shell.settings["visible_tabs"])
        shell._suspend_open_due_reminder.assert_called_once()
        shell.schedule_save.assert_called_once()

    def test_suspending_active_reminder_saves_draft_without_completion(self):
        note = self._note()
        dialog = SimpleNamespace(
            winfo_exists=lambda: True, _source_record=note,
            _response_enabled=SimpleNamespace(get=lambda: True),
            _response_input=SimpleNamespace(get=lambda *_: "unsent reply"),
            _suspend_without_completion=Mock())
        desk = SimpleNamespace(
            _due_reminder_dialog=dialog, _write_now=Mock(return_value=True))
        Desk._suspend_open_due_reminder(desk)
        self.assertEqual(note["reminder_draft"], "unsent reply")
        self.assertTrue(note["reminder_add_response"])
        self.assertEqual(note["reminder_sent_at"], "")
        desk._write_now.assert_called_once()
        dialog._suspend_without_completion.assert_called_once()

    def test_saved_disabled_reminders_setting_survives_restart(self):
        profile = APP["default_data"]()
        profile["settings"]["visible_tabs"].remove("reminders")
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "data.json"
            APP["save_data"](path, profile)
            loaded = APP["load_data"](path)
        self.assertFalse(APP["reminders_enabled"](loaded["settings"]))
        self.assertEqual(loaded["reminders"], [])

    def test_note_calendar_save_failure_rolls_back(self):
        note = self._note()
        original = dict(note)
        captured = {}
        desk = SimpleNamespace(
            data={"notes": [note]}, _reminder_dialog=None, _modal=False,
            _flush_current_note=Mock(), _write_now=Mock(return_value=False),
            _refresh_note_reminder_ui=Mock(), root=object(), theme="blue")
        with patch.object(APP["reminder_ui"], "open_datetime_editor",
                          side_effect=lambda root, record, save, close, **kw:
                              (captured.update(save=save) or
                               SimpleNamespace(winfo_exists=lambda: True))):
            Desk._edit_note_reminder(desk, note["id"])
        with self.assertRaises(OSError):
            captured["save"]((datetime.now().astimezone() +
                              timedelta(minutes=35)).isoformat(timespec="minutes"))
        self.assertEqual(note, original)

    @staticmethod
    def _clear_fixture():
        from pocket import reminder_store
        from datetime import timedelta

        def linked(state, index):
            n = nm.new_note(f"Note {index}", f"Keep original {index}")
            n["reminder_enabled"] = True
            n["reminder_at"] = (datetime.now().astimezone() +
                                timedelta(hours=1)).isoformat(timespec="minutes")
            if state == "Snoozed":
                n["reminder_snoozed"] = True
                n["reminder_draft"] = "Unsent draft"
                n["reminder_add_response"] = True
            elif state == "Completed":
                n["reminder_sent_at"] = datetime.now().astimezone().isoformat()
            return n

        def separate(state, index):
            r = reminder_store.make_reminder(
                f"Standalone {index}", f"Keep details {index}",
                (datetime.now().astimezone() + timedelta(hours=1)).isoformat(timespec="minutes"))
            if state == "Snoozed":
                r["reminder_snoozed"] = True
            elif state == "Completed":
                r["reminder_sent_at"] = datetime.now().astimezone().isoformat()
            return r

        states = ("Upcoming", "Snoozed", "Completed")
        linked_notes = [linked(state, i) for i, state in enumerate(states)]
        untouched = nm.new_note("No reminder", "Keep this Note")
        reminders = [separate(state, i) for i, state in enumerate(states)]
        profile = {"notes": linked_notes + [untouched], "reminders": reminders}
        return profile, linked_notes, untouched, reminders

    @staticmethod
    def _clear_desk(profile, *, saved=True):
        return SimpleNamespace(
            data=profile, settings={"visible_tabs": ["notes", "reminders"]},
            _modal=False, root=object(),
            _due_reminder_dialog=None, _reminder_dialog=None,
            _flush_current_note=Mock(), _write_now=Mock(return_value=saved),
            _refresh_note_reminder_ui=Mock())

    def test_clear_all_removes_reminders_but_never_deletes_notes(self):
        data, linked, untouched, originals = self._clear_fixture()
        before_notes = [(n["id"], n["title"], n["body"]) for n in data["notes"]]
        desk = self._clear_desk(data)
        with patch.object(APP["messagebox"], "askyesno", return_value=True) as ask:
            self.assertTrue(Desk._clear_reminders(desk, "All"))
        self.assertEqual(data["reminders"], [])
        self.assertEqual(len(data["notes"]), 4)
        self.assertEqual(
            [(n["id"], n["title"], n["body"]) for n in data["notes"]],
            before_notes)
        self.assertTrue(all(nm.reminder_status(n) is None for n in linked))
        self.assertIsNone(nm.reminder_status(untouched))
        self.assertEqual(desk._write_now.call_count, 1)
        desk._refresh_note_reminder_ui.assert_called_once()
        self.assertFalse(desk._modal)
        self.assertIn("Notes and their text will NOT be deleted", ask.call_args.args[1])
        self.assertEqual(ask.call_args.kwargs["default"], "no")

    def test_clear_selected_status_deletes_only_that_category(self):
        from pocket import reminder_store
        for scope in ("Upcoming", "Snoozed", "Completed"):
            with self.subTest(tab=scope):
                data, linked, untouched, independent = self._clear_fixture()
                original_notes = [(n["title"], n["body"]) for n in data["notes"]]
                desk = self._clear_desk(data)
                desk._reminders_search = "text not matching anything"
                with patch.object(APP["messagebox"], "askyesno", return_value=True) as ask:
                    self.assertTrue(Desk._clear_reminders(desk, scope))
                self.assertEqual(
                    [(n["title"], n["body"]) for n in data["notes"]],
                    original_notes)
                self.assertEqual(len(data["reminders"]), 2)
                self.assertTrue(all(reminder_store.status(r) != scope for r in data["reminders"]))
                self.assertEqual([nm.reminder_status(n) for n in linked].count(None), 1)
                for i, state in enumerate(("Upcoming", "Snoozed", "Completed")):
                    if state != scope:
                        self.assertEqual(nm.reminder_status(linked[i]), state)
                        self.assertTrue(any(r is independent[i] for r in data["reminders"]))
                self.assertIsNone(nm.reminder_status(untouched))
                self.assertIn("even if Search is active", ask.call_args.args[1])
                desk._write_now.assert_called_once()

    def test_clear_confirmation_cancel_and_failed_write_leave_data_intact(self):
        for approved, saved in ((False, True), (True, False)):
            with self.subTest(approved=approved, saved=saved):
                data, linked, _, _ = self._clear_fixture()
                prior_notes = [dict(n) for n in data["notes"]]
                prior_reminders = list(data["reminders"])
                desk = self._clear_desk(data, saved=saved)
                with patch.object(APP["messagebox"], "askyesno", return_value=approved):
                    self.assertFalse(Desk._clear_reminders(desk, "Completed"))
                self.assertEqual(data["notes"], prior_notes)
                self.assertEqual(data["reminders"], prior_reminders)
                self.assertTrue(all(x is y for x, y in zip(data["reminders"], prior_reminders)))
                self.assertEqual(desk._write_now.call_count, int(approved))
                desk._refresh_note_reminder_ui.assert_not_called()

    def test_clear_invalid_or_empty_scope_and_open_popup_are_noops(self):
        data, linked, _, _ = self._clear_fixture()
        desk = self._clear_desk(data)
        with patch.object(APP["messagebox"], "askyesno") as ask:
            self.assertFalse(Desk._clear_reminders(desk, "Invalid"))
            self.assertFalse(Desk._clear_reminders(desk, "Done"))  # UI uses Completed.
        ask.assert_not_called()
        # A visible popup can hold a draft that must not be destroyed.
        popup = SimpleNamespace(winfo_exists=lambda: True, lift=Mock())
        desk._due_reminder_dialog = popup
        self.assertFalse(Desk._clear_reminders(desk, "All"))
        popup.lift.assert_called_once()
        desk._write_now.assert_not_called()
        self.assertEqual(len(data["reminders"]), 3)

    def test_clear_done_does_not_remove_previous_note_response(self):
        data, linked, _, _ = self._clear_fixture()
        linked[-1]["body"] += "\n\nSaved response"
        desk = self._clear_desk(data)
        with patch.object(APP["messagebox"], "askyesno", return_value=True):
            self.assertTrue(Desk._clear_reminders(desk, "Completed"))
        self.assertEqual(linked[-1]["body"], "Keep original 2\n\nSaved response")
        self.assertEqual(linked[-1]["title"], "Note 2")

    def test_mini_top_icon_layout_uses_exact_fit_and_expandable_more(self):
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
        self.assertIn('width=38, height=45', app_source)
        self.assertIn('tile.pack(side="left", fill="x", expand=True', app_source)
        self.assertIn('"Less" if expanded else "More"', app_source)
        self.assertIn('self._mini_nav_separator', app_source)
        settings_source = (ROOT / "pocket/settings_ui.py").read_text(encoding="utf-8")
        self.assertNotIn('"open_reminders"', settings_source)
        self.assertIn('"reminders":', settings_source)


if __name__ == "__main__":
    unittest.main()
