"""Compact, fully wired Pocket desktop dashboard.

This is a Tkinter presentation-only mode. All feature pages, data stores, and
network actions remain owned by app.PocketDesk: nothing is copied or simulated.
"""
from __future__ import annotations

import tkinter as tk

# Every real Pocket menu is reachable without an overflow menu.
NAVIGATION = (
    ("home", "⌂", "Home"),
    ("notes", "▤", "Notes"),
    ("links", "↗", "Shortcuts"),
    ("ports", "⇄", "TCP Ports"),
    ("mac", "▦", "MAC Lookup"),
    ("commands", "⌘", "Commands"),
    ("subnet", "⌗", "Subnet"),
    ("clipboard", "▣", "Clipboard"),
    ("settings", "⚙", "Settings"),
)

PAGES = {
    "home": ("Overview", "Your tools, one click away"),
    "notes": ("Notes", "Notes, phone numbers and reminders"),
    "links": ("Shortcuts", "Files, folders and websites"),
    "ports": ("TCP Ports", "On-demand connectivity checks"),
    "mac": ("MAC Lookup", "IEEE vendor lookup"),
    "commands": ("Commands", "Search, edit and copy CLI references"),
    "subnet": ("Subnet", "IPv4 networks and address ranges"),
    "clipboard": ("Clipboard", "Session-only copied text"),
    "settings": ("Settings", "Customize Pocket"),
}

TOOL_DESCRIPTIONS = {
    "notes": "Write and pin notes, schedule reminders",
    "links": "Open saved files, folders and websites",
    "ports": "Check TCP ports on demand",
    "mac": "Identify MAC address manufacturers",
    "commands": "Find and copy CLI commands safely",
    "subnet": "Calculate and split IPv4 networks",
    "clipboard": "Find text copied in this session",
}


def visible_navigation(visible_tabs):
    """Fixed navigation order, honoring menu visibility and always showing Settings."""
    allowed = set(visible_tabs)
    return tuple(item for item in NAVIGATION
                 if item[0] in ("home", "settings") or item[0] in allowed)


def _label(parent, text, c, *, size=10, bold=False, bg=None, fg=None, **kwargs):
    return tk.Label(parent, text=text, bg=bg if bg is not None else c["PANEL"],
                    fg=fg if fg is not None else c["WHITE"],
                    font=("Segoe UI", size, "bold" if bold else "normal"), **kwargs)


def _button(parent, caption, command, c, *, primary=False, **kwargs):
    return tk.Button(
        parent, text=caption, command=command,
        bg=c["ACCENT_DARK"] if primary else c["CARD"],
        fg=c["ACCENT"] if primary else c["WHITE"],
        activebackground=c["CARD_HOVER"], activeforeground=c["WHITE"],
        relief="flat", bd=0, highlightthickness=0, takefocus=1,
        cursor="hand2", font=("Segoe UI", 9, "bold" if primary else "normal"),
        padx=11, pady=7, **kwargs,
    )


def _card(parent, c):
    return tk.Frame(parent, bg=c["PANEL"], bd=0, highlightthickness=1,
                    highlightbackground=c["BORDER"])


def _go_commands(app):
    if "commands" not in app.settings["visible_tabs"]:
        app.show_tab("settings")
        return
    app.show_tab("commands")
    app._focus_command_search()


