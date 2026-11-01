"""PocketDesk icon themes based on the selected corrected LTR pocket icon pack.

The six gradients and hand/pocket geometry are adapted from the ZIP SVGs.
Pillow renders local PNG and multi-resolution ICO files; no downloads required.
"""
from __future__ import annotations

from pathlib import Path

THEME_ORDER = ("blue", "dark_blue", "black", "red", "green", "purple")
THEMES = {
    "blue": {"name": "Blue", "top": "#08A9F5", "bottom": "#0750F9", "accent": "#489BFF", "dark": "#152B51"},
    "dark_blue": {"name": "Dark blue", "top": "#102F67", "bottom": "#071D43", "accent": "#80AEFF", "dark": "#1A3156"},
    "black": {"name": "Black", "top": "#22242A", "bottom": "#08090D", "accent": "#D0D5E2", "dark": "#343945"},
    "red": {"name": "Red", "top": "#FF3C57", "bottom": "#E2183E", "accent": "#FF7188", "dark": "#4A202E"},
    "green": {"name": "Green", "top": "#1DC997", "bottom": "#068B65", "accent": "#58DEB2", "dark": "#184537"},
    "purple": {"name": "Purple", "top": "#A755FF", "bottom": "#6233DB", "accent": "#B693FF", "dark": "#362450"},
}
SURFACES = {
    "blue": ("#101725", "#192237", "#22304A", "#2B3C5D", "#111C2C", "#31425F"),
    "dark_blue": ("#0B1323", "#12213B", "#1B2D4E", "#274065", "#0C182C", "#283C5E"),
    "black": ("#101114", "#1A1C21", "#24272E", "#30343C", "#14161A", "#373B43"),
    "red": ("#1D1118", "#291A24", "#39232E", "#492B37", "#231720", "#52303C"),
    "green": ("#0C1B19", "#142A24", "#1C3A30", "#254C3E", "#101F1C", "#2A5546"),
    "purple": ("#161221", "#231B34", "#312743", "#423357", "#1B1728", "#513E68"),
}


def valid_theme(value: object) -> str:
    """Reject unknown themes without breaking older data.json files."""
    return value if isinstance(value, str) and value in THEMES else "blue"


def palette(theme: str) -> dict[str, str]:
    theme = valid_theme(theme)
    bg, panel, card, hover, field, border = SURFACES[theme]
    return {"BG": bg, "PANEL": panel, "CARD": card, "CARD_HOVER": hover,
            "INPUT": field, "BORDER": border,
            "ACCENT": THEMES[theme]["accent"],
            "ACCENT_DARK": THEMES[theme]["dark"],
            "ACCENT_HOVER": THEMES[theme]["top"],
            "WHITE": "#F3F4FA", "SECONDARY": "#B7C0CF",
            "MUTED": "#8692A5", "DANGER": "#FF8E9C"}


def _quad(a, b, c, t):
    return ((1-t)**2*a[0]+2*(1-t)*t*b[0]+t*t*c[0],
            (1-t)**2*a[1]+2*(1-t)*t*b[1]+t*t*c[1])


def _cubic(a, b, c, d, t):
    return ((1-t)**3*a[0]+3*(1-t)**2*t*b[0]+3*(1-t)*t*t*c[0]+t**3*d[0],
            (1-t)**3*a[1]+3*(1-t)**2*t*b[1]+3*(1-t)*t*t*c[1]+t**3*d[1])


def _points(path: str):
    """Flatten M/L/Q/C/Z commands from the original 816px SVG coordinates."""
    import re
    tokens = re.findall(r"[MLQCZ]|-?\d+(?:\.\d+)?", path)
    i, current, first, points = 0, (0.0, 0.0), None, []
    while i < len(tokens):
        op = tokens[i]; i += 1
        if op in ("M", "L"):
            current = (float(tokens[i]), float(tokens[i+1])); i += 2
            points.append(current)
            if first is None:
                first = current
        elif op == "Q":
            ctl = (float(tokens[i]), float(tokens[i+1]))
            end = (float(tokens[i+2]), float(tokens[i+3])); i += 4
            points.extend(_quad(current, ctl, end, j/16) for j in range(1, 17))
            current = end
        elif op == "C":
            ctl1 = (float(tokens[i]), float(tokens[i+1]))
            ctl2 = (float(tokens[i+2]), float(tokens[i+3]))
            end = (float(tokens[i+4]), float(tokens[i+5])); i += 6
            points.extend(_cubic(current, ctl1, ctl2, end, j/24) for j in range(1, 25))
            current = end
        elif op == "Z" and first is not None:
            points.append(first)
        else:
            raise ValueError("Unsupported icon path operator: " + op)
    return points


