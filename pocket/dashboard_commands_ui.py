"""Dashboard-only command workspace.

Use the wide Dashboard's available columns: a larger searchable command
table alongside an editable, copy-only detail panel. The Normal and Mini
builders and all shared command actions remain unchanged.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from . import command_helper as ch
from . import pocket_design as design

FONT = "Segoe UI"


def build(app):
    """Build the wide Dashboard Commands page using existing app callbacks."""
    c = design.colors(app.theme)
    bg, panel, accent = c["BG"], c["PANEL"], c["ACCENT"]
    muted, secondary, white = c["MUTED"], c["SECONDARY"], c["WHITE"]
    border, input_bg = c["BORDER"], c["INPUT"]
    body = app.body

    # Dashboard already has a persistent page title in the shell. Avoid a
    # second oversized hero heading; reserve vertical space for actual results.
    toolbar = tk.Frame(body, bg=bg)
    toolbar.pack(fill="x", pady=(0, 10))
    captions = tk.Frame(toolbar, bg=bg)
    captions.pack(side="left", fill="x", expand=True)
    tk.Label(captions, text="CLI WORKSPACE", bg=bg, fg=white,
             font=(FONT, 13, "bold"), anchor="w").pack(anchor="w")
    tk.Label(captions, text="Find references, adjust text, and copy safely",
             bg=bg, fg=muted, font=(FONT, 9), anchor="w").pack(anchor="w", pady=(2, 0))
    design.button(toolbar, "Backup", app._show_command_backup_menu, app.theme,
                  compact=True).pack(side="right", padx=(7, 0))
    design.button(toolbar, "+ New command", app._add_custom_command,
                  app.theme, primary=True, compact=True).pack(side="right")

    # The controls use horizontal space instead of accumulating five separate
    # rows as they do in Normal mode.
    filter_card = tk.Frame(body, bg=panel, highlightthickness=1,
                           highlightbackground=border)
    filter_card.pack(fill="x", pady=(0, 12))
    filter_row = tk.Frame(filter_card, bg=panel)
    filter_row.pack(fill="x", padx=12, pady=(10, 7))
    filter_row.columnconfigure(0, weight=6, uniform="cmd-filters")
    filter_row.columnconfigure(1, weight=3, uniform="cmd-filters")
    filter_row.columnconfigure(2, weight=3, uniform="cmd-filters")

    def heading(col, title):
        tk.Label(filter_row, text=title, bg=panel, fg=muted,
                 font=(FONT, 8, "bold"), anchor="w").grid(
                     row=0, column=col, sticky="ew", padx=(0, 10 if col < 2 else 0),
                     pady=(0, 5))

    for col, title in enumerate(("SEARCH COMMANDS", "DEVICE / VENDOR", "CATEGORY")):
        heading(col, title)

    app.command_query = tk.StringVar()
    app.command_search_entry = app._entry(filter_row, app.command_query)
    app.command_search_entry.configure(font=(FONT, 10), fg=muted)
    app._command_placeholder = "Search command, purpose, interface, IP..."
    app._command_placeholder_active = True
    app.command_search_entry.insert(0, app._command_placeholder)
    app.command_search_entry.bind("<FocusIn>", app._command_focus_in)
    app.command_search_entry.bind("<FocusOut>", app._command_focus_out)
    app.command_search_entry.grid(row=1, column=0, sticky="ew", ipady=8, padx=(0, 10))
    app.command_query.trace_add("write", lambda *_: app._refresh_command_results())

    prefs = app.data["command_state"]
    names = [ch.ALL_MACHINES] + ch.machines_for(app.command_library, app.machine_catalog)
    chosen = prefs.get("machine")
    app.machine_var = tk.StringVar(value=chosen if chosen in names else ch.ALL_MACHINES)
    app.machine_picker = ttk.Combobox(
        filter_row, style="Pocket.TCombobox", textvariable=app.machine_var,
        values=names, state="readonly", font=(FONT, 9), height=18)
    app.machine_picker.grid(row=1, column=1, sticky="ew", padx=(0, 10))
    app.machine_picker.bind("<<ComboboxSelected>>", app._change_machine)
    app._protect_command_picker(app.machine_picker)

    app.command_category_var = tk.StringVar(value=ch.ALL_CATEGORIES)
    app.command_category_picker = ttk.Combobox(
        filter_row, style="Pocket.TCombobox", textvariable=app.command_category_var,
        values=[ch.ALL_CATEGORIES] + ch.categories_for(app.command_library, app.machine_var.get()),
        state="readonly", font=(FONT, 9))
    app.command_category_picker.grid(row=1, column=2, sticky="ew")
    app.command_category_picker.bind("<<ComboboxSelected>>",
                                     lambda _event: app._refresh_command_results())
    app._protect_command_picker(app.command_category_picker)

    bottom_filter = tk.Frame(filter_card, bg=panel)
    bottom_filter.pack(fill="x", padx=12, pady=(0, 9))
    app.command_modes = {}
    for mode, label in (("all", "All commands"), ("favorites", "★ Favorites"),
                        ("recent", "Recent")):
        btn = design.button(bottom_filter, label, lambda key=mode: app._set_command_mode(key),
                            app.theme, compact=True)
        btn.pack(side="left", padx=(0, 5))
        app.command_modes[mode] = btn
    tk.Label(bottom_filter, text="Offline  ·  Commands are never executed",
             bg=panel, fg=muted, font=(FONT, 8)).pack(side="right")

    # The list and editor now share width, not scarce vertical height. A
    # draggable sash lets the user trade width between reference and editing.
    panes = tk.PanedWindow(body, orient=tk.HORIZONTAL, bg=bg, bd=0,
                           sashwidth=7, sashrelief=tk.FLAT,
                           showhandle=False, opaqueresize=True)
    panes.pack(fill="both", expand=True)
    results = tk.Frame(panes, bg=panel, width=495, height=390,
                       highlightthickness=1, highlightbackground=border)
    details = tk.Frame(panes, bg=panel, width=340, height=390,
                       highlightthickness=1, highlightbackground=border)
    panes.add(results, minsize=320, stretch="always")
    panes.add(details, minsize=295, stretch="never")
    app.command_panes = panes

    result_header = tk.Frame(results, bg=panel)
    result_header.pack(fill="x", padx=12, pady=(11, 2))
    tk.Label(result_header, text="REFERENCE LIBRARY", bg=panel, fg=white,
             font=(FONT, 10, "bold")).pack(side="left")
    app.command_count = tk.Label(result_header, text="", bg=panel, fg=accent,
                                  font=(FONT, 9))
    app.command_count.pack(side="right")
    tk.Label(results, text="Select a row to preview. Double-click to edit.",
             bg=panel, fg=muted, font=(FONT, 8), anchor="w").pack(
                 fill="x", padx=12, pady=(0, 3))
    table_area = tk.Frame(results, bg=bg)
    table_area.pack(fill="both", expand=True, padx=9, pady=(0, 10))
    # Sixteen visible rows rather than the four hard-coded in Normal.
    app.command_tree = app._tree(
        table_area, ("Command", "Purpose / Description"), (280, 200),
        rows=16, aligns=("w", "e"))
    app.command_tree.bind("<<TreeviewSelect>>", app._select_command)
    app.command_tree.bind("<Double-1>", lambda _event: app._focus_command_editor())
    app.command_tree.bind("<Return>", lambda _event: app._focus_command_editor())

    editor_heading = tk.Frame(details, bg=panel)
    editor_heading.pack(fill="x", padx=12, pady=(12, 3))
    tk.Label(editor_heading, text="COMMAND PREVIEW", bg=panel, fg=white,
             font=(FONT, 10, "bold")).pack(side="left")
    tk.Label(editor_heading, text="COPY ONLY", bg=c["ACCENT_DARK"], fg=accent,
             font=(FONT, 8, "bold"), padx=7, pady=3).pack(side="right")
    tags = tk.Frame(details, bg=panel)
    tags.pack(fill="x", padx=12, pady=(3, 5))
    app.command_machine_tag = tk.Label(tags, text="SELECT A COMMAND", bg=panel, fg=accent,
                                        font=(FONT, 9, "bold"))
    app.command_machine_tag.pack(side="left")
    app.command_category_tag = tk.Label(tags, text="", bg=panel, fg=muted,
                                         font=(FONT, 8), wraplength=160)
    app.command_category_tag.pack(side="right")

    app.command_description_label = tk.Label(
        details, text="Select a reference to view its command.", bg=panel,
        fg=white, font=(FONT, 9), justify="left", anchor="nw",
        wraplength=310)
    app.command_description_label.pack(fill="x", padx=12, pady=(1, 9))
    tk.Label(details, text="EDIT BEFORE COPYING  ·  CHANGES ARE TEMPORARY",
             bg=panel, fg=muted, font=(FONT, 8), anchor="w").pack(
                 fill="x", padx=12, pady=(0, 5))
    app.command_code = tk.Text(
        details, wrap="word", undo=True, height=10, font=("Consolas", 10),
        bg=input_bg, fg="#D3E4FF", insertbackground=accent, bd=0,
        padx=10, pady=9, highlightthickness=1, highlightbackground=border)
    app.command_code.pack(fill="both", expand=True, padx=12, pady=(0, 7))
    app.command_code.bind("<Control-a>", app._command_select_all)
    app.command_code.bind("<Control-Return>",
                          lambda _event: (app._copy_command(), "break")[1])

    app._build_template_actions(details, mini=False)

    actions = tk.Frame(details, bg=panel)
    actions.pack(fill="x", padx=8, pady=(4, 5))
    app.command_star = design.button(actions, "☆ Save", app._toggle_command_favorite,
                                      app.theme, compact=True)
    app.command_star.pack(side="left", padx=(0, 3))
    app.command_edit = design.button(actions, "Edit", app._edit_custom_command,
                                      app.theme, compact=True)
    app.command_edit.pack(side="left", padx=(0, 3))
    app.command_delete = design.button(actions, "Delete", app._delete_custom_command,
                                        app.theme, compact=True)
    app.command_delete.pack(side="left", padx=(0, 3))
    app.command_reset = design.button(actions, "Reset", app._reset_command_draft,
                                       app.theme, compact=True)
    app.command_reset.pack(side="right")
    design.button(details, "Copy edited command", app._copy_command,
                  app.theme, primary=True, compact=True).pack(
                      fill="x", padx=12, pady=(1, 5))
    app.command_feedback = tk.Label(
        details, text="Offline · Nothing is executed", bg=panel, fg=muted,
        font=(FONT, 8), anchor="w", wraplength=310)
    app.command_feedback.pack(fill="x", padx=12, pady=(0, 8))

    # Reuse all existing command filtering, selection, template and copy logic.
    app._style_command_modes()
    app._refresh_command_results()
