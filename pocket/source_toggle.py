"""Compact, keyboard-accessible Local / DashDash source selector for Pocket.

Presentation only. Switching the source never performs network I/O.
"""
from __future__ import annotations

import tkinter as tk

from . import pocket_design as design

FONT = "Segoe UI"


def make_source_toggle(parent, variable, on_change, theme, *, hint=""):
    """Return one short horizontal switch that fits Normal, Mini and Dashboard.

    'Local' is the left/off position. 'DashDash' is the right/on position.
    Mouse, keyboard (Space/Enter), and text-label clicks update the same variable.
    """
    c = design.colors(theme)
    row = tk.Frame(parent, bg=c["BG"])
    left = tk.Label(row, text="Local", bg=c["BG"], font=(FONT, 8, "bold"),
                    cursor="hand2")
    left.pack(side="left", padx=(0, 5))
    toggle = tk.Canvas(row, width=44, height=22, bg=c["BG"], bd=0,
                       highlightthickness=1, highlightbackground=c["BG"],
                       highlightcolor=c["ACCENT"], cursor="hand2", takefocus=True)
    toggle.pack(side="left")
    right = tk.Label(row, text="DashDash", bg=c["BG"], font=(FONT, 8, "bold"),
                     cursor="hand2")
    right.pack(side="left", padx=(5, 0))

    def redraw(*_):
        remote = variable.get() == "dashdash"
        toggle.delete("all")
        # Rounded track (Tk canvas has no rounded-rectangle primitive).
        fill = c["ACCENT"] if remote else c["CARD_HOVER"]
        toggle.create_oval(2, 2, 21, 20, fill=fill, outline=fill)
        toggle.create_rectangle(11, 2, 33, 20, fill=fill, outline=fill)
        toggle.create_oval(23, 2, 42, 20, fill=fill, outline=fill)
        x = 31 if remote else 13
        toggle.create_oval(x-8, 3, x+8, 19, fill=c["WHITE"], outline="")
        left.config(fg=c["MUTED"] if remote else c["WHITE"])
        right.config(fg=c["WHITE"] if remote else c["MUTED"])

    def set_source(value):
        if variable.get() == value:
            return
        variable.set(value)
        on_change()

    def flip(_event=None):
        set_source("local" if variable.get() == "dashdash" else "dashdash")
        toggle.focus_set()
        return "break"

    toggle.bind("<Button-1>", flip)
    toggle.bind("<space>", flip)
    toggle.bind("<Return>", flip)
    left.bind("<Button-1>", lambda _e: set_source("local"))
    right.bind("<Button-1>", lambda _e: set_source("dashdash"))
    variable.trace_add("write", redraw)
    redraw()
    if hint:
        design.Tooltip(toggle, hint, theme)
        design.Tooltip(right, hint, theme)
    return row
