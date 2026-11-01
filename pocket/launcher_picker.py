"""Searchable, theme-aware Extra Mini tile picker and lightweight rename dialogs."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from . import launcher_pages as lp
from . import pocket_design as design

TYPES = (
    ("tool", "Tools"),
    ("command", "Commands"),
    ("template", "Smart Templates"),
    ("note", "Notes"),
    ("shortcut", "Shortcuts"),
)


def _base_dialog(app, caption, width, height):
    c = design.colors(app.theme)
    win = tk.Toplevel(app.root)
    win.title("Pocket · " + caption)
    win.configure(bg=c["BG"])
    # A short rename form should stay short; the searchable picker needs space.
    win.minsize(365, min(height, 300))
    win.geometry(f"{width}x{height}")
    win.transient(app.root)
    previous = app._modal
    app._modal = True
    closed = False
    def close():
        nonlocal closed
        if closed:
            return
        closed = True
        try:
            win.grab_release()
            win.destroy()
        finally:
            app._modal = previous
    win.protocol("WM_DELETE_WINDOW", close)
    win.bind("<Escape>", lambda _e: close())
    win.grab_set()
    return win, c, close


def rename_dialog(app, initial, title, callback):
    win, c, close = _base_dialog(app, title, 405, 180)
    area = tk.Frame(win, bg=c["BG"])
    area.pack(fill="both", expand=True, padx=16, pady=14)
    tk.Label(area, text=title, bg=c["BG"], fg=c["WHITE"],
             font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(0, 10))
    value = tk.StringVar(value=initial)
    field = design.entry(area, value, app.theme)
    field.pack(fill="x", ipady=6)
    bottom = tk.Frame(area, bg=c["BG"])
    bottom.pack(fill="x", pady=(13, 0))
    def submit():
        callback(value.get())
        close()
    design.button(bottom, "Save", submit, app.theme, primary=True,
                  compact=True).pack(side="right")
    design.button(bottom, "Cancel", close, app.theme, compact=True).pack(
        side="right", padx=5)
    field.bind("<Return>", lambda _e: submit())
    field.focus_set()
    field.selection_range(0, "end")


def choose_item(app, on_choose, *, selected=None):
    """Pick an action using one search field and click-to-select category chips.

    Search is instant; double-click on a result adds it immediately. The copy
    toggle is offered only for plain CLI commands, never for Smart Templates.
    """
    win, c, close = _base_dialog(app, "Quick actions", 530, 510)
    root = tk.Frame(win, bg=c["BG"])
    root.pack(fill="both", expand=True, padx=16, pady=14)
    tk.Label(root, text="What would you like to add?", bg=c["BG"], fg=c["WHITE"],
             font=("Segoe UI", 15, "bold")).pack(anchor="w")
    tk.Label(root, text="Pick a category, then click an item. Nothing runs automatically.",
             bg=c["BG"], fg=c["MUTED"], font=("Segoe UI", 9)).pack(anchor="w", pady=(4, 10))

    selected_kind = tk.StringVar(value=selected.get("kind", "tool") if isinstance(selected, dict) else "tool")
    chips = tk.Frame(root, bg=c["BG"])
    chips.pack(fill="x", pady=(0, 12))
    chip_buttons = {}
    query = tk.StringVar()
    search = design.entry(root, query, app.theme)
    search.pack(fill="x", ipady=7, pady=(0, 9))
    search.insert(0, "")
    list_frame = tk.Frame(root, bg=c["PANEL"], highlightthickness=1,
                          highlightbackground=c["BORDER"])
    list_frame.pack(fill="both", expand=True)
    scroller = ttk.Scrollbar(list_frame, orient="vertical", style="Pocket.Vertical.TScrollbar")
    choices = tk.Listbox(list_frame, activestyle="none", exportselection=False,
                         bg=c["PANEL"], fg=c["WHITE"], selectbackground=c["ACCENT_DARK"],
                         selectforeground=c["WHITE"], font=("Segoe UI", 10), relief="flat",
                         bd=0, height=10, selectmode="browse")
    scroller.configure(command=choices.yview)
    choices.configure(yscrollcommand=scroller.set)
    choices.pack(side="left", fill="both", expand=True, padx=5, pady=5)
    scroller.pack(side="right", fill="y")
    description = tk.Label(root, text="Select an action", bg=c["BG"], fg=c["SECONDARY"],
                           wraplength=480, anchor="w", justify="left", font=("Segoe UI", 9))
    description.pack(fill="x", pady=(8, 4))
    copy_direct = tk.BooleanVar(value=bool(selected and selected.get("action") == "copy"))
    copy_toggle = tk.Checkbutton(root, text="Copy command directly (never execute)",
                                 variable=copy_direct, bg=c["BG"], fg=c["WHITE"],
                                 selectcolor=c["INPUT"], activebackground=c["BG"],
                                 activeforeground=c["WHITE"], font=("Segoe UI", 9))
    footer = tk.Frame(root, bg=c["BG"])
    footer.pack(fill="x", pady=(7, 0))
    items = []
    selected_entry = None

    def update_selection(_event=None):
        nonlocal selected_entry
        indexes = choices.curselection()
        selected_entry = items[indexes[0]] if indexes and indexes[0] < len(items) else None
        description.configure(text=selected_entry["detail"] if selected_entry else "No matching items.")
        if selected_kind.get() == "command":
            copy_toggle.pack(fill="x", before=footer)
        else:
            copy_toggle.pack_forget()
        add.configure(state="normal" if selected_entry else "disabled")

    def refresh(*_):
        nonlocal items
        items = lp.candidates(app.data, app.command_library,
                              app.settings["visible_tabs"], selected_kind.get(),
                              query.get(), limit=200)
        choices.delete(0, tk.END)
        for item in items:
            choices.insert(tk.END, item["title"])
        if items:
            choices.selection_set(0)
            choices.activate(0)
        update_selection()

    def change_kind(kind):
        selected_kind.set(kind)
        for k, button in chip_buttons.items():
            active = k == kind
            button.configure(bg=c["ACCENT_DARK"] if active else c["CARD"],
                             fg=c["ACCENT"] if active else c["SECONDARY"])
        refresh()
        search.focus_set()

    def save(_event=None):
        if selected_entry is None:
            return
        tile = dict(selected_entry["tile"])
        if tile["kind"] == "command" and copy_direct.get():
            tile["action"] = "copy"
        on_choose(tile)
        close()

    for kind, label in TYPES:
        button = tk.Button(chips, text=label, command=lambda k=kind: change_kind(k),
                           relief="flat", bd=0, font=("Segoe UI", 8, "bold"),
                           cursor="hand2", padx=8, pady=7)
        button.pack(side="left", padx=(0, 4))
        chip_buttons[kind] = button
    design.button(footer, "Cancel", close, app.theme, compact=True).pack(side="right")
    add = design.button(footer, "Add action", save, app.theme, primary=True, compact=True)
    add.pack(side="right", padx=(0, 8))
    choices.bind("<<ListboxSelect>>", update_selection)
    choices.bind("<Double-Button-1>", save)
    choices.bind("<Return>", save)
    search.bind("<Return>", save)
    query.trace_add("write", refresh)
    change_kind(selected_kind.get())
    search.focus_set()
