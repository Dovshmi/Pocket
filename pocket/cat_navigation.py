"""Tiny local pathfinding brain for a cat that must NOT cover Pocket controls.

This module is GUI-free. It treats editable fields, result views, labels and
buttons as obstacles, and walks only through fully clear rectangles. A blocked
or overcrowded layout makes the cat rest/hide, never overlap user data.
"""
from __future__ import annotations

from collections import deque
import math
import random

from .cat_sprites import FRAMES


def overlaps(a, b):
    """True for rectangles with positive intersection area."""
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


class SafeSpace:
    """Navigable grid of positions for a rectangular (unobtrusive) sprite.

    The obstacles are given in window-local screen pixels, not widget contents.
    Occupancy includes the *entire sprite footprint*, not its center point.
    """

    def __init__(self, width, height, size=40, obstacles=(), spacing=14):
        self.width = max(1, int(width))
        self.height = max(1, int(height))
        self.size = max(1, int(size))
        self.spacing = max(8, int(spacing))
        self.obstacles = tuple(
            tuple(int(value) for value in rect)
            for rect in obstacles if len(rect) == 4 and rect[0] < rect[2] and rect[1] < rect[3])
        self.xs = self._axis(max(0, self.width - self.size))
        self.ys = self._axis(max(0, self.height - self.size))
        self.points = {}
        for iy, y in enumerate(self.ys):
            for ix, x in enumerate(self.xs):
                if self.clear(x, y):
                    self.points[(ix, iy)] = (x, y)
        self._neighbors_cache = {}

    def _axis(self, maximum):
        if not maximum:
            return (0,)
        values = list(range(0, maximum + 1, self.spacing))
        if values[-1] != maximum:
            values.append(maximum)
        return tuple(values)

    @property
    def available(self):
        return bool(self.points)

    def clear(self, x, y):
        """Reject any overlap with visible widgets, including padded margins."""
        if x < 0 or y < 0 or x + self.size > self.width or y + self.size > self.height:
            return False
        body = (x, y, x + self.size, y + self.size)
        return not any(overlaps(body, obstacle) for obstacle in self.obstacles)

    def _swept_clear(self, a, b):
        """Reject even thin widgets between two otherwise safe grid points."""
        x1, y1 = a
        x2, y2 = b
        sweep = (min(x1, x2), min(y1, y2),
                 max(x1, x2) + self.size, max(y1, y2) + self.size)
        return not any(overlaps(sweep, rect) for rect in self.obstacles)

    def nearest(self, x, y):
        if not self.points:
            return None
        return min(self.points, key=lambda key: (
            (self.points[key][0]-x)**2 + (self.points[key][1]-y)**2))

    def neighbors(self, node):
        if node in self._neighbors_cache:
            return self._neighbors_cache[node]
        x, y = self.points[node]
        result = []
        for dx, dy in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            nxt = node[0] + dx, node[1] + dy
            if nxt in self.points and self._swept_clear((x, y), self.points[nxt]):
                result.append(nxt)
        self._neighbors_cache[node] = tuple(result)
        return self._neighbors_cache[node]

    def route(self, start_x, start_y, rng, pointer=None):
        """Return a collision-free list of waypoints along a reachable path.

        A breadth-first search avoids the wall-crossing/teleport behavior of
        straight-line random movement. It is bounded by reachable grid cells.
        """
        start = self.nearest(start_x, start_y)
        if start is None:
            return []
        seen = {start: None}
        queue = deque([start])
        while queue:
            node = queue.popleft()
            for neighbor in self.neighbors(node):
                if neighbor not in seen:
                    seen[neighbor] = node
                    queue.append(neighbor)
        if len(seen) < 2:
            return []
        sx, sy = self.points[start]
        candidates = [key for key in seen if key != start and
                      24 < math.dist((sx, sy), self.points[key]) < 260]
        if not candidates:
            candidates = [key for key in seen if key != start]
        if pointer is not None and rng.random() < 0.16:
            # Curious cat can approach the pointer only via safe navigation.
            goal = min(candidates, key=lambda key: math.dist(self.points[key], pointer))
        else:
            # Favor quiet edges/corners over busy central content.
            def edge_weight(key):
                x, y = self.points[key]
                edge = min(x, y, self.width-self.size-x, self.height-self.size-y)
                return 1.0 / (1.0 + edge / 45)
            picks = rng.sample(candidates, min(30, len(candidates)))
            goal = max(picks, key=lambda key: edge_weight(key) * rng.uniform(.6, 1.4))
        path = []
        while goal != start:
            path.append(self.points[goal])
            goal = seen[goal]
        path.reverse()
        return path