def build_shell(app, colors):
    """Compact 820px-wide shell; reuses existing tool builders unchanged."""
    c = dict(colors)
    c["SIDEBAR"] = c["INPUT"]
    c["SUCCESS"] = "#50D6AD"
    app._compact_colors = c
    root = app.root

    outer = tk.Frame(root, bg=c["BG"], bd=0, highlightthickness=1,
                     highlightbackground=c["BORDER"])
    outer.pack(fill="both", expand=True)

    rail = tk.Frame(outer, width=144, bg=c["SIDEBAR"])
    rail.pack(side="left", fill="y")
    rail.pack_propagate(False)

    brand = tk.Frame(rail, bg=c["SIDEBAR"], height=64, cursor="fleur")
    brand.pack(fill="x", padx=12, pady=(12, 4))
    brand.pack_propagate(False)
    app._header_photo = tk.PhotoImage(
        file=str(app.theme_icons[app.theme]["png"])).subsample(16, 16)
    app.header_icon = tk.Label(brand, image=app._header_photo, bg=c["SIDEBAR"],
                               cursor="hand2")
    app.header_icon.pack(side="left", padx=(1, 7), pady=8)
    app.header_icon.bind("<Button-1>", app._show_theme_menu)
    app.header_icon.bind("<Button-3>", app._show_theme_menu)
    brand_title = _label(brand, "Pocket", c, bold=True, size=14, bg=c["SIDEBAR"],
                         anchor="w", cursor="fleur")
    brand_title.pack(side="left", fill="y")
    for target in (brand, brand_title):
        target.bind("<ButtonPress-1>", app._begin_window_drag)
        target.bind("<B1-Motion>", app._continue_window_drag)
        target.bind("<ButtonRelease-1>", app._finish_window_drag)
        target.bind("<Button-3>", app._show_header_menu)

    _label(rail, "WORKSPACE", c, size=8, bold=True, fg=c["MUTED"],
           bg=c["SIDEBAR"], anchor="w").pack(fill="x", padx=17, pady=(10, 5))

    app.tab_buttons = {}
    app.compact_nav = {}
    for key, glyph, name in visible_navigation(app.settings["visible_tabs"]):
        if key == "settings":
            tk.Frame(rail, height=1, bg=c["BORDER"]).pack(
                fill="x", padx=13, pady=(8, 6))
        button = tk.Button(
            rail, text=f"{glyph}   {name}", command=lambda k=key: app.show_tab(k),
            bg=c["SIDEBAR"], fg=c["SECONDARY"], activebackground=c["CARD_HOVER"],
            activeforeground=c["WHITE"], font=("Segoe UI", 9), anchor="w",
            padx=11, pady=8, relief="flat", bd=0, highlightthickness=0,
            takefocus=1, cursor="hand2"
        )
        button.pack(fill="x", padx=9, pady=1)
        app.compact_nav[key] = button

    tk.Frame(rail, bg=c["SIDEBAR"]).pack(fill="both", expand=True)
    bottom = _card(rail, c)
    bottom.pack(fill="x", padx=10, pady=(8, 12))
    _label(bottom, "●  Local data", c, size=9, bold=True,
           fg=c["SUCCESS"]).pack(anchor="w", padx=10, pady=(10, 2))
    _label(bottom, "Only when needed", c, size=8,
           fg=c["MUTED"]).pack(anchor="w", padx=10, pady=(0, 10))

    main = tk.Frame(outer, bg=c["BG"])
    main.pack(side="left", fill="both", expand=True)
    top = tk.Frame(main, height=66, bg=c["BG"], cursor="fleur")
    top.pack(fill="x", padx=20, pady=(5, 0))
    top.pack_propagate(False)

    title_block = tk.Frame(top, bg=c["BG"], cursor="fleur")
    title_block.pack(side="left", fill="both", expand=True)
    app.compact_heading = _label(title_block, "Overview", c, bg=c["BG"],
                                 bold=True, size=17, anchor="w", cursor="fleur")
    app.compact_heading.pack(anchor="w", pady=(5, 0))
    app.compact_subtitle = _label(title_block, "Your tools, one click away", c,
                                  bg=c["BG"], fg=c["MUTED"],
                                  size=9, anchor="w", cursor="fleur")
    app.compact_subtitle.pack(anchor="w", pady=(2, 0))
    for handle in (top, title_block, app.compact_heading, app.compact_subtitle):
        handle.bind("<ButtonPress-1>", app._begin_window_drag)
        handle.bind("<B1-Motion>", app._continue_window_drag)
        handle.bind("<ButtonRelease-1>", app._finish_window_drag)
        handle.bind("<Button-3>", app._show_header_menu)

    _button(top, "×", app.hide, c, padx=9, pady=3).pack(side="right", padx=(5, 0))
    app.pin_button = _button(top, "PINNED" if app.pinned else "PIN",
                             app.toggle_pin, c, primary=app.pinned, padx=8, pady=5)
    app.pin_button.pack(side="right", padx=(4, 0))
    app.shortcut_hint = _button(top, app._hotkey_hint(), app._open_hotkey_picker,
                                c, padx=8, pady=5)
    app.shortcut_hint.pack(side="right", padx=(4, 0))
    _button(top, "⌕  CLI", lambda: _go_commands(app),
            c, primary=True, padx=9, pady=5).pack(side="right", padx=(4, 0))

    tk.Frame(main, height=1, bg=c["BORDER"]).pack(fill="x")

    app.body = tk.Frame(main, bg=c["BG"])
    app.body.pack(fill="both", expand=True, padx=20, pady=(14, 16))
    app._mini_root_body = app.body
    style_nav(app, app.current_tab)


