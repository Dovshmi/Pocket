"""Modern Settings page for all three Pocket working layouts.

Presentation only. All changes dispatch through PocketDesk's existing
validated settings and persistence methods; no new data stores or I/O.
"""
from __future__ import annotations
import tkinter as tk
from . import icon_themes as themes
from . import tool_icons

LAYOUTS = (
    ("normal", "▣", "Normal", "Classic tray window"),
    ("mini", "▫", "Mini", "Compact tools"),
    ("dashboard", "▦", "Dashboard", "Wide workspace"),
)

TOOL_HELP = {
    "notes": "Notes, phone numbers and reminders",
    "links": "Websites, files and folders",
    "ports": "On-demand TCP checks",
    "mac": "Local IEEE vendor lookup",
    "commands": "CLI library and manual backups",
    "subnet": "IPv4 subnet calculator",
    "clipboard": "Session-only clipboard history",
}
TOOL_ICONS = {
    "notes": "✎", "links": "↗", "ports": "⇄", "mac": "▦",
    "commands": ">_", "subnet": "⌗", "clipboard": "▤",
}


def _text(parent, text, c, size=9, *, bold=False, fg=None, bg=None, **opts):
    return tk.Label(parent, text=text, bg=bg or c["PANEL"],
                    fg=fg or c["WHITE"], font=("Segoe UI", size,
                    "bold" if bold else "normal"), **opts)


def _button(parent, text, callback, c, primary=False, **opts):
    return tk.Button(parent, text=text, command=callback, relief="flat", bd=0,
                     highlightthickness=0, bg=c["ACCENT_DARK"] if primary else c["CARD"],
                     fg=c["ACCENT"] if primary else c["WHITE"],
                     activebackground=c["CARD_HOVER"], activeforeground=c["WHITE"],
                     cursor="hand2", font=("Segoe UI", 9, "bold"), padx=11, pady=6,
                     **opts)


def _section(parent, c, title, subtitle=None):
    frame = tk.Frame(parent, bg=c["PANEL"], highlightthickness=1,
                     highlightbackground=c["BORDER"], bd=0)
    frame.pack(fill="x", pady=(0, 12))
    head = tk.Frame(frame, bg=c["PANEL"])
    head.pack(fill="x", padx=14, pady=(11, 8))
    _text(head, title, c, size=11, bold=True).pack(anchor="w")
    if subtitle:
        _text(head, subtitle, c, size=8, fg=c["MUTED"],
              wraplength=660, justify="left").pack(anchor="w", pady=(3, 0))
    return frame


def _separator(frame, c):
    tk.Frame(frame, bg=c["BORDER"], height=1).pack(fill="x", padx=14)


def _toggle(parent, c, title, detail, enabled, on_change, *, compact=False):
    """Native checkbox with accessible toggle and themed descriptive row."""
    line = tk.Frame(parent, bg=c["PANEL"])
    line.pack(fill="x", padx=12, pady=7)
    flag = tk.BooleanVar(value=bool(enabled))
    check = tk.Checkbutton(
        line, text=title, variable=flag,
        command=lambda: on_change(flag.get()),
        bg=c["PANEL"], fg=c["WHITE"], selectcolor=c["INPUT"],
        activebackground=c["PANEL"], activeforeground=c["ACCENT"],
        font=("Segoe UI", 9, "bold"), anchor="w", highlightthickness=0,
        cursor="hand2", padx=0, pady=1)
    check.pack(fill="x")
    _text(line, detail, c, size=8, fg=c["MUTED"],
          wraplength=245 if compact else 650, justify="left",
          anchor="w").pack(fill="x", padx=(20, 0), pady=(2, 0))


