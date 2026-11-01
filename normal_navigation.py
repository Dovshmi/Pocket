"""Normal-mode-only icon navigation, including compact overflow.

Mini and Dashboard are intentionally not imported or changed here.
All enabled tools remain available, even when the toolbar cannot fit them.
"""
from __future__ import annotations

import tkinter as tk

import pocket_design as design
import tool_icons

LABELS = {
    "notes": "Notes",
    "links": "Links",
    "ports": "Ports",
    "mac": "MAC",
    "commands": "CLI",
    "subnet": "Subnet",
    "clipboard": "Clip",
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
    """Install a focused two-row toolbar only inside the Normal shell."""
    parent.configure(bg=bg)
    parent.pack_propagate(False)
    total_width = max(0, 480 - 40)  # Normal is a fixed 480px popup.
    last_plan = None
    buttons = {}
    tiles = {}
    app.normal_icon_tabs = {}
    app.normal_overflow_keys = ()

    def render(selected):
        nonlocal last_plan, buttons, tiles
        keys = [key for key, _label in app.VISIBLE_TABS_REFERENCE
                if key in app.settings["visible_tabs"]]
        visible, hidden = plan_tabs(keys, selected, total_width)
        plan = visible, hidden
        if plan != last_plan:
            for child in parent.winfo_children():
                child.destroy()
            buttons = {}
            tiles = {}
            app.tab_buttons = buttons
            app.normal_icon_tabs = buttons
            app.normal_overflow_keys = hidden

            def add_tile(key, caption, action, *, width=TILE_WIDTH, more=False):
                shell = tk.Frame(parent, bg=bg, width=width, height=54,
                                 highlightthickness=0)
                shell.pack(side="left", padx=(0, GAP), anchor="center")
                shell.pack_propagate(False)
                tile = tk.Button(
                    shell, text=caption, command=action, compound="top",
                    bg=bg, fg=secondary, activebackground=panel,
                    activeforeground=white, relief="flat", bd=0,
                    highlightthickness=1, highlightbackground=bg,
                    highlightcolor=accent, font=("Segoe UI", 8),
                    padx=1, pady=3, cursor="hand2", takefocus=True)
                tile.pack(fill="both", expand=True)
                tile.image = tool_icons.icon_image(tile, "more" if more else key,
                                                  secondary, size=19)
                tile.configure(image=tile.image)
                tile.bind("<Return>", lambda _event: action())
                if more:
                    design.Tooltip(tile, "More enabled tools", app.theme)
                else:
                    design.Tooltip(tile, "Open " + FULL_NAMES.get(key, caption), app.theme)
                buttons[key] = tile
                tiles[key] = shell
                return tile

            for key in visible:
                add_tile(key, LABELS.get(key, key.title()),
                         lambda dest=key: app.show_tab(dest))
            if hidden:
                def open_more():
                    anchor = buttons["more"]
                    menu = tk.Menu(app.root, tearoff=False, bg=panel, fg=white,
                                   activebackground=accent_dark,
                                   activeforeground=white, bd=1, relief="flat")
                    menu.images = []
                    for key in app.normal_overflow_keys:
                        picture = tool_icons.icon_image(menu, key, accent, size=18)
                        menu.images.append(picture)
                        menu.add_command(
                            label="  " + FULL_NAMES.get(key, key.title()),
                            image=picture, compound="left",
                            command=lambda dest=key: app.show_tab(dest))
                    try:
                        menu.tk_popup(anchor.winfo_rootx(),
                                      anchor.winfo_rooty() + anchor.winfo_height() + 2)
                    finally:
                        menu.grab_release()

                add_tile("more", "More", open_more, more=True)
            # Settings stays at the right edge and never enters overflow.
            settings_tile = add_tile("settings", "Settings",
                                     lambda: app.show_tab("settings"),
                                     width=SETTINGS_WIDTH)
            settings_tile.master.pack_configure(side="right", padx=(GAP, 0))
            last_plan = plan

        for key, button in buttons.items():
            selected_now = key == selected or (key == "more" and selected in hidden)
            back = accent_dark if selected_now else bg
            fore = white if selected_now else muted
            button.configure(bg=back, fg=fore,
                             activebackground=panel)
            image_name = "more" if key == "more" else key
            button.image = tool_icons.icon_image(
                button, image_name, accent if selected_now else secondary, size=19)
            button.configure(image=button.image)
            tiles[key].configure(bg=back)

    app._normal_nav_refresh = render
    render(app.current_tab)