def style_nav(app, key):
    """Refresh selection and heading whenever any real tool is opened."""
    c = app._compact_colors
    for page, button in getattr(app, "compact_nav", {}).items():
        active = key == page
        button.configure(
            bg=c["ACCENT_DARK"] if active else c["SIDEBAR"],
            fg=c["ACCENT"] if active else c["SECONDARY"],
            font=("Segoe UI", 9, "bold" if active else "normal"))
    title, subtitle = PAGES.get(key, PAGES["home"])
    app.compact_heading.configure(text=title)
    app.compact_subtitle.configure(text=subtitle)


def _tool_card(parent, app, c, key, icon, title, description, r, col):
    card = _card(parent, c)
    card.grid(row=r, column=col, sticky="nsew",
              padx=(0, 10) if col == 0 else 0, pady=(0, 9))
    row = tk.Frame(card, bg=c["PANEL"])
    row.pack(fill="x", padx=12, pady=(12, 4))
    _label(row, icon, c, size=16, bold=True, fg=c["ACCENT"]
           ).pack(side="left", padx=(0, 10))
    _label(row, title, c, size=10, bold=True, anchor="w"
           ).pack(side="left", fill="x", expand=True)
    _label(card, description, c, size=8, fg=c["MUTED"],
           anchor="w", wraplength=255, justify="left"
           ).pack(fill="x", padx=12, pady=(0, 6))
    _button(card, "Open  →", lambda: app.show_tab(key), c,
            primary=True, padx=9, pady=3
            ).pack(anchor="w", padx=12, pady=(0, 11))


def build_home(app):
    """Actionable, scroll-friendly home page with genuine local data only."""
    c = app._compact_colors
    body = app.body
    hero = _card(body, c)
    hero.pack(fill="x", pady=(0, 12))
    intro = tk.Frame(hero, bg=c["PANEL"])
    intro.pack(side="left", fill="both", expand=True, padx=16, pady=13)
    _label(intro, "POCKET / QUICK ACCESS", c, size=8, bold=True,
           fg=c["ACCENT"]).pack(anchor="w")
    _label(intro, "Ready when you need it.", c, size=17, bold=True
           ).pack(anchor="w", pady=(4, 0))
    _label(intro, "The same seven tools, in a smaller workspace.", c,
           fg=c["MUTED"], size=9).pack(anchor="w", pady=(3, 0))
    if "notes" in app.settings["visible_tabs"]:
        _button(hero, "+ Note", app.add_note, c,
                primary=True, padx=12, pady=7).pack(side="right", padx=14)

    totals = tk.Frame(body, bg=c["BG"])
    totals.pack(fill="x", pady=(0, 12))
    stats = (
        (len(app.data.get("notes", [])), "Notes"),
        (len(app.data.get("links", [])), "Shortcuts"),
        (len(app.command_library), "Commands"),
    )
    for i, (number, label) in enumerate(stats):
        totals.columnconfigure(i, weight=1, uniform="stat")
        item = _card(totals, c)
        item.grid(row=0, column=i, sticky="nsew",
                  padx=(0, 9) if i < len(stats) - 1 else 0)
        _label(item, str(number), c, size=17, bold=True, fg=c["ACCENT"]
               ).pack(side="left", padx=(12, 8), pady=9)
        _label(item, label, c, size=9, fg=c["SECONDARY"]
               ).pack(side="left", pady=9)

    _label(body, "YOUR TOOLS", c, size=9, bold=True, bg=c["BG"],
           fg=c["SECONDARY"]).pack(anchor="w", pady=(0, 9))
    grid = tk.Frame(body, bg=c["BG"])
    grid.pack(fill="x")
    grid.columnconfigure(0, weight=1, uniform="actions")
    grid.columnconfigure(1, weight=1, uniform="actions")
    visible = [
        (key, glyph, name) for key, glyph, name
        in visible_navigation(app.settings["visible_tabs"])
        if key not in ("home", "settings")
    ]
    for index, (key, glyph, name) in enumerate(visible):
        _tool_card(grid, app, c, key, glyph, name,
                   TOOL_DESCRIPTIONS[key], index // 2, index % 2)

    _label(body, "Pocket doesn't execute CLI commands. Clipboard history is "
           "session-only. Network access is limited to actions you initiate.",
           c, bg=c["BG"], fg=c["MUTED"], size=8, justify="left",
           wraplength=590, anchor="w").pack(fill="x", pady=(5, 5))