class CatMotion:
    """Original, deterministic autonomous animations with collision-free paths."""

    def __init__(self, seed=None):
        self.random = random.Random(seed)
        self.x = 0.0
        self.y = 0.0
        self.pose = "sit"
        self.facing = 1
        self.frame = 0
        self.remaining = 22
        self.steps = 0
        self.route = []
        self.last_pointer = None
        self._free_space = None
        self._last_space = None
        # Local personality state, never inferred from notes or clipboard.
        self.energy = .82
        self._hover_ticks = 0
        self._purr_cooldown = 0

    @staticmethod
    def limits(width, height):
        # Legacy public test helper; actual size-aware positions use SafeSpace.
        return 0.0, max(0.0, width - 40.0), 0.0, max(0.0, height - 40.0)

    def _rest(self):
        roll = self.random.random()
        # A tired cat rests longer, recovers energy and explores again later.
        if self.energy < .28 or roll < .16:
            self.pose, self.remaining = "sleep", self.random.randint(55, 115)
            self.energy = min(1.0, self.energy + .24)
        elif roll < .35:
            self.pose, self.remaining = "groom", self.random.randint(16, 34)
        elif roll < .47:
            self.pose, self.remaining = "stretch", self.random.randint(9, 19)
        elif roll < .57:
            self.pose, self.remaining = "scratch", self.random.randint(10, 24)
        elif roll < .67:
            self.pose, self.remaining = "play", self.random.randint(12, 27)
        elif roll < .80:
            self.pose, self.remaining = "look", self.random.randint(11, 24)
        elif roll < .87:
            self.pose, self.remaining = "yawn", self.random.randint(7, 15)
        else:
            self.pose, self.remaining = "sit", self.random.randint(14, 48)

    def step(self, width, height, pointer=None, safe_space=None, busy=False):
        if safe_space is None:
            dims = int(width), int(height)
            if self._free_space is None or (self._free_space.width,
                                            self._free_space.height) != dims:
                self._free_space = SafeSpace(*dims, size=40, obstacles=())
            safe_space = self._free_space
        self.steps += 1
        # Animate every tick rather than holding each pose for 250ms.
        self.frame = self.steps % FRAMES
        if self._purr_cooldown > 0:
            self._purr_cooldown -= 1
        if not safe_space.available:
            self.route = []
            self.pose = "sit"
            return (round(self.x), round(self.y), self.pose, self.facing, self.frame)

        # Fully validate the *whole* cat, especially after a layout change or
        # when an editable field expands under an existing resting location.
        if self._last_space is not safe_space or not safe_space.clear(self.x, self.y):
            node = safe_space.nearest(self.x, self.y)
            self.x, self.y = safe_space.points[node]
            self.route = []
            self._last_space = safe_space
            self.pose, self.remaining = "sit", 8

        # When a real input owns keyboard focus, become a quiet mascot.
        # Do not chase the pointer or wander while somebody is typing.
        if busy:
            self.route = []
            self.pose = "sit"
            self._hover_ticks = 0
            self.remaining = max(self.remaining, 16)
            quiet = "blink" if self.steps % 41 == 0 else "sit"
            return round(self.x), round(self.y), quiet, self.facing, self.frame

        if pointer is not None and (not 0 <= pointer[0] < width or
                                    not 0 <= pointer[1] < height):
            pointer = None
        # A pointer above protected text, inputs or buttons must not attract
        # the cat to their edges. Only clear, empty local space invites it.
        safe_pointer = None
        if pointer is not None:
            size = safe_space.size
            if safe_space.clear(pointer[0] - size / 2, pointer[1] - size / 2):
                safe_pointer = pointer
        moved = (safe_pointer is not None and self.last_pointer is not None and
                 math.dist(safe_pointer, self.last_pointer) > 45)
        self.last_pointer = safe_pointer

        # Purr if the pointer lingers near the cat in unobstructed space.
        # No click or keyboard handlers are registered by the companion.
        if (safe_pointer is not None and self._purr_cooldown == 0 and
                math.dist((self.x + safe_space.size / 2,
                           self.y + safe_space.size / 2), safe_pointer)
                < safe_space.size * .92):
            self._hover_ticks += 1
        else:
            self._hover_ticks = 0
        if self._hover_ticks >= 9:
            self.route = []
            self.pose, self.remaining = "purr", 28
            self._hover_ticks = 0
            self._purr_cooldown = 135
        if self.pose != "walk":
            if moved and self.pose in ("sleep", "sit"):
                self.remaining = min(self.remaining, 4)
            if self.remaining > 0:
                self.remaining -= 1
                shown = "blink" if self.pose == "sit" and self.remaining % 31 == 0 else self.pose
                return round(self.x), round(self.y), shown, self.facing, self.frame
            self.route = safe_space.route(self.x, self.y, self.random, safe_pointer)
            if self.route:
                self.pose = "walk"
            else:
                self._rest()
                return round(self.x), round(self.y), self.pose, self.facing, self.frame

        if not self.route:
            self._rest()
            return round(self.x), round(self.y), self.pose, self.facing, self.frame
        target_x, target_y = self.route[0]
        dx, dy = target_x - self.x, target_y - self.y
        distance = math.hypot(dx, dy)
        velocity = 2.5 if distance < 10 else 3.2
        if distance <= velocity:
            new_x, new_y = target_x, target_y
            self.route.pop(0)
        else:
            new_x = self.x + velocity * dx / distance
            new_y = self.y + velocity * dy / distance
        if not safe_space.clear(new_x, new_y):
            # A moved widget must never be drawn under the cat.
            self.route = []
            self._rest()
            return round(self.x), round(self.y), self.pose, self.facing, self.frame
        self.x, self.y = new_x, new_y
        self.energy = max(0.0, self.energy - .0014)
        if abs(dx) > .2:
            self.facing = 1 if dx > 0 else -1
        if not self.route:
            self._rest()
        return round(self.x), round(self.y), self.pose, self.facing, self.frame
