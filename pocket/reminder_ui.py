"""Offline, native-looking reminder dialogs and the Note-linked overview.

The Windows MessageBox cannot host user text entry. These are ordinary
decorated child windows with system ttk controls, independent of Pocket's
custom main popup, and require no optional libraries or network access.
"""
from __future__ import annotations

import calendar
from datetime import datetime, timedelta
import tkinter as tk
from tkinter import ttk, messagebox

from . import note_model as notes

FONT = "Segoe UI"
BG = "#F5F5F7"
FG = "#20242A"
MUTED = "#565D69"
SNOOZE_LABELS = (
    ("5 minutes", 5), ("15 minutes", 15),
    ("30 minutes", 30), ("1 hour", 60),
)


def _dialog(root, title, width, height):
    window = tk.Toplevel(root)
    window.title(title)
    window.configure(bg=BG)
    window.resizable(False, False)
    window.update_idletasks()
    screen_w, screen_h = window.winfo_screenwidth(), window.winfo_screenheight()
    x = max(8, min(screen_w - width - 8, root.winfo_pointerx() - width // 2))
    y = max(8, min(screen_h - height - 55, root.winfo_pointery() - height // 3))
    window.geometry(f"{width}x{height}+{x}+{y}")
    window.attributes("-topmost", True)
    window.lift()
    return window


def open_datetime_editor(root, note, on_save, on_close):
    """Calendar with real date buttons, 24h dropdowns, and quick time presets."""
    now = datetime.now().astimezone()
    try:
        current = datetime.fromisoformat(note["reminder_at"]).astimezone()
        if current <= now:
            current = now + timedelta(minutes=15)
    except (KeyError, TypeError, ValueError):
        current = now + timedelta(minutes=15)
    window = _dialog(root, "Pocket · Set note reminder", 425, 522)
    window._selected_date = current.date()
    window._view_year = current.year
    window._view_month = current.month
    hour = tk.StringVar(window, current.strftime("%H"))
    minute = tk.StringVar(window, current.strftime("%M"))
    status = tk.StringVar(window, "")

    head = tk.Frame(window, bg=BG)
    head.pack(fill="x", padx=18, pady=(15, 4))
    tk.Label(head, text="Set a reminder", font=(FONT, 13, "bold"),
             fg=FG, bg=BG).pack(anchor="w")
    tk.Label(head, text=(note.get("title") or "Note")[:58],
             font=(FONT, 9), fg=MUTED, bg=BG).pack(anchor="w", pady=(4, 0))

    shortcuts = tk.Frame(window, bg=BG)
    shortcuts.pack(fill="x", padx=16, pady=(10, 7))
    def choose_in(minutes_delta):
        target = datetime.now().astimezone() + timedelta(minutes=minutes_delta)
        choose_date(target.date())
        hour.set(target.strftime("%H"))
        minute.set(target.strftime("%M"))

    def choose_tomorrow():
        target = datetime.now().astimezone() + timedelta(days=1)
        choose_date(target.date())
        hour.set("09")
        minute.set("00")

    for label, fn in (
        ("+15 min", lambda: choose_in(15)),
        ("+1 hour", lambda: choose_in(60)),
        ("Tomorrow 09:00", choose_tomorrow),
    ):
        ttk.Button(shortcuts, text=label, command=fn).pack(
            side="left", padx=(0, 6))

    bar = tk.Frame(window, bg=BG)
    bar.pack(fill="x", padx=18, pady=(3, 4))
    previous = ttk.Button(bar, text="‹", width=3)
    previous.pack(side="left")
    month_label = tk.Label(bar, font=(FONT, 11, "bold"), fg=FG, bg=BG)
    month_label.pack(side="left", expand=True)
    following = ttk.Button(bar, text="›", width=3)
    following.pack(side="right")
    calendar_frame = tk.Frame(window, bg=BG)
    calendar_frame.pack(fill="x", padx=18)
    for col in range(7):
        calendar_frame.grid_columnconfigure(col, weight=1, uniform="cal")

    def redraw():
        for widget in calendar_frame.winfo_children():
            widget.destroy()
        month_label.configure(text=f"{calendar.month_name[window._view_month]} {window._view_year}")
        for col, name in enumerate(("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")):
            tk.Label(calendar_frame, text=name, bg=BG, fg=MUTED,
                     font=(FONT, 8)).grid(row=0, column=col, pady=2)
        weeks = calendar.Calendar(firstweekday=0).monthdatescalendar(
            window._view_year, window._view_month)
        while len(weeks) < 6:
            last = weeks[-1][-1]
            weeks.append([last + timedelta(days=delta) for delta in range(1, 8)])
        for row, week in enumerate(weeks, start=1):
            for col, day in enumerate(week):
                selected = day == window._selected_date
                in_month = day.month == window._view_month
                button = tk.Button(
                    calendar_frame, text=str(day.day), relief="flat",
                    font=(FONT, 9, "bold" if selected else "normal"),
                    bg="#DCEBFF" if selected else BG,
                    fg="#111A2D" if selected else (FG if in_month else "#858A94"),
                    activebackground="#CBDCFA",
                    command=lambda value=day: choose_date(value))
                button.grid(row=row, column=col, sticky="ew", padx=1, pady=1)

    def choose_date(day):
        window._selected_date = day
        window._view_year, window._view_month = day.year, day.month
        redraw()

    def step_month(offset):
        year, month = window._view_year, window._view_month + offset
        if month < 1:
            year, month = year - 1, 12
        elif month > 12:
            year, month = year + 1, 1
        window._view_year, window._view_month = year, month
        redraw()

    previous.configure(command=lambda: step_month(-1))
    following.configure(command=lambda: step_month(1))
    redraw()

    clock = tk.Frame(window, bg=BG)
    clock.pack(pady=(13, 3))
    tk.Label(clock, text="Time (24h)", font=(FONT, 9), fg=MUTED,
             bg=BG).pack(side="left", padx=(0, 14))
    hours = ttk.Combobox(clock, textvariable=hour, state="readonly",
                         width=5, values=[f"{i:02}" for i in range(24)])
    hours.pack(side="left")
    tk.Label(clock, text=":", font=(FONT, 13, "bold"), fg=FG, bg=BG).pack(
        side="left", padx=3)
    minutes = ttk.Combobox(clock, textvariable=minute, state="readonly",
                           width=5, values=[f"{i:02}" for i in range(60)])
    minutes.pack(side="left")
    window._hour_picker = hours
    window._minute_picker = minutes

    tk.Label(window, text="Local computer time · Pocket must be running.",
             bg=BG, fg=MUTED, font=(FONT, 8)).pack(pady=(7, 3))
    tk.Label(window, textvariable=status, bg=BG, fg="#AD3741",
             font=(FONT, 8), wraplength=385).pack(pady=(0, 2))
    footer = tk.Frame(window, bg=BG)
    footer.pack(fill="x", side="bottom", padx=18, pady=(8, 14))

    closed = False
    def close():
        nonlocal closed
        if closed:
            return
        closed = True
        window.destroy()
        on_close()

    def save():
        try:
            when = notes.parse_reminder_time(
                window._selected_date.isoformat(), f"{hour.get()}:{minute.get()}")
        except ValueError as exc:
            status.set(str(exc))
            return
        try:
            on_save(when)
        except Exception as exc:
            messagebox.showerror("Pocket reminder", str(exc), parent=window)
            return
        close()

    ttk.Button(footer, text="Cancel", command=close).pack(side="right")
    ttk.Button(footer, text="Save reminder", command=save).pack(
        side="right", padx=(0, 8))
    window._save_reminder = save
    window.protocol("WM_DELETE_WINDOW", close)
    window.bind("<Escape>", lambda _event: close())
    window.focus_force()
    return window


def open_due_dialog(root, note, on_done, on_snooze, on_close):
    """Windows-style reminder; input is impossible until Add response is checked."""
    window = _dialog(root, "Pocket · Note reminder", 438, 326)
    title = (note.get("title") or "Note").strip() or "Note"
    heading = tk.Frame(window, bg=BG)
    heading.pack(fill="x", padx=20, pady=(18, 8))
    tk.Label(heading, text="Reminder", font=(FONT, 14, "bold"),
             fg=FG, bg=BG).pack(anchor="w")
    tk.Label(heading, text=title[:72], font=(FONT, 10),
             fg=FG, bg=BG, wraplength=396, justify="left").pack(
                 anchor="w", pady=(6, 0))

    add_response = tk.BooleanVar(window, note.get("reminder_add_response") is True)
    checked = ttk.Checkbutton(window, text="Add response to the bottom of this note",
                              variable=add_response)
    checked.pack(anchor="w", padx=20, pady=(5, 6))
    input_text = tk.Text(window, height=4, width=48, wrap="word",
                         font=(FONT, 10), relief="solid", bd=1, undo=True)
    input_text.pack(fill="x", padx=20)
    draft = note.get("reminder_draft", "")
    if draft and add_response.get():
        input_text.insert("1.0", draft[:4000])

    def sync_input(*_args):
        input_text.configure(state="normal" if add_response.get() else "disabled",
                             bg="#FFFFFF" if add_response.get() else "#E4E6EA")
        if add_response.get():
            input_text.focus_set()

    add_response.trace_add("write", sync_input)
    sync_input()
    window._response_input = input_text
    window._response_enabled = add_response
    window._response_checkbox = checked

    description = tk.Label(
        window, text="Response is optional. Closing dismisses this reminder.",
        bg=BG, fg=MUTED, font=(FONT, 8))
    description.pack(anchor="w", padx=20, pady=(6, 2))

    footer = tk.Frame(window, bg=BG)
    footer.pack(fill="x", padx=20, pady=(13, 12), side="bottom")
    interval = tk.StringVar(window, "15 minutes")
    picker = ttk.Combobox(footer, textvariable=interval, state="readonly",
                          width=11, values=[label for label, _ in SNOOZE_LABELS])
    picker.pack(side="left")
    window._snooze_minutes = interval
    closed = False

    def response():
        return (input_text.get("1.0", "end-1c")[:4000]
                if add_response.get() else "")

    def finish(kind):
        nonlocal closed
        if closed:
            return
        try:
            if kind == "snooze":
                minutes = dict(SNOOZE_LABELS)[interval.get()]
                on_snooze(minutes, response(), add_response.get())
            else:
                on_done(response(), add_response.get())
        except Exception as exc:
            messagebox.showerror("Pocket reminder", str(exc), parent=window)
            return
        closed = True
        window.destroy()
        on_close()

    snooze = ttk.Button(footer, text="Snooze",
                        command=lambda: finish("snooze"))
    snooze.pack(side="left", padx=(6, 0))
    ttk.Button(footer, text="Dismiss", command=lambda: finish("done")).pack(
        side="right")
    done = ttk.Button(footer, text="Done", command=lambda: finish("done"))
    done.pack(side="right", padx=(0, 7))
    window._done_button = done
    window._snooze_button = snooze
    window.protocol("WM_DELETE_WINDOW", lambda: finish("done"))
    window.bind("<Escape>", lambda _event: finish("done"))
    window.lift()
    if not add_response.get():
        done.focus_set()
    return window


def build_overview(app, parent, *, colors):
    """A separate view reached from Notes/More, without adding top-bar icons."""
    c = colors
    tk.Label(parent, text="Reminders", bg=c["BG"], fg=c["WHITE"],
             font=(FONT, 17, "bold")).pack(anchor="w", pady=(2, 5))
    tk.Label(parent, text="All your Note reminders in one place.",
             bg=c["BG"], fg=c["MUTED"], font=(FONT, 9)).pack(anchor="w", pady=(0, 10))
    notes_with_reminders = [
        note for note in app.data["notes"] if notes.reminder_status(note)]
    counts = {status: sum(notes.reminder_status(note) == status
                          for note in notes_with_reminders)
              for status in ("Upcoming", "Snoozed", "Completed")}
    tk.Label(parent, text="   ".join(f"{name}: {count}" for name, count in counts.items()),
             bg=c["BG"], fg=c["SECONDARY"], font=(FONT, 9, "bold"),
             anchor="w").pack(fill="x", pady=(0, 10))

    actions = tk.Frame(parent, bg=c["BG"])
    actions.pack(fill="x", pady=(0, 10))
    ttk.Button(actions, text="← Notes", command=lambda: app.show_tab("notes")).pack(
        side="left")
    ttk.Button(actions, text="Set reminder for active note",
               command=lambda: app._edit_note_reminder(app.data["active_note"])).pack(
                   side="right")

    status_filter = tk.StringVar(parent, "All")
    filter_frame = tk.Frame(parent, bg=c["BG"])
    filter_frame.pack(fill="x", pady=(0, 8))
    tk.Label(filter_frame, text="Show", font=(FONT, 9), bg=c["BG"],
             fg=c["SECONDARY"]).pack(side="left", padx=(0, 9))
    choice = ttk.Combobox(filter_frame, textvariable=status_filter,
                          values=("All", "Upcoming", "Snoozed", "Completed"),
                          state="readonly", width=16)
    choice.pack(side="left")
    listing = tk.Frame(parent, bg=c["BG"])
    listing.pack(fill="x")

    def render(_event=None):
        for child in listing.winfo_children():
            child.destroy()
        entries = [n for n in notes_with_reminders
                   if status_filter.get() in ("All", notes.reminder_status(n))]
        entries.sort(key=lambda n: (notes.reminder_status(n) == "Completed",
                                    n.get("reminder_at", "")))
        if not entries:
            tk.Label(listing, text="No reminders in this view.",
                     bg=c["BG"], fg=c["MUTED"], font=(FONT, 9)).pack(
                         anchor="w", pady=12)
            return
        for note in entries:
            item = tk.Frame(listing, bg=c["PANEL"], highlightthickness=1,
                            highlightbackground=c["BORDER"])
            item.pack(fill="x", pady=(0, 7))
            tk.Label(item, text=(note.get("title") or "Note")[:52],
                     bg=c["PANEL"], fg=c["WHITE"], font=(FONT, 10, "bold"),
                     anchor="w").pack(fill="x", padx=9, pady=(8, 2))
            when = notes.format_reminder(note)
            tk.Label(item, text=f"{notes.reminder_status(note)} · {when}",
                     bg=c["PANEL"], fg=c["SECONDARY"],
                     font=(FONT, 8), anchor="w").pack(fill="x", padx=9)
            buttons = tk.Frame(item, bg=c["PANEL"])
            buttons.pack(fill="x", padx=8, pady=6)
            def open_note(note_id=note["id"]):
                app.data["active_note"] = note_id
                app.show_tab("notes")
            ttk.Button(buttons, text="Open", command=open_note).pack(side="left")
            ttk.Button(buttons, text="Edit time",
                       command=lambda note_id=note["id"]: app._edit_note_reminder(note_id)
                       ).pack(side="left", padx=(5, 0))
            if notes.reminder_status(note) != "Completed":
                ttk.Button(buttons, text="Snooze 15m",
                           command=lambda note_id=note["id"]: app._manage_note_reminder(
                               note_id, "snooze")).pack(side="left", padx=(5, 0))
                ttk.Button(buttons, text="Done",
                           command=lambda note_id=note["id"]: app._manage_note_reminder(
                               note_id, "done")).pack(side="right")
    choice.bind("<<ComboboxSelected>>", render)
    render()
    parent._reminders_filter = status_filter
