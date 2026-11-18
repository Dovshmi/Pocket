"""Desktop checks for the v1.39.9 Note reminder dialog and date/time picker.

Runs on native Windows Tk or under xvfb-run on Linux. Does not send toasts or
write any user's files.
"""
import sys
import tkinter as tk
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from pocket import note_model, reminder_ui


def run():
    root = tk.Tk()
    root.withdraw()
    try:
        note = note_model.new_note("בדיקת לקוח", "Original text")
        done = []
        closed = []
        window = reminder_ui.open_due_dialog(
            root, note, lambda text, checked: done.append((text, checked)),
            lambda *args: None, lambda: closed.append(True))
        root.update()
        assert window.winfo_viewable(), "Reminder must be visible while main Pocket window is hidden"
        entry = window._response_input
        assert entry.cget("state") == "disabled", "Input must be disabled by default"
        entry.insert("1.0", "blocked")
        assert entry.get("1.0", "end-1c") == "", "Disabled input accepted typing"
        window._response_enabled.set(True)
        root.update()
        assert entry.cget("state") == "normal", "Checkbox should enable the input"
        entry.insert("1.0", "a quick response")
        window._done_button.invoke()
        assert done == [("a quick response", True)], done
        assert closed == [True]

        # A user who unchecks the box after typing must not save that text.
        unchecked = []
        ignored = reminder_ui.open_due_dialog(
            root, note, lambda text, checked: unchecked.append((text, checked)),
            lambda *_: None, lambda: None)
        root.update()
        ignored._response_enabled.set(True)
        ignored._response_input.insert("1.0", "should not save")
        ignored._response_enabled.set(False)
        root.update()
        assert ignored._response_input.cget("state") == "disabled"
        ignored._done_button.invoke()
        assert unchecked == [("", False)], unchecked

        snoozed = []
        second = reminder_ui.open_due_dialog(
            root, note, lambda *_: None,
            lambda minutes, text, checked: snoozed.append((minutes, text, checked)),
            lambda: closed.append(True))
        root.update()
        second._response_enabled.set(True)
        second._response_input.insert("1.0", "later")
        second._snooze_minutes.set("30 minutes")
        second._snooze_button.invoke()
        assert snoozed == [(30, "later", True)], snoozed

        selected = []
        dismissed = []
        editor = reminder_ui.open_datetime_editor(
            root, note, lambda when: selected.append(when),
            lambda: dismissed.append(True))
        root.update()
        editor._selected_date = date.today() + timedelta(days=3)
        editor._hour_picker.set("13")
        editor._minute_picker.set("05")
        editor._save_reminder()
        assert len(selected) == 1, selected
        assert selected[0].endswith("13:05" + selected[0][-6:]), selected
        assert len(dismissed) == 1, dismissed
    finally:
        root.destroy()
    print("PASS: editable response only after checked, Snooze and calendar selection")


if __name__ == "__main__":
    run()
