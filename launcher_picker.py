"""Searchable, theme-aware Extra Mini tile picker and lightweight rename dialogs."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

import launcher_pages as lp
import pocket_design as design

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
    """Four operations max: choose kind, search, pick row, Add to tile.

    No saved user data is touched until Add is pressed. Choosing a template
    shows only approved/current templates, and every other command is a normal
    reference. Copy-direct is available only for plain command entries.
    """
    win, c, close = _base_dialog(app, "Add quick action", 505, 555)
    root = tk.Frame(win, bg=c["BG"])
    root.pack(fill="both", expand=True, padx=15, pady=13)
    tk.Label(root, text="Add a quick action", bg=c["BG"], fg=c["WHITE"],
             font=("Segoe UI", 14, "bold")).pack(anchor="w")
    tk.Label(root, text="Choose something already saved in Pocket.",
             bg=c["BG"], fg=c["MUTED"], font=("Segoe UI", 9)).pack(
             anchor="w", pady=(3, 12))
    initial_kind = selected.get("kind") if isinstance(selected, dict) else "tool"
    kind_labels = {key: name for key, name in TYPES}
    selected_kind = tk.StringVar(value=kind_labels.get(initial_kind, "Tools"))
    tk.Label(root, text="TYPE", bg=c["BG"], fg=c["SECONDARY"],
             font=("Segoe UI", 8, "bold")).pack(anchor="w")
    kindbox = ttk.Combobox(root, state="readonly", style="Pocket.TCombobox",
                           textvariable=selected_kind, values=list(kind_labels.values()))
    kindbox.pack(fill="x", pady=(4, 10))
    tk.Label(root, text="FIND ITEM", bg=c["BG"], fg=c["SECONDARY"],
             font=("Segoe UI", 8, "bold")).pack(anchor="w")
    query = tk.StringVar()
    search = design.entry(root, query, app.theme)
    search.pack(fill="x", pady=(4, 10), ipady=6)
    listing = tk.Frame(root, bg=c["PANEL"], highlightthickness=1,
                       highlightbackground=c["BORDER"])
    listing.pack(fill="both", expand=True)
    scroller = ttk.Scrollbar(listing, orient="vertical",
                             style="Pocket.Vertical.TScrollbar")
    choices = tk.Listbox(listing, activestyle="none", exportselection=False,
                         bg=c["PANEL"], fg=c["WHITE"],
                         selectbackground=c["ACCENT_DARK"], selectforeground=c["WHITE"],
                         font=("Segoe UI", 10), relief="flat", bd=0, height=8)
    scroller.configure(command=choices.yview)
    choices.configure(yscrollcommand=scroller.set)
    choices.pack(side="left", fill="both", expand=True)
    scroller.pack(side="right", fill="y")
    description = tk.Label(root, text="", bg=c["BG"], fg=c["MUTED"],
                           wraplength=450, justify="left", anchor="w",
                           font=("Segoe UI", 9))
    description.pack(fill="x", pady=(7, 3))
    copy_direct = tk.BooleanVar(value=bool(selected and selected.get("action") == "copy"))
    copy_toggle = tk.Checkbutton(root, text="Copy directly (no command execution)",
                                 variable=copy_direct, bg=c["BG"], fg=c["WHITE"],
                                 selectcolor=c["INPUT"], activebackground=c["BG"],
                                 activeforeground=c["WHITE"], font=("Segoe UI", 9))
    footer = tk.Frame(root, bg=c["BG"])
    footer.pack(fill="x", pady=(9, 0))
    selected_entry = None
    items = []

    def selected_type():
        return next((key for key, label in TYPES if label == selected_kind.get()), "tool")

    def update_selection(*_):
        nonlocal selected_entry
        indexes = choices.curselection()
        selected_entry = items[indexes[0]] if indexes else None
        if selected_entry:
            description.configure(text=selected_entry["detail"])
        else:
            description.configure(text="Choose an item from the list.")
        kind = selected_type()
        if kind == "command":
            copy_toggle.pack(fill="x", before=footer)
        else:
            copy_toggle.pack_forget()
        add.configure(state="normal" if selected_entry else "disabled")

    def refresh(*_):
        nonlocal items, selected_entry
        items = lp.candidates(app.data, app.command_library,
                              app.settings["visible_tabs"], selected_type(),
                              query.get(), limit=200)
        choices.delete(0, tk.END)
        for item in items:
            choices.insert(tk.END, item["title"])
        selected_entry = None
        if items:
            choices.selection_set(0)
        update_selection()

    def save():
        if selected_entry is None:
            return
        tile = dict(selected_entry["tile"])
        if tile["kind"] == "command" and copy_direct.get():
            tile["action"] = "copy"
        on_choose(tile)
        close()

    design.button(footer, "Cancel", close, app.theme, compact=True).pack(side="right")
    add = design.button(footer, "Add to tile", save, app.theme, primary=True)
    add.pack(side="right", padx=(0, 8))
    choices.bind("<<ListboxSelect>>", update_selection)
    choices.bind("<Double-Button-1>", lambda _e: save())
    choices.bind("<Return>", lambda _e: save())
    selected_kind.trace_add("write", refresh)
    query.trace_add("write", refresh)
    refresh()
    search.focus_set()
