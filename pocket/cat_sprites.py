"""Polished original pixel animation for Pocket's autonomous black cat.

36x36 authored, layered charcoal sprite art with subtle contrast, organic
eight-frame motion and distinct gestures. Entirely local: no assets, downloads,
Pillow or animation threads. Tk scales the sprites to available safe space.
"""
from __future__ import annotations

from functools import lru_cache
import math

PIXELS = 36
FRAMES = 8
POSES = ("walk", "sit", "blink", "look", "groom", "sleep", "stretch",
         "scratch", "play", "yawn", "purr")

# Dark fur with a cool rim-light and warm, friendly eyes.
INK = "#090b13"
OUTLINE = "#10141e"
SHADOW = "#171c27"
FUR = "#242b37"
MID = "#343e4e"
LIGHT = "#526077"
MOON = "#69798e"
INNER_EAR = "#c38a9c"
EYES = "#bbf4a4"
GLOW = "#eefdd6"
PUPIL = "#0a1420"
NOSE = "#f2a3b9"
WHISKER = "#8e9cac"
PAW = "#303744"
SPARKLE = "#f4d68f"
HEART = "#d8a2bd"


class Painter:
    def __init__(self):
        self.grid = [[""] * PIXELS for _ in range(PIXELS)]

    def rect(self, x1, y1, x2, y2, color):
        x1, y1, x2, y2 = map(round, (x1, y1, x2, y2))
        for y in range(max(0, y1), min(PIXELS, y2 + 1)):
            for x in range(max(0, x1), min(PIXELS, x2 + 1)):
                self.grid[y][x] = color

    def dot(self, x, y, color):
        self.rect(x, y, x, y, color)

    def oval(self, x1, y1, x2, y2, color):
        cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
        rx = max(.5, (x2 - x1 + 1) / 2)
        ry = max(.5, (y2 - y1 + 1) / 2)
        for y in range(max(0, int(y1)), min(PIXELS, int(y2) + 1)):
            for x in range(max(0, int(x1)), min(PIXELS, int(x2) + 1)):
                if ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= .98:
                    self.grid[y][x] = color

    def line(self, x1, y1, x2, y2, color, thickness=0):
        count = max(abs(x2 - x1), abs(y2 - y1), 1)
        for index in range(int(count) + 1):
            xx = round(x1 + (x2-x1)*index/count)
            yy = round(y1 + (y2-y1)*index/count)
            self.rect(xx-thickness, yy-thickness, xx+thickness, yy+thickness, color)

    def tail(self, frame, side=False):
        # The joint is stationary, while the tip follows a smooth 8-frame arc.
        sway = (0, 1, 2, 2, 1, 0, -1, -1)[frame]
        if side:
            self.oval(3, 18, 10, 29, OUTLINE)
            self.line(5, 23, 4 + sway, 14, INK, 2)
            self.line(4 + sway, 14, 7 + sway, 9, INK, 2)
            self.line(5 + sway, 13, 8 + sway, 10, LIGHT)
            self.dot(6 + sway, 10, MID)
        elif frame < 4:
            self.line(28, 28, 31, 19, INK, 2)
            self.line(31, 19, 28 + sway//2, 12, INK, 2)
            self.line(31, 22, 30, 17, MID)
            self.dot(29 + sway//2, 12, LIGHT)
        else:
            self.line(8, 28, 4, 19, INK, 2)
            self.line(4, 19, 6 - sway//2, 12, INK, 2)
            self.line(4, 22, 5, 17, MID)
            self.dot(6 - sway//2, 12, LIGHT)

    def ears(self, bob=0, twitch=False):
        # Compact, genuine stepped triangles rather than square protrusions.
        for x in range(8, 15):
            self.rect(x, 6 + bob + abs(x-10)//2, x, 15 + bob, OUTLINE)
        for x in range(21, 28):
            self.rect(x, 6 + bob + abs(x-25)//2 - (1 if twitch else 0),
                      x, 15 + bob, OUTLINE)
        for x in range(10, 14):
            self.rect(x, 10 + bob + abs(x-11)//2, x, 14 + bob, INNER_EAR)
        for x in range(22, 26):
            self.rect(x, 10 + bob + abs(x-24)//2, x, 14 + bob, INNER_EAR)
        self.line(9, 8+bob, 9, 12+bob, LIGHT)
        self.line(26, 8+bob, 26, 12+bob, MID)

    def face(self, pose, frame, bob=0):
        self.ears(bob, twitch=(pose == "look" and frame in (5, 6)))
        # Subtle layered facial planes preserve a black-cat silhouette.
        self.oval(6, 12+bob, 29, 29+bob, OUTLINE)
        self.oval(7, 13+bob, 28, 28+bob, FUR)
        self.line(10, 16+bob, 16, 14+bob, LIGHT)
        self.line(20, 14+bob, 26, 16+bob, MID)
        self.oval(7, 23+bob, 14, 28+bob, MID)
        self.oval(21, 23+bob, 28, 28+bob, MID)
        self.oval(12, 23+bob, 23, 28+bob, FUR)

        closed = pose in ("blink", "sleep") or (pose == "groom" and frame > 5)
        sleepy = pose == "yawn"
        if closed:
            self.line(11, 21+bob, 15, 21+bob, EYES)
            self.line(21, 21+bob, 25, 21+bob, EYES)
            self.dot(12, 22+bob, MID)
            self.dot(24, 22+bob, MID)
        elif sleepy:
            self.line(11, 21+bob, 15, 21+bob, EYES)
            self.line(21, 21+bob, 25, 21+bob, EYES)
        else:
            glance = (1 if frame in (3, 4, 5) and pose == "look" else
                      -1 if frame in (6, 7) and pose == "look" else 0)
            for xx in (11, 21):
                self.oval(xx, 18+bob, xx+5, 23+bob, MID)
                self.rect(xx+1, 19+bob, xx+4, 22+bob, EYES)
                self.line(xx+2+glance, 19+bob, xx+2+glance, 22+bob, PUPIL)
                self.dot(xx+1, 19+bob, GLOW)

        self.rect(17, 25+bob, 18, 25+bob, NOSE)
        self.line(17, 26+bob, 17, 27+bob, SHADOW)
        self.dot(15, 27+bob, LIGHT)
        self.dot(20, 27+bob, LIGHT)
        self.line(7, 25+bob, 13, 24+bob, WHISKER)
        self.line(7, 27+bob, 13, 26+bob, MOON)
        self.line(23, 24+bob, 29, 25+bob, WHISKER)
        self.line(23, 26+bob, 29, 27+bob, MOON)
        if pose == "yawn":
            self.oval(15, 27+bob, 20, 31+bob, INK)
            self.rect(17, 30+bob, 18, 30+bob, NOSE)

    def sit(self, pose, frame):
        breath = (0, 0, -1, -1, 0, 0, 1, 0)[frame]
        self.tail(frame)
        self.oval(9, 20, 27, 34, OUTLINE)
        self.oval(10, 21, 26, 33, SHADOW)
        self.oval(12, 23, 24, 32, FUR)
        self.oval(15, 23, 21, 31, MID)
        self.line(13, 28, 15, 31, LIGHT)
        self.line(21, 31, 23, 28, MID)
        self.rect(12, 30, 16, 34, PAW)
        self.rect(20, 30, 24, 34, PAW)
        for x in (14, 22):
            self.dot(x, 33, LIGHT)
        self.face(pose, frame, bob=breath)

        if pose == "groom":
            paw_x = (11, 12, 15, 18, 22, 23, 19, 15)[frame]
            self.oval(paw_x-2, 22, paw_x+2, 28, OUTLINE)
            self.oval(paw_x-1, 23, paw_x+1, 27, FUR)
            if frame in (2, 3, 5, 6):
                self.dot(17, 28, NOSE)
        if pose == "scratch":
            ear_x = 25 if frame % 2 == 0 else 27
            self.line(ear_x, 19, ear_x-1, 12, OUTLINE, 2)
            self.dot(ear_x, 14, LIGHT)
        if pose == "play":
            px = (24, 26, 28, 29, 29, 27, 25, 24)[frame]
            py = (22, 19, 16, 15, 15, 17, 20, 23)[frame]
            self.line(23, 27, px, py, OUTLINE, 2)
            if frame in (0, 3, 4, 7):
                self.line(28, 8, 28, 12, SPARKLE)
                self.line(26, 10, 30, 10, SPARKLE)
        if pose == "purr":
            self.dot(11, 24, INNER_EAR)
            self.dot(25, 24, INNER_EAR)
            if frame in (2, 3, 4, 5):
                # Floating micro-heart remains inside the existing sprite.
                self.rect(17, 5, 17, 6, HEART)
                self.rect(20, 5, 20, 6, HEART)
                self.line(17, 6, 20, 9, HEART)
                self.line(20, 6, 17, 9, HEART)
                self.dot(18, 10, HEART)

    def walk(self, pose, frame):
        # Eight steps: alternating diagonal paws, realistic squash/stretch and
        # slight head bob rather than simply shifting a static rectangle.
        bounce = (0, -1, -2, -1, 0, 1, 1, 0)[frame] if pose == "walk" else 0
        self.tail(frame, side=True)
        self.oval(7, 17+bounce, 26, 29+bounce, OUTLINE)
        self.oval(8, 18+bounce, 25, 28+bounce, SHADOW)
        self.oval(10, 19+bounce, 24, 27+bounce, FUR)
        self.line(12, 20+bounce, 21, 19+bounce, LIGHT)
        self.line(10, 26+bounce, 16, 27+bounce, MID)

        # Legs are behind the head and the gait cycles independently.
        if pose == "walk":
            legs = ((10, 24), (11, 24), (13, 22), (15, 20),
                    (15, 20), (13, 22), (11, 24), (10, 24))
            left, right = legs[frame]
            self.rect(left, 26+bounce, left+2, 32+bounce, OUTLINE)
            self.rect(right, 27+bounce, right+3, 32+bounce, PAW)
            self.rect(23 if frame < 4 else 21, 27+bounce,
                      25 if frame < 4 else 23, 32+bounce, OUTLINE)
            self.dot(left+1, 32+bounce, LIGHT)
        elif pose == "stretch":
            self.rect(7, 27, 18, 29, FUR)
            self.rect(19, 29, 32, 30, PAW)
            self.rect(7, 28, 12, 33, OUTLINE)

        # Pointed profile ears and a soft round muzzle.
        self.rect(23, 9+bounce, 26, 19+bounce, OUTLINE)
        self.rect(28, 10+bounce, 31, 18+bounce, OUTLINE)
        self.rect(24, 11+bounce, 25, 16+bounce, INNER_EAR)
        self.rect(29, 12+bounce, 30, 16+bounce, INNER_EAR)
        self.oval(21, 14+bounce, 34, 28+bounce, OUTLINE)
        self.oval(22, 15+bounce, 33, 27+bounce, FUR)
        self.line(24, 16+bounce, 28, 15+bounce, LIGHT)
        self.oval(28, 20+bounce, 31, 23+bounce, EYES)
        self.line(30, 20+bounce, 30, 23+bounce, PUPIL)
        self.dot(28, 20+bounce, GLOW)
        self.dot(34, 25+bounce, NOSE)
        self.line(30, 27+bounce, 35, 28+bounce, WHISKER)

    def sleep(self, frame):
        # Tight croissant shape, curled tail, rising and falling shoulder.
        breath = (0, 0, 1, 1, 1, 0, -1, -1)[frame]
        self.oval(4, 17, 32, 33, OUTLINE)
        self.oval(6, 18, 30, 32, FUR)
        self.oval(11, 20+breath, 27, 30+breath, MID)
        self.oval(15, 21+breath, 30, 31+breath, SHADOW)
        self.oval(16, 21+breath, 28, 30+breath, FUR)
        self.rect(20, 17+breath, 23, 23+breath, INNER_EAR)
        self.rect(27, 16+breath, 29, 22+breath, INNER_EAR)
        self.line(18, 25+breath, 21, 25+breath, EYES)
        self.line(25, 25+breath, 28, 25+breath, EYES)
        self.dot(23, 28+breath, NOSE)
        self.oval(7, 26, 19, 34, OUTLINE)
        self.oval(8, 27, 18, 33, MID)
        self.line(8, 29, 15, 31, LIGHT)
        if frame in (3, 4):
            self.line(27, 10, 30, 10, SPARKLE)
            self.dot(29, 8, SPARKLE)

    def image(self, pose, facing, frame):
        frame = int(frame) % FRAMES
        if pose == "sleep":
            self.sleep(frame)
        elif pose in ("walk", "stretch"):
            self.walk(pose, frame)
        else:
            self.sit(pose, frame)
        if facing < 0 and pose in ("walk", "stretch"):
            self.grid = [list(reversed(row)) for row in self.grid]
        return tuple(tuple(row) for row in self.grid)


@lru_cache(maxsize=POSES.__len__() * 2 * FRAMES)
def sprite_pixels(pose, facing=1, frame=0):
    """Return immutable 36×36 pixels; '' means fully transparent."""
    if pose not in POSES:
        raise ValueError("Unknown cat pose")
    return Painter().image(pose, facing, frame)
