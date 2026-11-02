"""Dedicated Dashboard Settings, designed for a wide workspace.

The common settings_ui remains authoritative for Normal and Mini. No new
settings, storage, network operations or preferences are introduced.
"""
from __future__ import annotations

import tkinter as tk

from . import icon_themes as themes
from . import pocket_design as design
from . import settings_ui

FONT = "Segoe UI"

MODE_DETAILS = (
    ("normal", "Normal", "Classic popup", "normal"),
    ("mini", "Mini", "Compact window", "notes"),
    ("dashboard", "Dashboard", "Wide workspace", "home"),
)


def _label(parent, value, colors, *, size=9, weight="normal", muted=False, **kwargs):
    return tk.Label(parent, text=value, bg=colors["PANEL"],
                    fg=colors["MUTED"] if muted else colors["WHITE"],
                    font=(FONT, size, weight), **kwargs)


def _section(parent, colors, title, description, *, row, col):
    panel = tk.Frame(parent, bg=colors["PANEL"], highlightthickness=1,
                     highlightbackground=colors["BORDER"])
    panel.grid(row=row, column=col, sticky="new",
               padx=(0, 8) if col == 0 else (8, 0), pady=(0, 13))
    header = tk.Frame(panel, bg=colors["PANEL"])
    header.pack(fill="x", padx=14, pady=(12, 8))
    _label(header, title, colors, size=11, weight="bold", anchor="w"
           ).pack(fill="x")
    if description:
        _label(header, description, colors, size=8, muted=True,
               wraplength=365, justify="left", anchor="w"
               ).pack(fill="x", pady=(4, 0))
    return panel


def _toggle(parent, app, colors, key, heading, description, checked, callback):
    """Themed, keyboard-accessible native checkbox; same persistence callback."""
    row = tk.Frame(parent, bg=colors["PANEL"])
    row.pack(fill="x", padx=13, pady=5)
    enabled = tk.BooleanVar(value=bool(checked))
    control = tk.Checkbutton(
        row, text=heading, variable=enabled,
        command=lambda: callback(enabled.get()), anchor="w",
        bg=colors["PANEL"], fg=colors["WHITE"],
        selectcolor=colors["INPUT"], activebackground=colors["PANEL"],
        activeforeground=colors["ACCENT"], font=(FONT, 9, "bold"),
        relief="flat", highlightthickness=0, padx=0, pady=2,
        cursor="hand2", takefocus=True)
    control.pack(fill="x")
    _label(row, description, colors, size=8, muted=True,
           anchor="w", justify="left", wraplength=365
           ).pack(fill="x", padx=(19, 0), pady=(1, 3))
    app.dashboard_settings_controls[key] = control
    return control


def _display(panel, app, colors):
    modes = tk.Frame(panel, bg=colors["PANEL"])
    modes.pack(fill="x", padx=13, pady=(0, 8))
    for col, (mode, title, detail, _destination) in enumerate(MODE_DETAILS):
        modes.grid_columnconfigure(col, weight=1, uniform="modes")
        selected = app.settings["display_mode"] == mode
        box = tk.Frame(
            modes, bg=colors["ACCENT_DARK"] if selected else colors["CARD"],
            highlightthickness=1,
            highlightbackground=colors["ACCENT"] if selected else colors["BORDER"])
        box.grid(row=0, column=col, sticky="nsew", padx=(0, 5) if col < 2 else (0, 0))
        label = title + (" · Active" if selected else "") + "\n" + detail
        control = tk.Button(
            box, text=label, command=lambda value=mode: app._set_display_mode(value),
            bg=colors["ACCENT_DARK"] if selected else colors["CARD"],
            fg=colors["WHITE"], activebackground=colors["CARD_HOVER"],
            activeforeground=colors["WHITE"], font=(FONT, 8, "bold" if selected else "normal"),
            anchor="w", justify="left", cursor="hand2", relief="flat", bd=0,
            padx=7, pady=10, takefocus=True)
        control.pack(fill="both", expand=True)
        app.dashboard_settings_controls["mode_" + mode] = control

    _label(panel, "COLOR THEME", colors, size=8, weight="bold",
           muted=True, anchor="w").pack(fill="x", padx=14, pady=(3, 6))
    swatches = tk.Frame(panel, bg=colors["PANEL"])
    swatches.pack(fill="x", padx=13, pady=(0, 13))
    for i, name in enumerate(themes.THEME_ORDER):
        swatches.grid_columnconfigure(i % 3, weight=1, uniform="themes")
        active = app.theme == name
        tile = tk.Frame(
            swatches, bg=colors["ACCENT_DARK"] if active else colors["CARD"],
            highlightthickness=1,
            highlightbackground=colors["ACCENT"] if active else colors["BORDER"])
        tile.grid(row=i // 3, column=i % 3, sticky="nsew",
                  padx=(0, 5) if i % 3 < 2 else (0, 0), pady=(0, 5))
        marker = tk.Frame(tile, bg=themes.THEMES[name]["accent"], width=5)
        marker.pack(side="left", fill="y")
        marker.pack_propagate(False)
        control = tk.Button(
            tile, text=themes.THEMES[name]["name"] + (" (active)" if active else ""),
            command=lambda theme=name: app._choose_theme(theme),
            bg=colors["ACCENT_DARK"] if active else colors["CARD"],
            fg=colors["WHITE"], activebackground=colors["CARD_HOVER"],
            activeforeground=colors["WHITE"], relief="flat", bd=0,
            cursor="hand2", anchor="w", font=(FONT, 8, "bold" if active else "normal"),
            padx=7, pady=7, takefocus=True)
        control.pack(side="left", fill="both", expand=True)
        app.dashboard_settings_controls["theme_" + name] = control


