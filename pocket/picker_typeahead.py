"""Incremental keyboard navigation for Pocket's existing readonly dropdowns.

Do not filter or replace their option lists. A posted ttk Combobox moves
keyboard focus into an internal Listbox: only *highlight* the matching row
while the popup is open. The stock Enter/click binding commits the choice,
keeping the list open and the user's multi-letter typing uninterrupted.
"""
from __future__ import annotations

import time
import tkinter as tk

TYPEAHEAD_TIMEOUT = 1.15


def find_match(values, query, *, selected=-1, cycle=False):
    """Prefer case-insensitive prefix matches, then substring matches.

    Notes keep their visual pinned-star marker; it is ignored for searching.
    """
    needle = str(query).strip().casefold()
    if not needle:
        return -1
    labels = [str(value).removeprefix("★ ").casefold() for value in values]
    for predicate in (lambda label: label.startswith(needle),
                      lambda label: needle in label):
        indices = [i for i, label in enumerate(labels) if predicate(label)]
        if indices:
            if cycle and len(needle) == 1 and selected in indices and len(indices) > 1:
                return indices[(indices.index(selected) + 1) % len(indices)]
            return indices[0]
    return -1


def _character(event):
    """Allow native Tk Unicode events and simple keysym-only fallbacks."""
    char = getattr(event, "char", "")
    if not char:
        key = str(getattr(event, "keysym", ""))
        if len(key) == 1:
            char = key
    if len(char) != 1 or not char.isprintable() or char in "\r\n\t":
        return ""
    return char


def install(widget, *, time_source=time.monotonic):
    """Add non-destructive type-to-jump to a ttk.Combobox.

    The entry remains readonly and its full options remain intact. When the
    dropdown is open, typeahead moves only the visible Listbox highlight and
    scrolls to it. Enter or clicking an item uses Tk's existing selection
    bindings and triggers Pocket's usual <<ComboboxSelected>> handler.
    """
    typed = ""
    last_key = None
    last_at = -float("inf")
    listing = None

    # The Tcl popdown is created on demand; ensure it exists at install time.
    # On non-Aqua systems its listbox path is the same on Windows and Linux.
    try:
        popdown = widget.tk.call("ttk::combobox::PopdownWindow", str(widget))
        candidate = str(popdown) + ".f.l"
        if widget.tk.call("winfo", "exists", candidate):
            listing = candidate
    except (AttributeError, RuntimeError, tk.TclError):
        pass

    def popup_open():
        if not listing:
            return False
        try:
            return bool(int(widget.tk.call("winfo", "ismapped", listing)))
        except (ValueError, RuntimeError, tk.TclError):
            return False

    def popup_selection():
        if not listing:
            return widget.current()
        try:
            indices = widget.tk.splitlist(widget.tk.call(listing, "curselection"))
            return int(indices[0]) if indices else widget.current()
        except (ValueError, RuntimeError, tk.TclError):
            return widget.current()

    def highlight(index):
        if not listing:
            return False
        try:
            widget.tk.call(listing, "selection", "clear", 0, "end")
            widget.tk.call(listing, "selection", "set", index)
            widget.tk.call(listing, "activate", index)
            widget.tk.call(listing, "see", index)
        except (ValueError, RuntimeError, tk.TclError):
            return False
        return True

    def on_key(event):
        nonlocal typed, last_key, last_at
        # AltGr sends Ctrl+Alt on Windows. Do not commandeer accelerators.
        if getattr(event, "state", 0) & 0x000C:
            return None
        key = str(getattr(event, "keysym", ""))
        if key in ("Escape", "Return", "Tab", "Up", "Down", "Left", "Right"):
            if key == "Escape":
                typed = ""
                last_key = None
            return None
        if key == "BackSpace":
            if typed:
                typed = typed[:-1]
                last_at = time_source()
                if typed:
                    values = widget["values"]
                    if isinstance(values, str):
                        values = widget.tk.splitlist(values)
                    match = find_match(values, typed)
                    if match >= 0:
                        if popup_open():
                            highlight(match)
                        elif match != widget.current():
                            widget.current(match)
                            widget.event_generate("<<ComboboxSelected>>")
                return "break"
            return None
        char = _character(event)
        if not char:
            return None

        now = time_source()
        if now - last_at > TYPEAHEAD_TIMEOUT:
            typed = ""
            last_key = None
        values = widget["values"]
        if isinstance(values, str):
            values = widget.tk.splitlist(values)
        opened = popup_open()
        selected = popup_selection() if opened else widget.current()
        repeated = typed == char and char == last_key
        tentative = char if repeated else typed + char
        match = find_match(values, tentative, selected=selected, cycle=repeated)
        if match < 0:
            tentative = char
            match = find_match(values, tentative, selected=selected)
        typed = tentative
        last_key = char
        last_at = now
        if match >= 0:
            if opened:
                # Crucial: never call current() or generate ComboboxSelected
                # while the popdown is posted. Doing so changes Notes/Commands
                # and steals popup focus before the rest of the name is typed.
                highlight(match)
            elif match != selected:
                widget.current(match)
                widget.event_generate("<<ComboboxSelected>>")
        return "break"

    # The main widget receives keys while the dropdown is closed.
    widget.bind("<KeyPress>", on_key, add="+")
    if listing:
        # When posted, keyboard focus belongs to the Tcl Listbox. Bind to its
        # widget tag, first in its native bindtags; Return/click continue to
        # execute the original ComboboxListbox class selection binding.
        try:
            widget._bind(("bind", listing), "<KeyPress>", on_key, add="+")
            widget._pocket_typeahead_popdown = listing
        except (AttributeError, RuntimeError, tk.TclError):
            pass

    widget._pocket_typeahead = on_key
    return widget
