"""Portable vector-drawn tool icons, independent of Unicode font coverage.

Rasterized locally with Pillow (already a Pocket dependency). No network,
external icon font or platform-specific glyph is required.
"""
from __future__ import annotations

from PIL import Image, ImageDraw, ImageTk

TOOLS = ("home", "notes", "links", "ports", "mac", "commands",
         "subnet", "clipboard", "settings", "template", "shortcut", "more")


def _drawing(name, color, size):
    scale = 3
    im = Image.new("RGBA", (size * scale, size * scale), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    def p(x, y):
        return round(x * size * scale / 24), round(y * size * scale / 24)
    def line(points, width=1.8):
        d.line([p(*point) for point in points], fill=color,
               width=max(2, round(width * size * scale / 24)), joint="curve")
    def rect(a, b, radius=2, width=1.7):
        d.rounded_rectangle([p(*a), p(*b)], radius=round(radius * size * scale / 24),
                            outline=color, width=max(2, round(width * size * scale / 24)))
    def oval(a, b, fill=None):
        d.ellipse([p(*a), p(*b)], fill=fill or color)
    if name == "more":
        for x in (5, 12, 19):
            oval((x - 2, 10), (x + 2, 14))
    elif name == "home":
        line([(3, 11), (12, 4), (21, 11)])
        line([(6, 10), (6, 20), (18, 20), (18, 10)])
        line([(10, 20), (10, 14), (14, 14), (14, 20)])
    elif name == "notes":
        rect((5, 3), (19, 21))
        for y in (8, 12, 16):
            line([(9, y), (16, y)])
    elif name in ("links", "shortcut"):
        rect((3, 9), (13, 20), radius=2)
        line([(11, 13), (21, 3), (14, 3)])
        line([(21, 3), (21, 10)])
    elif name == "ports":
        rect((2, 7), (22, 17), radius=2)
        for x in (6, 10, 14, 18):
            oval((x - .9, 11), (x + .9, 13))
    elif name == "mac":
        rect((3, 5), (21, 19), radius=2)
        for x in (7, 12, 17):
            for y in (9, 15):
                oval((x - 1, y - 1), (x + 1, y + 1))
    elif name in ("commands", "template"):
        rect((2, 4), (22, 20))
        line([(6, 9), (10, 12), (6, 15)])
        line([(12, 16), (18, 16)])
    elif name == "subnet":
        for x, y in ((12, 5), (5, 18), (19, 18)):
            oval((x - 3, y - 3), (x + 3, y + 3))
        line([(11, 8), (7, 15)])
        line([(13, 8), (17, 15)])
        line([(8, 18), (16, 18)])
    elif name == "clipboard":
        rect((5, 5), (19, 21))
        rect((9, 2), (15, 8), radius=1)
        line([(9, 12), (16, 12)])
        line([(9, 16), (16, 16)])
    elif name == "settings":
        oval((8, 8), (16, 16), fill=None)
        for x1, y1, x2, y2 in ((12, 2, 12, 6), (12, 18, 12, 22),
                                (2, 12, 6, 12), (18, 12, 22, 12),
                                (5, 5, 8, 8), (16, 16, 19, 19),
                                (16, 8, 19, 5), (5, 19, 8, 16)):
            line([(x1, y1), (x2, y2)], width=2.5)
    return im.resize((size, size), Image.Resampling.LANCZOS)


def icon_image(master, name, color="#FFFFFF", size=20):
    """Create an owned Tk image. Widgets must keep a reference."""
    return ImageTk.PhotoImage(_drawing(name, color, size), master=master)


def label(parent, name, color, background, *, size=20, **kwargs):
    import tkinter as tk
    photo = icon_image(parent, name, color, size)
    widget = tk.Label(parent, image=photo, bg=background, **kwargs)
    widget.image = photo
    return widget
