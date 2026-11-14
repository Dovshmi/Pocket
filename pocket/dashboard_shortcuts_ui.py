"""Wide Dashboard-only shortcut library and compact inline editor.

Normal and Mini retain their previous scrollable card layouts and form UX.
Launching shortcuts remains explicit: rendering/search never opens a URL/file.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from urllib.parse import urlsplit

from . import pocket_design as design
from . import hotkey_settings as hk
from . import shortcut_folders
from . import shortcut_sections_ui as sections_ui

FONT = "Segoe UI"
KINDS = (("all", "All"), ("url", "Websites"), ("file", "Files"), ("folder", "Folders"))


def column_count(width):
    """Keep compact cards readable on small Windows display work areas."""
    return 3 if width >= 790 else 2 if width >= 540 else 1


def preview_target(link):
    target = link.get("url", "")
    if link.get("kind", "url") == "url":
        return urlsplit(target).netloc or target
    return target


def shorten(text, limit):
    return text if len(text) <= limit else text[:max(1, limit - 1)] + "…"


def build(app):
    c = design.colors(app.theme)
    bg, panel, border = c["BG"], c["PANEL"], c["BORDER"]
    muted, accent, white = c["MUTED"], c["ACCENT"], c["WHITE"]

    header = tk.Frame(app.body, bg=bg)
    header.pack(fill="x", pady=(0, 9))
    intro = tk.Frame(header, bg=bg)
    intro.pack(side="left", fill="x", expand=True)
    tk.Label(intro, text="SHORTCUT LIBRARY", bg=bg, fg=white,
             font=(FONT, 13, "bold")).pack(anchor="w")
    tk.Label(intro, text="Open your websites, files and folders",
             bg=bg, fg=muted, font=(FONT, 9)).pack(anchor="w", pady=(2, 0))
    design.button(header, "+ New shortcut", lambda: app._toggle_link_form(None),
                  app.theme, primary=True, compact=True).pack(side="right")
    design.button(header, "+ Folder", lambda: sections_ui.prompt_folder(app),
                  app.theme, compact=True).pack(side="right", padx=(0, 8))

    filters = tk.Frame(app.body, bg=panel, highlightthickness=1,
                       highlightbackground=border)
    filters.pack(fill="x", pady=(0, 8))
    row = tk.Frame(filters, bg=panel)
    row.pack(fill="x", padx=11, pady=(9, 6))
    app.link_query = tk.StringVar()
    search = design.entry(row, app.link_query, app.theme)
    search.pack(side="left", fill="x", expand=True, ipady=6)
    search.configure(font=(FONT, 10))
    app.link_query.trace_add("write", lambda *_: app.refresh_links())
    app.dashboard_shortcut_kind = tk.StringVar(value="all")
    app.dashboard_shortcut_filters = {}
    for kind, caption in KINDS:
        button = design.button(
            row, caption,
            lambda choice=kind: select_kind(app, choice),
            app.theme, compact=True)
        button.pack(side="left", padx=(6, 0))
        app.dashboard_shortcut_filters[kind] = button
    filter_state(app)

    status = tk.Frame(filters, bg=panel)
    status.pack(fill="x", padx=11, pady=(0, 8))
    app.dashboard_shortcut_count = tk.Label(
        status, text="", bg=panel, fg=accent, font=(FONT, 8, "bold"))
    app.dashboard_shortcut_count.pack(side="left")
    tk.Label(status, text="Drag ⋮⋮ to organize · Drop on a folder title to group",
             bg=panel, fg=muted, font=(FONT, 8)).pack(side="left", padx=(18, 0))
    tk.Label(status, text="No automatic opening · Local-first",
             bg=panel, fg=muted, font=(FONT, 8)).pack(side="right")

    # Keep the existing app-level DnD callbacks: a drop opens an editable
    # draft, never directly adds an unreviewed shortcut.
    app.drop_panel = tk.Frame(app.body, bg=panel,
                              highlightthickness=1, highlightbackground=c["ACCENT_DARK"],
                              height=46)
    app.drop_panel.pack(fill="x", pady=(0, 9))
    app.drop_panel.pack_propagate(False)
    drop_line = tk.Frame(app.drop_panel, bg=panel)
    drop_line.pack(fill="both", expand=True, padx=13)
    app.drop_title = tk.Label(
        drop_line, text="DROP WEBSITE, FILE OR FOLDER HERE",
        bg=panel, fg=accent, font=(FONT, 9, "bold"), anchor="w")
    app.drop_title.pack(side="left", fill="y")
    app.drop_hint = tk.Label(
        drop_line,
        text=("Pin Pocket before dragging from Explorer or browser"
              if app.dnd_available else "Drag & drop unavailable · tkinterdnd2 required"),
        bg=panel, fg=muted, font=(FONT, 8), anchor="e")
    app.drop_hint.pack(side="right", fill="y")
    for widget in (app.drop_panel, drop_line, app.drop_title, app.drop_hint):
        app._register_shortcut_drop(widget)

    # Unpacked until New/Edit is clicked; no permanent blank form gap.
    app.form_holder = tk.Frame(app.body, bg=bg)
    frame = tk.Frame(app.body, bg=bg)
    frame.pack(fill="both", expand=True)
    app.dashboard_shortcut_columns = 1
    app.dashboard_shortcut_cards = []

    canvas = tk.Canvas(frame, bg=bg, bd=0, highlightthickness=0)
    scroll = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview,
                           style="Pocket.Vertical.TScrollbar")
    canvas.configure(yscrollcommand=scroll.set)
    canvas.pack(side="left", fill="both", expand=True)
    scroll.pack(side="right", fill="y")
    app._scroll_canvas = canvas
    app.links_stack = tk.Frame(canvas, bg=bg)
    app._register_shortcut_drop(canvas)
    app._register_shortcut_drop(app.links_stack)
    window = canvas.create_window((0, 0), window=app.links_stack, anchor="nw")
    app.links_stack.bind(
        "<Configure>", lambda _event: canvas.configure(scrollregion=canvas.bbox("all")))
    def sized(event):
        canvas.itemconfigure(window, width=event.width)
        columns = column_count(event.width)
        if columns != app.dashboard_shortcut_columns:
            app.dashboard_shortcut_columns = columns
            app.refresh_links()

    canvas.bind("<Configure>", sized, add="+")
    canvas.bind("<Enter>", lambda _event: canvas.bind_all("<MouseWheel>", app._mousewheel))
    canvas.bind("<Leave>", lambda _event: canvas.unbind_all("<MouseWheel>"))
    app.refresh_links()


def select_kind(app, kind):
    app.dashboard_shortcut_kind.set(kind)
    filter_state(app)
    app._scroll_canvas.yview_moveto(0)
    app.refresh_links()


def filter_state(app):
    c = design.colors(app.theme)
    selected = app.dashboard_shortcut_kind.get()
    for kind, widget in app.dashboard_shortcut_filters.items():
        active = selected == kind
        widget.configure(bg=c["ACCENT_DARK"] if active else c["CARD"],
                         fg=c["ACCENT"] if active else c["SECONDARY"])


def _card(app, parent, link, *, row, column, columns, colors):
    """Draw a normal Dashboard card into either the root or a folder grid."""
    c = colors
    panel, accent, muted, white = (c["PANEL"], c["ACCENT"],
                                   c["MUTED"], c["WHITE"])
    tile = tk.Frame(
        parent, bg=panel, highlightthickness=1,
        highlightbackground=c["BORDER"])
    tile.grid(row=row, column=column, sticky="nsew", padx=5, pady=(3, 6))
    app.dashboard_shortcut_cards.append(tile)
    app._register_shortcut_drop(tile)
    sections_ui.register_target(app, tile, ("link", link["id"]))
    header = tk.Frame(tile, bg=panel)
    header.pack(fill="x", padx=9, pady=(8, 4))
    label = {"url": "WEBSITE", "file": "FILE", "folder": "FOLDER"}.get(
        link.get("kind", "url"), "SHORTCUT")
    tk.Label(header, text=label, bg=c["ACCENT_DARK"], fg=accent,
             padx=6, pady=3, font=(FONT, 8, "bold")).pack(side="left")
    button = tk.Button(
        header, text=shorten(link["title"], 28 if columns == 2 else 20),
        command=lambda item=link: app.open_shortcut(item),
        bg=panel, fg=white, activebackground=panel,
        activeforeground=accent, font=(FONT, 9, "bold"),
        relief="flat", bd=0, anchor="w", cursor="hand2")
    button.pack(side="left", fill="x", expand=True, padx=(7, 0))
    button.bind("<Button-3>", lambda _e, item=link: app._show_link_menu(item))
    app._register_shortcut_drop(button)
    grip = tk.Label(header, text="⋮⋮", bg=panel, fg=accent,
                    cursor="fleur", font=(FONT, 11, "bold"))
    grip.pack(side="right", padx=(5, 0))
    sections_ui.setup_grip(app, grip, shortcut_folders.link_key(link["id"]))
    target = tk.Label(
        tile, text=shorten(preview_target(link),
                           52 if columns == 1 else (39 if columns == 2 else 31)),
        bg=panel, fg=muted, font=(FONT, 8), anchor="w")
    target.pack(fill="x", padx=10, pady=(0, 6))
    target.bind("<Button-3>", lambda _e, item=link: app._show_link_menu(item))
    actions = tk.Frame(tile, bg=panel)
    actions.pack(fill="x", padx=8, pady=(0, 7))
    for caption, handler in (
            ("Open", lambda item=link: app.open_shortcut(item)),
            ("Copy", lambda item=link: app._copy_shortcut(item)),
            ("···", lambda item=link: app._show_link_menu(item))):
        design.button(actions, caption, handler, app.theme,
                      compact=True).pack(side="left", padx=(0, 5))
    return tile


def refresh(app):
    c = design.colors(app.theme)
    bg, accent = c["BG"], c["ACCENT"]
    muted = c["MUTED"]
    layout = shortcut_folders.normalize(
        app.data.get("shortcut_folders"), app.data["links"])
    app.data["shortcut_folders"] = layout
    sections_ui.reset_targets(app)
    for child in app.links_stack.winfo_children():
        child.destroy()

    matches = hk.filter_shortcuts(app.data["links"], app.link_query.get())
    kind = app.dashboard_shortcut_kind.get()
    if kind != "all":
        matches = [item for item in matches if item.get("kind", "url") == kind]
    app.dashboard_shortcut_count.configure(
        text=f"{len(matches)} of {len(app.data['links'])} shortcuts")

    count = app.dashboard_shortcut_columns
    app.dashboard_shortcut_cards = []
    for col in range(count):
        app.links_stack.grid_columnconfigure(col, weight=1, uniform="shortcut-cards")

    rows = shortcut_folders.visible_rows(
        layout, app.data["links"], query=app.link_query.get(), kind=kind)
    row_no = 0
    if layout["folders"]:
        host = tk.Frame(app.links_stack, bg=bg)
        host.grid(row=row_no, column=0, columnspan=count, sticky="ew")
        sections_ui.unfiled_drop_zone(app, host)
        row_no += 1
    if not rows:
        tk.Label(
            app.links_stack,
            text="No matching shortcuts. Change the filter or add a new shortcut.",
            bg=bg, fg=muted, font=(FONT, 10), anchor="center"
        ).grid(row=row_no, column=0, columnspan=count, sticky="ew", pady=35)
        row_no += 1

    column = 0
    for row in rows:
        if row["type"] == "link":
            _card(app, app.links_stack, row["link"], row=row_no,
                  column=column, columns=count, colors=c)
            column += 1
            if column >= count:
                column = 0
                row_no += 1
            continue
        if column:
            row_no += 1
            column = 0
        group = row["folder"]
        host = tk.Frame(app.links_stack, bg=bg)
        host.grid(row=row_no, column=0, columnspan=count, sticky="ew")
        sections_ui.folder_header(
            app, host, group, row["total"], expanded=row["expanded"])
        if row["expanded"] and row["links"]:
            contents = tk.Frame(host, bg=bg)
            contents.pack(fill="x", padx=(12, 0), pady=(0, 5))
            for col in range(count):
                contents.grid_columnconfigure(col, weight=1, uniform="folder-cards")
            for n, link in enumerate(row["links"]):
                _card(app, contents, link, row=n // count,
                      column=n % count, columns=count, colors=c)
        row_no += 1

    # Reset the scroll area after filter/collapse without reloading the page.
    app.links_stack.update_idletasks()
    app._scroll_canvas.configure(scrollregion=app._scroll_canvas.bbox("all"))


def toggle_form(app, item, *, draft=None):
    """Dashboard uses a compact horizontal editor; same save/browse callbacks."""
    c = design.colors(app.theme)
    bg, panel, border, muted = c["BG"], c["PANEL"], c["BORDER"], c["MUTED"]
    accent, white = c["ACCENT"], c["WHITE"]
    for child in app.form_holder.winfo_children():
        child.destroy()
    app.edit_link_id = item["id"] if item else None
    app.form_holder.pack(fill="x", before=app._scroll_canvas.master)
    pane = tk.Frame(app.form_holder, bg=panel, highlightthickness=1,
                    highlightbackground=c["ACCENT_DARK"])
    pane.pack(fill="x", pady=(0, 9))
    headline = tk.Frame(pane, bg=panel)
    headline.pack(fill="x", padx=12, pady=(8, 5))
    tk.Label(headline, text="EDIT SHORTCUT" if item else "NEW SHORTCUT",
             fg=accent, bg=panel, font=(FONT, 9, "bold")).pack(side="left")
    kinds = tk.Frame(headline, bg=panel)
    kinds.pack(side="right")
    title_var = tk.StringVar(value=item["title"] if item else (draft or {}).get("title", ""))
    target_var = tk.StringVar(value=item["url"] if item else (draft or {}).get("url", ""))
    kind_var = tk.StringVar(value=item.get("kind", "url") if item else (draft or {}).get("kind", "url"))
    bottom = tk.Frame(pane, bg=panel)
    bottom.pack(fill="x", padx=12)
    bottom.grid_columnconfigure(0, weight=3)
    bottom.grid_columnconfigure(1, weight=5)

    def kind_changed():
        if kind_var.get() == "url":
            browse.pack_forget()
            hint.config(text="Website opens in your browser")
        else:
            browse.pack(side="right", padx=(7, 0))
            hint.config(text="Opens locally; path must exist")

    for value, label in (("url", "Website"), ("file", "File"), ("folder", "Folder")):
        tk.Radiobutton(kinds, text=label, value=value, variable=kind_var,
                       command=kind_changed,
                       bg=panel, fg=white, activebackground=panel,
                       activeforeground=accent, selectcolor=c["INPUT"],
                       font=(FONT, 8), highlightthickness=0).pack(
                           side="left", padx=(8, 0))
    for col, caption in ((0, "NAME"), (1, "TARGET / PATH")):
        tk.Label(bottom, text=caption, fg=muted, bg=panel,
                 font=(FONT, 8, "bold")).grid(row=0, column=col, sticky="w",
                                               pady=(0, 3), padx=(0, 10) if col == 0 else (0, 0))
    name_entry = design.entry(bottom, title_var, app.theme)
    name_entry.grid(row=1, column=0, sticky="ew", ipady=6, padx=(0, 10))
    target_area = tk.Frame(bottom, bg=panel)
    target_area.grid(row=1, column=1, sticky="ew")
    address = design.entry(target_area, target_var, app.theme)
    address.pack(side="left", fill="x", expand=True, ipady=6)
    browse = design.button(target_area, "Browse", lambda: app._browse_shortcut(
        kind_var, target_var, title_var), app.theme, compact=True)
    footer = tk.Frame(pane, bg=panel)
    footer.pack(fill="x", padx=12, pady=(5, 8))
    hint = tk.Label(footer, text="", bg=panel, fg=muted,
                    font=(FONT, 8), anchor="w")
    hint.pack(side="left", fill="x", expand=True)
    design.button(footer, "Cancel", app._close_form, app.theme,
                  compact=True).pack(side="right", padx=(7, 0))
    design.button(footer, "Save shortcut", lambda: app._save_link(
        title_var.get(), target_var.get(), kind_var.get()), app.theme,
        primary=True, compact=True).pack(side="right")
    kind_changed()
    app.root.after(30, lambda: name_entry.focus_set() if name_entry.winfo_exists() else None)


def close_form(app):
    for child in app.form_holder.winfo_children():
        child.destroy()
    app.form_holder.pack_forget()
    app.edit_link_id = None
    if app.drop_title.winfo_exists():
        app.drop_title.config(text="DROP WEBSITE, FILE OR FOLDER HERE")
    if app.drop_hint.winfo_exists():
        app.drop_hint.config(text=(
            "Pin Pocket before dragging from Explorer or browser"
            if app.dnd_available else
            "Drag & drop unavailable · tkinterdnd2 required"))
    if app._scroll_canvas is not None and app._scroll_canvas.winfo_exists():
        app._scroll_canvas.yview_moveto(0)
