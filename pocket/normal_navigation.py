"""Normal-mode responsive icon navigation with inline overflow.

Mini and Dashboard are intentionally not imported or changed here.
All enabled tools remain available, even when the toolbar cannot fit them.
"""
from __future__ import annotations

import tkinter as tk
from . import menu_order

from . import pocket_design as design
from . import tool_icons

LABELS = {
    "notes": "Notes",
    "links": "Links",
    "ports": "Ports",
    "mac": "MAC",
    "commands": "CLI",
    "subnet": "Subnet",
    "clipboard": "Clip",
    "reminders": "Remind",
    "extra": "Extra",
    "settings": "Settings",
}
FULL_NAMES = {
    "notes": "Notes & reminders",
    "links": "Shortcuts",
    "ports": "TCP Ports",
    "mac": "MAC Lookup",
    "commands": "Commands",
    "subnet": "Subnet Calculator",
    "clipboard": "Clipboard",
    "reminders": "Reminders",
    "extra": "Excel lookup",
    "settings": "Settings",
}
TILE_WIDTH = 52
SETTINGS_WIDTH = 56
GAP = 2


def plan_tabs(enabled, selected, available_width=440):
    """Return visible keys and hidden keys; always reserve room for Settings.

    Keep the active tool in the bar when overflow is required. Tool order is
    stable, and the overflow menu contains every hidden tool exactly once.
    Works with additional future tools without requiring a hard-coded five-tab
    limit. Deliberately does not modify the saved visible-tabs preference.
    """
    enabled = list(dict.fromkeys(key for key in enabled if key != "settings"))
    available_width = max(0, int(available_width))
    capacity = max(0, (available_width - SETTINGS_WIDTH - GAP) // (TILE_WIDTH + GAP))
    if len(enabled) > capacity:
        # Reserve a matching icon+label tile for More.
        capacity = max(0, (available_width - SETTINGS_WIDTH - TILE_WIDTH - 2 * GAP)
                       // (TILE_WIDTH + GAP))
    visible = enabled[:capacity]
    if selected in enabled and selected not in visible and capacity:
        visible[-1] = selected
        visible = [key for key in enabled if key in visible]
    hidden = [key for key in enabled if key not in visible]
    return tuple(visible), tuple(hidden)


def install(app, parent, *, bg, panel, accent, accent_dark, muted, secondary, white):
    """Responsive inline More/Less rows, without moving the selected tool."""
    parent.configure(bg=bg)
    parent.pack_propagate(False)
    total_width = 446
    last_plan = None
    buttons = {}
    tiles = {}
    rows = []
    drag = None
    app.normal_icon_tabs = {}
    app.normal_overflow_keys = ()

    def expand():
        app._normal_nav_expanded = not getattr(app, "_normal_nav_expanded", False)
        update_rows()
        style(app.current_tab)

    def update_rows():
        expanded = bool(app.normal_overflow_keys and
                        getattr(app, "_normal_nav_expanded", False))
        for row in rows[1:]:
            if expanded:
                row.pack(fill="x")
            else:
                row.pack_forget()
        parent.configure(height=59 + (54 * (len(rows) - 1) if expanded else 0))
        if "more" in buttons:
            buttons["more"].configure(text="Less" if expanded else "More")

    def style(selected):
        for key, button in buttons.items():
            selected_now = key == selected or (key == "more" and (
                getattr(app, "_normal_nav_expanded", False) or
                selected in app.normal_overflow_keys))
            back = accent_dark if selected_now else bg
            button.configure(bg=back, fg=white if selected_now else muted,
                             activebackground=panel)
            button.image = tool_icons.icon_image(
                button, key, accent if selected_now else secondary, size=19)
            button.configure(image=button.image)
            tiles[key].configure(bg=back)

    def hit(x, y):
        for key, shell in tiles.items():
            if shell.winfo_ismapped() and (
                    shell.winfo_rootx() <= x < shell.winfo_rootx() + shell.winfo_width()
                    and shell.winfo_rooty() <= y < shell.winfo_rooty() + shell.winfo_height()):
                return key
        return None

    def press(event, key):
        nonlocal drag
        drag = (key, event.x_root, event.y_root, False)
        return "break"

    def motion(event):
        nonlocal drag
        if drag is None:
            return "break"
        key, x, y, moved = drag
        if moved or abs(event.x_root - x) + abs(event.y_root - y) >= 7:
            drag = key, x, y, True
            target = hit(event.x_root, event.y_root)
            for dest, button in buttons.items():
                button.configure(highlightbackground=accent if
                                 dest == target and dest not in (key, "more") else bg)
        return "break"

    def release(event, key, action):
        nonlocal drag
        previous, drag = drag, None
        for button in buttons.values():
            button.configure(highlightbackground=bg)
        if previous is None or previous[0] != key:
            return "break"
        if previous[3] or abs(event.x_root - previous[1]) + abs(event.y_root - previous[2]) >= 7:
            target = hit(event.x_root, event.y_root)
            if target and target not in (key, "more"):
                app._set_menu_order(menu_order.move(
                    app.settings["menu_order"], key, target,
                    after=event.x_root >= tiles[target].winfo_rootx() +
                    tiles[target].winfo_width() / 2))
        elif hit(event.x_root, event.y_root) == key:
            action()
        return "break"

    def render(selected):
        nonlocal last_plan, buttons, tiles, rows
        keys = menu_order.enabled_order(
            app.settings["menu_order"], app.settings["visible_tabs"])
        # Settings is always accessible, but its position follows the saved
        # menu order rather than being hardwired to the right edge.
        visible, hidden = plan_tabs(keys, None, total_width)
        first_keys = []
        for key in keys:
            if key in visible or key == "settings":
                first_keys.append(key)
            elif "more" not in first_keys:
                first_keys.append("more")
        plan = tuple(first_keys), hidden, max(1, total_width // (TILE_WIDTH + GAP))
        if plan != last_plan:
            last_plan = plan
            for child in parent.winfo_children():
                child.destroy()
            buttons = {}
            tiles = {}
            rows = []
            app.tab_buttons = buttons
            app.normal_icon_tabs = buttons
            app.normal_overflow_keys = hidden
            if not hidden:
                app._normal_nav_expanded = False

            def new_row():
                row = tk.Frame(parent, bg=bg, height=54)
                row.pack_propagate(False)
                rows.append(row)
                return row

            def add_tile(row, key, caption, action, width=TILE_WIDTH):
                shell = tk.Frame(row, bg=bg, width=width, height=54,
                                 highlightthickness=0)
                shell.pack(side="left", fill="x", expand=True, padx=(0, GAP))
                shell.pack_propagate(False)
                tile = tk.Button(
                    shell, text=caption, command=action, compound="top",
                    bg=bg, fg=secondary, activebackground=panel,
                    activeforeground=white, relief="flat", bd=0,
                    highlightthickness=1, highlightbackground=bg,
                    highlightcolor=accent, font=("Segoe UI", 8),
                    padx=1, pady=3, cursor="hand2", takefocus=True)
                tile.pack(fill="both", expand=True)
                tile.bind("<Return>", lambda _event: action())
                if key != "more":
                    tile.bind("<ButtonPress-1>", lambda event: press(event, key))
                    tile.bind("<B1-Motion>", motion)
                    tile.bind("<ButtonRelease-1>", lambda event: release(event, key, action))
                    tile.bind("<Button-3>", lambda event: app._mini_nav_context_menu(event, key))
                design.Tooltip(tile, "Expand or collapse tools" if key == "more"
                               else "Open " + FULL_NAMES.get(key, caption), app.theme)
                buttons[key] = tile
                tiles[key] = shell

            first = new_row()
            first.pack(fill="x")
            for key in first_keys:
                if key == "more":
                    add_tile(first, key, "More", expand)
                else:
                    add_tile(first, key, LABELS.get(key, key.title()),
                             lambda dest=key: app.show_tab(dest),
                             SETTINGS_WIDTH if key == "settings" else TILE_WIDTH)
            capacity = plan[2]
            for offset in range(0, len(hidden), capacity):
                row = new_row()
                for key in hidden[offset:offset + capacity]:
                    add_tile(row, key, LABELS.get(key, key.title()),
                             lambda dest=key: app.show_tab(dest))
            update_rows()
        style(selected)

    def resized(event):
        nonlocal total_width
        if event.width != total_width and event.width > 1:
            total_width = event.width
            render(app.current_tab)

    app._normal_nav_refresh = render
    parent.bind("<Configure>", resized)
    render(app.current_tab)
