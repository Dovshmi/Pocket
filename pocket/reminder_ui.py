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
from . import icon_themes as themes

FONT = "Segoe UI"
SNOOZE_LABELS = (
    ("5 minutes", 5), ("15 minutes", 15),
    ("30 minutes", 30), ("1 hour", 60),
)


def _dialog(root, title, width, height, theme="blue"):
    c = themes.palette(theme)
    window = tk.Toplevel(root)
    window.title(title)
    window.configure(bg=c["BG"])
    window._reminder_colors = c
    window.resizable(False, False)
    window.update_idletasks()
    screen_w, screen_h = window.winfo_screenwidth(), window.winfo_screenheight()
    x = max(8, min(screen_w - width - 8, root.winfo_pointerx() - width // 2))
    y = max(8, min(screen_h - height - 55, root.winfo_pointery() - height // 3))
    window.geometry(f"{width}x{height}+{x}+{y}")
    window.attributes("-topmost", True)
    window.lift()
    style = ttk.Style(window)
    style.configure("Reminder.TCombobox", padding=3,
                    foreground=c["WHITE"], background=c["CARD"],
                    fieldbackground=c["INPUT"], arrowcolor=c["ACCENT"])
    style.map("Reminder.TCombobox",
              fieldbackground=[("disabled", c["CARD"]), ("readonly", c["INPUT"])],
              foreground=[("disabled", c["MUTED"]), ("readonly", c["WHITE"])],
              selectbackground=[("readonly", c["INPUT"])],
              selectforeground=[("readonly", c["WHITE"])])
    style.configure("Reminder.TCheckbutton", background=c["BG"],
                    foreground=c["WHITE"], font=(FONT, 9))
    style.map("Reminder.TCheckbutton", background=[("active", c["BG"])],
              foreground=[("disabled", c["MUTED"])])
    return window


def open_datetime_editor(root, note, on_save, on_close, theme="blue"):
    """A compact Pocket-themed calendar, preset dropdown and 24h time fields."""
    now = datetime.now().astimezone()
    try:
        current = datetime.fromisoformat(note["reminder_at"]).astimezone()
        if current <= now:
            current = now + timedelta(minutes=15)
    except (KeyError, TypeError, ValueError):
        current = now + timedelta(minutes=15)

    window = _dialog(root, "Pocket · Set reminder", 366, 445, theme=theme)
    c = window._reminder_colors
    window._selected_date = current.date()
    window._view_year = current.year
    window._view_month = current.month
    hour = tk.StringVar(window, current.strftime("%H"))
    minute = tk.StringVar(window, current.strftime("%M"))
    preset = tk.StringVar(window, "Custom time")
    status = tk.StringVar(window, "")

    def label(parent, text, *, size=9, bold=False, fg=None):
        return tk.Label(parent, text=text, font=(FONT, size, "bold" if bold else "normal"),
                        bg=c["BG"], fg=fg or c["WHITE"], anchor="w")

    def button(parent, title, command, *, width=None):
        options = {"width": width} if width else {}
        return tk.Button(
            parent, text=title, command=command,
            font=(FONT, 9), relief="flat", bd=0, cursor="hand2",
            bg=c["CARD"], fg=c["WHITE"], activebackground=c["CARD_HOVER"],
            activeforeground=c["ACCENT"], padx=5, pady=3, **options)

    head = tk.Frame(window, bg=c["BG"])
    head.pack(fill="x", padx=16, pady=(12, 4))
    label(head, "Set a reminder", size=12, bold=True).pack(anchor="w")
    label(head, (note.get("title") or "Note")[:55], size=8, fg=c["MUTED"]
          ).pack(anchor="w", pady=(3, 0))

    quick = tk.Frame(window, bg=c["BG"])
    quick.pack(fill="x", padx=16, pady=(8, 6))
    label(quick, "When", size=9, fg=c["SECONDARY"]).pack(side="left", padx=(0, 10))
    preset_picker = ttk.Combobox(
        quick, textvariable=preset, state="readonly",
        style="Reminder.TCombobox", font=(FONT, 9), width=23,
        values=("Custom time", "+15 minutes", "+1 hour", "Tomorrow 09:00"))
    preset_picker.pack(side="left", fill="x", expand=True)
    window._preset_picker = preset_picker

    month_bar = tk.Frame(window, bg=c["BG"])
    month_bar.pack(fill="x", padx=16, pady=(2, 1))
    previous = button(month_bar, "‹", lambda: step_month(-1), width=3)
    previous.pack(side="left")
    month_label = label(month_bar, "", size=10, bold=True)
    month_label.pack(side="left", expand=True)
    following = button(month_bar, "›", lambda: step_month(1), width=3)
    following.pack(side="right")

    calendar_frame = tk.Frame(window, bg=c["BG"])
    calendar_frame.pack(fill="x", padx=16)
    window._calendar_frame = calendar_frame
    for col in range(7):
        calendar_frame.grid_columnconfigure(col, weight=1, uniform="reminder_calendar")

    def redraw():
        for child in calendar_frame.winfo_children():
            child.destroy()
        month_label.configure(text=f"{calendar.month_name[window._view_month]} {window._view_year}")
        for col, weekday in enumerate(("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")):
            tk.Label(calendar_frame, text=weekday, font=(FONT, 7),
                     bg=c["BG"], fg=c["MUTED"]).grid(row=0, column=col, pady=(0, 1))
        weeks = calendar.Calendar(firstweekday=0).monthdatescalendar(
            window._view_year, window._view_month)
        while len(weeks) < 6:
            last = weeks[-1][-1]
            weeks.append([last + timedelta(days=i) for i in range(1, 8)])
        for row, week in enumerate(weeks, start=1):
            for col, day in enumerate(week):
                active = day == window._selected_date
                belongs = day.month == window._view_month
                b = tk.Button(calendar_frame, text=f"{day.day}", cursor="hand2",
                              font=(FONT, 8, "bold" if active else "normal"),
                              relief="flat", bd=0, highlightthickness=0,
                              bg=c["ACCENT_DARK"] if active else c["BG"],
                              fg=c["WHITE"] if active else (
                                  c["SECONDARY"] if belongs else c["MUTED"]),
                              activebackground=c["CARD_HOVER"],
                              activeforeground=c["WHITE"], padx=0, pady=1,
                              command=lambda value=day: choose_date(value))
                b.grid(row=row, column=col, sticky="ew", padx=1, pady=1)

    def choose_date(day, *, from_preset=False):
        window._selected_date = day
        window._view_year, window._view_month = day.year, day.month
        if not from_preset and preset.get() != "Custom time":
            preset.set("Custom time")
            hours.configure(state="readonly")
            minutes.configure(state="readonly")
        redraw()

    def step_month(delta):
        year, month = window._view_year, window._view_month + delta
        if month < 1:
            year, month = year - 1, 12
        elif month > 12:
            year, month = year + 1, 1
        window._view_year, window._view_month = year, month
        redraw()

    clock = tk.Frame(window, bg=c["BG"])
    clock.pack(pady=(10, 2))
    label(clock, "Time (24h)", fg=c["SECONDARY"], size=9).pack(
        side="left", padx=(0, 12))
    hours = ttk.Combobox(clock, textvariable=hour, state="readonly",
                         style="Reminder.TCombobox", font=(FONT, 9),
                         width=3, values=[f"{i:02}" for i in range(24)])
    hours.pack(side="left")
    tk.Label(clock, text=":", font=(FONT, 12, "bold"), fg=c["WHITE"],
             bg=c["BG"]).pack(side="left", padx=3)
    minutes = ttk.Combobox(clock, textvariable=minute, state="readonly",
                           style="Reminder.TCombobox", font=(FONT, 9),
                           width=3, values=[f"{i:02}" for i in range(60)])
    minutes.pack(side="left")
    window._hour_picker = hours
    window._minute_picker = minutes
    window._choose_date = choose_date

    def on_preset(_event=None):
        choice = preset.get()
        if choice == "Custom time":
            hours.configure(state="readonly")
            minutes.configure(state="readonly")
            return
        now_local = datetime.now().astimezone()
        if choice == "+15 minutes":
            target = now_local + timedelta(minutes=15)
        elif choice == "+1 hour":
            target = now_local + timedelta(hours=1)
        elif choice == "Tomorrow 09:00":
            target = (now_local + timedelta(days=1)).replace(
                hour=9, minute=0, second=0, microsecond=0)
        else:
            preset.set("Custom time")
            return
        choose_date(target.date(), from_preset=True)
        hour.set(target.strftime("%H"))
        minute.set(target.strftime("%M"))
        # Preset owns the time. Manual hour/minute selectors are visibly grey.
        hours.configure(state="disabled")
        minutes.configure(state="disabled")

    preset_picker.bind("<<ComboboxSelected>>", on_preset)
    window._apply_preset = on_preset
    redraw()

    label(window, "Local computer time · Pocket must be running.",
          fg=c["MUTED"], size=8).pack(pady=(5, 1))
    tk.Label(window, textvariable=status, bg=c["BG"], fg=c["DANGER"],
             font=(FONT, 8), wraplength=330).pack(pady=(0, 1))
    footer = tk.Frame(window, bg=c["BG"])
    footer.pack(fill="x", side="bottom", padx=16, pady=(8, 13))

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

    button(footer, "Cancel", close).pack(side="right")
    button(footer, "Save reminder", save).pack(side="right", padx=(0, 8))
    window._save_reminder = save
    window.protocol("WM_DELETE_WINDOW", close)
    window.bind("<Escape>", lambda _event: close())
    window.focus_force()
    window.grab_set()
    return window


def open_due_dialog(root, note, on_done, on_snooze, on_close, theme="blue"):
    """Pocket-themed reminder; input is disabled until Add response is checked."""
    window = _dialog(root, "Pocket · Note reminder", 438, 326, theme=theme)
    c = window._reminder_colors
    BG, FG, MUTED = c["BG"], c["WHITE"], c["MUTED"]
    title = (note.get("title") or "Note").strip() or "Note"
    heading = tk.Frame(window, bg=BG)
    heading.pack(fill="x", padx=20, pady=(18, 8))
    tk.Label(heading, text="Reminder", font=(FONT, 14, "bold"),
             fg=FG, bg=BG).pack(anchor="w")
    tk.Label(heading, text=title[:72], font=(FONT, 10),
             fg=FG, bg=BG, wraplength=396, justify="left").pack(
                 anchor="w", pady=(6, 0))

    add_response = tk.BooleanVar(window, note.get("reminder_add_response") is True)
    standalone = note.get("kind") == "standalone"
    caption = ("Save a response with this reminder"
               if standalone else "Add response to the bottom of this note")
    checked = ttk.Checkbutton(window, text=caption,
                              variable=add_response, style="Reminder.TCheckbutton")
    checked.pack(anchor="w", padx=20, pady=(5, 6))
    input_text = tk.Text(window, height=4, width=48, wrap="word",
                         font=(FONT, 10), relief="flat", bd=0, undo=True,
                         bg=c["INPUT"], fg=c["WHITE"],
                         insertbackground=c["ACCENT"], selectbackground=c["ACCENT_DARK"],
                         highlightthickness=1, highlightbackground=c["BORDER"],
                         highlightcolor=c["ACCENT"])
    input_text.pack(fill="x", padx=20)
    draft = note.get("reminder_draft", "")
    if draft and add_response.get():
        input_text.insert("1.0", draft[:4000])

    def sync_input(*_args):
        input_text.configure(state="normal" if add_response.get() else "disabled",
                             bg=c["INPUT"] if add_response.get() else c["CARD"])
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
                          style="Reminder.TCombobox",
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
    window.grab_set()  # Modal to Pocket, but does not block other Windows apps.
    return window


def open_standalone_form(root, reminder, on_save, on_close, theme="blue"):
    """Create/edit a local reminder with title, details and a scheduled time.

    The calendar is shared with Notes, but the record is independent.
    """
    c = themes.palette(theme)
    window = _dialog(root, "Pocket · Reminder", 420, 404, theme=theme)
    bg, white, muted = c["BG"], c["WHITE"], c["MUTED"]
    tk.Label(window, text="New reminder" if reminder is None else "Edit reminder",
             font=(FONT, 15, "bold"), bg=bg, fg=white).pack(
                 anchor="w", padx=20, pady=(16, 4))
    tk.Label(window, text="Saved locally. No Note will be created.",
             font=(FONT, 9), bg=bg, fg=muted).pack(
                 anchor="w", padx=20, pady=(0, 12))

    def field_label(text):
        tk.Label(window, text=text, font=(FONT, 9, "bold"), bg=bg,
                 fg=c["SECONDARY"]).pack(anchor="w", padx=20, pady=(2, 4))

    field_label("Title")
    title = tk.Entry(window, font=(FONT, 11), relief="flat", bd=0,
                     highlightthickness=1, highlightbackground=c["BORDER"],
                     highlightcolor=c["ACCENT"], bg=c["INPUT"],
                     fg=white, insertbackground=white)
    title.pack(fill="x", padx=20, ipady=7)
    if reminder:
        title.insert(0, reminder.get("title", ""))
    field_label("Details  ·  Optional")
    details = tk.Text(window, height=4, wrap="word", font=(FONT, 9),
                      bg=c["INPUT"], fg=white, insertbackground=white,
                      highlightthickness=1, highlightbackground=c["BORDER"],
                      highlightcolor=c["ACCENT"], bd=0, padx=7, pady=7)
    details.pack(fill="x", padx=20)
    if reminder:
        details.insert("1.0", reminder.get("details", ""))

    selected_time = [reminder.get("reminder_at", "") if reminder else ""]
    when_text = tk.StringVar(
        window, notes.format_reminder(reminder) if reminder else "Choose date and time")
    time_row = tk.Frame(window, bg=bg)
    time_row.pack(fill="x", padx=20, pady=(12, 7))
    when = tk.Label(time_row, textvariable=when_text, font=(FONT, 9),
                    bg=bg, fg=c["SECONDARY"])
    when.pack(side="left", fill="x", expand=True, anchor="w")
    window._time_label = when_text
    message = tk.StringVar(window, "")
    tk.Label(window, textvariable=message, bg=bg, fg=c["DANGER"],
             font=(FONT, 8), wraplength=375).pack(anchor="w", padx=20)

    calendar_window = [None]
    def pick_time():
        other = calendar_window[0]
        if other is not None and other.winfo_exists():
            other.lift()
            return
        try:
            window.grab_release()
        except tk.TclError:
            pass

        def choose(value):
            selected_time[0] = value
            try:
                dt = datetime.fromisoformat(value).astimezone()
                when_text.set(dt.strftime("%d %b %Y · %H:%M"))
            except (TypeError, ValueError):
                when_text.set("Time selected")
            message.set("")

        def calendar_closed():
            calendar_window[0] = None
            if window.winfo_exists():
                window.lift()
                window.grab_set()

        calendar_window[0] = open_datetime_editor(
            root, reminder or {"title": title.get() or "Reminder",
                               "reminder_at": selected_time[0]},
            choose, calendar_closed, theme=theme)

    pick = tk.Button(time_row, text="Date & time", command=pick_time,
                     font=(FONT, 9, "bold"), bg=c["CARD"], fg=white,
                     activebackground=c["CARD_HOVER"],
                     activeforeground=white, relief="flat", bd=0,
                     padx=10, pady=6, cursor="hand2")
    pick.pack(side="right")

    footer = tk.Frame(window, bg=bg)
    footer.pack(fill="x", side="bottom", padx=20, pady=13)
    closed = False

    def close():
        nonlocal closed
        if closed:
            return
        closed = True
        window.destroy()
        on_close()

    def submit():
        value = title.get().strip()
        content = details.get("1.0", "end-1c")
        if not value:
            message.set("Enter a title.")
            title.focus_set()
            return
        if not selected_time[0]:
            message.set("Choose a date and time.")
            return
        try:
            on_save(value, content, selected_time[0])
        except Exception as exc:
            message.set(str(exc))
            return
        close()

    tk.Button(footer, text="Cancel", command=close, font=(FONT, 9),
              bg=c["CARD"], fg=white, relief="flat", bd=0,
              padx=13, pady=7).pack(side="right")
    tk.Button(footer, text="Save reminder", command=submit,
              font=(FONT, 9, "bold"), bg=c["ACCENT_DARK"], fg=white,
              relief="flat", bd=0, padx=13, pady=7).pack(side="right", padx=(0, 8))
    window.protocol("WM_DELETE_WINDOW", close)
    window.bind("<Escape>", lambda _event: close())
    window._title_entry = title
    window._details_text = details
    window._choose_time = pick_time
    window._selected_time = selected_time
    window._submit_reminder = submit
    window.grab_set()
    title.focus_set()
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
            top_actions = tk.Frame(buttons, bg=c["PANEL"])
            top_actions.pack(fill="x")
            ttk.Button(top_actions, text="Open", command=open_note).pack(side="left")
            ttk.Button(top_actions, text="Edit time",
                       command=lambda note_id=note["id"]: app._edit_note_reminder(note_id)
                       ).pack(side="right")
            if notes.reminder_status(note) != "Completed":
                # A second short row prevents button overflow inside 346px Mini.
                bottom_actions = tk.Frame(buttons, bg=c["PANEL"])
                bottom_actions.pack(fill="x", pady=(5, 0))
                ttk.Button(bottom_actions, text="Snooze 15m",
                           command=lambda note_id=note["id"]: app._manage_note_reminder(
                               note_id, "snooze")).pack(side="left")
                ttk.Button(bottom_actions, text="Done",
                           command=lambda note_id=note["id"]: app._manage_note_reminder(
                               note_id, "done")).pack(side="right")
    choice.bind("<<ComboboxSelected>>", render)
    render()
    parent._reminders_filter = status_filter
