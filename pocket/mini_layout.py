"""Small, display-independent helpers for Pocket's compact layout.

Normal and mini modes share application data; only geometry and presentation
differ. Keep a distinct saved position for each window size.
"""
from __future__ import annotations

MODES = ("normal", "mini", "dashboard", "compact")
NORMAL_WIDTH, NORMAL_HEIGHT = 480, 850
MINI_WIDTH, MINI_HEIGHT = 346, 530
DASHBOARD_WIDTH, DASHBOARD_HEIGHT = 1160, 800
COMPACT_WIDTH, COMPACT_HEIGHT = 322, 256


def display_mode(value) -> str:
    return value if value in MODES else "normal"


def view_dimensions(mode: str) -> tuple[int, int]:
    mode = display_mode(mode)
    if mode == "mini":
        return MINI_WIDTH, MINI_HEIGHT
    if mode == "dashboard":
        return DASHBOARD_WIDTH, DASHBOARD_HEIGHT
    if mode == "compact":
        return COMPACT_WIDTH, COMPACT_HEIGHT
    return NORMAL_WIDTH, NORMAL_HEIGHT


def window_position(raw):
    """Validate positions; None means automatic placement."""
    if not isinstance(raw, dict):
        return None
    x, y = raw.get("x"), raw.get("y")
    if type(x) is not int or type(y) is not int:
        return None
    if abs(x) > 100000 or abs(y) > 100000:
        return None
    return {"x": x, "y": y}


def window_positions(raw, legacy=None):
    """Migrate old position to normal; never reuse it for a smaller window."""
    raw = raw if isinstance(raw, dict) else {}
    normal = window_position(raw.get("normal")) or window_position(legacy)
    mini = window_position(raw.get("mini"))
    dashboard = window_position(raw.get("dashboard"))
    compact = window_position(raw.get("compact"))
    return {"normal": normal, "mini": mini, "dashboard": dashboard, "compact": compact}


def selected_index(matches, selected_id=None):
    """Search ranking wins unless the currently selected result still exists."""
    return next((i for i, item in enumerate(matches)
                 if item["id"] == selected_id), 0) if matches else -1


def carousel_index(index: int, count: int, step: int) -> int:
    """Clamp pagination at the ends; never wrap invisibly."""
    if count < 1:
        return -1
    return max(0, min(count - 1, index + step))
