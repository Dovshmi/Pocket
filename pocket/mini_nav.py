"""Fixed-width Mini icon-bar planner with optional expandable overflow.

Pocket Mini always has at most eight icon positions in its first row.
The final tile is Settings when everything fits; otherwise it is a
More/Less toggle. Remaining tools and Settings occupy rows of equal capacity.
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
    keys = list(dict.fromkeys(key for key in enabled if key not in ("settings", "more")))
    if len(keys) + 1 <= columns:
        return tuple(keys + ["settings"]), ()
    first = tuple(keys[:columns - 1] + ["more"])
    rest = keys[columns - 1:] + ["settings"]
    rows = tuple(tuple(rest[i:i + columns]) for i in range(0, len(rest), columns))
    return first, rows
