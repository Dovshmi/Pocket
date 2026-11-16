"""Incremental keyboard navigation for Pocket's existing read-only dropdowns.

No changes to the Combobox state, popup, values, or visual appearance.
Typing selects an existing item instead of filtering or replacing the list.
"""
from __future__ import annotations

import time

TYPEAHEAD_TIMEOUT = 1.15


def find_match(values, query, *, selected=-1, cycle=False):
    """Prefer case-insensitive prefix matches, then substring matches.

    Notes use the existing visible pinned-star marker. It is ignored for
    searching, but remains visible in the normal dropdown.
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


def install(widget, *, time_source=time.monotonic):
    """Add type-to-jump to a ttk.Combobox, leaving readonly/dropdown intact.

    Does not create a search field and does not change available options.
    Existing <<ComboboxSelected>> handlers perform the normal selection flow.
    """
    typed = ""
    last_key = None
    last_at = -float("inf")

    def on_key(event):
        nonlocal typed, last_key, last_at
        # Ctrl+letters and AltGr remain available to the system, and normal
        # combobox arrows, Return, Tab and Escape retain their default behavior.
        if getattr(event, "state", 0) & 0x000C:
            return None
        key = getattr(event, "keysym", "")
        if key == "Escape":
            typed = ""
            last_key = None
            return None
        if key == "BackSpace":
            if typed:
                typed = typed[:-1]
                last_at = time_source()
                return "break"
            return None
        char = getattr(event, "char", "")
        if not char or not char.isprintable() or char in "\r\n\t":
            return None

        now = time_source()
        if now - last_at > TYPEAHEAD_TIMEOUT:
            typed = ""
            last_key = None
        values = widget["values"]
        if isinstance(values, str):
            values = widget.tk.splitlist(values)
        selected = widget.current()
        tentative = typed + char
        # Repeating a character steps through other values beginning with
        # that character rather than searching for "jjj".
        repeated = typed == char and char == last_key
        if repeated:
            tentative = char
        candidate = find_match(
            values, tentative, selected=selected, cycle=repeated)
        if candidate < 0:
            tentative = char
            candidate = find_match(values, tentative, selected=selected)
        typed = tentative
        last_key = char
        last_at = now
        if candidate >= 0 and candidate != selected:
            widget.current(candidate)
            widget.event_generate("<<ComboboxSelected>>")
        return "break"

    widget.bind("<KeyPress>", on_key, add="+")
    # Keeping a reference also allows integration tests to exercise a precise
    # keyboard sequence without relying on the native focus manager.
    widget._pocket_typeahead = on_key
    return widget