def build_settings(app, parent):
    """Render responsive Settings cards, including the small Mini view."""
    c = themes.palette(app.theme)
    narrow = app.display_mode in ("mini", "normal")
    mini = app.display_mode == "mini"
    wrap = 270 if mini else (405 if narrow else 800)
    label = "SETTINGS  /  POCKET"
    _text(parent, label, c, size=8, fg=c["ACCENT"], bg=c["BG"],
          bold=True).pack(anchor="w", pady=(0, 4))
    _text(parent, "Personalize your workspace", c, size=16 if mini else 21,
          bg=c["BG"], bold=True).pack(anchor="w", pady=(0, 4))
    _text(parent, "Your preferences are saved locally and applied immediately.",
          c, size=9, bg=c["BG"], fg=c["MUTED"], wraplength=wrap,
          anchor="w", justify="left").pack(fill="x", pady=(0, 14))

    layout = _section(parent, c, "Appearance & layout",
                      "Choose your working window. Extra Mini is an optional quick launcher.")
    tiles = tk.Frame(layout, bg=c["PANEL"])
    tiles.pack(fill="x", padx=12, pady=(1, 12))
    for index, (mode, icon, name, subtitle) in enumerate(LAYOUTS):
        selected = app.settings["display_mode"] == mode
        block = tk.Frame(tiles, bg=c["ACCENT_DARK"] if selected else c["CARD"],
                         highlightthickness=1,
                         highlightbackground=c["ACCENT"] if selected else c["BORDER"])
        if mini:
            block.pack(fill="x", pady=(0, 6))
        else:
            block.pack(side="left", fill="both", expand=True,
                       padx=(0, 6) if index < 2 else 0)
        action = tk.Button(
            block, text=f"{name}\n{subtitle}", justify="left", anchor="w",
            command=lambda target=mode: app._set_display_mode(target),
            bg=c["ACCENT_DARK"] if selected else c["CARD"],
            fg=c["WHITE"], activebackground=c["CARD_HOVER"],
            activeforeground=c["WHITE"], font=("Segoe UI", 9,
                "bold" if selected else "normal"),
            cursor="hand2", relief="flat", bd=0, highlightthickness=0,
            padx=11, pady=9 if mini else 12)
        action.pack(fill="both", expand=True)
    _separator(layout, c)
    theme_line = tk.Frame(layout, bg=c["PANEL"])
    theme_line.pack(fill="x", padx=14, pady=12)
    label_group = tk.Frame(theme_line, bg=c["PANEL"])
    label_group.pack(side="left", fill="x", expand=True)
    _text(label_group, "Color theme", c, bold=True).pack(anchor="w")
    _text(label_group, themes.THEMES[app.theme]["name"] + " · 6 color variants",
          c, fg=c["MUTED"], size=8).pack(anchor="w", pady=(2, 0))
    _button(theme_line, "Change ▾", app._show_theme_menu, c, primary=True
            ).pack(side="right")

    extra = _section(parent, c, "Extra Mini launcher",
                     "A 322 × 256 shortcut window that works with Normal, Mini and Dashboard.")
    _toggle(extra, c, "Enable Extra Mini",
            "Show a minimize-to-launcher button in the working window.",
            app.settings["extra_mini_enabled"], app._set_extra_mini_enabled,
            compact=mini)
    _separator(extra, c)
    actions = tk.Frame(extra, bg=c["PANEL"])
    actions.pack(fill="x", padx=13, pady=12)
    _button(actions, "Customize quick actions", app._edit_extra_mini_from_settings,
            c, primary=True).pack(side="left")
    _text(extra, "Pages appear automatically for each four saved actions. Add notes, commands, Smart Templates, or shortcuts. Click to choose, drag to rearrange.",
          c, fg=c["MUTED"], size=8, wraplength=wrap, justify="left"
          ).pack(anchor="w", padx=14, pady=(0, 12))

    tools = _section(parent, c, "Visible tools",
                     "Show or hide menus across every working layout and Extra Mini.")
    for index, (key, caption) in enumerate(app.VISIBLE_TABS_REFERENCE):
        if index:
            _separator(tools, c)
        _toggle(tools, c, caption.title(),
                TOOL_HELP[key], key in app.settings["visible_tabs"],
                lambda active, tool=key: app._set_visible_tab(tool, active),
                compact=mini)

    behavior = _section(parent, c, "Behavior & privacy")
    row = tk.Frame(behavior, bg=c["PANEL"])
    row.pack(fill="x", padx=14, pady=(4, 10))
    _text(row, "Keyboard shortcut", c, bold=True).pack(anchor="w")
    _text(row, app._hotkey_hint(), c, size=8, fg=c["MUTED"],
          wraplength=wrap).pack(anchor="w", pady=(3, 7))
    _button(row, "Change shortcut", app._open_hotkey_picker, c).pack(anchor="w")
    _separator(behavior, c)
    _toggle(behavior, c, "Pause clipboard capture",
            "Stop collecting new text; existing session history remains accessible.",
            app.settings["clipboard_paused"],
            lambda enabled: app._set_clipboard_paused(enabled), compact=mini)
    _separator(behavior, c)
    _toggle(behavior, c, "Skip recognized sensitive text",
            "Avoid capturing common passwords, API tokens and private keys. "
            "Pattern checks cannot guarantee detection of every secret.",
            app.settings["clipboard_sensitive_filter"],
            app._set_clipboard_sensitive_filter, compact=mini)
    _separator(behavior, c)
    search_row = tk.Frame(behavior, bg=c["PANEL"])
    search_row.pack(fill="x", padx=14, pady=(10, 8))
    _text(search_row, "Quick Search", c, bold=True).pack(anchor="w")
    _text(search_row, "Ctrl+K or Ctrl+F · local search only", c,
          size=8, fg=c["MUTED"]).pack(anchor="w", pady=(3, 7))
    _button(search_row, "Open Quick Search", app._open_global_search, c,
            primary=True).pack(anchor="w")
    _separator(behavior, c)
    _text(behavior, "Clipboard captures only while its menu is enabled. "
          "Captured text stays in memory, not in your saved settings.",
          c, fg=c["MUTED"], size=8, wraplength=wrap, justify="left",
          ).pack(fill="x", padx=14, pady=(11, 5))
    _text(behavior, "Note reminders work while Pocket is running in the tray. "
          "Commands are copied, never executed.",
          c, fg=c["MUTED"], size=8, wraplength=wrap, justify="left",
          ).pack(fill="x", padx=14, pady=(0, 13))
