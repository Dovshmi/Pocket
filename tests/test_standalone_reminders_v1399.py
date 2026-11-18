"""Standalone reminders must never accidentally create or modify a Note."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch
import runpy
import tempfile
import unittest

from pocket import note_model, reminder_store, portable_backup

APP = runpy.run_path(str(Path(__file__).resolve().parents[1] / "app.pyw"), run_name="test_import")
Desk = APP["PocketDesk"]


def future(minutes=90):
    return (datetime.now().astimezone() + timedelta(minutes=minutes)).isoformat(timespec="minutes")


class StandaloneRemindersTests(unittest.TestCase):
    def test_create_independent_reminder_and_store_after_restart(self):
        data = APP["default_data"]()
        prior_notes = [dict(n) for n in data["notes"]]
        item = reminder_store.make_reminder("Call customer", "Check link status", future())
        data["reminders"].append(item)
        with tempfile.TemporaryDirectory() as folder:
            file = Path(folder) / "data.json"
            APP["save_data"](file, data)
            loaded = APP["load_data"](file)
        self.assertEqual(loaded["notes"], prior_notes)
        self.assertEqual(len(loaded["reminders"]), 1)
        self.assertEqual(loaded["reminders"][0]["title"], "Call customer")
        self.assertEqual(loaded["reminders"][0]["details"], "Check link status")

    def test_old_user_profile_migrates_without_standalone_records(self):
        data = APP["default_data"]()
        data.pop("reminders")
        with tempfile.TemporaryDirectory() as folder:
            file = Path(folder) / "data.json"
            APP["save_data"](file, data)
            loaded = APP["load_data"](file)
            self.assertEqual(loaded["reminders"], [])
            self.assertEqual(len(loaded["notes"]), 1)

    def test_invalid_dates_bad_data_and_duplicate_ids_are_rejected(self):
        with self.assertRaises(ValueError):
            reminder_store.make_reminder(" ", "text", future())
        with self.assertRaises(ValueError):
            reminder_store.make_reminder("Task", "", "not-a-date")
        with self.assertRaises(ValueError):
            reminder_store.make_reminder("Task", "", datetime(2020, 1, 1, tzinfo=timezone.utc).isoformat())
        item = reminder_store.make_reminder("Task", "", future())
        with self.assertRaises(ValueError):
            reminder_store.normalize_reminders([item, item])
        with self.assertRaises(ValueError):
            reminder_store.normalize_reminders([{"title": "invalid"}])

    def test_standalone_done_saves_reply_on_reminder_not_on_notes(self):
        item = reminder_store.make_reminder("Finish ticket", "", future())
        original_note = note_model.new_note("Other note", "DO NOT CHANGE")
        old = dict(original_note)
        now = datetime(2026, 11, 18, 20, 17, tzinfo=timezone.utc)
        reminder_store.complete(item, "Customer confirmed", True, now=now)
        self.assertEqual(original_note, old)
        self.assertEqual(len(item["responses"]), 1)
        self.assertEqual(item["responses"][0]["text"], "Customer confirmed")
        self.assertRegex(item["responses"][0]["time"], r"^\d{2}/\d{2}/\d{4} \d{2}:\d{2}$")
        self.assertEqual(reminder_store.status(item), "Completed")

    def test_snooze_draft_stays_with_standalone_reminder(self):
        item = reminder_store.make_reminder("Task", "Details", future())
        reminder_store.snooze(item, 15, "draft text", True)
        self.assertEqual(item["details"], "Details")
        self.assertEqual(item["reminder_draft"], "draft text")
        self.assertEqual(reminder_store.status(item), "Snoozed")
        self.assertEqual(item["responses"], [])

    def test_checkbox_unchecked_does_not_write_a_reply(self):
        item = reminder_store.make_reminder("Task", "", future())
        reminder_store.complete(item, "Hidden", False)
        self.assertEqual(item["responses"], [])

    def test_pending_standalone_is_delivered_when_due(self):
        item = reminder_store.make_reminder("Urgent", "", future())
        item["reminder_at"] = (datetime.now().astimezone() -
                               timedelta(minutes=2)).isoformat(timespec="minutes")
        note = note_model.new_note()
        calls = []
        desk = SimpleNamespace(data={"notes": [note], "reminders": [item]},
                               _due_reminder_dialog=None, _reminder_dialog=None,
                               _modal=False, _display_due_reminder=
                               lambda ident, source="note": calls.append((ident, source)))
        Desk._reminder_poll(desk)
        self.assertEqual(calls, [(item["id"], "standalone")])
        self.assertEqual(item["reminder_sent_at"], "")

    def test_existing_note_delivery_still_uses_original_path(self):
        item = note_model.new_note("Legacy note")
        item.update(reminder_enabled=True,
                    reminder_at=(datetime.now().astimezone() -
                                 timedelta(minutes=1)).isoformat(timespec="minutes"))
        calls = []
        desk = SimpleNamespace(data={"notes": [item], "reminders": []},
                               _due_reminder_dialog=None, _reminder_dialog=None,
                               _modal=False, _display_due_reminder=
                               lambda ident, source="note": calls.append((ident, source)))
        Desk._reminder_poll(desk)
        self.assertEqual(calls, [(item["id"], "note")])

    def test_app_handler_appends_to_standalone_record_only(self):
        reminder = reminder_store.make_reminder("Call", "", future())
        reminder["reminder_at"] = (datetime.now().astimezone() -
                                   timedelta(minutes=1)).isoformat(timespec="minutes")
        note = note_model.new_note("Keep this", "Unmodified")
        captured = {}
        desk = SimpleNamespace(
            data={"notes": [note], "reminders": [reminder], "active_note": note["id"]},
            current_tab="reminders", _modal=False, _due_reminder_dialog=None,
            _flush_current_note=Mock(), _write_now=Mock(return_value=True),
            _load_selected_note=Mock(), _refresh_note_reminder_ui=Mock(),
            root=object(), theme="blue")
        with patch.object(APP["reminder_ui"], "open_due_dialog",
                          side_effect=lambda root, data, done, snooze, close, **kw:
                              (captured.update(done=done, close=close, data=data) or
                               SimpleNamespace(winfo_exists=lambda: True))):
            Desk._display_due_reminder(desk, reminder["id"], source="standalone")
        self.assertEqual(captured["data"]["kind"], "standalone")
        captured["done"]("done without Note", True)
        self.assertEqual(note["body"], "Unmodified")
        self.assertEqual(reminder["responses"][0]["text"], "done without Note")
        self.assertEqual(reminder_store.status(reminder), "Completed")
        captured["close"]()
        self.assertFalse(desk._modal)

    def test_notes_backup_contains_independent_reminders_and_restore(self):
        data = APP["default_data"]()
        item = reminder_store.make_reminder("Local task", "some details", future())
        data["reminders"] = [item]
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            output = root / "backup.zip"
            portable_backup.make_backup(output, data, selected=("notes",), profile_dir=root)
            bundle = portable_backup.read_backup(output)
            self.assertEqual(bundle["payload"]["notes"]["reminders"][0]["id"], item["id"])
            dest = APP["default_data"]()
            # Merge identical note IDs; a fresh starter Note naturally has a different UUID.
            dest["notes"] = [dict(n) for n in data["notes"]]
            dest["active_note"] = data["active_note"]
            restored = portable_backup.plan_restore(bundle, dest, selected=("notes",),
                                                    mode="merge")["profile"]
            self.assertEqual(restored["reminders"][0]["title"], "Local task")
            self.assertEqual(len(restored["notes"]), 1)

    def test_legacy_notes_backup_without_reminders_is_compatible(self):
        data = APP["default_data"]()
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            output = root / "backup.zip"
            portable_backup.make_backup(output, data, selected=("notes",), profile_dir=root)
            bundle = portable_backup.read_backup(output)
            del bundle["payload"]["notes"]["reminders"]
            planned = portable_backup.plan_restore(bundle, data, selected=("notes",),
                                                   mode="merge")
            self.assertEqual(planned["profile"]["reminders"], [])


if __name__ == "__main__":
    unittest.main()
