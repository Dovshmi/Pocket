"""v1.39.9 Note reminder lifecycle; all operations stay local and append-only."""
from datetime import datetime, timedelta, timezone
import unittest

from pocket import note_model as notes


class NoteReminderLifecycleTests(unittest.TestCase):
    def test_response_never_modifies_existing_content(self):
        instant = datetime(2026, 11, 18, 20, 17, tzinfo=timezone.utc)
        stamp = instant.astimezone().strftime("%d/%m/%Y %H:%M")
        initial = "כותרת\nתוכן קיים\n"
        result = notes.append_reminder_response(
            initial, "  הפעולה הושלמה  ", True, now=instant)
        self.assertTrue(result.startswith(initial))
        self.assertEqual(result, initial + "\n" + stamp + "\nהפעולה הושלמה")
        self.assertEqual(notes.append_reminder_response(
            "hello", "world", True, now=instant),
            "hello\n\n" + stamp + "\nworld")
        self.assertEqual(notes.append_reminder_response(
            "", "  hello  ", True, now=instant), stamp + "\nhello")

    def test_no_checkbox_or_empty_response_never_writes(self):
        for checked, value in ((False, "typed"), (True, "  "), (False, "")):
            note = notes.new_note("Task", "keep this exactly")
            now = datetime(2026, 11, 18, 18, tzinfo=timezone.utc)
            self.assertFalse(notes.complete_reminder(note, value, checked, now=now))
            self.assertEqual(note["body"], "keep this exactly")
            self.assertTrue(note["reminder_sent_at"])
            self.assertFalse(note["reminder_snoozed"])

    def test_response_is_appended_once_and_marks_complete(self):
        note = notes.new_note("Task", "step 1")
        moment = datetime(2026, 11, 18, 20, 17, tzinfo=timezone.utc)
        self.assertTrue(notes.complete_reminder(note, "step 2", True, now=moment))
        stamp = moment.astimezone().strftime("%d/%m/%Y %H:%M")
        self.assertEqual(note["body"], "step 1\n\n" + stamp + "\nstep 2")
        self.assertEqual(notes.reminder_status({**note, "reminder_enabled": True}),
                         "Completed")

    def test_snooze_keeps_uncommitted_draft_and_reschedules(self):
        start = datetime(2026, 11, 18, 18, 30, tzinfo=timezone.utc)
        for minutes in notes.SNOOZE_MINUTES:
            n = notes.new_note("Task", "original")
            notes.snooze_reminder(n, minutes, "draft for later", True, now=start)
            self.assertEqual(n["body"], "original")
            self.assertEqual(n["reminder_draft"], "draft for later")
            self.assertTrue(n["reminder_add_response"])
            self.assertTrue(n["reminder_snoozed"])
            self.assertEqual(n["reminder_sent_at"], "")
            self.assertEqual(notes.reminder_status(n), "Snoozed")
            when = datetime.fromisoformat(n["reminder_at"])
            self.assertEqual(when, start + timedelta(minutes=minutes))
            self.assertFalse(notes.reminder_is_due(n, now=start))
            self.assertTrue(notes.reminder_is_due(n, now=when))
            notes.normalize_note_reminder(n)
            self.assertEqual(n["reminder_draft"], "draft for later")
            self.assertEqual(n["reminder_at"], when.isoformat(timespec="minutes"))
        with self.assertRaises(ValueError):
            notes.snooze_reminder(n, 7, "text", True)

    def test_disabled_snooze_discards_unchecked_response(self):
        n = notes.new_note()
        notes.snooze_reminder(n, 15, "must not be written", False)
        self.assertEqual(n["reminder_draft"], "")
        self.assertFalse(n["reminder_add_response"])

    def test_old_notes_migrate_without_becoming_due(self):
        old = {"id": "legacy", "body": "old text", "reminder_enabled": False}
        notes.normalize_note_reminder(old)
        self.assertFalse(notes.reminder_is_due(old))
        self.assertFalse(old["reminder_snoozed"])
        self.assertEqual(old["reminder_draft"], "")
        self.assertFalse(old["reminder_add_response"])
        self.assertIsNone(notes.reminder_status(old))

    def test_unchecked_and_long_response_safeguards(self):
        with self.assertRaises(ValueError):
            notes.append_reminder_response("keep", "a" * 4001, True)
        self.assertEqual(notes.append_reminder_response("keep", "a" * 4001, False),
                         "keep")


if __name__ == "__main__":
    unittest.main()
