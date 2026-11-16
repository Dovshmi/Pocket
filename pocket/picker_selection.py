"""Restore ordinary readonly dropdown behavior and remove closed text highlighting.

Pocket's Mini Notes / CLI pickers should show the chosen value normally.
The selection highlight is useful only while navigating an open dropdown.
No typeahead, key interception, Win32 hooks or option filtering is installed.
"""
from __future__ import annotations

import tkinter as tk


def clear_closed_selection(widget, attempts=10):
    """Clear only the text selection, never the selected value or popup row.

    ttk may set the Combobox entry selection while committing an option.
    Defer until after its native popup closes, leaving open-list highlighting
    entirely under Tk's built-in navigation behavior.
    """
    try:
        if not widget.winfo_exists():
            return
        popup = widget.tk.call("ttk::combobox::PopdownWindow", str(widget))
        listbox = str(popup) + ".f.l"
        if bool(int(widget.tk.call("winfo", "ismapped", listbox))):
            if attempts > 0:
                widget.after(35, lambda: clear_closed_selection(widget, attempts - 1))
            return
        widget.selection_clear()
    except (tk.TclError, RuntimeError):
        pass


def install(widget):
    """Keep standard readonly selection; hide the blue text highlight on close."""
    def on_chosen(_event):
        # The original application's selection callback is kept as-is.
        widget.after(35, lambda: clear_closed_selection(widget))

    widget.bind("<<ComboboxSelected>>", on_chosen, add="+")
    return widget
