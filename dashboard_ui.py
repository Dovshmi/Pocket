"""Pocket's optional desktop dashboard chrome.

This is a presentation layer only: notes, CLI, network actions, data storage and
tray behavior remain implemented by PocketDesk in app.pyw. No network calls.
"""
from __future__ import annotations

import tkinter as tk
import pocket_design as design
import tool_icons

NAVIGATION = (
    ("home", "⌂", "Overview"),
    ("notes", "▤", "Notes"),
    ("links", "↗", "Shortcuts"),
    ("ports", "⇄", "TCP Ports"),
    ("mac", "▦", "MAC Lookup"),
    ("commands", ">_", "Commands"),
    ("subnet", "⌗", "Subnet Calculator"),
    ("clipboard", "▣", "Clipboard"),
    ("settings", "⚙", "Settings"),
)

TITLES = {
    "home": ("Your workspace", "Everything you use often, one shortcut away."),
    "notes": ("Notes", "Your locally saved notes and scheduled reminders."),
    "links": ("Shortcuts", "Launch websites, folders and files from one place."),
    "ports": ("TCP port checker", "Test network connectivity only when you choose."),
    "mac": ("MAC lookup", "Identify manufacturers using locally cached IEEE data."),
    "commands": ("Command library", "Search, edit and copy CLI commands. Never execute them."),
    "subnet": ("Subnet calculator", "Explore IPv4 masks, ranges and subnet divisions."),
    "clipboard": ("Clipboard history", "Session-only copied text; never saved to disk."),
    "settings": ("Preferences", "Choose your layout, theme and visible tools."),
}


def _label(parent, text, c, *, size=10, strong=False, bg=None, fg=None, **options):
    return tk.Label(parent, text=text, bg=bg or c["PANEL"],
                    fg=fg or c["WHITE"], font=("Segoe UI", size, "bold" if strong else "normal"),
                    **options)


def _card(parent, c):
    return tk.Frame(parent, bg=c["PANEL"], highlightbackground=c["BORDER"],
                    highlightthickness=1, bd=0)


def _link(parent, text, callback, c, *, emphasis=False, padx=13, pady=9):
    bg = c["ACCENT_DARK"] if emphasis else c["CARD"]
    fg = c["ACCENT"] if emphasis else c["WHITE"]
    widget = _label(parent, text, c, size=10, strong=emphasis, bg=bg, fg=fg,
                    padx=padx, pady=pady, cursor="hand2")
    widget.bind("<Button-1>", lambda _event: callback())
    widget.bind("<Enter>", lambda _event: widget.configure(bg=c["CARD_HOVER"]))
    widget.bind("<Leave>", lambda _event: widget.configure(bg=bg))
    return widget