def _launcher(panel, app, colors):
    _toggle(panel, app, colors, "extra_mini", "Enable Extra Mini",
            "Show the compact quick launcher when minimizing Pocket.",
            app.settings["extra_mini_enabled"], app._set_extra_mini_enabled)
    foot = tk.Frame(panel, bg=colors["PANEL"])
    foot.pack(fill="x", padx=13, pady=(6, 12))
    design.button(foot, "Customize quick actions",
                  app._edit_extra_mini_from_settings, app.theme,
                  primary=True, compact=True).pack(side="left")
    _label(foot, "4 actions per page · adds pages as needed",
           colors, size=8, muted=True).pack(side="right")
    app.dashboard_settings_controls["customize_launcher"] = foot


def _visible_tools(panel, app, colors):
    for key, caption in app.VISIBLE_TABS_REFERENCE:
        _toggle(panel, app, colors, "tool_" + key, caption.title(),
                settings_ui.TOOL_HELP[key],
                key in app.settings["visible_tabs"],
                lambda enabled, tool=key: app._set_visible_tab(tool, enabled))
    _label(panel, "At least one tool must remain enabled. Changes apply in all modes.",
           colors, size=8, muted=True, wraplength=375,
           justify="left").pack(fill="x", padx=14, pady=(2, 13))


def _behavior(panel, app, colors):
    bar = tk.Frame(panel, bg=colors["PANEL"])
    bar.pack(fill="x", padx=13, pady=(0, 9))
    label = tk.Frame(bar, bg=colors["PANEL"])
    label.pack(side="left", fill="x", expand=True)
    _label(label, "GLOBAL SHORTCUT", colors, size=8, muted=True,
           weight="bold").pack(anchor="w")
    _label(label, app._hotkey_hint(), colors, size=10, weight="bold"
           ).pack(anchor="w", pady=(3, 0))
    button = design.button(bar, "Change", app._open_hotkey_picker,
                           app.theme, compact=True)
    button.pack(side="right")
    app.dashboard_settings_controls["change_hotkey"] = button
    tk.Frame(panel, height=1, bg=colors["BORDER"]).pack(fill="x", padx=14, pady=(0, 5))
    search = tk.Frame(panel, bg=colors["PANEL"])
    search.pack(fill="x", padx=13, pady=(1, 12))
    titles = tk.Frame(search, bg=colors["PANEL"])
    titles.pack(side="left", fill="x", expand=True)
    _label(titles, "QUICK SEARCH", colors, size=8, muted=True,
           weight="bold").pack(anchor="w")
    _label(titles, "Ctrl+K · local search", colors, size=8,
           muted=True).pack(anchor="w", pady=(3, 0))
    button = design.button(search, "Open search", app._open_global_search,
                           app.theme, compact=True)
    button.pack(side="right")
    app.dashboard_settings_controls["quick_search"] = button


def _privacy(panel, app, colors):
    _toggle(panel, app, colors, "clipboard_paused", "Pause clipboard capture",
            "Stop monitoring new text, while keeping current session history.",
            app.settings["clipboard_paused"], app._set_clipboard_paused)
    _toggle(panel, app, colors, "sensitive_filter", "Skip recognized sensitive text",
            "Avoid common passwords and tokens. Detection cannot catch every secret.",
            app.settings["clipboard_sensitive_filter"],
            app._set_clipboard_sensitive_filter)
    tk.Frame(panel, bg=colors["BORDER"], height=1).pack(fill="x", padx=14, pady=(4, 9))
    _label(panel, "Clipboard capture is session-only and runs when Clipboard is enabled. "
           "Note reminders operate while Pocket is running. CLI commands are copied, not executed.",
           colors, size=8, muted=True, justify="left", wraplength=370,
           anchor="w").pack(fill="x", padx=14, pady=(0, 13))


def build(app, parent):
    """Two-column Dashboard view in the existing scrollable tool body."""
    c = themes.palette(app.theme)
    app.dashboard_settings_controls = {}
    heading = tk.Frame(parent, bg=c["BG"])
    heading.pack(fill="x", pady=(0, 12))
    tk.Label(heading, text="WORKSPACE PREFERENCES", bg=c["BG"], fg=c["WHITE"],
             font=(FONT, 13, "bold"), anchor="w").pack(side="left")
    tk.Label(heading, text="Stored locally · Applied immediately",
             bg=c["BG"], fg=c["MUTED"], font=(FONT, 9),
             anchor="e").pack(side="right")

    grid = tk.Frame(parent, bg=c["BG"])
    grid.pack(fill="x")
    grid.grid_columnconfigure(0, weight=1, uniform="settings")
    grid.grid_columnconfigure(1, weight=1, uniform="settings")

    layout = _section(grid, c, "Appearance & layout",
                      "Choose a working mode and a color palette.", row=0, col=0)
    _display(layout, app, c)
    extra = _section(grid, c, "Extra Mini launcher",
                     "A small, optional page of your most-used actions.", row=1, col=0)
    _launcher(extra, app, c)
    behavior = _section(grid, c, "Keyboard & search",
                        "Quick access without leaving your current workflow.",
                        row=2, col=0)
    _behavior(behavior, app, c)

    tools = _section(grid, c, "Visible tools",
                     "Enable or hide tools across all working modes.", row=0, col=1)
    _visible_tools(tools, app, c)
    privacy = _section(grid, c, "Clipboard & privacy",
                       "Control the session-only clipboard monitor.", row=1, col=1)
    _privacy(privacy, app, c)

    footer = tk.Label(
        parent, text="Pocket works offline unless you explicitly run a network-dependent tool.",
        bg=c["BG"], fg=c["MUTED"], font=(FONT, 8), anchor="w")
    footer.pack(fill="x", pady=(0, 8))
