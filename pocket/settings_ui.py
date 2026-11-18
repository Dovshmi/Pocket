"""One contemporary, responsive Settings experience for Pocket.

The screen is presentation-only: all actions call the existing PocketDesk
callbacks. Normal and Mini use a readable single-column arrangement;
Dashboard uses independent two-column stacks. No new data or network I/O.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from . import icon_themes as themes
from . import app_info
from . import quick_slots

FONT = "Segoe UI"

# Retained for settings/data regression checks and menu parity.
LAYOUTS = (
    ("normal", "▣", "Normal", "Everyday popup"),
    ("mini", "▫", "Mini", "Compact workspace"),
    ("dashboard", "▦", "Dashboard", "Expanded workspace"),
)
TOOL_HELP = {
    "notes": "Notes, phone numbers and reminders",
    "links": "Websites, files and folders",
    "ports": "On-demand TCP checks",
    "mac": "Local IEEE vendor lookup",
    "commands": "CLI library and manual backups",
    "subnet": "IPv4 subnet calculator",
    "clipboard": "RAM or optional local clipboard history",
}
TOOL_ICONS = {
    "notes": "✎", "links": "↗", "ports": "⇄", "mac": "▦",
    "commands": ">_", "subnet": "⌗", "clipboard": "▤",
}


def _label(parent, text, c, *, size=9, bold=False, muted=False,
           background=None, **kwargs):
    return tk.Label(
        parent, text=text, bg=background or c["PANEL"],
        fg=c["MUTED"] if muted else c["WHITE"],
        font=(FONT, size, "bold" if bold else "normal"), **kwargs)


def _button(parent, caption, callback, c, *, primary=False, compact=False):
    return tk.Button(
        parent, text=caption, command=callback,
        bg=c["ACCENT_DARK"] if primary else c["CARD"],
        fg=c["WHITE"] if primary else c["SECONDARY"],
        activebackground=c["CARD_HOVER"], activeforeground=c["WHITE"],
        highlightthickness=1,
        highlightbackground=c["ACCENT"] if primary else c["BORDER"],
        highlightcolor=c["ACCENT"], relief="flat", bd=0,
        cursor="hand2", takefocus=True, font=(FONT, 9, "bold"),
        padx=8 if compact else 12, pady=7)


def _section(parent, c, heading, description, *, compact=False, wide=False):
    """Consistent bordered surface, accent cap and predictable spacing."""
    card = tk.Frame(
        parent, bg=c["PANEL"], bd=0,
        highlightthickness=1, highlightbackground=c["BORDER"])
    card.pack(fill="x", pady=(0, 12))
    tk.Frame(card, bg=c["ACCENT"], height=2).pack(fill="x")
    head = tk.Frame(card, bg=c["PANEL"])
    head.pack(fill="x", padx=13, pady=(12, 9))
    _label(head, heading, c, size=11 if compact else 12, bold=True,
           anchor="w").pack(fill="x")
    _label(head, description, c, size=8, muted=True,
           wraplength=230 if compact else (350 if wide else 365),
           anchor="w", justify="left").pack(fill="x", pady=(4, 0))
    return card


def _divider(parent, c):
    tk.Frame(parent, bg=c["BORDER"], height=1).pack(fill="x", padx=13)


def _register(app, name, widget):
    app.settings_controls[name] = widget
    return widget


def _toggle(parent, app, c, key, title, description, checked, callback,
            *, compact=False):
    """Focusable switch-style Checkbutton retaining .invoke() semantics.

    Use Tk Checkbutton rather than an inert canvas: it supports click, Space,
    keyboard focus and existing GUI regression tests.
    """
    line = tk.Frame(parent, bg=c["PANEL"])
    line.pack(fill="x", padx=13, pady=9)
    state = tk.BooleanVar(master=line, value=bool(checked))
    control = tk.Checkbutton(
        line, variable=state, indicatoron=False,
        bg=c["CARD"], fg=c["SECONDARY"],
        activebackground=c["CARD_HOVER"], activeforeground=c["WHITE"],
        selectcolor=c["ACCENT_DARK"], bd=0,
        relief="flat", offrelief="flat",
        highlightthickness=1, highlightbackground=c["BORDER"],
        highlightcolor=c["ACCENT"], cursor="hand2", takefocus=True,
        font=(FONT, 8, "bold"), width=7, pady=6, padx=5)

    def sync():
        active = bool(state.get())
        control.configure(
            text="●  ON" if active else "OFF  ○",
            bg=c["ACCENT_DARK"] if active else c["CARD"],
            fg=c["WHITE"] if active else c["SECONDARY"],
            highlightbackground=c["ACCENT"] if active else c["BORDER"])

    def apply():
        sync()
        callback(bool(state.get()))

    control.configure(command=apply)
    control.pack(side="right", padx=(8, 0))
    info = tk.Frame(line, bg=c["PANEL"])
    info.pack(side="left", fill="x", expand=True)
    title_label = _label(
        info, title, c, size=9, bold=True, anchor="w",
        wraplength=145 if compact else 320, justify="left")
    title_label.pack(fill="x")
    detail_label = _label(
        info, description, c, size=8, muted=True,
        wraplength=145 if compact else 320, anchor="w", justify="left")
    detail_label.pack(fill="x", pady=(3, 0))
    # Allow the entire descriptive area to toggle as well as the switch.
    for widget in (info, title_label, detail_label):
        widget.bind("<Button-1>", lambda _event: control.invoke())
        widget.configure(cursor="hand2")
    sync()
    return _register(app, key, control)


def _action(parent, app, c, key, title, detail, caption, callback,
            *, compact=False, primary=False):
    line = tk.Frame(parent, bg=c["PANEL"])
    line.pack(fill="x", padx=13, pady=(7, 11))
    button = _button(line, caption, callback, c, compact=compact,
                     primary=primary)
    button.pack(side="right", padx=(7, 0))
    info = tk.Frame(line, bg=c["PANEL"])
    info.pack(side="left", fill="x", expand=True)
    _label(info, title, c, size=9, bold=True, anchor="w",
           justify="left", wraplength=140 if compact else 310).pack(fill="x")
    _label(info, detail, c, muted=True, size=8,
           justify="left", anchor="w",
           wraplength=140 if compact else 310).pack(fill="x", pady=(4, 0))
    return _register(app, key, button)


def _mode_picker(parent, app, c, *, wide=False, compact=False):
    group = tk.Frame(parent, bg=c["PANEL"])
    group.pack(fill="x", padx=13, pady=(1, 12))
    for i, (mode, icon, title, detail) in enumerate(LAYOUTS):
        selected = app.settings["display_mode"] == mode
        surface = c["ACCENT_DARK"] if selected else c["CARD"]
        outline = c["ACCENT"] if selected else c["BORDER"]
        holder = tk.Frame(
            group, bg=surface, highlightthickness=1,
            highlightbackground=outline)
        if wide:
            group.grid_columnconfigure(i, weight=1, uniform="layout")
            holder.grid(row=0, column=i, sticky="nsew",
                        padx=(0, 5) if i < 2 else 0)
        else:
            holder.pack(fill="x", pady=(0, 5))
        caption = (icon + "  " + title +
                   ("   ● ACTIVE" if selected else "") + "\n" + detail)
        button = tk.Button(
            holder, text=caption, command=lambda name=mode: app._set_display_mode(name),
            bg=surface, fg=c["WHITE"] if selected else c["SECONDARY"],
            activebackground=c["CARD_HOVER"], activeforeground=c["WHITE"],
            font=(FONT, 9, "bold" if selected else "normal"),
            anchor="w", justify="left", cursor="hand2",
            relief="flat", bd=0, highlightthickness=0,
            padx=9, pady=9 if not compact else 7, takefocus=True)
        button.pack(fill="both", expand=True)
        _register(app, "mode_" + mode, button)


def _theme_picker(parent, app, c, *, wide=False, compact=False):
    header = tk.Frame(parent, bg=c["PANEL"])
    header.pack(fill="x", padx=13, pady=(1, 8))
    _label(header, "COLOR PALETTE", c, size=8, bold=True, muted=True,
           anchor="w").pack(side="left")
    _label(header, "Choose a theme", c, size=8, muted=True
           ).pack(side="right")
    swatches = tk.Frame(parent, bg=c["PANEL"])
    swatches.pack(fill="x", padx=13, pady=(0, 12))
    columns = 3 if wide else 2
    for index, name in enumerate(themes.THEME_ORDER):
        col, row = index % columns, index // columns
        swatches.grid_columnconfigure(col, weight=1, uniform="colors")
        active = app.theme == name
        surface = c["ACCENT_DARK"] if active else c["CARD"]
        tile = tk.Frame(
            swatches, bg=surface, highlightthickness=1,
            highlightbackground=c["ACCENT"] if active else c["BORDER"])
        tile.grid(row=row, column=col, sticky="nsew",
                  padx=(0, 5) if col < columns - 1 else 0, pady=(0, 5))
        indicator = tk.Frame(
            tile, bg=themes.THEMES[name]["accent"],
            width=6 if compact else 8)
        indicator.pack(side="left", fill="y")
        indicator.pack_propagate(False)
        button = tk.Button(
            tile, text=themes.THEMES[name]["name"] + ("  ✓" if active else ""),
            command=lambda chosen=name: app._choose_theme(chosen),
            bg=surface, fg=c["WHITE"] if active else c["SECONDARY"],
            activebackground=c["CARD_HOVER"], activeforeground=c["WHITE"],
            font=(FONT, 8, "bold" if active else "normal"),
            padx=6, pady=7, bd=0, relief="flat",
            cursor="hand2", anchor="w", takefocus=True)
        button.pack(side="left", fill="both", expand=True)
        _register(app, "theme_" + name, button)


def _appearance(parent, app, c, *, wide=False, compact=False):
    card = _section(parent, c, "Appearance & layout",
                    "Switch windows and choose a theme that fits your workspace.",
                    compact=compact, wide=wide)
    _mode_picker(card, app, c, wide=wide, compact=compact)
    _divider(card, c)
    _theme_picker(card, app, c, wide=wide, compact=compact)


def _launcher(parent, app, c, *, compact=False, wide=False):
    card = _section(parent, c, "Extra Mini launcher",
                    "An optional quick launcher with your favourite actions.",
                    compact=compact, wide=wide)
    _toggle(card, app, c, "extra_mini", "Enable Extra Mini",
            "Keep your quick launcher one click away.",
            app.settings["extra_mini_enabled"], app._set_extra_mini_enabled,
            compact=compact)
    _divider(card, c)
    _action(card, app, c, "customize_launcher", "Quick actions",
            "Reorder shortcuts and organize launcher pages.",
            "Customize", app._edit_extra_mini_from_settings,
            compact=compact, primary=True)


def _tools(parent, app, c, *, compact=False, wide=False):
    card = _section(parent, c, "Visible tools",
                    "Choose what appears in Pocket. At least one tool stays on.",
                    compact=compact, wide=wide)
    for index, (key, caption) in enumerate(app.VISIBLE_TABS_REFERENCE):
        if index:
            _divider(card, c)
        _toggle(card, app, c, "tool_" + key,
                TOOL_ICONS[key] + "  " + caption.title(),
                TOOL_HELP[key], key in app.settings["visible_tabs"],
                lambda active, tool=key: app._set_visible_tab(tool, active),
                compact=compact)



def _dropdown_field(parent, app, c, key, heading, detail,
                    choices, selected, callback, *, compact=False,
                    wheel_scroll_page=False):
    """Native themed readonly dropdown, uniform in Mini/Normal/Dashboard."""
    section = tk.Frame(parent, bg=c["PANEL"])
    section.pack(fill="x", padx=13, pady=(9, 11))
    _label(section, heading, c, size=9, bold=True, anchor="w").pack(fill="x")
    if detail:
        _label(section, detail, c, size=8, muted=True, anchor="w",
               justify="left", wraplength=190 if compact else 360).pack(
                   fill="x", pady=(3, 7))
    select = ttk.Combobox(section, style="Pocket.TCombobox",
                          values=[label for label, _ in choices],
                          state="readonly", width=23 if compact else 31,
                          takefocus=True)
    chosen = next((i for i, (_label, value) in enumerate(choices)
                   if value == selected), 0)
    select.current(chosen)
    select.pack(fill="x", padx=(0, 2), pady=(0, 3))

    def apply(_event=None):
        index = select.current()
        if 0 <= index < len(choices):
            callback(choices[index][1])
        return "break"

    select.bind("<<ComboboxSelected>>", apply)
    if wheel_scroll_page:
        # Match the protected history-size selectors: the wheel scrolls the
        # Settings canvas instead of changing a saved Combobox preference.
        def scroll_page(event):
            app._scroll_tool_on_wheel(event, from_picker=True)
            return "break"

        for event_name in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            select.bind(event_name, scroll_page)
    return _register(app, key, select)


def _convert_mode_picker(parent, app, c, *, compact=False):
    return _dropdown_field(
        parent, app, c, "convert_mode_picker", "Translate behavior",
        "Mark replaces selected text; Clipboard corrects copied text.",
        [("Mark — selected text", "mark"),
         ("Clipboard — copied text", "clipboard")],
        app.settings["convert_mode"], app._set_convert_mode,
        compact=compact, wheel_scroll_page=True)


def _network_preferences(parent, app, c, *, compact=False, wide=False):
    card = _section(parent, c, "Network connection",
                    "Choose how requested DashDash and IEEE HTTPS traffic connects.",
                    compact=compact, wide=wide)
    _toggle(card, app, c, "use_windows_proxy", "Use Windows Proxy",
            "ON: Windows PAC. OFF: direct HTTPS; IEEE GET uses Windows TLS.",
            app.settings["use_windows_proxy"], app._set_windows_proxy,
            compact=compact)
    _divider(card, c)
    _label(card,
           "Default ON for workplace networks. Local checks stay offline. "
           "Changes affect the next request, not an in-progress check.",
           c, size=8, muted=True, justify="left", anchor="w",
           wraplength=200 if compact else 350).pack(
               fill="x", padx=13, pady=(10, 13))


def _shortcuts(parent, app, c, *, compact=False, wide=False):
    card = _section(parent, c, "Keyboard & quick search",
                    "Stay productive without opening another window.",
                    compact=compact, wide=wide)
    _action(card, app, c, "change_hotkey",
            "Pocket shortcut", app._hotkey_hint(),
            "Edit", app._open_hotkey_picker, compact=compact)
    _divider(card, c)
    _action(card, app, c, "quick_search",
            "Quick Search", "Ctrl+K · Search all enabled tools locally.",
            "Open", app._open_global_search, compact=compact, primary=True)


def _clipboard_history_controls(parent, app, c, *, compact=False):
    """Four independent history settings in a space-efficient two-column grid.

    The mouse wheel is intentionally intercepted only for these selectors.
    Other Pocket Comboboxes retain their original mouse-wheel behavior.
    """
    section = tk.Frame(parent, bg=c["PANEL"])
    section.pack(fill="x", padx=13, pady=(7, 9))
    _label(section, "History capacity & cleanup", c, size=9,
           bold=True, anchor="w").pack(fill="x", pady=(0, 5))
    grid = tk.Frame(section, bg=c["PANEL"])
    grid.pack(fill="x")
    for col in (0, 1):
        grid.columnconfigure(col, weight=1, uniform="history")

    ram_counts = [(str(value), value) for value in (10, 15, 20, 25, 30)]
    db_images = [(str(value), value) for value in range(10, 101, 10)]
    db_text = [(str(value), value) for value in
               (100, 300, 500, 800, 1000, 1200, 1500)]
    retention = [("Off", 0)] + [
        (f"{day} days", day) for day in range(7, 31)]
    fields = (
        ("ram_image_limit", "RAM images", ram_counts,
         app.settings["clipboard_image_limit"], app._set_clipboard_image_limit),
        ("db_image_display_limit", "DB images shown", db_images,
         app.settings["clipboard_db_image_display_limit"],
         lambda count: app._set_clipboard_display_limit("images", count)),
        ("db_text_display_limit", "DB text shown", db_text,
         app.settings["clipboard_text_display_limit"],
         lambda count: app._set_clipboard_display_limit("text", count)),
        ("clipboard_retention", "Auto-delete", retention,
         app.settings["clipboard_autodelete_days"],
         app._set_clipboard_autodelete_days),
    )
    for index, (key, title, options, value, callback) in enumerate(fields):
        cell = tk.Frame(grid, bg=c["PANEL"])
        cell.grid(row=index // 2, column=index % 2, sticky="ew",
                  padx=(0, 5) if index % 2 == 0 else (5, 0),
                  pady=(2, 6))
        _label(cell, title, c, size=8, anchor="w").pack(fill="x", pady=(0, 3))
        select = ttk.Combobox(
            cell, style="Pocket.TCombobox", state="readonly",
            values=[label for label, _ in options], width=9,
            takefocus=True)
        select.current(next((i for i, (_label, actual) in enumerate(options)
                             if actual == value), 0))
        select.pack(fill="x")

        def apply(_event=None, dropdown=select, choices=options, change=callback):
            current = dropdown.current()
            if 0 <= current < len(choices):
                change(choices[current][1])
            return "break"

        def scroll_page(event):
            # Delegate scrolling to the existing Settings canvas *before*
            # the Combobox class binding can silently change its value.
            # No other dropdown bindings or global widget styles change.
            app._scroll_tool_on_wheel(event, from_picker=True)
            return "break"

        select.bind("<<ComboboxSelected>>", apply)
        for event_name in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            select.bind(event_name, scroll_page)
        _register(app, key, select)

    _label(section, "RAM images: 10–30 · DB images: 10–100 · "
           "DB text: 100–1500 · Auto-delete: Off or 7–30 days.",
           c, muted=True, size=8, anchor="w", justify="left",
           wraplength=185 if compact else 330).pack(fill="x", pady=(1, 0))


def _privacy(parent, app, c, *, compact=False, wide=False):
    card = _section(parent, c, "Clipboard & privacy",
                    "Control local clipboard capture and sensitive data.",
                    compact=compact, wide=wide)
    _toggle(card, app, c, "clipboard_paused", "Pause clipboard capture",
            "Keep history available, but stop capturing new text.",
            app.settings["clipboard_paused"], app._set_clipboard_paused,
            compact=compact)
    _divider(card, c)
    _toggle(card, app, c, "sensitive_filter", "Skip recognized sensitive text",
            "Try to exclude passwords and tokens (not a guarantee).",
            app.settings["clipboard_sensitive_filter"],
            app._set_clipboard_sensitive_filter, compact=compact)
    _divider(card, c)
    _clipboard_history_controls(card, app, c, compact=compact)
    _divider(card, c)
    _toggle(card, app, c, "quick_slots_enabled", "Enable Quick Slots",
            "Paste or save text directly with separate Numpad1–9 shortcuts.",
            app.settings["quick_slots_enabled"], app._set_quick_slots_enabled,
            compact=compact)
    _dropdown_field(
        card, app, c, "quick_slots_save_mode_picker", "Quick Slot save behavior",
        "Auto Copy Selection sends Ctrl+C; Current Clipboard reads what you copied.",
        quick_slots.SAVE_MODE_CHOICES, app.settings["quick_slots_save_mode"],
        app._set_quick_slots_save_mode,
        compact=compact, wheel_scroll_page=True)
    _dropdown_field(
        card, app, c, "quick_slots_paste_mode_picker", "Quick Slot paste behavior",
        "Auto Paste inserts immediately; Copy to Clipboard lets you press Ctrl+V.",
        quick_slots.PASTE_MODE_CHOICES, app.settings["quick_slots_paste_mode"],
        app._set_quick_slots_paste_mode,
        compact=compact, wheel_scroll_page=True)
    _dropdown_field(
        card, app, c, "quick_slots_notification_mode_picker",
        "Quick Slot notifications",
        "Choose which shortcut actions show Windows notifications.",
        quick_slots.NOTIFICATION_CHOICES,
        app.settings["quick_slots_notification_mode"],
        app._set_quick_slots_notification_mode,
        compact=compact, wheel_scroll_page=True)
    _dropdown_field(
        card, app, c, "quick_slots_paste_prefix_picker", "Paste shortcut prefix",
        "Default Ctrl+Alt + Numpad1–9; only modifier keys can change.",
        quick_slots.PREFIX_CHOICES, app.settings["quick_slots_paste_prefix"],
        app._set_quick_slots_paste_prefix,
        compact=compact, wheel_scroll_page=True)
    _dropdown_field(
        card, app, c, "quick_slots_copy_prefix_picker", "Save / Copy shortcut prefix",
        "Default Ctrl+Alt+Win + Numpad1–9; only modifier keys can change.",
        quick_slots.PREFIX_CHOICES, app.settings["quick_slots_copy_prefix"],
        app._set_quick_slots_copy_prefix,
        compact=compact, wheel_scroll_page=True)
    _divider(card, c)
    _toggle(card, app, c, "convert_enabled", "Enable Translate shortcut",
            "Register the global EN / HE layout correction shortcut.",
            app.settings["convert_enabled"],
            app._set_convert_enabled, compact=compact)
    _action(card, app, c, "change_convert_hotkey",
            "Translate keyboard shortcut", app._convert_hotkey_hint(),
            "Edit", app._open_convert_hotkey_picker, compact=compact)
    _convert_mode_picker(card, app, c, compact=compact)
    _divider(card, c)
    _label(card, "RAM never saves history to disk. DATABASE writes text in daily "
           "TXT files and screenshots in one dated PNG folder. Auto-delete "
           "is OFF by default; enable 7–30-day cleanup if you choose. "
           "The sensitive-text filter is heuristic and does not guarantee privacy.",
           c, size=8, muted=True, justify="left", anchor="w",
           wraplength=210 if compact else 350
           ).pack(fill="x", padx=13, pady=(10, 13))


def _backup_controls(parent, app, c, *, compact=False, wide=False):
    card = _section(parent, c, "Backup & Restore",
                    "Portable, selective and offline. Quick Slots are never backed up.",
                    compact=compact, wide=wide)
    _action(card, app, c, "create_pocket_backup", "Create Backup",
            "Select Notes, Links, CLI, Settings or saved Clipboard history.",
            "Save ZIP", app._open_backup_dialog, compact=compact, primary=True)
    _divider(card, c)
    _action(card, app, c, "restore_pocket_backup", "Restore Backup",
            "Preview, merge or replace selected data on another computer.",
            "Open ZIP", app._open_restore_dialog, compact=compact)
    _divider(card, c)
    _label(card,
           "Backups are not encrypted. Review CLI commands and clipboard "
           "history before sharing a backup with anyone.",
           c, size=8, muted=True, anchor="w", justify="left",
           wraplength=200 if compact else 350).pack(
               fill="x", padx=13, pady=(2, 13))

    defaults = _section(parent, c, "Default Settings",
                        "Restore preferences only, without deleting personal data.",
                        compact=compact, wide=wide)
    _action(defaults, app, c, "reset_default_settings", "Reset preferences",
            "Choose appearance, menus, keyboard, clipboard or network.",
            "Reset…", app._open_reset_settings_dialog, compact=compact)


def build_settings(app, parent, *, wide=False):
    """Build all modes from a single settings design system."""
    c = themes.palette(app.theme)
    compact = app.display_mode == "mini"
    app.settings_controls = {}
    if wide:
        # Existing integration tests and consumers use this public mapping.
        app.dashboard_settings_controls = app.settings_controls

    intro = tk.Frame(parent, bg=c["BG"])
    intro.pack(fill="x", pady=(0, 14))
    eyebrow = _label(intro, "POCKET  /  PREFERENCES", c, size=8,
                     background=c["BG"], bold=True, anchor="w")
    eyebrow.configure(fg=c["ACCENT"])
    eyebrow.pack(fill="x", pady=(0, 4))
    _label(intro, "Settings", c, size=19 if not compact else 16,
           background=c["BG"], bold=True, anchor="w").pack(fill="x")
    _label(intro, "Saved automatically on this device · Changes apply immediately",
           c, size=8, muted=True, background=c["BG"], justify="left",
           anchor="w", wraplength=225 if compact else 690
           ).pack(fill="x", pady=(4, 0))

    if wide:
        columns = tk.Frame(parent, bg=c["BG"])
        columns.pack(fill="x")
        columns.grid_columnconfigure(0, weight=1, uniform="preferences")
        columns.grid_columnconfigure(1, weight=1, uniform="preferences")
        left = tk.Frame(columns, bg=c["BG"])
        right = tk.Frame(columns, bg=c["BG"])
        left.grid(row=0, column=0, sticky="new", padx=(0, 8))
        right.grid(row=0, column=1, sticky="new", padx=(8, 0))
    else:
        left = right = parent

    _appearance(left, app, c, wide=wide, compact=compact)
    _shortcuts(left, app, c, wide=wide, compact=compact)
    _launcher(left, app, c, wide=wide, compact=compact)
    _tools(right, app, c, wide=wide, compact=compact)
    _network_preferences(right, app, c, wide=wide, compact=compact)
    _privacy(right, app, c, wide=wide, compact=compact)
    _backup_controls(right, app, c, wide=wide, compact=compact)

    # The footer is the last element of the scrollable Settings body in all
    # three layouts. It is not a floating overlay and obscures no controls.
    footer = tk.Frame(parent, bg=c["BG"])
    footer.pack(fill="x", pady=(5, 8))
    tk.Frame(footer, height=1, bg=c["BORDER"]).pack(fill="x", pady=(0, 10))
    credits = tk.Frame(footer, bg=c["BG"])
    credits.pack(fill="x", padx=3)
    author = _label(credits, app_info.AUTHOR_CREDIT, c, size=8, muted=True,
                    background=c["BG"], anchor="w")
    author.pack(side="left")
    version = _label(credits, "Version " + app_info.version_label(), c,
                     size=8, muted=True, background=c["BG"], anchor="e")
    version.pack(side="right")
    app.settings_footer_author = author
    app.settings_footer_version = version
