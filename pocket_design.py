"""Pocket visual language — semantic tokens and reusable Tk/ttk components.

All colors originate from the existing Pocket icon theme. This module styles
controls only; it never changes storage, launches a shortcut or runs commands.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

import icon_themes as themes

FONT = "Segoe UI"
SPACING = (4, 8, 12, 16, 24)
RADIUS_NOTE = "Tkinter uses flat surfaces and 1px borders; no bitmap backgrounds."


def colors(theme):
    p = themes.palette(theme)
    return {**p, "POSITIVE": "#63DCA8", "NOTICE": "#F5C66A"}


def configure_ttk(root, theme):
    """Consistent editable/picker/table styling on Windows and fallback Tk."""
    c = colors(theme)
    style = ttk.Style(root)
    # Clam honors colored fields/headings; switching it for a single widget
    # would change styling elsewhere, so configure Pocket-prefixed styles only.
    style.configure("Pocket.Treeview", background=c["PANEL"], foreground=c["WHITE"],
                    fieldbackground=c["PANEL"], borderwidth=0, rowheight=30,
                    font=(FONT, 9))
    style.configure("Pocket.Treeview.Heading", background=c["CARD"],
                    foreground=c["SECONDARY"], relief="flat",
                    padding=(10, 9), font=(FONT, 9, "bold"))
    style.map("Pocket.Treeview",
              background=[("selected", c["ACCENT_DARK"])],
              foreground=[("selected", c["WHITE"])])
    style.configure("Pocket.TCombobox", fieldbackground=c["INPUT"],
                    background=c["CARD"], foreground=c["WHITE"],
                    borderwidth=1, padding=(8, 6), arrowsize=12)
    style.map("Pocket.TCombobox",
              fieldbackground=[("readonly", c["INPUT"]), ("focus", c["INPUT"])],
              foreground=[("readonly", c["WHITE"])])
    style.configure("Pocket.Vertical.TScrollbar",
                    background=c["CARD"], troughcolor=c["BG"],
                    borderwidth=0, arrowsize=11)
    style.configure("Pocket.TSeparator", background=c["BORDER"])
    return c


def panel(parent, theme, *, background=None):
    c = colors(theme)
    return tk.Frame(parent, bg=background or c["PANEL"],
                    highlightthickness=1, highlightbackground=c["BORDER"], bd=0)


def button(parent, title, action, theme, *, primary=False, destructive=False,
           compact=False, **kwargs):
    c = colors(theme)
    color = c["DANGER"] if destructive else c["ACCENT"] if primary else c["WHITE"]
    bg = c["ACCENT_DARK"] if primary else c["CARD"]
    return tk.Button(parent, text=title, command=action, cursor="hand2",
                     bg=bg, fg=color, activebackground=c["CARD_HOVER"],
                     activeforeground=c["WHITE"], relief="flat", bd=0,
                     highlightthickness=1, highlightbackground=c["BORDER"],
                     highlightcolor=c["ACCENT"], takefocus=True,
                     padx=9 if compact else 13, pady=6 if compact else 9,
                     font=(FONT, 8 if compact else 9, "bold"), **kwargs)


def entry(parent, variable, theme, *, compact=False, **kwargs):
    c = colors(theme)
    return tk.Entry(parent, textvariable=variable, bg=c["INPUT"], fg=c["WHITE"],
                    insertbackground=c["WHITE"], selectbackground=c["ACCENT_DARK"],
                    relief="flat", bd=0, highlightthickness=1,
                    highlightbackground=c["BORDER"], highlightcolor=c["ACCENT"],
                    font=(FONT, 9 if compact else 10), **kwargs)


def section_header(parent, title, subtitle, command_label, command, theme, *, compact=False):
    """A subtle, consistent header for tools with the original action callback."""
    c = colors(theme)
    shell = panel(parent, theme)
    shell.pack(fill="x", pady=(0, 12 if compact else 15))
    accent = tk.Frame(shell, bg=c["ACCENT"], width=3)
    accent.pack(side="left", fill="y")
    accent.pack_propagate(False)
    content = tk.Frame(shell, bg=c["PANEL"])
    content.pack(side="left", fill="both", expand=True, padx=(11, 3),
                 pady=(8 if compact else 12))
    tk.Label(content, text=title, bg=c["PANEL"], fg=c["WHITE"],
             font=(FONT, 12 if compact else 15, "bold"),
             anchor="w").pack(anchor="w")
    tk.Label(content, text=subtitle, bg=c["PANEL"], fg=c["MUTED"],
             font=(FONT, 8 if compact else 9),
             wraplength=210 if compact else 650,
             anchor="w", justify="left").pack(anchor="w", pady=(3, 0))
    button(shell, command_label, command, theme, primary=True,
           compact=compact).pack(side="right", padx=(4, 10))
    return shell


def empty_state(parent, heading, detail, theme):
    """Accessible empty-state text; no placeholder content or network requests."""
    c = colors(theme)
    box = panel(parent, theme)
    box.pack(fill="x", pady=8)
    tk.Label(box, text=heading, bg=c["PANEL"], fg=c["SECONDARY"],
             font=(FONT, 11, "bold")).pack(anchor="w", padx=14, pady=(14, 4))
    tk.Label(box, text=detail, bg=c["PANEL"], fg=c["MUTED"], font=(FONT, 9),
             wraplength=365, justify="left").pack(anchor="w",
                                                padx=14, pady=(0, 14))
    return box
