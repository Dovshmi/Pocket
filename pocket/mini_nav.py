"""Width-aware Mini icon-bar planner with expandable overflow."""
from __future__ import annotations

COLUMNS = 8


def plan_mini_icons(enabled, columns=COLUMNS, *, add_available=False):
    """Return (first_row, overflow_rows) without changing saved menu ordering.

    The final icon occupies the *same* position in either mode. Overflow
    is expanded only when More is pressed, never at startup.
    """
    if not isinstance(columns, int) or isinstance(columns, bool) or columns < 2:
        raise ValueError("Mini must have room for a tool and More/Settings")
    keys = list(dict.fromkeys(key for key in enabled
                              if key not in ("more", "plus")))
    if "settings" not in keys:
        keys.append("settings")  # Backward-compatible callers omit Settings.
    # Only reserve More when the actual tools (including Add) cannot fit.
    if len(keys) + int(add_available) <= columns:
        return tuple(keys + (["plus"] if add_available else [])), ()
    first = tuple(keys[:columns - 1] + ["more"])
    rest = keys[columns - 1:] + (["plus"] if add_available else [])
    rows = tuple(tuple(rest[i:i + columns]) for i in range(0, len(rest), columns))
    return first, rows