def build_shell(app, colors):
    """Large desktop layout, reusing Pocket's exact existing tool pages."""
    c = colors
    app._dashboard_colors = c
    root = app.root
    outer = tk.Frame(root, bg=c["BG"], highlightbackground=c["BORDER"], highlightthickness=1)
    outer.pack(fill="both", expand=True)

    # Persistent left rail: all enabled tools are visible, no MORE menu.
    side = tk.Frame(outer, bg=c["SIDEBAR"], width=228)
    side.pack(side="left", fill="y")
    side.pack_propagate(False)
    brand = tk.Frame(side, bg=c["SIDEBAR"], height=82, cursor="fleur")
    brand.pack(fill="x", padx=18, pady=(17, 9))
    brand.pack_propagate(False)

    app._header_photo = tk.PhotoImage(
        file=str(app.theme_icons[app.theme]["png"])).subsample(12, 12)
    app.header_icon = tk.Label(brand, image=app._header_photo, bg=c["SIDEBAR"], cursor="hand2")
    app.header_icon.pack(side="left", padx=(0, 9), anchor="n", pady=2)
    app.header_icon.bind("<Button-1>", app._show_theme_menu)
    app.header_icon.bind("<Button-3>", app._show_theme_menu)
    logo_text = tk.Frame(brand, bg=c["SIDEBAR"])
    logo_text.pack(side="left", fill="both")
    brand_name = _label(logo_text, "Pocket", c, size=19, strong=True, bg=c["SIDEBAR"])
    brand_name.pack(anchor="w")
    _label(logo_text, "DESKTOP TOOLBOX", c, size=8, bg=c["SIDEBAR"],
           fg=c["MUTED"]).pack(anchor="w", pady=(1, 0))

    for handle in (brand, brand_name, logo_text):
        handle.bind("<ButtonPress-1>", app._begin_window_drag)
        handle.bind("<B1-Motion>", app._continue_window_drag)
        handle.bind("<ButtonRelease-1>", app._finish_window_drag)
        handle.bind("<Button-3>", app._show_header_menu)

    _label(side, "WORKSPACE", c, size=8, strong=True, bg=c["SIDEBAR"],
           fg=c["MUTED"]).pack(anchor="w", padx=23, pady=(14, 10))
    app.tab_buttons = {}
    app.dashboard_nav = {}
    for key, glyph, caption in NAVIGATION:
        if key not in ("home", "settings") and key not in app.settings["visible_tabs"]:
            continue
        if key == "settings":
            tk.Frame(side, bg=c["BORDER"], height=1).pack(fill="x", padx=18, pady=(14, 12))
        selected = key == app.current_tab
        entry = tk.Button(
            side, text=f"     {caption}", command=lambda tab=key: app.show_tab(tab),
            bg=c["ACCENT_DARK"] if selected else c["SIDEBAR"],
            fg=c["WHITE"] if selected else c["SECONDARY"],
            activebackground=c["CARD_HOVER"], activeforeground=c["WHITE"],
            relief="flat", bd=0, highlightthickness=1,
            highlightbackground=c["ACCENT_DARK"] if selected else c["SIDEBAR"],
            highlightcolor=c["ACCENT"], takefocus=True,
            font=("Segoe UI", 10, "bold" if selected else "normal"),
            cursor="hand2", padx=12, pady=10, anchor="w")
        entry.pack(fill="x", padx=12, pady=2)
        entry.tool_icon = tool_icons.icon_image(entry, key, c["ACCENT"] if selected else c["SECONDARY"], 19)
        entry.configure(image=entry.tool_icon, compound="left")
        design.Tooltip(entry, TITLES.get(key, (caption, caption))[1], app.theme)
        app.dashboard_nav[key] = entry

    tk.Frame(side, bg=c["SIDEBAR"]).pack(fill="both", expand=True)
    status = _card(side, c)
    status.pack(fill="x", padx=15, pady=(0, 19))
    _label(status, "●  Local-first", c, fg=c["SUCCESS"], size=10, strong=True
           ).pack(anchor="w", padx=12, pady=(10, 1))
    _label(status, "Tools stay on this computer", c, fg=c["MUTED"], size=8
           ).pack(anchor="w", padx=12, pady=(0, 11))

    workspace = tk.Frame(outer, bg=c["BG"])
    workspace.pack(side="left", fill="both", expand=True)
    header = tk.Frame(workspace, bg=c["BG"], height=77, cursor="fleur")
    header.pack(fill="x", padx=29, pady=(9, 0))
    header.pack_propagate(False)
    heading = tk.Frame(header, bg=c["BG"], cursor="fleur")
    heading.pack(side="left", fill="y", expand=True, anchor="w")
    app.dashboard_heading = _label(heading, "Your workspace", c, size=19, strong=True,
                                   bg=c["BG"], anchor="w")
    app.dashboard_heading.pack(anchor="w", pady=(6, 0))
    app.dashboard_subtitle = _label(heading, "Your everyday tools", c, size=9,
                                    bg=c["BG"], fg=c["MUTED"], anchor="w")
    app.dashboard_subtitle.pack(anchor="w", pady=(3, 0))
    for widget in (header, heading, app.dashboard_heading, app.dashboard_subtitle):
        widget.bind("<ButtonPress-1>", app._begin_window_drag)
        widget.bind("<B1-Motion>", app._continue_window_drag)
        widget.bind("<ButtonRelease-1>", app._finish_window_drag)
        widget.bind("<Button-3>", app._show_header_menu)

    _link(header, "×", app.hide, c, padx=12, pady=4).pack(side="right", padx=(7, 0))
    if app.settings["extra_mini_enabled"]:
        _link(header, "▾ Extra Mini", app._return_to_compact, c, emphasis=True,
              padx=8, pady=6).pack(side="right", padx=3)
    app.pin_button = _link(header, "PIN", app.toggle_pin, c, padx=12, pady=6)
    app.pin_button.pack(side="right", padx=3)
    app.shortcut_hint = _link(header, app._hotkey_hint(), lambda: app._open_hotkey_picker(), c,
                              padx=12, pady=6)
    app.shortcut_hint.pack(side="right", padx=3)
    design.button(header, "⌕  Search", app._open_global_search,
                  app.theme, primary=True, compact=True).pack(side="right", padx=5)

    tk.Frame(workspace, bg=c["BORDER"], height=1).pack(fill="x")
    app.body = tk.Frame(workspace, bg=c["BG"])
    app.body.pack(fill="both", expand=True, padx=27, pady=(20, 21))
    app._mini_root_body = app.body
    style_nav(app, app.current_tab)


