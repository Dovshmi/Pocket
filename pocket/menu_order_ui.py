"""Interactive, compact Pocket Settings menu icon ordering.

Both mouse drag-and-drop and click-source/click-destination are supported.
Uses the real local Pocket icons rather than font-dependent Unicode symbols.
An accessible live Mini preview preserves its seven-tools-plus-More layout.
No preference is changed until a user completes a move or presses Reset.
"""
from __future__ import annotations

import tkinter as tk

from . import menu_order
from . import mini_nav
from . import tool_icons
from . import pocket_design as design


def build(parent, app, c, *, compact=False):
    """Render a reorderable list plus live mini preview with no extra windows."""
    wrap = tk.Frame(parent, bg=c["PANEL"])
    wrap.pack(fill="x", padx=9, pady=(8, 11))

    header = tk.Frame(wrap, bg=c["PANEL"])
    header.pack(fill="x", pady=(0, 3))
    tk.Label(header, text="MENU ORDER", fg=c["WHITE"], bg=c["PANEL"],
             font=("Segoe UI", 9, "bold")).pack(side="left")
    tk.Button(header, text="Reset order",
              command=lambda: reset_order(), fg=c["ACCENT"],
              bg=c["PANEL"], activebackground=c["CARD_HOVER"],
              activeforeground=c["WHITE"], bd=0, relief="flat",
              cursor="hand2", font=("Segoe UI", 8),
              padx=3, pady=3).pack(side="right")
    tk.Label(wrap, text="Drag icons or select one, then click its destination.",
             fg=c["MUTED"], bg=c["PANEL"], font=("Segoe UI", 8),
             anchor="w", justify="left",
             wraplength=260 if compact else 490).pack(fill="x", pady=(0, 8))

    grid = tk.Frame(wrap, bg=c["PANEL"])
    grid.pack(fill="x")
    for column in range(5):
        grid.grid_columnconfigure(column, weight=1, uniform="menus")

    tk.Label(wrap, text="LIVE MINI PREVIEW", fg=c["MUTED"],
             bg=c["PANEL"], font=("Segoe UI", 8, "bold"),
             anchor="w").pack(fill="x", pady=(11, 4))
    preview = tk.Frame(wrap, bg=c["INPUT"], highlightthickness=1,
                       highlightbackground=c["BORDER"])
    preview.pack(fill="x", padx=1, pady=(0, 3))
    status = tk.Label(wrap, text="", fg=c["MUTED"], bg=c["PANEL"],
                      font=("Segoe UI", 8), justify="left", anchor="w",
                      wraplength=260 if compact else 460)
    status.pack(fill="x", pady=(3, 0))

    selected = None
    drag = None
    cells = {}
    # Helpful for non-destructive Windows GUI integration checks.
    app.menu_order_editor_cells = cells
    app.menu_order_editor_grid = grid
    app.menu_order_editor_preview = preview

    def icon_tile(container, key, *, miniature=False, active=False, hidden=False):
        back = c["ACCENT_DARK"] if active else c["CARD"]
        fore = c["MUTED"] if hidden else (c["WHITE"] if active else c["SECONDARY"])
        tile = tk.Frame(container, bg=back,
                        highlightthickness=1 if not miniature else 0,
                        highlightbackground=c["ACCENT"] if active else c["BORDER"],
                        width=(36 if miniature else 53),
                        height=(49 if miniature else 66),
                        cursor="hand2" if not miniature else "arrow",
                        takefocus=0 if miniature else 1)
        tile.pack_propagate(False)
        icon = tool_icons.label(tile, key, fore, back,
                                size=17 if miniature else 22)
        icon.pack(pady=(4 if miniature else 6, 1))
        caption = "Less" if key == "more" else menu_order.LABELS.get(key, key)
        title = tk.Label(tile, text=caption, bg=back, fg=fore,
                         font=("Segoe UI", 7),
                         anchor="center", justify="center")
        title.pack(fill="x")
        return tile, (tile, icon, title)

    def refresh_preview(order):
        for child in preview.winfo_children():
            child.destroy()
        current = menu_order.enabled_order(order, app.settings["visible_tabs"])
        first, others = mini_nav.plan_mini_icons(current)
        # Visualize actual Mini rows, including the fixed More/Less position.
        rows = [first, *others]
        for row_index, keys in enumerate(rows):
            bar = tk.Frame(preview, bg=c["INPUT"])
            bar.pack(fill="x", padx=3, pady=(3 if row_index == 0 else 0, 2))
            for key in keys:
                item, _widgets = icon_tile(bar, key, miniature=True,
                                            active=key == "more")
                item.pack(side="left", padx=(0, 1))
                if key == "more":
                    # Preview shows expanded rows and the corresponding toggle.
                    for child in item.winfo_children():
                        if isinstance(child, tk.Label) and child.cget("text") == "Less":
                            child.configure(text="Less")

    def cell_at(x, y):
        for key, tile in list(cells.items()):
            if not tile.winfo_exists():
                continue
            try:
                left, top = tile.winfo_rootx(), tile.winfo_rooty()
                if left <= x < left + tile.winfo_width() and (
                        top <= y < top + tile.winfo_height()):
                    return key
            except tk.TclError:
                continue
        return None

    def commit(moving, target):
        nonlocal selected
        old = menu_order.normalize(app.settings["menu_order"])
        updated = menu_order.move(old, moving, target)
        selected = None
        if updated != old:
            status.configure(text=menu_order.LABELS[moving] + " moved. Saved automatically.")
            app._set_menu_order(updated)
        else:
            refresh()

    def reset_order():
        nonlocal selected
        selected = None
        if menu_order.normalize(app.settings["menu_order"]) != list(menu_order.DEFAULT_ORDER):
            status.configure(text="Default icon order restored.")
            app._set_menu_order(list(menu_order.DEFAULT_ORDER))
        else:
            status.configure(text="The default menu order is already active.")
            refresh()

    def on_press(event, key):
        nonlocal drag
        drag = {"key": key, "x": event.x_root, "y": event.y_root,
                "moved": False}
        # Clicking on an image or its caption must focus the parent tile.
        if key in cells:
            cells[key].focus_set()

    def on_motion(event):
        nonlocal drag
        if drag is None:
            return
        if abs(event.x_root - drag["x"]) + abs(event.y_root - drag["y"]) >= 7:
            drag["moved"] = True
        if drag["moved"]:
            over = cell_at(event.x_root, event.y_root)
            for key, cell in cells.items():
                if cell.winfo_exists():
                    cell.configure(highlightbackground=(
                        c["ACCENT"] if over == key else c["BORDER"]))

    def on_release(event):
        nonlocal drag, selected
        action = drag
        drag = None
        if not action:
            return
        key = action["key"]
        if action["moved"]:
            destination = cell_at(event.x_root, event.y_root)
            if destination and destination != key:
                commit(key, destination)
            else:
                status.configure(text="Drop an icon on another icon to move it.")
                refresh()
            return
        if selected is None:
            selected = key
            status.configure(text=menu_order.LABELS[key] +
                             " selected. Click the destination icon.")
            refresh()
        elif selected == key:
            selected = None
            status.configure(text="Selection cleared.")
            refresh()
        else:
            commit(selected, key)

    def refresh():
        cells.clear()
        for child in grid.winfo_children():
            child.destroy()
        order = menu_order.normalize(app.settings["menu_order"])
        for index, key in enumerate(order):
            hidden = key != "settings" and key not in app.settings["visible_tabs"]
            tile, widgets = icon_tile(
                grid, key, active=(key == selected), hidden=hidden)
            tile.grid(row=index // 5, column=index % 5, sticky="ew",
                      padx=(0, 4) if index % 5 < 4 else 0,
                      pady=(0, 5))
            cells[key] = tile
            for widget in widgets:
                widget.configure(cursor="hand2")
                widget.bind("<ButtonPress-1>", lambda e, k=key: on_press(e, k))
                widget.bind("<B1-Motion>", on_motion)
                widget.bind("<ButtonRelease-1>", on_release)
            tile.bind("<Return>", lambda _e, k=key: keyboard_pick(k))
            tile.bind("<space>", lambda _e, k=key: keyboard_pick(k))
            design.Tooltip(tile,
                           menu_order.LABELS[key] +
                           (" (hidden, position preserved)" if hidden else ""),
                           app.theme)
        refresh_preview(order)

    def keyboard_pick(key):
        nonlocal selected
        if selected is None:
            selected = key
            status.configure(text=menu_order.LABELS[key] + " selected.")
            refresh()
        elif selected == key:
            selected = None
            refresh()
        else:
            commit(selected, key)
        return "break"

    refresh()
    return wrap
