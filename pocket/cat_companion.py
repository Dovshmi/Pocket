"""Optional, self-contained oneko-style black cat for Pocket's Windows window.

Original pixel art and a local-only motion engine. The companion uses its own
small, transparent Win32 click-through Toplevel, never a canvas across Pocket's
real widgets. It cannot capture keystrokes, clicks, clipboard, or network data.

The model is deliberately Tk-free so it can be tested on Windows and Linux.
"""
from __future__ import annotations

import ctypes
import math
import random
import sys
import tkinter as tk

SIZE = 48
TICK_MS = 145
KEY_COLOR = "#ff00ff"  # Transparent window color; not present in cat sprites.
POSES = ("walk", "sit", "blink", "groom", "sleep", "stretch", "scratch")
FUR = "#07090d"
FUR_LIGHT = "#191d24"
EDGE = "#4f5663"
EYES = "#addf90"
NOSE = "#e58a9f"
WHISKER = "#a4a6b1"


def _limit(value, low, high):
    return max(low, min(value, high))


class CatMotion:
    """Bounded, independent roaming with occasional cursor curiosity.

    Uses no system/global hooks. Pointer coordinates are optional ephemeral
    local-window coordinates and are neither stored nor persisted.
    """

    def __init__(self, seed=None):
        self.random = random.Random(seed)
        self.x = 16.0
        self.y = 130.0
        self.target = None
        self.pose = "sit"
        self.facing = 1
        self.frame = 0
        self.remaining = 16
        self.steps = 0
        self.last_pointer = None

    @staticmethod
    def limits(width, height):
        return (8.0, max(8.0, float(width - SIZE - 8)),
                32.0, max(32.0, float(height - SIZE - 8)))

    def _choose_destination(self, width, height, pointer):
        left, right, top, bottom = self.limits(width, height)
        # Most adventures take place at the window edges so editable content
        # stays visually unobstructed, although all pointer clicks pass through.
        if pointer and self.random.random() < 0.21:
            px, py = pointer
            self.target = (_limit(px - SIZE / 2, left, right),
                           _limit(py - SIZE / 2, top, bottom))
        else:
            edge = self.random.randrange(4)
            margin_x = self.random.uniform(left, right)
            margin_y = self.random.uniform(top, bottom)
            self.target = (
                (margin_x, top) if edge == 0 else
                (margin_x, bottom) if edge == 1 else
                (left, margin_y) if edge == 2 else
                (right, margin_y)
            )
        self.pose = "walk"
        self.remaining = 0

    def _rest(self):
        roll = self.random.random()
        if roll < 0.14:
            self.pose, self.remaining = "sleep", self.random.randrange(45, 105)
        elif roll < 0.33:
            self.pose, self.remaining = "groom", self.random.randrange(12, 29)
        elif roll < 0.48:
            self.pose, self.remaining = "stretch", self.random.randrange(8, 17)
        elif roll < 0.61:
            self.pose, self.remaining = "scratch", self.random.randrange(10, 23)
        else:
            self.pose, self.remaining = "sit", self.random.randrange(12, 42)
        self.target = None

    def step(self, width, height, pointer=None):
        """Advance one frame; return (x, y, pose, facing, frame).

        Size changes re-clamp the state so no teleport outside Mini/Extra Mini.
        """
        left, right, top, bottom = self.limits(width, height)
        self.x = _limit(self.x, left, right)
        self.y = _limit(self.y, top, bottom)
        if self.target is not None:
            self.target = (_limit(self.target[0], left, right),
                           _limit(self.target[1], top, bottom))
        self.steps += 1
        self.frame = (self.steps // 3) % 2

        if pointer is not None:
            pointer = (float(pointer[0]), float(pointer[1]))
            if not (0 <= pointer[0] < width and 0 <= pointer[1] < height):
                pointer = None
        changed = (pointer is not None and self.last_pointer is not None and
                   math.dist(pointer, self.last_pointer) > 34)
        self.last_pointer = pointer

        if self.pose != "walk":
            # An abrupt local cursor movement can wake a sleeping cat.
            if self.pose == "sleep" and changed:
                self.remaining = 0
            if self.remaining > 0:
                self.remaining -= 1
                pose = "blink" if self.pose == "sit" and self.remaining % 23 == 0 else self.pose
                return (round(self.x), round(self.y), pose, self.facing, self.frame)
            self._choose_destination(width, height, pointer)

        tx, ty = self.target if self.target is not None else (self.x, self.y)
        dx, dy = tx - self.x, ty - self.y
        distance = math.hypot(dx, dy)
        if distance <= 3:
            self.x, self.y = tx, ty
            self._rest()
        else:
            velocity = 2.75 if distance < 125 else 3.7
            self.x += velocity * dx / distance
            self.y += velocity * dy / distance
            if abs(dx) > 0.75:
                self.facing = 1 if dx > 0 else -1

        return (round(self.x), round(self.y), self.pose, self.facing, self.frame)


class _Pixels:
    """Draw a tiny original, hard-edged 24×24 black-cat sprite in memory."""

    def __init__(self):
        self.grid = [[""] * 24 for _ in range(24)]

    def rect(self, x1, y1, x2, y2, color):
        for y in range(max(0, y1), min(24, y2 + 1)):
            for x in range(max(0, x1), min(24, x2 + 1)):
                self.grid[y][x] = color

    def ellipse(self, x1, y1, x2, y2, color):
        cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
        rx, ry = max(0.5, (x2 - x1 + 1) / 2), max(0.5, (y2 - y1 + 1) / 2)
        for y in range(max(0, y1), min(24, y2 + 1)):
            for x in range(max(0, x1), min(24, x2 + 1)):
                if ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1:
                    self.grid[y][x] = color

    def tail(self, facing, motion):
        if facing > 0:
            self.rect(2, 17, 5, 19, EDGE)
            self.rect(2, 10, 4, 17, EDGE)
            self.rect(3, 8 if motion else 9, 6, 11, EDGE)
            self.rect(3, 10, 4, 17, FUR)
        else:
            self.rect(18, 17, 21, 19, EDGE)
            self.rect(20, 10, 22, 17, EDGE)
            self.rect(18, 8 if motion else 9, 21, 11, EDGE)
            self.rect(20, 10, 21, 17, FUR)

    def front(self, pose, frame):
        self.tail(1 if frame else -1, frame)
        self.ellipse(6, 11, 19, 22, EDGE)
        self.ellipse(7, 12, 18, 21, FUR)
        self.rect(8, 18, 10, 22, FUR_LIGHT)
        self.rect(15, 18, 17, 22, FUR_LIGHT)
        # Two triangular ears (small straight pixel steps, no smoothing).
        self.rect(6, 4, 10, 10, EDGE)
        self.rect(15, 4, 19, 10, EDGE)
        self.rect(7, 6, 10, 10, FUR)
        self.rect(15, 6, 18, 10, FUR)
        self.ellipse(5, 7, 20, 17, EDGE)
        self.ellipse(6, 8, 19, 16, FUR)
        self.rect(8, 10, 10, 12, FUR_LIGHT)
        self.rect(15, 10, 17, 12, FUR_LIGHT)
        if pose == "blink":
            self.rect(8, 12, 10, 12, EYES)
            self.rect(15, 12, 17, 12, EYES)
        elif pose == "sleep":
            self.rect(9, 13, 11, 13, EYES)
            self.rect(15, 13, 17, 13, EYES)
        else:
            self.rect(9, 11, 10, 12, EYES)
            self.rect(16, 11, 17, 12, EYES)
        self.rect(12, 14, 13, 14, NOSE)
        self.rect(4, 14, 7, 14, WHISKER)
        self.rect(18, 14, 21, 14, WHISKER)
        if pose == "groom":
            if frame:
                self.rect(14, 13, 17, 18, EDGE)
                self.rect(15, 13, 17, 17, FUR)
            else:
                self.rect(7, 14, 10, 19, EDGE)
                self.rect(7, 14, 9, 18, FUR)
            self.rect(12, 16, 14, 17, NOSE)
        if pose == "scratch":
            self.rect(7 if frame else 16, 6, 9 if frame else 18, 10, EDGE)
        if pose == "stretch":
            self.rect(6, 20, 19, 22, EDGE)

    def side(self, pose, frame):
        self.tail(1, frame)
        bob = 1 if pose == "walk" and frame else 0
        self.ellipse(5, 12 + bob, 18, 20 + bob, EDGE)
        self.ellipse(6, 13 + bob, 17, 19 + bob, FUR)
        # Rounded head and sharp silhouette ears.
        self.rect(16, 6 + bob, 19, 11 + bob, EDGE)
        self.rect(20, 8 + bob, 22, 13 + bob, EDGE)
        self.rect(17, 7 + bob, 19, 11 + bob, FUR)
        self.ellipse(14, 10 + bob, 23, 17 + bob, EDGE)
        self.ellipse(15, 11 + bob, 22, 16 + bob, FUR)
        self.rect(19, 12 + bob, 20, 13 + bob, EYES)
        self.rect(22, 15 + bob, 23, 15 + bob, NOSE)
        self.rect(21, 16 + bob, 23, 16 + bob, WHISKER)
        # Alternating feet create a genuine two-frame walking cycle.
        if pose == "walk":
            self.rect(8 if frame else 10, 19, 10 if frame else 12, 22, EDGE)
            self.rect(16 if frame else 14, 19, 18 if frame else 16, 22, EDGE)
        elif pose == "stretch":
            self.rect(6, 19, 12, 21, EDGE)
            self.rect(15, 19, 22, 21, EDGE)
        else:
            self.rect(9, 19, 11, 22, EDGE)
            self.rect(17, 19, 19, 22, EDGE)

    def sleep(self, frame):
        self.ellipse(4, 12, 20, 22, EDGE)
        self.ellipse(5, 13, 19, 21, FUR)
        self.rect(5, 10, 9, 15, EDGE)
        self.rect(13, 11, 16, 15, EDGE)
        self.ellipse(7, 13, 18, 20, FUR_LIGHT)
        self.ellipse(7, 14, 17, 19, FUR)
        self.rect(10, 16, 12, 16, EYES)
        self.rect(14, 16, 16, 16, EYES)
        self.rect(13, 18, 14, 18, NOSE)
        if frame:
            self.rect(19, 6, 21, 6, WHISKER)
            self.rect(21, 4, 22, 4, WHISKER)
            self.rect(19, 2, 21, 2, WHISKER)

    def make(self, pose, facing, frame):
        if pose == "sleep":
            self.sleep(frame)
        elif pose in ("walk", "stretch"):
            self.side(pose, frame)
        else:
            self.front(pose, frame)
        if facing < 0 and pose in ("walk", "stretch"):
            self.grid = [list(reversed(row)) for row in self.grid]
        return tuple(tuple(row) for row in self.grid)


def sprite_pixels(pose, facing=1, frame=0):
    """Provide raw pixels for deterministic art tests, without a display."""
    if pose not in POSES:
        raise ValueError("Unknown cat animation pose")
    return _Pixels().make(pose, facing, frame)


def _photo(root, pixels):
    """Render transparent 2× pixel art using only Tk's built-in PhotoImage."""
    image = tk.PhotoImage(master=root, width=SIZE, height=SIZE)
    for y, row in enumerate(pixels):
        x = 0
        while x < len(row):
            color = row[x]
            end = x + 1
            while end < len(row) and row[end] == color:
                end += 1
            if color:
                image.put(color, to=(x * 2, y * 2, end * 2, y * 2 + 2))
            x = end
    return image


class PocketCat:
    """Windows-only click-through overlay that follows Pocket's geometry.

    On unsupported systems or if OS hit-test transparency cannot be established
    the feature fails closed (no popup), not as an invisible input blocker.
    """

    def __init__(self, root):
        self.root = root
        self.motion = CatMotion()
        self.window = None
        self.canvas = None
        self.sprite = None
        self.images = {}
        self.enabled = False
        self.failed = False
        self.visible = False

    def enable(self, value):
        self.enabled = bool(value)
        if not self.enabled:
            self.hide()

    @staticmethod
    def _protect_window(window):
        """Make the *native wrapper* transparent to hit tests and focus.

        Tk can replace native extended styles during the initial mapping of
        an overrideredirect Toplevel; call both before and after deiconify.
        """
        user32 = ctypes.windll.user32
        user32.GetParent.argtypes = [ctypes.c_void_p]
        user32.GetParent.restype = ctypes.c_void_p
        user32.GetWindowLongW.argtypes = [ctypes.c_void_p, ctypes.c_int]
        user32.GetWindowLongW.restype = ctypes.c_long
        user32.SetWindowLongW.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_long]
        user32.SetWindowLongW.restype = ctypes.c_long
        user32.SetWindowPos.argtypes = [
            ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int, ctypes.c_int,
            ctypes.c_int, ctypes.c_int, ctypes.c_uint]
        user32.SetWindowPos.restype = ctypes.c_bool
        handle = user32.GetParent(window.winfo_id()) or window.winfo_id()
        necessary = 0x20 | 0x08000000 | 0x80
        style = user32.GetWindowLongW(handle, -20)
        if style & necessary != necessary:
            user32.SetWindowLongW(handle, -20, style | necessary)
            # SWP_FRAMECHANGED applies the style without activating or moving.
            if not user32.SetWindowPos(handle, ctypes.c_void_p(-1),
                                       0, 0, 0, 0, 0x0033):
                raise RuntimeError("Cannot apply nonactivating overlay styles")
        if user32.GetWindowLongW(handle, -20) & necessary != necessary:
            raise RuntimeError("Cannot make Pocket Cat click-through")

    def _make_window(self):
        if sys.platform != "win32":
            self.failed = True
            return
        window = None
        try:
            window = tk.Toplevel(self.root)
            window.withdraw()
            window.overrideredirect(True)
            window.attributes("-transparentcolor", KEY_COLOR)
            window.attributes("-topmost", True)
            window.configure(bg=KEY_COLOR)
            window.geometry(f"{SIZE}x{SIZE}+0+0")
            canvas = tk.Canvas(window, width=SIZE, height=SIZE, bg=KEY_COLOR,
                               highlightthickness=0, bd=0, relief="flat")
            canvas.pack(fill="both", expand=True)
            images = {}
            for pose in POSES:
                for direction in (-1, 1):
                    for frame in (0, 1):
                        images[(pose, direction, frame)] = _photo(
                            window, sprite_pixels(pose, direction, frame))
            sprite = canvas.create_image(0, 0, anchor="nw", image=images[("sit", 1, 0)])
            # Initial protection; Tk can rewrite extended styles when a
            # withdrawn Toplevel is mapped, so reapply after deiconify too.
            self._protect_window(window)
            self.window, self.canvas, self.sprite, self.images = (
                window, canvas, sprite, images)
        except (tk.TclError, AttributeError, OSError, RuntimeError):
            if window is not None:
                try:
                    window.destroy()
                except tk.TclError:
                    pass
            self.failed = True

    def _after_map(self):
        """Restore transparency once Tk has finished mapping the native HWND."""
        if not self.enabled or not self.visible or self.window is None:
            return
        try:
            self._protect_window(self.window)
        except (tk.TclError, AttributeError, OSError, RuntimeError):
            self.failed = True
            self.hide()

    def hide(self):
        if self.window is not None and self.visible:
            try:
                self.window.withdraw()
            except tk.TclError:
                pass
        self.visible = False

    def tick(self, *, blocked=False):
        """Called by Pocket's existing Tk UI thread, never a background thread."""
        if not self.enabled or self.failed or blocked or sys.platform != "win32":
            self.hide()
            return
        try:
            if self.root.state() != "normal" or not self.root.winfo_viewable():
                self.hide()
                return
            if self.window is None:
                self._make_window()
            if self.window is None:
                return
            x, y = self.root.winfo_rootx(), self.root.winfo_rooty()
            width, height = self.root.winfo_width(), self.root.winfo_height()
            px, py = self.root.winfo_pointerx() - x, self.root.winfo_pointery() - y
            pointer = (px, py) if 0 <= px < width and 0 <= py < height else None
            cx, cy, pose, direction, frame = self.motion.step(width, height, pointer)
            image = self.images[(pose, direction, frame)]
            self.canvas.itemconfigure(self.sprite, image=image)
            self.window.geometry(f"{SIZE}x{SIZE}+{x + cx}+{y + cy}")
            if not self.visible:
                self.window.deiconify()
                # Native styles may be reset by a later Tk <Map> event. Apply
                # now and again after mapping completes, before user input.
                self._protect_window(self.window)
                self.visible = True
                self.window.after_idle(self._after_map)
            else:
                self._protect_window(self.window)
        except (tk.TclError, RuntimeError, OSError):
            self.hide()
            self.failed = True

    def destroy(self):
        self.hide()
        if self.window is not None:
            try:
                self.window.destroy()
            except tk.TclError:
                pass
        self.window = None
        self.canvas = None
        self.images.clear()