def _find_command(app):
    if "commands" not in app.settings["visible_tabs"]:
        app.show_tab("settings")
        return
    app.show_tab("commands")
    app._focus_command_search()


def _hover_nav(app, row, glyph, title, key, hover):
    if key == app.current_tab:
        return
    if not row.winfo_exists():
        return
    c = app._dashboard_colors
    bg = c["CARD"] if hover else c["SIDEBAR"]
    for widget in (row, glyph, title):
        widget.configure(bg=bg)


def style_nav(app, selected):
    """Reflect the selected menu in a keyboard-accessible sidebar."""
    c = app._dashboard_colors
    for key, button in getattr(app, "dashboard_nav", {}).items():
        active = key == selected
        button.tool_icon = tool_icons.icon_image(button, key, c["ACCENT"] if active else c["SECONDARY"], 19)
        button.configure(image=button.tool_icon, bg=c["ACCENT_DARK"] if active else c["SIDEBAR"],
                         fg=c["WHITE"] if active else c["SECONDARY"],
                         highlightbackground=c["ACCENT_DARK"] if active else c["SIDEBAR"],
                         font=("Segoe UI", 10, "bold" if active else "normal"))
    main, subtitle = TITLES.get(selected, TITLES["home"])
    app.dashboard_heading.configure(text=main)
    app.dashboard_subtitle.configure(text=subtitle)


def _dashboard_tile(parent, app, c, icon, title, detail, destination, row, col):
    frame = _card(parent, c)
    frame.grid(row=row, column=col, sticky="nsew", padx=(0, 12) if col == 0 else (0, 0),
               pady=(0, 12))
    top = tk.Frame(frame, bg=c["PANEL"])
    top.pack(fill="x", padx=17, pady=(16, 6))
    tool_icons.label(top, destination, c["ACCENT"], c["PANEL"], size=25).pack(side="left", padx=(0, 11))
    _label(top, title, c, size=12, strong=True, anchor="w").pack(side="left")
    _label(frame, detail, c, size=9, fg=c["MUTED"], anchor="w",
           justify="left", wraplength=320).pack(fill="x", padx=17)
    design.button(frame, "Open  →", lambda: app.show_tab(destination), app.theme,
                  primary=True, compact=True).pack(anchor="w", padx=17, pady=(11, 17))


