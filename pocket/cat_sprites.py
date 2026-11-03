"""Original 32x32 Pocket black-cat sprite art with expressive four-frame animation.

No image files, web access, GUI imports or third-party dependencies are needed.
Sprites are generated once and cached by the Tk companion when displayed.
"""
from __future__ import annotations

PIXELS = 32
POSES = ("walk", "sit", "blink", "look", "groom", "sleep",
         "stretch", "scratch", "play", "yawn")
# Soft charcoal shading + warm eyes avoids the old two-tone mascot look.
INK = "#08090e"
SHADOW = "#14161d"
FUR = "#20232c"
MID = "#2b303b"
LIGHT = "#404652"
MOON = "#59616d"
INNER_EAR = "#b87e88"
EYES = "#e3d277"
GLOW = "#fff2a4"
PUPIL = "#10151b"
NOSE = "#e99aa6"
WHISKER = "#a5adb9"
PAW = "#252831"
SPARKLE = "#f1cc83"


class PixelPainter:
    def __init__(self):
        self.p = [[""] * PIXELS for _ in range(PIXELS)]

    def rect(self, a, b, c, d, color):
        for y in range(max(0, int(b)), min(PIXELS, int(d) + 1)):
            for x in range(max(0, int(a)), min(PIXELS, int(c) + 1)):
                self.p[y][x] = color

    def ellipse(self, x1, y1, x2, y2, color):
        cx, cy = (x1+x2)/2, (y1+y2)/2
        rx, ry = max(.5, (x2-x1+1)/2), max(.5, (y2-y1+1)/2)
        for y in range(max(0, y1), min(PIXELS, y2+1)):
            for x in range(max(0, x1), min(PIXELS, x2+1)):
                if ((x-cx)/rx)**2 + ((y-cy)/ry)**2 < 1:
                    self.p[y][x] = color

    def line(self, x1, y1, x2, y2, color):
        n = max(abs(x2-x1), abs(y2-y1), 1)
        for i in range(n+1):
            self.rect(round(x1+(x2-x1)*i/n), round(y1+(y2-y1)*i/n),
                      round(x1+(x2-x1)*i/n), round(y1+(y2-y1)*i/n), color)

    def ears(self, bob=0):
        # Pixel-stepped pointed ears with a small inner pink triangle.
        for x in range(8, 14):
            self.rect(x, 5 + bob + abs(x-10)//2, x, 14+bob, INK)
        for x in range(19, 25):
            self.rect(x, 5 + bob + abs(x-21)//2, x, 14+bob, INK)
        for x in range(9, 13):
            self.rect(x, 8 + bob + abs(x-10)//2, x, 12+bob, INNER_EAR)
        for x in range(20, 24):
            self.rect(x, 8 + bob + abs(x-21)//2, x, 12+bob, INNER_EAR)
        self.rect(10, 8+bob, 11, 10+bob, FUR)
        self.rect(21, 8+bob, 22, 10+bob, FUR)

    def tail(self, frame, side=False):
        flip = (frame % 4) in (1,2)
        if side:
            # An animated curved tail rises behind the walking body.
            self.rect(3, 19, 6, 23, INK)
            self.rect(2, 11 if flip else 13, 4, 21, INK)
            self.rect(3, 8 if flip else 10, 7, 13 if flip else 15, INK)
            self.rect(3, 14, 4, 21, MID)
            self.rect(4, 10 if flip else 12, 6, 11 if flip else 13, FUR)
        else:
            if flip:
                self.rect(24, 20, 27, 24, INK)
                self.rect(27, 13, 29, 23, INK)
                self.rect(25, 10, 28, 14, INK)
                self.rect(28, 15, 28, 21, MID)
            else:
                self.rect(4, 20, 7, 24, INK)
                self.rect(2, 14, 4, 23, INK)
                self.rect(3, 11, 7, 15, INK)
                self.rect(3, 15, 3, 20, MID)

    def face(self, pose, frame, bob=0):
        self.ears(bob)
        self.ellipse(6, 11+bob, 26, 25+bob, INK)
        self.ellipse(7, 12+bob, 25, 24+bob, FUR)
        # Light catching top of the head/cheeks creates depth.
        self.line(10, 13+bob, 13, 12+bob, LIGHT)
        self.line(20, 12+bob, 23, 13+bob, MID)
        self.rect(8, 17+bob, 10, 18+bob, MID)
        self.rect(22, 17+bob, 24, 18+bob, MID)
        closed = pose in ("blink", "sleep") or (pose == "groom" and frame == 3)
        if closed:
            self.line(10, 19+bob, 13, 19+bob, EYES)
            self.line(20, 19+bob, 23, 19+bob, EYES)
        else:
            glance = (1 if frame % 4 == 2 and pose == "look" else 0)
            self.rect(10, 17+bob, 13, 20+bob, EYES)
            self.rect(20, 17+bob, 23, 20+bob, EYES)
            self.rect(12+glance, 17+bob, 12+glance, 20+bob, PUPIL)
            self.rect(22+glance, 17+bob, 22+glance, 20+bob, PUPIL)
            self.rect(10, 17+bob, 10, 17+bob, GLOW)
            self.rect(20, 17+bob, 20, 17+bob, GLOW)
        self.rect(16, 22+bob, 17, 22+bob, NOSE)
        self.rect(16, 23+bob, 16, 24+bob, MID)
        self.line(8, 23+bob, 13, 22+bob, WHISKER)
        self.line(8, 25+bob, 13, 24+bob, MOON)
        self.line(20, 22+bob, 25, 23+bob, WHISKER)
        self.line(20, 24+bob, 25, 25+bob, MOON)
        if pose == "yawn":
            self.ellipse(14, 24+bob, 19, 28+bob, INK)
            self.rect(16, 27+bob, 17, 27+bob, NOSE)

    def sitting(self, pose, frame):
        self.tail(frame)
        self.ellipse(9, 20, 24, 29, INK)
        self.ellipse(10, 21, 23, 28, FUR)
        self.ellipse(11, 21, 20, 25, MID)
        self.rect(11, 27, 14, 30, PAW)
        self.rect(19, 27, 22, 30, PAW)
        self.rect(13, 29, 14, 29, LIGHT)
        self.rect(20, 29, 21, 29, LIGHT)
        self.face(pose, frame, bob=0 if frame < 2 else 1)
        if pose == "groom":
            px = (10 if frame % 2 == 0 else 20)
            self.ellipse(px, 19, px+6, 26, INK)
            self.ellipse(px+1, 19, px+5, 25, FUR)
            self.rect(16, 24, 17, 25, NOSE)
        if pose == "scratch":
            if frame % 2:
                self.rect(22, 15, 25, 19, INK)
                self.rect(23, 13, 25, 16, FUR)
            else:
                self.rect(8, 17, 10, 23, INK)
        if pose == "play":
            # A tiny luminous sparkle appears beyond the outstretched paw.
            self.line(25, 5, 25, 9, SPARKLE)
            self.line(23, 7, 27, 7, SPARKLE)
            self.rect(21 if frame%2 else 23, 16, 26, 19, FUR)
            self.rect(24, 19, 26, 22, INK)

    def side(self, pose, frame):
        bob = (0, -1, 0, 1)[frame % 4] if pose == "walk" else 0
        self.tail(frame, side=True)
        self.ellipse(6, 17+bob, 22, 26+bob, INK)
        self.ellipse(7, 18+bob, 21, 25+bob, FUR)
        self.ellipse(9, 18+bob, 17, 22+bob, MID)
        self.line(9, 19+bob, 15, 18+bob, LIGHT)
        # Profile: pointed ears, expressive single gold eye, soft cheek.
        self.rect(19, 9+bob, 22, 18+bob, INK)
        self.rect(24, 10+bob, 27, 18+bob, INK)
        self.rect(20, 11+bob, 21, 15+bob, INNER_EAR)
        self.rect(25, 12+bob, 26, 15+bob, INNER_EAR)
        self.ellipse(17, 13+bob, 30, 24+bob, INK)
        self.ellipse(18, 14+bob, 29, 23+bob, FUR)
        self.line(20, 15+bob, 23, 14+bob, LIGHT)
        self.rect(25, 18+bob, 27, 20+bob, EYES)
        self.rect(27, 18+bob, 27, 20+bob, PUPIL)
        self.rect(29, 21+bob, 30, 21+bob, NOSE)
        self.line(26, 23+bob, 30, 24+bob, WHISKER)
        self.line(26, 24+bob, 30, 26+bob, MOON)
        if pose == "walk":
            legs = ((9, 22), (11, 20), (12, 19), (10, 21))[frame % 4]
            self.rect(legs[0], 24+bob, legs[0]+2, 28+bob, INK)
            self.rect(legs[1], 27+bob, legs[1]+4, 29+bob, PAW)
            self.rect(22 if frame % 2 else 20, 24+bob,
                      24 if frame % 2 else 22, 29+bob, INK)
        elif pose == "stretch":
            self.rect(6, 24, 17, 27, FUR)
            self.rect(17, 25, 29, 27, PAW)
            self.rect(6, 26, 11, 29, INK)
        else:
            self.rect(10, 25, 14, 29, PAW)
            self.rect(21, 25, 25, 29, PAW)

    def sleeping(self, frame):
        self.ellipse(5, 17, 28, 29, INK)
        self.ellipse(6, 18, 27, 28, FUR)
        self.ellipse(9, 19, 22, 27, MID)
        self.rect(7, 15, 10, 21, INK)
        self.rect(21, 14, 24, 21, INK)
        self.rect(8, 17, 9, 19, INNER_EAR)
        self.rect(22, 16, 23, 19, INNER_EAR)
        self.ellipse(11, 19, 25, 27, FUR)
        self.line(14, 22, 17, 22, EYES)
        self.line(20, 22, 23, 22, EYES)
        self.rect(19, 24, 20, 24, NOSE)
        self.line(11, 25, 15, 24, WHISKER)
        self.ellipse(9, 26, 20, 30, INK)
        self.ellipse(10, 27, 19, 29, MID)
        # A tiny, animated breathing highlight and optional sleepy sparkles.
        if frame in (1, 2):
            self.rect(13, 19, 18, 19, LIGHT)
        if frame == 3:
            self.line(25, 7, 27, 7, SPARKLE)
            self.line(26, 6, 26, 8, SPARKLE)

    def image(self, pose, facing, frame):
        frame %= 4
        if pose == "sleep":
            self.sleeping(frame)
        elif pose in ("walk", "stretch"):
            self.side(pose, frame)
        else:
            self.sitting(pose, frame)
        if facing < 0 and pose in ("walk", "stretch"):
            self.p = [list(reversed(row)) for row in self.p]
        return tuple(tuple(row) for row in self.p)


def sprite_pixels(pose, facing=1, frame=0):
    """Return immutable 32×32 RGB/transparent pixel rows for tests/rendering."""
    if pose not in POSES:
        raise ValueError("Unknown cat pose")
    return PixelPainter().image(pose, facing, frame)
