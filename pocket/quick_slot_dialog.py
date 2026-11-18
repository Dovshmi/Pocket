"""Compact themed confirmation for replacing one numbered Clipboard Quick Slot.

A single local Tk dialog with fixed New (left) -> Old (right) semantics.
Text is previewed only; nothing touches the Windows clipboard.
"""
from __future__ import annotations

import tkinter as tk

from . import icon_themes as themes
from . import quick_slots


def confirmation_labels(number, old_text, new_text):
    """Preview model shared by the actual dialog and headless tests."""
    if number not in quick_slots.SLOT_NUMBERS:
        raise ValueError("Invalid Quick Slot")
    maximum = quick_slots.REPLACEMENT_PREVIEW_LENGTH
    return {
        "title": f"Replace Quick Slot [{number}]?",
        "new": quick_slots.notification_preview(new_text, max_length=maximum),
        "old": quick_slots.notification_preview(old_text, max_length=maximum),
    }


def confirm_replace(root, theme, number, old_text, new_text):
    """Return True only after pressing Yes; No/Escape/close leaves data intact."""
    info = confirmation_labels(number, old_text, new_text)
    c = themes.palette(theme)
    result = False
    dialog = tk.Toplevel(root)
    dialog.title(info["title"])
    dialog.configure(bg=c["BG"])
    dialog.resizable(False, False)
    width, height = 400, 175
    screen_w, screen_h = dialog.winfo_screenwidth(), dialog.winfo_screenheight()
    if root.state() == "normal":
        x = root.winfo_rootx() + max(0, (root.winfo_width() - width) // 2)
        y = root.winfo_rooty() + 60
        dialog.transient(root)
    else:
        # A global Numpad hotkey also works while the main Pocket popup is hidden.
        x = root.winfo_pointerx() - width // 2
        y = root.winfo_pointery() - height // 2
        dialog.attributes("-topmost", True)
    x = max(8, min(x, screen_w - width - 8))
    y = max(8, min(y, screen_h - height - 48))
    dialog.geometry(f"{width}x{height}+{x}+{y}")

    def finish(accepted=False):
        nonlocal result
        result = bool(accepted)
        dialog.destroy()

    tk.Label(dialog, text=info["title"], bg=c["BG"], fg=c["WHITE"],
             font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=16, pady=(11, 9))

    body = tk.Frame(dialog, bg=c["BG"])
    body.pack(fill="x", padx=16)
    body.grid_columnconfigure(0, weight=1, uniform="slots")
    body.grid_columnconfigure(2, weight=1, uniform="slots")
    for column, name, value in ((0, "NEW", info["new"]), (2, "OLD", info["old"])):
        frame = tk.Frame(body, bg=c["CARD"], height=64)
        frame.grid(row=0, column=column, sticky="nsew")
        frame.grid_propagate(False)
        tk.Label(frame, text=name, bg=c["CARD"], fg=c["MUTED"],
                 font=("Segoe UI", 8, "bold")).pack(pady=(6, 2))
        tk.Label(frame, text=value, bg=c["CARD"], fg=c["WHITE"],
                 font=("Segoe UI", 9), anchor="center", wraplength=146,
                 justify="center").pack(padx=4, fill="x")
    tk.Label(body, text="→", bg=c["BG"], fg=c["ACCENT"],
             font=("Segoe UI", 17, "bold")).grid(row=0, column=1, padx=9)

    controls = tk.Frame(dialog, bg=c["BG"])
    controls.pack(fill="x", padx=16, pady=(11, 9))
    yes = tk.Button(controls, text="Yes", command=lambda: finish(True),
                    bg=c["ACCENT"], fg=c["BG"], relief="flat", width=8)
    yes.pack(side="right", padx=(7, 0))
    no = tk.Button(controls, text="No", command=lambda: finish(False),
                   bg=c["CARD"], fg=c["WHITE"], relief="flat", width=8)
    no.pack(side="right")
    dialog.protocol("WM_DELETE_WINDOW", lambda: finish(False))
    dialog.bind("<Escape>", lambda _event: finish(False))
    dialog.update_idletasks()
    dialog.lift()
    dialog.grab_set()
    no.focus_set()
    dialog.wait_window()
    return result