def build_home(app):
    """Overview uses real saved counts and functional navigation, no demo data."""
    c = app._dashboard_colors
    body = app.body
    hero = _card(body, c)
    hero.pack(fill="x", pady=(0, 18))
    hero_left = tk.Frame(hero, bg=c["PANEL"])
    hero_left.pack(side="left", fill="both", expand=True, padx=21, pady=20)
    _label(hero_left, "YOUR DESKTOP. ORGANIZED.", c, fg=c["ACCENT"], size=9,
           strong=True).pack(anchor="w")
    _label(hero_left, "Welcome to Pocket", c, size=22, strong=True
           ).pack(anchor="w", pady=(5, 4))
    _label(hero_left, "Choose a tool card below to open its working page.",
           c, size=10, fg=c["SECONDARY"]).pack(anchor="w")
    if "notes" in app.settings["visible_tabs"]:
        design.button(hero, "Open Notes  →", lambda: app.show_tab("notes"), app.theme,
                      primary=True).pack(side="right", padx=20)

    _label(body, "AT A GLANCE  ·  Counts are informational, not buttons", c,
           size=8, bg=c["BG"], fg=c["MUTED"]).pack(anchor="w", pady=(0, 7))
    stats = tk.Frame(body, bg=c["BG"])
    stats.pack(fill="x", pady=(0, 18))
    values = (
        (str(len(app.data.get("notes", []))), "Saved notes"),
        (str(len(app.data.get("links", []))), "Shortcuts"),
        (str(len(app.command_library)), "CLI references"),
        (str(len(app.clipboard_items)), "Clipboard items"),
    )
    for i, (value, caption) in enumerate(values):
        stats.columnconfigure(i, weight=1, uniform="stat")
        frame = _card(stats, c)
        frame.grid(row=0, column=i, sticky="nsew", padx=(0, 10) if i < 3 else 0)
        _label(frame, value, c, size=20, strong=True, fg=c["ACCENT"]
               ).pack(anchor="w", padx=17, pady=(13, 1))
        _label(frame, caption, c, size=9, fg=c["MUTED"]
               ).pack(anchor="w", padx=17, pady=(0, 14))

    _label(body, "OPEN A TOOL  ·  SELECT OPEN TO START", c, size=9, strong=True, bg=c["BG"],
           fg=c["SECONDARY"]).pack(anchor="w", pady=(0, 12))
    all_tools = (
        ("⌘", "CLI command library", "Search and copy commands without running them.", "commands"),
        ("▤", "Notes and reminders", "Your notes, phone fields and scheduled alerts.", "notes"),
        ("⌗", "Subnet calculator", "IPv4 address ranges, masks and subnet division.", "subnet"),
        ("↗", "Shortcuts", "Open your saved local folders and websites.", "links"),
        ("⇄", "TCP port checks", "Diagnose network connectivity when you request it.", "ports"),
        ("▦", "MAC vendor lookup", "Identify vendors with your locally cached IEEE data.", "mac"),
        ("▣", "Clipboard history", "Search your current session's copied text.", "clipboard"),
    )
    visible = [t for t in all_tools if t[3] in app.settings["visible_tabs"]]
    grid = tk.Frame(body, bg=c["BG"])
    grid.pack(fill="x")
    grid.columnconfigure(0, weight=1, uniform="tools")
    grid.columnconfigure(1, weight=1, uniform="tools")
    for index, (icon, title, detail, key) in enumerate(visible):
        _dashboard_tile(grid, app, c, icon, title, detail, key, index // 2, index % 2)
    if not visible:
        design.empty_state(body, "No tools enabled", "Show tools in Settings to see quick access here.", app.theme)
    _label(body, "Pocket stores notes and settings locally. Network requests happen only "
           "when you invoke a tool that needs them.", c, size=9, bg=c["BG"],
           fg=c["MUTED"], anchor="w").pack(fill="x", pady=(9, 0))
