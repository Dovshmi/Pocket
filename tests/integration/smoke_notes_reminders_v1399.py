"""Desktop checks for the v1.39.9 Note reminder dialog and date/time picker.

Runs on native Windows Tk or under xvfb-run on Linux. Does not send toasts or
write any user's files.
"""
import sys
import tkinter as tk
from datetime import date, timedelta, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from pocket import note_model, reminder_ui, icon_themes, reminder_store


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
        assert (editor.winfo_width(), editor.winfo_height()) == (366, 445), (
            "Calendar should be more compact than the old 425×522 window")
        assert editor.cget("bg") == icon_themes.palette("blue")["BG"], (
            "Scheduler must match the Pocket theme")
        assert editor._preset_picker.get() == "Custom time"
        assert str(editor._hour_picker.cget("state")) == "readonly"
        editor._preset_picker.set("+15 minutes")
        editor._apply_preset()
        root.update()
        assert str(editor._hour_picker.cget("state")) == "disabled"
        assert str(editor._minute_picker.cget("state")) == "disabled"
        editor._preset_picker.set("Custom time")
        editor._apply_preset()
        assert str(editor._hour_picker.cget("state")) == "readonly"
        assert str(editor._minute_picker.cget("state")) == "readonly"
        editor._choose_date(date.today() + timedelta(days=3))
        editor._hour_picker.set("13")
        editor._minute_picker.set("05")
        editor._save_reminder()
        assert len(selected) == 1, selected
        assert selected[0].endswith("13:05" + selected[0][-6:]), selected
        assert len(dismissed) == 1, dismissed
        # A standalone record has its own title/details/time and makes no Note.
        saved = []
        form = reminder_ui.open_standalone_form(
            root, None, lambda title, details, when: saved.append((title, details, when)),
            lambda: None)
        root.update()
        form._submit_reminder()
        assert not saved, "Empty standalone reminders must be rejected"
        form._title_entry.insert(0, "Call customer")
        form._details_text.insert("1.0", "Check the link status")
        form._selected_time[0] = (datetime.now().astimezone() +
                                  timedelta(hours=2)).isoformat(timespec="minutes")
        form._submit_reminder()
        assert len(saved) == 1, saved
        assert saved[0][0] == "Call customer"
        assert saved[0][1] == "Check the link status"
        assert note["body"] == "Original text", "Creating a reminder changed Notes"

        independent = reminder_store.make_reminder(*saved[0])
        independent["reminder_at"] = saved[0][2]
        events = []
        from types import SimpleNamespace
        app = SimpleNamespace(
            data={"notes": [note], "reminders": [independent]},
            _edit_standalone_reminder=lambda *_args: events.append("new"),
            _edit_note_reminder=lambda *_args: events.append("note"),
            _manage_note_reminder=lambda *a, **kw: events.append("manage"),
            _delete_standalone_reminder=lambda *_args: events.append("delete"),
            show_tab=lambda *_args: events.append("navigate"),
            _reminders_status_filter="All")
        overview = tk.Frame(root)
        overview.pack()
        reminder_ui.build_overview(
            app, overview, colors=icon_themes.palette("blue"))
        root.update()
        def descendants(widget):
            for child in widget.winfo_children():
                yield child
                yield from descendants(child)
        buttons = [w for w in descendants(overview) if isinstance(w, tk.Button)]
        assert any(w.cget("text") == "Details" for w in buttons), (
            "Standalone card missing Details action")
        assert any(w.cget("text") == "Snooze 15m" for w in buttons)
        next(w for w in buttons if w.cget("text") == "+ New").invoke()
        assert events == ["new"]
        assert app._reminders_status_filter == "All"
        assert app._reminders_search_entry.cget("bg") == icon_themes.palette("blue")["INPUT"]

        # The same reminder popup uses a standalone-specific response label.
        standalone_popup = reminder_ui.open_due_dialog(
            root, {**independent, "kind": "standalone"},
            lambda *_args: None, lambda *_args: None, lambda: None)
        root.update()
        assert "this reminder" in standalone_popup._response_checkbox.cget("text")
        assert standalone_popup._response_input.cget("state") == "disabled"
        standalone_popup._done_button.invoke()

    finally:
        root.destroy()
    print("PASS: editable response only after checked, Snooze and calendar selection")


if __name__ == "__main__":
    run()
