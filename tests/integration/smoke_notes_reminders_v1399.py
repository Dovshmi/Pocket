"""Desktop checks for the v1.39.9 Note reminder dialog and date/time picker.

Runs on native Windows Tk or under xvfb-run on Linux. Does not send toasts or
write any user's files.
"""
import sys
import tkinter as tk
from datetime import date, timedelta, datetime
from pathlib import Path
from types import SimpleNamespace
from tkinter import ttk

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from pocket import note_model, reminder_ui, icon_themes, reminder_store

import runpy
APP = runpy.run_path(str(Path(__file__).resolve().parents[2] / "app.pyw"),
                     run_name="test_import")
Desk = APP["PocketDesk"]


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
        assert window._reminder_title_label.cget("text") == "בדיקת לקוח"
        assert window._reminder_content_view.get("1.0", "end-1c") == "Original text"
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
        # New independent reminders start with a calendar, then edit in-card.
        independent = reminder_store.make_reminder(
            "New reminder", "", (datetime.now().astimezone() +
                                  timedelta(hours=2)).isoformat(timespec="minutes"))
        events = []
        from types import SimpleNamespace
        def inline_save(ident, **fields):
            assert ident == independent["id"]
            return reminder_store.update_inline_fields(independent, **fields)

        app = SimpleNamespace(
            data={"notes": [note], "reminders": [independent]},
            _edit_standalone_reminder=lambda *_args: events.append("calendar"),
            _save_standalone_inline=inline_save,
            _edit_note_reminder=lambda *_args: events.append("note"),
            _manage_note_reminder=lambda *a, **kw: events.append("manage"),
            _delete_standalone_reminder=lambda *_args: events.append("delete"),
            _delete_reminder=lambda *_args, **kwargs: events.append(
                ("delete", kwargs.get("source"))),
            show_tab=lambda *_args: events.append("navigate"),
            _reminders_status_filter="All", _reminders_focus_new=independent["id"])
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
        assert not hasattr(reminder_ui, "open_standalone_form"), (
            "Standalone title/Note must not open a separate form")
        assert any(w.cget("text") == "Change time" for w in buttons)
        assert not any(w.cget("text") == "Details" for w in buttons)
        assert any(w.cget("text") == "Snooze 15m" for w in buttons)
        assert not any(w.cget("text") in ("Delete", "Done") for w in buttons)
        assert sum(w.cget("text") == "×" for w in buttons) == 1
        assert sum(w.cget("text") == "✓" for w in buttons) == 1
        next(w for w in buttons if w.cget("text") == "✓").invoke()
        assert events == ["manage"]
        events.clear()
        next(w for w in buttons if w.cget("text") == "×").invoke()
        assert events == [("delete", "standalone")]
        events.clear()
        next(w for w in buttons if w.cget("text") == "+ New").invoke()
        assert events == ["calendar"]
        title_field, note_field = app._reminders_inline_fields[independent["id"]]
        assert isinstance(title_field, tk.Entry) and isinstance(note_field, tk.Text)
        assert app._reminders_focus_new is None
        title_field.delete(0, "end")
        title_field.insert(0, "Call customer")
        assert independent["title"] == "Call customer", independent
        note_field.insert("1.0", "Check the link status")
        note_field.edit_modified(True)
        root.update()
        assert independent["details"] == "Check the link status", independent
        assert note["body"] == "Original text", "Editing a standalone reminder changed Notes"
        assert len(app.data["notes"]) == 1, "No Note should be created by + New"
        assert app._reminders_status_filter == "All"
        assert app._reminders_search_entry.cget("bg") == icon_themes.palette("blue")["INPUT"]
        assert overview._reminders_summary.winfo_height() < 43, (
            "The status counters must be compact")

        # The same reminder popup uses a standalone-specific response label.
        standalone_popup = reminder_ui.open_due_dialog(
            root, {**independent, "kind": "standalone"},
            lambda *_args: None, lambda *_args: None, lambda: None)
        root.update()
        assert "this reminder" in standalone_popup._response_checkbox.cget("text")
        assert standalone_popup._response_input.cget("state") == "disabled"
        assert standalone_popup._reminder_title_label.cget("text") == "Call customer"
        assert (standalone_popup._reminder_content_view.get("1.0", "end-1c")
                == "Check the link status")
        standalone_popup._done_button.invoke()

        independent["reminder_sent_at"] = datetime.now().astimezone().isoformat()
        completed = tk.Frame(root)
        completed.pack()
        reminder_ui.build_overview(app, completed, colors=icon_themes.palette("blue"))
        root.update()
        finished_buttons = [w for w in descendants(completed) if isinstance(w, tk.Button)]
        assert any(w.cget("text") == "Reactivate" for w in finished_buttons)
        assert not any(w.cget("text") == "Change time" for w in finished_buttons)
        next(w for w in finished_buttons if w.cget("text") == "Reactivate").invoke()
        assert events[-1] == "calendar"

        # Long reminder body is COMPLETE and readable in a scrollable viewer,
        # not truncated to the title or to an arbitrary preview length.
        long_body = "First line\n" + "\n".join(
            "Customer action " + str(i) for i in range(80))
        long_popup = reminder_ui.open_due_dialog(
            root, {**note, "body": long_body}, lambda *_args: None,
            lambda *_args: None, lambda: None)
        root.update()
        viewer = long_popup._reminder_content_view
        assert viewer is not None
        assert viewer.get("1.0", "end-1c") == long_body
        assert viewer.yview()[1] < 1, "Full Note content should be scrollable"
        viewer.yview_moveto(1.0)
        assert viewer.yview()[0] > 0, "Could not scroll full Note content"
        long_popup._done_button.invoke()

        # The Mini Reminders page scrolls with the wheel, with no visible rail.
        page = tk.Toplevel(root)
        page.geometry("340x210")
        outer = tk.Frame(page)
        outer.pack(fill="both", expand=True)
        host = SimpleNamespace(body=outer, display_mode="mini",
                               current_tab="reminders", _tool_scroll_canvas=None)
        Desk._scrolling_tool_body(host)
        for i in range(45):
            tk.Label(host.body, text=f"Reminder number {i}").pack()
        root.update()
        assert not any(isinstance(w, ttk.Scrollbar) for w in outer.winfo_children()), (
            "Reminder scroll rail should remain invisible")
        canvas = host._tool_scroll_canvas
        assert canvas.yview()[1] < 1, "Scrollable Reminder area not sized"
        start = canvas.yview()[0]
        wheel = SimpleNamespace(delta=-120, num=None, widget=host.body)
        assert Desk._scroll_tool_on_wheel(host, wheel) == "break"
        root.update()
        assert canvas.yview()[0] > start, "Mini Reminder mouse wheel did not scroll"
        page.destroy()

    finally:
        root.destroy()
    print("PASS: editable response only after checked, Snooze and calendar selection")


if __name__ == "__main__":
    run()
