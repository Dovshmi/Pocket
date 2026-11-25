"""Monitor-aware, display-independent geometry for Pocket v1.41.

Mini, Normal and Dashboard are responsive layouts of one resizable window.
The optional Extra Mini launcher deliberately stays outside this system.
No GUI imports: behavior is testable without Windows or a Tk display.
"""
from __future__ import annotations

MIN_WIDTH = 330
MIN_HEIGHT = 440
NORMAL_WIDTH = 470
DASHBOARD_WIDTH = 950
DASHBOARD_HEIGHT = 600


def saved_size(raw):
    """Return a safe persisted size, or None for legacy profiles."""
    if not isinstance(raw, dict):
        return None
    width, height = raw.get("width"), raw.get("height")
    if type(width) is not int or type(height) is not int:
        return None
    if not (240 <= width <= 20000 and 240 <= height <= 20000):
        return None
    return {"width": width, "height": height}


def layout_for(width, height):
    """Select presentation, not a new application instance or data store."""
    if width >= DASHBOARD_WIDTH and height >= DASHBOARD_HEIGHT:
        return "dashboard"
    if width >= NORMAL_WIDTH:
        return "normal"
    return "mini"


def resize_rectangle(rect, edges, dx, dy, work_area, margin=7):
    """Resize (x,y,w,h) by dragged edge(s), within a monitor's work area.

    The opposite edges remain fixed; moving a left/top edge also moves the
    origin. On unusually small screens the effective minimum shrinks to fit.
    """
    x, y, width, height = rect
    work_left, work_top, work_right, work_bottom = work_area
    left_bound = work_left + margin
    top_bound = work_top + margin
    right_bound = work_right - margin
    bottom_bound = work_bottom - margin
    min_width = min(MIN_WIDTH, max(1, right_bound - left_bound))
    min_height = min(MIN_HEIGHT, max(1, bottom_bound - top_bound))
    left, top = x, y
    right, bottom = x + width, y + height

    def clamp(value, low, high):
        return max(low, min(value, max(low, high)))

    if "w" in edges:
        left = clamp(left + dx, left_bound, right - min_width)
    if "e" in edges:
        right = clamp(right + dx, left + min_width, right_bound)
    if "n" in edges:
        top = clamp(top + dy, top_bound, bottom - min_height)
    if "s" in edges:
        bottom = clamp(bottom + dy, top + min_height, bottom_bound)
    return left, top, right - left, bottom - top
