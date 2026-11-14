"""Small collapsible folder headers and internal mouse reordering for Shortcuts.

Internal drag uses ordinary Tk events on dedicated grip handles, independent
of tkinterdnd2's external Explorer/browser drop-to-draft workflow.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, simpledialog

from . import pocket_design as design
from . import shortcut_folders as folders

FONT = "Segoe UI"


def _layout(app):
    return app.data["shortcut_folders"]


def show_add_menu(app, button):
    """One consistent Add dropdown for Mini, Normal and Dashboard."""
    if button is None or not button.winfo_exists():
        return
    c = design.colors(app.theme)
    menu = tk.Menu(
        app.root, tearoff=False, bg=c["PANEL"], fg=c["WHITE"],
        activebackground=c["ACCENT_DARK"], activeforeground=c["WHITE"],
        disabledforeground=c["MUTED"], font=(FONT, 9), bd=1,
        activeborderwidth=0)
    menu.add_command(
        label="↗   New shortcut",
        command=lambda: app._toggle_link_form(None))
    menu.add_command(
        label="▣   New Pocket folder",
        command=lambda: prompt_folder(app))
    try:
        menu.tk_popup(button.winfo_rootx(),
                      button.winfo_rooty() + button.winfo_height())
    finally:
        menu.grab_release()


def prompt_folder(app, ident=None):
    layout = _layout(app)
    folder = next((f for f in layout["folders"] if f["id"] == ident), None)
    if ident is not None and folder is None:
        return
    old_modal = app._modal
    app._modal = True
    try:
        answer = simpledialog.askstring(
            "Pocket shortcut folders",
            "Folder name (only organizes Pocket shortcuts):",
            initialvalue=folder["title"] if folder else "",
            parent=app.root)
    finally:
        app._modal = old_modal
    if answer is None:
        return
    try:
        changed = (folders.rename_folder(layout, ident, answer)
                   if folder else bool(folders.add_folder(layout, answer)))
    except ValueError as exc:
        app._warning("Shortcut folder", str(exc))
        return
    if changed:
        app.refresh_links()
        app.schedule_save()


def toggle(app, ident):
    layout = _layout(app)
    folder = next((f for f in layout["folders"] if f["id"] == ident), None)
    if folder and folders.set_expanded(layout, ident, not folder["expanded"]):
        app.refresh_links()
        app.schedule_save()


def remove_folder(app, ident):
    layout = _layout(app)
    folder = next((f for f in layout["folders"] if f["id"] == ident), None)
    if folder is None:
        return
    old_modal = app._modal
    app._modal = True
    try:
        accepted = messagebox.askyesno(
            "Remove Pocket folder",
            f'Remove "{folder["title"]}"?\n\n'
            "All shortcuts inside will be kept and shown without a folder.",
            parent=app.root)
    finally:
        app._modal = old_modal
    if accepted and folders.delete_folder(layout, ident):
        app.refresh_links()
        app.schedule_save()


def move_step(app, key, step):
    layout = _layout(app)
    if key in layout["root"]:
        items = layout["root"]
        current = key
    elif key.startswith("l:"):
        fid = folders.link_folder(layout, key[2:])
        if fid is None:
            return
        items = layout["children"][fid]
        current = key[2:]
    else:
        return
    index = items.index(current)
    target = index + step
    if not 0 <= target < len(items):
        return
    items[index], items[target] = items[target], items[index]
    app.refresh_links()
    app.schedule_save()


def move_link_to(app, link, folder_id):
    layout = _layout(app)
    key = folders.link_key(link["id"])
    if folder_id is None:
        changed = folders.move(layout, key, "root")
    else:
        changed = folders.move(layout, key, folders.folder_key(folder_id), "inside")
    if changed:
        app.refresh_links()
        app.schedule_save()


def link_move_menu(app, parent, link):
    c = design.colors(app.theme)
    menu = tk.Menu(
        parent, tearoff=False, bg=c["PANEL"], fg=c["WHITE"],
        activebackground=c["ACCENT_DARK"], activeforeground=c["WHITE"],
        font=(FONT, 9))
    layout = _layout(app)
    current = folders.link_folder(layout, link["id"])
    menu.add_command(
        label="Unfiled shortcuts" + (" ✓" if current is None else ""),
        command=lambda: move_link_to(app, link, None))
    for group in layout["folders"]:
        fid = group["id"]
        menu.add_command(
            label=group["title"] + (" ✓" if fid == current else ""),
            command=lambda fid=fid: move_link_to(app, link, fid))
    return menu


def folder_menu(app, ident):
    layout = _layout(app)
    folder = next((f for f in layout["folders"] if f["id"] == ident), None)
    if folder is None:
        return
    c = design.colors(app.theme)
    menu = tk.Menu(
        app.root, tearoff=False, bg=c["PANEL"], fg=c["WHITE"],
        activebackground=c["ACCENT_DARK"], activeforeground=c["WHITE"],
        font=(FONT, 9))
    menu.add_command(label="Collapse" if folder["expanded"] else "Expand",
                     command=lambda: toggle(app, ident))
    menu.add_command(label="Rename folder", command=lambda: prompt_folder(app, ident))
    menu.add_command(label="Move folder up",
                     command=lambda: move_step(app, folders.folder_key(ident), -1))
    menu.add_command(label="Move folder down",
                     command=lambda: move_step(app, folders.folder_key(ident), 1))
    menu.add_separator()
    menu.add_command(label="Remove folder (keep shortcuts)",
                     command=lambda: remove_folder(app, ident))
    x, y = app.root.winfo_pointerxy()
    try:
        menu.tk_popup(x, y)
    finally:
        menu.grab_release()


def folder_header(app, parent, folder, total, *, expanded):
    """Compact divider-style folder title, not an oversized shortcut card."""
    c = design.colors(app.theme)
    bar = tk.Frame(parent, bg=c["PANEL"], highlightthickness=1,
                   highlightbackground=c["BORDER"])
    bar.pack(fill="x", padx=(2, 3), pady=(6, 3), ipady=1)
    ident = folder["id"]

    # Pack the grip FIRST on the right so folders and shortcut cards share
    # exactly the same right-edge drag affordance in every layout.
    grip = tk.Label(
        bar, text="⋮⋮", bg=c["PANEL"], fg=c["SECONDARY"],
        font=(FONT, 10, "bold"), cursor="fleur",
        padx=5, pady=4)
    grip.pack(side="right", padx=(1, 5))
    more = tk.Button(
        bar, text="···", bg=c["PANEL"], fg=c["MUTED"],
        activebackground=c["PANEL"], activeforeground=c["ACCENT"],
        bd=0, relief="flat", font=(FONT, 10, "bold"), cursor="hand2",
        command=lambda: folder_menu(app, ident))
    more.pack(side="right", padx=(0, 4))
    count = tk.Label(
        bar, text=str(total), bg=c["PANEL"], fg=c["SECONDARY"],
        font=(FONT, 8), padx=3)
    count.pack(side="right", padx=(0, 5))

    arrow = "▾" if expanded else "▸"
    btn = tk.Button(
        bar, text=arrow, bg=c["PANEL"], fg=c["ACCENT"],
        relief="flat", bd=0, cursor="hand2", font=(FONT, 10, "bold"),
        width=2, command=lambda: toggle(app, ident))
    btn.pack(side="left", padx=(4, 0))
    title = tk.Button(
        bar, text=folder["title"], bg=c["PANEL"], fg=c["WHITE"],
        activebackground=c["PANEL"], activeforeground=c["ACCENT"],
        relief="flat", bd=0, font=(FONT, 9, "bold"),
        anchor="w", cursor="hand2", command=lambda: toggle(app, ident))
    title.pack(side="left", fill="x", expand=True, padx=(1, 4))

    register_target(app, bar, ("folder", ident))
    setup_grip(app, grip, folders.folder_key(ident))
    for widget in (bar, grip, more, count, btn, title):
        app._register_shortcut_drop(widget, folder_id=ident)
    for widget in (btn, title, count):
        widget.bind("<Button-3>", lambda _event, i=ident: folder_menu(app, i))
    app.shortcut_folder_headers[ident] = bar
    return bar



def unfiled_drop_zone(app, parent):
    """Small visible exit target for moving a shortcut out of a folder."""
    c = design.colors(app.theme)
    bar = tk.Label(
        parent, text="Unfiled  ·  drop here",
        fg=c["MUTED"], bg=c["BG"], font=(FONT, 8),
        anchor="w", pady=3, cursor="hand2")
    bar.pack(fill="x", padx=5, pady=(1, 3))
    register_target(app, bar, ("root", ""))
    return bar


def reset_targets(app):
    app.shortcut_drop_targets = {}
    app.shortcut_folder_headers = {}
    app.shortcut_drag_handles = {}
    app.shortcut_drag_state = None
    app.shortcut_drag_highlight = None


def register_target(app, widget, target):
    app.shortcut_drop_targets[str(widget)] = (widget, target)


def setup_grip(app, grip, key):
    app.shortcut_drag_handles[key] = grip
    grip.bind("<ButtonPress-1>", lambda event, source=key: begin_drag(app, source, event))
    grip.bind("<B1-Motion>", lambda event: drag_motion(app, event))
    grip.bind("<ButtonRelease-1>", lambda event: finish_drag(app, event))


def _target_at(app, x, y):
    try:
        widget = app.root.winfo_containing(x, y)
    except tk.TclError:
        return None
    while widget is not None:
        registered = app.shortcut_drop_targets.get(str(widget))
        if registered:
            return registered
        widget = widget.master
    return None


def begin_drag(app, source, event):
    if app.current_tab != "links":
        return
    # Sorting while filtered makes invisible items' positions ambiguous.
    if (app.link_query.get().strip() or
            (app.display_mode == "dashboard"
             and app.dashboard_shortcut_kind.get() != "all")):
        return
    app.shortcut_drag_state = {
        "source": source, "start": (event.x_root, event.y_root), "active": False}
    return "break"


def _clear_highlight(app):
    previous = getattr(app, "shortcut_drag_highlight", None)
    if previous is None:
        return
    widget, color = previous
    if widget.winfo_exists():
        if isinstance(widget, tk.Label):
            widget.configure(bg=color)
        else:
            widget.configure(highlightbackground=color)
    app.shortcut_drag_highlight = None


def _highlight(app, dest):
    widget = dest[0] if dest else None
    previous = getattr(app, "shortcut_drag_highlight", None)
    if previous is not None and previous[0] is widget:
        return
    _clear_highlight(app)
    if widget is not None and widget.winfo_exists():
        c = design.colors(app.theme)
        if isinstance(widget, tk.Label):
            app.shortcut_drag_highlight = (widget, widget.cget("bg"))
            widget.configure(bg=c["ACCENT_DARK"])
        else:
            app.shortcut_drag_highlight = (widget, widget.cget("highlightbackground"))
            widget.configure(highlightbackground=c["ACCENT"])


def drag_motion(app, event):
    state = getattr(app, "shortcut_drag_state", None)
    if state is None:
        return
    if not state["active"]:
        dx = event.x_root - state["start"][0]
        dy = event.y_root - state["start"][1]
        if dx * dx + dy * dy < 36:
            return "break"
        state["active"] = True
    destination = _target_at(app, event.x_root, event.y_root)
    _highlight(app, destination)
    canvas = getattr(app, "_scroll_canvas", None)
    if canvas is not None and canvas.winfo_exists():
        top = canvas.winfo_rooty()
        bottom = top + canvas.winfo_height()
        if top <= event.y_root < top + 25:
            canvas.yview_scroll(-2, "units")
        elif bottom - 25 < event.y_root <= bottom:
            canvas.yview_scroll(2, "units")
    return "break"


def finish_drag(app, event):
    state = getattr(app, "shortcut_drag_state", None)
    app.shortcut_drag_state = None
    _clear_highlight(app)
    if state is None or not state["active"]:
        return "break"
    target = _target_at(app, event.x_root, event.y_root)
    if target is None:
        return "break"
    widget, (kind, ident) = target
    source = state["source"]
    if kind == "root":
        destination = "root"
        position = "before"
    elif kind == "folder":
        destination = folders.folder_key(ident)
        if source.startswith("l:"):
            position = "inside"
        else:
            center = widget.winfo_rooty() + widget.winfo_height() / 2
            position = "before" if event.y_root < center else "after"
    else:
        destination = folders.link_key(ident)
        center = widget.winfo_rooty() + widget.winfo_height() / 2
        position = "before" if event.y_root < center else "after"
    if folders.move(_layout(app), source, destination, position):
        app.refresh_links()
        app.schedule_save()
    return "break"
