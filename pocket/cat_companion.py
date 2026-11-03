"""An expressive black pixel cat that respects Pocket's data and controls.

The companion uses a tiny transparent, click-through Win32 popup. Its art,
collision-aware paths and idle behavior are independent of Pocket features.
No hooks, file reads, network requests, clipboard access or extra threads.
"""
from __future__ import annotations

import ctypes
import sys
import tkinter as tk

from .cat_navigation import CatMotion, SafeSpace
from .cat_sprites import PIXELS, POSES, sprite_pixels

SIZE = 40  # Nominal reference; real sprite size adapts to available screen space.
TICK_MS = 125
KEY_COLOR = "#ff00ff"

# Protect what a user actually interacts with or reads, not entire container
# frames. This includes Tk Text, Lists, Comboboxes, Canvas data views, buttons,
# labels and Windows' native RichEdit frame (its content is a child HWND).
_PROTECTED_CLASSES = {
    "Entry", "TEntry", "Text", "Listbox", "Treeview", "TCombobox",
    "TSpinbox", "Spinbox", "Button", "TButton", "Checkbutton",
    "TCheckbutton", "Radiobutton", "TRadiobutton", "Label", "TLabel",
    "Scrollbar", "TScrollbar", "Canvas", "Scale", "TScale",
}

def collect_obstacles(root, overlay=None):
    """Read mapped widget geometry, never their content; return local rectangles."""
    blockers = []
    ox, oy = root.winfo_rootx(), root.winfo_rooty()
    width, height = root.winfo_width(), root.winfo_height()
    stack = list(root.winfo_children())
    while stack:
        widget = stack.pop()
        if widget is overlay or isinstance(widget, tk.Toplevel):
            continue
        try:
            if not widget.winfo_exists() or not widget.winfo_viewable():
                continue
            stack.extend(widget.winfo_children())
            cls = widget.winfo_class()
            native_editor = hasattr(widget, "_hwnd") and hasattr(widget, "_resize")
            if cls not in _PROTECTED_CLASSES and not native_editor:
                continue
            if cls in {"Label", "TLabel"}:
                # Blank labels are spacers; only protect meaningful text/art.
                try:
                    if not widget.cget("text") and not widget.cget("image"):
                        continue
                except tk.TclError:
                    pass
            x = widget.winfo_rootx() - ox
            y = widget.winfo_rooty() - oy
            w, h = widget.winfo_width(), widget.winfo_height()
            if w < 2 or h < 2:
                continue
            pad = 4 if cls in ("Text", "Entry", "TEntry", "TCombobox", "Listbox",
                                "Treeview", "Canvas") or native_editor else 2
            rectangle = (max(0, x-pad), max(0, y-pad),
                         min(width, x+w+pad), min(height, y+h+pad))
            if rectangle[0] < rectangle[2] and rectangle[1] < rectangle[3]:
                blockers.append(rectangle)
        except (tk.TclError, RuntimeError):
            continue
    return tuple(sorted(set(blockers)))


def _photo(root, pixels, size):
    """Render detailed original sprite at a compact size, nearest-neighbor."""
    image = tk.PhotoImage(master=root, width=size, height=size)
    for y, row in enumerate(pixels):
        top, bottom = y * size // PIXELS, (y + 1) * size // PIXELS
        if top == bottom:
            continue
        column = 0
        while column < PIXELS:
            color = row[column]
            end = column+1
            while end < PIXELS and row[end] == color:
                end += 1
            left, right = column*size//PIXELS, end*size//PIXELS
            if color and left < right:
                image.put(color, to=(left, top, right, bottom))
            column = end
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
        self.size = SIZE
        self.space = None
        self._space_signature = None
        self._space_age = 999

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
            # Lazy sprite cache keeps startup snappy; at most one image is
            # generated for a newly encountered pose/frame/direction/size.
            images = {}
            first = _photo(window, sprite_pixels("sit", 1, 0), SIZE)
            images[("sit", 1, 0, SIZE)] = first
            sprite = canvas.create_image(0, 0, anchor="nw", image=first)
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

    def invalidate(self):
        """Forget stale obstacles immediately after a tab/layout is rebuilt."""
        self._space_age = 999
        self._space_signature = None
        self.space = None
        self.hide()

    def _new_space(self, width, height, size):
        """Refresh only when geometry changed; no extra background polling."""
        self._space_age += 1
        if (self.space is not None and self._space_age < 10 and
                self.space.width == width and self.space.height == height and
                self.space.size == size):
            return self.space
        obstacles = collect_obstacles(self.root, self.window)
        signature = width, height, size, obstacles
        if signature != self._space_signature:
            self.space = SafeSpace(width, height, size=size, obstacles=obstacles)
            self._space_signature = signature
        self._space_age = 0
        return self.space

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
            # Small windows get a smaller detailed sprite; Dashboard has
            # enough space to show more expressive animation frames.
            size = (32 if min(width, height) < 350 else
                    40 if width < 600 else 48)
            space = self._new_space(width, height, size)
            if not space.available:
                self.hide()  # Busy screens take precedence over decoration.
                return
            px, py = self.root.winfo_pointerx()-x, self.root.winfo_pointery()-y
            pointer = (px, py) if 0 <= px < width and 0 <= py < height else None
            focus = self.root.focus_get()
            typing = bool(focus and focus.winfo_class() in (
                "Text", "Entry", "TEntry", "TCombobox", "TSpinbox",
                "Spinbox", "Listbox", "Treeview"))
            cx, cy, pose, direction, frame = self.motion.step(
                width, height, pointer, safe_space=space, busy=typing)
            if not space.clear(cx, cy):
                self.hide()  # Refuse to draw over newly occupied UI.
                return
            key = pose, direction, frame, size
            if key not in self.images:
                self.images[key] = _photo(self.window, sprite_pixels(pose, direction, frame), size)
            self.canvas.itemconfigure(self.sprite, image=self.images[key])
            self.window.geometry(f"{size}x{size}+{x+cx}+{y+cy}")
            if not self.visible:
                self.window.deiconify()
                # Flush the first native Map/Configure event synchronously;
                # Tk otherwise rewrites extended styles *after* our setter.
                # This happens only on showing the cat, not every animation.
                self.window.update()
                self._protect_window(self.window)
                self.visible = True
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