# Geometry transcribed from the corrected ZIP's original blue SVG.
HAND = "M272 478 L302 348 Q303 339 309 333 L470 151 Q479 141 488 149 L640 282 Q650 290 642 302 L577 400 L524 536 Q520 549 507 546 L431 538 L444 467 Q448 453 441 451 Q431 447 427 463 L408 532 L354 515 L371 437 Q374 423 364 420 Q353 417 350 432 L334 507 L277 485 Q270 482 272 478 Z"
POCKET = "M157 463 C253 506 360 550 460 569 C521 581 550 571 577 545 Q595 518 612 519 L648 519 L648 730"


def render_icon(theme: str, size: int = 512):
    """Render the selected pocket silhouette, rivet and slanted pocket opening."""
    from PIL import Image, ImageDraw, ImageOps
    theme = valid_theme(theme)
    side = 816
    top = bytes.fromhex(THEMES[theme]["top"][1:])
    bottom = bytes.fromhex(THEMES[theme]["bottom"][1:])
    image = Image.new("RGBA", (side, side))
    draw = ImageDraw.Draw(image)
    for y in range(side):
        t = y / (side-1)
        rgb = tuple(round(a*(1-t)+b*t) for a,b in zip(top,bottom))
        draw.line((0,y,side,y), fill=rgb+(255,))
    mask = Image.new("L", (side,side))
    ImageDraw.Draw(mask).rounded_rectangle((8,8,808,808), radius=168, fill=255)
    image.putalpha(mask)
    draw = ImageDraw.Draw(image)
    draw.polygon(_points(HAND), fill="#FFFFFF")
    for start,end in (((363,432),(341,510)), ((438,462),(417,530))):
        t = ((start[1]+end[1])/2)/(side-1)
        rgb = tuple(round(a*(1-t)+b*t) for a,b in zip(top,bottom))
        draw.line((*start,*end), fill=rgb+(255,), width=17)
        for x,y in (start,end):
            draw.ellipse((x-8,y-8,x+8,y+8), fill=rgb+(255,))
    line = _points(POCKET)
    draw.line(line, fill="#FFFFFF", width=21, joint="curve")
    for x,y in (line[0],line[-1]):
        draw.ellipse((x-10,y-10,x+10,y+10),fill="#FFFFFF")
    draw.ellipse((558,596,598,636),fill="#FFFFFF")
    # The corrected pack mirrors the source artwork to put the seam at left.
    image = ImageOps.mirror(image)
    return image.resize((size,size), Image.Resampling.LANCZOS)


def ensure_icons(directory: Path) -> dict[str, dict[str, Path]]:
    """Cache all six PNG and multiresolution ICO files under user AppData."""
    directory.mkdir(parents=True, exist_ok=True)
    icons = {}
    for theme in THEME_ORDER:
        png, ico = directory / f"{theme}.png", directory / f"{theme}.ico"
        if not png.is_file() or not ico.is_file():
            image = render_icon(theme)
            image.save(png)
            image.save(ico, format="ICO",
                       sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)])
        icons[theme] = {"png": png, "ico": ico}
    return icons


def build_default_icon(destination: Path) -> None:
    """Use blue as the build-time EXE icon; users may switch live window/tray icons."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    render_icon("blue").save(destination, format="ICO",
                            sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)])


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--build-icon", type=Path)
    args = parser.parse_args()
    if args.build_icon:
        build_default_icon(args.build_icon)
    else:
        parser.print_help()
