"""Fixed-width Mini icon-bar planner with optional expandable overflow.

Mini always has at most eight icons in the first row. More/Less occupies the
fixed eighth slot when overflowing. User-sorted Settings is a normal icon;
the legacy default still places Settings last.
"""
from __future__ import annotations

COLUMNS = 8


def plan_mini_icons(enabled, columns=COLUMNS):
    """Return (first_row, overflow_rows) without changing saved menu ordering.

    The final icon occupies the *same* position in either mode. Overflow
    is expanded only when More is pressed, never at startup.
    """
    if not isinstance(columns, int) or isinstance(columns, bool) or columns < 2:
        raise ValueError("Mini must have room for a tool and More/Settings")
    keys = list(dict.fromkeys(key for key in enabled if key != "more"))
    if "settings" not in keys:
        keys.append("settings")  # Backward-compatible callers omit Settings.
    if len(keys) <= columns:
        return tuple(keys), ()
    first = tuple(keys[:columns - 1] + ["more"])
    rest = keys[columns - 1:]
    rows = tuple(tuple(rest[i:i + columns]) for i in range(0, len(rest), columns))
    return first, rows
