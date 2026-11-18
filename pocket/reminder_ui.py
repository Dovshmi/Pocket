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


def build_overview(app, parent, *, colors):
    """Polished, narrow-friendly hub for Note-linked and independent reminders."""
    c = colors
    bg, panel, white = c["BG"], c["PANEL"], c["WHITE"]

    def text(parent_widget, caption, *, size=9, bold=False, fg=None, bg_color=None,
             **kwargs):
        return tk.Label(parent_widget, text=caption,
                        bg=bg_color or bg, fg=fg or white,
                        font=(FONT, size, "bold" if bold else "normal"), **kwargs)

    def action(parent_widget, caption, callback, *, primary=False, danger=False, size=8):
        color = c["ACCENT_DARK"] if primary else c["CARD"]
        fore = c["WHITE"] if primary else (c["DANGER"] if danger else c["SECONDARY"])
        return tk.Button(parent_widget, text=caption, command=callback,
                         bg=color, fg=fore, activebackground=c["CARD_HOVER"],
                         activeforeground=white, relief="flat", bd=0,
                         padx=7, pady=5, font=(FONT, size, "bold"),
                         cursor="hand2", takefocus=True,
                         highlightthickness=1, highlightbackground=c["BORDER"])

    # Header: one obvious, first-class "New reminder" action.
    header = tk.Frame(parent, bg=bg)
    header.pack(fill="x", pady=(0, 4))
    action(header, "+ New", app._edit_standalone_reminder, primary=True,
           size=9).pack(side="right")
    text(header, "Reminders", size=17, bold=True).pack(side="left")
    text(parent, "Scheduled tasks & reminders, all in one place.",
         size=8, fg=c["MUTED"], anchor="w", justify="left",
         wraplength=285).pack(fill="x", pady=(0, 12))

    linked = [("note", item) for item in app.data["notes"]
              if notes.reminder_status(item)]
    independent = [("standalone", item) for item in app.data.get("reminders", [])
                   if notes.reminder_status(item)]
    items = linked + independent
    statuses = ("Upcoming", "Snoozed", "Completed")
    counts = {status: sum(notes.reminder_status(item) == status for _kind, item in items)
              for status in statuses}

    # Tiny, single-line counters leave the vertical space for the actual list.
    summary = tk.Frame(parent, bg=bg)
    summary.pack(fill="x", pady=(0, 7))
    parent._reminders_summary = summary
    for idx, (status, caption) in enumerate(
            (("Upcoming", "Next"), ("Snoozed", "Snoozed"), ("Completed", "Done"))):
        card = tk.Frame(summary, bg=panel, highlightthickness=1,
                        highlightbackground=c["BORDER"])
        card.grid(row=0, column=idx, sticky="nsew", padx=(0, 4) if idx < 2 else 0)
        summary.grid_columnconfigure(idx, weight=1, uniform="reminders_summary")
        text(card, f"{counts[status]}  {caption}", size=8, bold=True,
             fg=c["SECONDARY"], bg_color=panel).pack(padx=6, pady=4)

    filter_state = getattr(app, "_reminders_status_filter", "All")
    if filter_state not in ("All", *statuses):
        filter_state = "All"
    search = tk.StringVar(parent, getattr(app, "_reminders_search", ""))
    selected = [filter_state]
    control = tk.Frame(parent, bg=bg)
    control.pack(fill="x", pady=(0, 8))
    tabs = tk.Frame(control, bg=bg)
    tabs.pack(fill="x")
    filter_buttons = {}
    results = tk.Frame(parent, bg=bg)

    def set_filter(value):
        selected[0] = value
        app._reminders_status_filter = value
        update_filters()
        render()

    for value, caption in (("All", "All"), ("Upcoming", "Next"),
                           ("Snoozed", "Snoozed"), ("Completed", "Done")):
        tabs.grid_columnconfigure(len(filter_buttons), weight=1, uniform="filter")
        button = action(tabs, caption, lambda target=value: set_filter(target))
        button.grid(row=0, column=len(filter_buttons), sticky="ew", padx=(0, 3))
        filter_buttons[value] = button

    def update_filters():
        for value, button in filter_buttons.items():
            active = value == selected[0]
            button.configure(bg=c["ACCENT_DARK"] if active else c["CARD"],
                             fg=white if active else c["SECONDARY"],
                             highlightbackground=c["ACCENT"] if active else c["BORDER"])
    update_filters()

    search_bar = tk.Frame(parent, bg=c["INPUT"], highlightthickness=1,
                          highlightbackground=c["BORDER"])
    search_bar.pack(fill="x", pady=(4, 11))
    text(search_bar, "⌕", size=12, fg=c["MUTED"],
         bg_color=c["INPUT"]).pack(side="left", padx=(9, 5))
    search_box = tk.Entry(search_bar, textvariable=search, font=(FONT, 9),
                          bg=c["INPUT"], fg=white, insertbackground=white,
                          relief="flat", bd=0, highlightthickness=0)
    search_box.pack(side="left", fill="x", expand=True, ipady=7)
    text(search_bar, "Search", size=8, fg=c["MUTED"],
         bg_color=c["INPUT"]).pack(side="right", padx=8)
    app._reminders_search_entry = search_box

    results_title = tk.Frame(parent, bg=bg)
    results_title.pack(fill="x", pady=(0, 7))
    result_count = text(results_title, "YOUR REMINDERS", size=8, bold=True,
                        fg=c["SECONDARY"])
    result_count.pack(side="left")
    results.pack(fill="x")

    def render(*_args):
        app._reminders_search = search.get()
        for child in results.winfo_children():
            child.destroy()
        app._reminders_inline_fields = {}
        needle = search.get().strip().casefold()
        filtered = []
        for source, item in items:
            status = notes.reminder_status(item)
            if selected[0] != "All" and status != selected[0]:
                continue
            haystack = f"{item.get('title', '')} {item.get('details','') if source == 'standalone' else ''}"
            if needle and needle not in haystack.casefold():
                continue
            filtered.append((source, item))
        focus_new = getattr(app, "_reminders_focus_new", None)
        filtered.sort(key=lambda pair: (
            pair[1]["id"] != focus_new if focus_new else True,
            notes.reminder_status(pair[1]) == "Completed",
            pair[1].get("reminder_at", "")))
        result_count.configure(text=f"YOUR REMINDERS   ·   {len(filtered)}")

        if not filtered:
            empty = tk.Frame(results, bg=panel, highlightthickness=1,
                             highlightbackground=c["BORDER"])
            empty.pack(fill="x", pady=(4, 6))
            text(empty, "Nothing here yet", bg_color=panel,
                 size=11, bold=True).pack(pady=(16, 3))
            text(empty, "Create a reminder or choose another filter.",
                 bg_color=panel, fg=c["MUTED"], wraplength=260,
                 size=8).pack(pady=(0, 13))
            return

        for source, reminder in filtered:
            status = notes.reminder_status(reminder)
            uid = reminder["id"]
            card = tk.Frame(results, bg=panel, highlightthickness=1,
                            highlightbackground=c["BORDER"])
            card.pack(fill="x", pady=(0, 8))
            stripe = tk.Frame(card, bg=(c["ACCENT"] if status == "Upcoming"
                                        else c["MUTED"] if status == "Snoozed"
                                        else c["BORDER"]), width=3)
            stripe.pack(side="left", fill="y")
            stripe.pack_propagate(False)
            content = tk.Frame(card, bg=panel)
            content.pack(side="left", fill="both", expand=True, padx=10, pady=(9, 8))

            badges = tk.Frame(content, bg=panel)
            badges.pack(fill="x", pady=(0, 5))
            source_text = "▤ Note" if source == "note" else "◉ Reminder"
            text(badges, source_text, fg=c["ACCENT"], bg_color=panel,
                 size=8, bold=True).pack(side="left")
            text(badges, status.upper() if status else "", size=7, bg_color=panel,
                 fg=c["MUTED"]).pack(side="right")

            if source == "standalone":
                # Inline editing: no secondary form or title/details popup.
                title_var = tk.StringVar(content, reminder["title"])
                title_field = tk.Entry(
                    content, textvariable=title_var, font=(FONT, 10, "bold"),
                    bg=c["INPUT"], fg=white, insertbackground=white,
                    selectbackground=c["ACCENT_DARK"], relief="flat", bd=0,
                    highlightthickness=1, highlightbackground=c["BORDER"],
                    highlightcolor=c["ACCENT"])
                title_field.pack(fill="x", ipady=5, pady=(0, 5))
                text(content, "Note  ·  Optional", bg_color=panel, size=8,
                     fg=c["SECONDARY"], anchor="w").pack(fill="x", pady=(0, 3))
                note_field = tk.Text(
                    content, height=2, wrap="word", font=(FONT, 9),
                    bg=c["INPUT"], fg=white, insertbackground=white,
                    selectbackground=c["ACCENT_DARK"], relief="flat", bd=0,
                    highlightthickness=1, highlightbackground=c["BORDER"],
                    highlightcolor=c["ACCENT"], padx=5, pady=4)
                note_field.pack(fill="x", pady=(0, 5))
                note_field.insert("1.0", reminder.get("details", ""))
                note_field.edit_modified(False)
                error = tk.StringVar(content, "")
                error_label = tk.Label(content, textvariable=error, font=(FONT, 8),
                                       bg=panel, fg=c["DANGER"], anchor="w")
                error_label.pack(fill="x")
                app._reminders_inline_fields[uid] = (title_field, note_field)

                def title_changed(*_unused, ident=uid, var=title_var, notice=error):
                    try:
                        if var.get().strip():
                            app._save_standalone_inline(ident, title=var.get())
                            notice.set("")
                    except ValueError as exc:
                        notice.set(str(exc))

                title_var.trace_add("write", title_changed)

                def title_finished(_event=None, ident=uid, var=title_var):
                    current_item = next((r for r in app.data.get("reminders", [])
                                         if r["id"] == ident), None)
                    if current_item is not None and not var.get().strip():
                        var.set(current_item["title"])

                title_field.bind("<FocusOut>", title_finished)
                title_field.bind("<Return>", lambda _event, field=title_field:
                                 (field.tk_focusNext().focus_set(), "break")[-1])

                def note_changed(_event=None, ident=uid, widget=note_field,
                                 notice=error):
                    if not widget.winfo_exists() or not widget.edit_modified():
                        return
                    widget.edit_modified(False)
                    try:
                        app._save_standalone_inline(
                            ident, details=widget.get("1.0", "end-1c"))
                        notice.set("")
                    except ValueError as exc:
                        notice.set(str(exc))

                note_field.bind("<<Modified>>", note_changed)

                if focus_new == uid:
                    app._reminders_focus_new = None
                    def focus_title(widget=title_field):
                        if widget.winfo_exists():
                            widget.focus_set()
                            widget.selection_range(0, "end")
                    title_field.after_idle(focus_title)
            else:
                text(content, (reminder.get("title") or "Untitled note")[:90],
                     bg_color=panel, size=10, bold=True, anchor="w",
                     wraplength=258, justify="left").pack(fill="x", pady=(0, 3))
                body = reminder.get("body", "")
                if isinstance(body, str) and body.strip():
                    snippet = " ".join(body.split())
                    if len(snippet) > 110:
                        snippet = snippet[:107] + "…"
                    text(content, snippet, fg=c["MUTED"], bg_color=panel, size=8,
                         anchor="w", justify="left", wraplength=258
                         ).pack(fill="x", pady=(0, 5))

            text(content, "◷  " + notes.format_reminder(reminder).replace(" · sent", ""),
                 fg=c["SECONDARY"], bg_color=panel, size=8, anchor="w").pack(
                     fill="x", pady=(0, 4))

            if source == "standalone" and reminder.get("responses"):
                latest = reminder["responses"][-1]
                text(content, "Reply · " + latest["time"], fg=c["ACCENT"],
                     bg_color=panel, size=8, anchor="w").pack(fill="x")
                last = " ".join(latest["text"].split())
                text(content, last[:105] + ("…" if len(last) > 105 else ""),
                     fg=c["SECONDARY"], bg_color=panel, size=8,
                     anchor="w", wraplength=258, justify="left").pack(
                         fill="x", pady=(0, 5))

            buttons = tk.Frame(content, bg=panel)
            buttons.pack(fill="x", pady=(5, 0))
            primary_row = tk.Frame(buttons, bg=panel)
            primary_row.pack(fill="x")
            if source == "note":
                def open_note(note_id=uid):
                    app.data["active_note"] = note_id
                    app.show_tab("notes")
                action(primary_row, "Open note", open_note).pack(side="left")
                edit_time = lambda ident=uid: app._edit_note_reminder(ident)
            else:
                edit_time = lambda ident=uid: app._edit_standalone_reminder(ident)
            action(primary_row, "Change time", edit_time).pack(side="right")
            if status != "Completed":
                secondary = tk.Frame(buttons, bg=panel)
                secondary.pack(fill="x", pady=(5, 0))
                action(secondary, "Snooze 15m",
                       lambda ident=uid, src=source:
                           app._manage_note_reminder(ident, "snooze", source=src)
                       ).pack(side="left")
                action(secondary, "Done",
                       lambda ident=uid, src=source:
                           app._manage_note_reminder(ident, "done", source=src),
                       primary=True).pack(side="right")
            elif source == "standalone":
                action(buttons, "Delete",
                       lambda ident=uid: app._delete_standalone_reminder(ident),
                       danger=True).pack(anchor="e", pady=(5, 0))

    search.trace_add("write", render)
    render()
    parent._reminders_filter = selected

