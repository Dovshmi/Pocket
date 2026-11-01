"""Pocket visual language — semantic tokens and reusable Tk/ttk components.

All colors originate from the existing Pocket icon theme. This module styles
controls only; it never changes storage, launches a shortcut or runs commands.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

import icon_themes as themes

FONT = "Segoe UI"
SPACING = (4, 8, 12, 16, 24)
RADIUS_NOTE = "Tkinter uses flat surfaces and 1px borders; no bitmap backgrounds."


def colors(theme):
    p = themes.palette(theme)
    return {**p, "POSITIVE": "#63DCA8", "NOTICE": "#F5C66A"}


def configure_ttk(root, theme):
    """Use one dark, genuinely readable palette for every Pocket ttk widget.

    The default Windows 'vista'/'xpnative' ttk themes draw the Combobox entry
    with a native *white* fill, ignoring fieldbackground. Pocket sets a light
    foreground, so the selected option was invisible. The cross-platform Clam
    theme honors field, arrow and dropdown state colors; choosing it here is
    intentional and applies only to ttk widgets (not native RichEdit or Tk).
    """
    c = colors(theme)
    style = ttk.Style(root)
    if "clam" in style.theme_names() and style.theme_use() != "clam":
        style.theme_use("clam")

    # ttk creates the dropdown Listbox lazily in its popdown Toplevel. These
    # option-db entries color the popup itself, not only the closed selection.
    root.option_add("*TCombobox*Listbox.background", c["PANEL"], 90)
    root.option_add("*TCombobox*Listbox.foreground", c["WHITE"], 90)
    root.option_add("*TCombobox*Listbox.selectBackground", c["ACCENT_DARK"], 90)
    root.option_add("*TCombobox*Listbox.selectForeground", c["WHITE"], 90)
    root.option_add("*TCombobox*Listbox.font", (FONT, 10), 90)
    root.option_add("*TCombobox*Listbox.relief", "flat", 90)

    style.configure("Pocket.Treeview",
                    background=c["PANEL"], foreground=c["WHITE"],
                    fieldbackground=c["PANEL"], borderwidth=0, rowheight=30,
                    font=(FONT, 9))
    style.configure("Pocket.Treeview.Heading", background=c["CARD"],
                    foreground=c["SECONDARY"], relief="flat",
                    padding=(10, 9), font=(FONT, 9, "bold"))
    style.map("Pocket.Treeview",
              background=[("selected", c["ACCENT_DARK"])],
              foreground=[("selected", c["WHITE"])])
    style.configure("Pocket.TCombobox",
                    fieldbackground=c["INPUT"], background=c["CARD"],
                    foreground=c["WHITE"], selectforeground=c["WHITE"],
                    selectbackground=c["ACCENT_DARK"],
                    arrowcolor=c["SECONDARY"], bordercolor=c["BORDER"],
                    lightcolor=c["BORDER"], darkcolor=c["BORDER"],
                    focuscolor=c["ACCENT"], borderwidth=1, relief="flat",
                    padding=(9, 7), arrowsize=13, font=(FONT, 10))
    # Order matters: disabled must precede readonly, so a disabled selector
    # never appears active. Focus preserves the same high contrast.
    style.map("Pocket.TCombobox",
              fieldbackground=[("disabled", c["CARD"]),
                               ("readonly", c["INPUT"]),
                               ("focus", c["INPUT"]), ("!disabled", c["INPUT"])],
              foreground=[("disabled", c["MUTED"]),
                          ("readonly", c["WHITE"]), ("!disabled", c["WHITE"])],
              selectforeground=[("disabled", c["MUTED"]),
                                ("readonly", c["WHITE"])],
              selectbackground=[("readonly", c["ACCENT_DARK"])],
              background=[("active", c["CARD_HOVER"]), ("!active", c["CARD"])],
              arrowcolor=[("disabled", c["MUTED"]),
                          ("active", c["WHITE"]), ("!disabled", c["SECONDARY"])],
              bordercolor=[("focus", c["ACCENT"]), ("!focus", c["BORDER"])])
    style.configure("Pocket.Vertical.TScrollbar",
                    background=c["CARD"], troughcolor=c["BG"],
                    bordercolor=c["BORDER"], lightcolor=c["CARD"],
                    darkcolor=c["CARD"], arrowcolor=c["SECONDARY"],
                    borderwidth=0, arrowsize=11, width=10)
    style.map("Pocket.Vertical.TScrollbar",
              background=[("active", c["CARD_HOVER"]), ("!active", c["CARD"])])
    style.configure("Pocket.TSeparator", background=c["BORDER"])
    return c

def panel(parent, theme, *, background=None):
    c = colors(theme)
    return tk.Frame(parent, bg=background or c["PANEL"],
                    highlightthickness=1, highlightbackground=c["BORDER"], bd=0)


def button(parent, title, action, theme, *, primary=False, destructive=False,
           compact=False, **kwargs):
    c = colors(theme)
    color = c["DANGER"] if destructive else c["ACCENT"] if primary else c["WHITE"]
    bg = c["ACCENT_DARK"] if primary else c["CARD"]
    return tk.Button(parent, text=title, command=action, cursor="hand2",
                     bg=bg, fg=color, activebackground=c["CARD_HOVER"],
                     activeforeground=c["WHITE"], relief="flat", bd=0,
                     highlightthickness=1, highlightbackground=c["BORDER"],
                     highlightcolor=c["ACCENT"], takefocus=True,
                     padx=9 if compact else 13, pady=6 if compact else 9,
                     font=(FONT, 8 if compact else 9, "bold"), **kwargs)


def entry(parent, variable, theme, *, compact=False, **kwargs):
    c = colors(theme)
    return tk.Entry(parent, textvariable=variable, bg=c["INPUT"], fg=c["WHITE"],
                    insertbackground=c["WHITE"], selectbackground=c["ACCENT_DARK"],
                    relief="flat", bd=0, highlightthickness=1,
                    highlightbackground=c["BORDER"], highlightcolor=c["ACCENT"],
                    font=(FONT, 9 if compact else 10), **kwargs)


def section_header(parent, title, subtitle, command_label, command, theme, *, compact=False,
                   balanced=False):
    """Readable tool heading with a distinct, space-efficient Normal variant.

    balanced changes Normal only. Mini keeps the compact design, while the
    Dashboard retains its generous title/hero sizing.
    """
    c = colors(theme)
    shell = panel(parent, theme)
    shell.pack(fill="x", pady=(0, 9 if balanced else (12 if compact else 15)))
    accent = tk.Frame(shell, bg=c["ACCENT"], width=3)
    accent.pack(side="left", fill="y")
    accent.pack_propagate(False)
    content = tk.Frame(shell, bg=c["PANEL"])
    content.pack(side="left", fill="both", expand=True, padx=(10 if balanced else 11, 3),
                 pady=(8 if balanced or compact else 12))
    tk.Label(content, text=title, bg=c["PANEL"], fg=c["WHITE"],
             font=(FONT, 13 if balanced else (12 if compact else 15), "bold"),
             anchor="w").pack(anchor="w")
    tk.Label(content, text=subtitle, bg=c["PANEL"], fg=c["MUTED"],
             font=(FONT, 8 if balanced or compact else 9),
             wraplength=270 if balanced else (210 if compact else 650),
             anchor="w", justify="left").pack(anchor="w", pady=(2 if balanced else 3, 0))
    button(shell, command_label, command, theme, primary=True,
           compact=compact or balanced).pack(side="right", padx=(4, 9 if balanced else 10))
    return shell


def empty_state(parent, heading, detail, theme):
    """Accessible empty-state text; no placeholder content or network requests."""
    c = colors(theme)
    box = panel(parent, theme)
    box.pack(fill="x", pady=8)
    tk.Label(box, text=heading, bg=c["PANEL"], fg=c["SECONDARY"],
             font=(FONT, 11, "bold")).pack(anchor="w", padx=14, pady=(14, 4))
    tk.Label(box, text=detail, bg=c["PANEL"], fg=c["MUTED"], font=(FONT, 9),
             wraplength=365, justify="left").pack(anchor="w",
                                                padx=14, pady=(0, 14))
    return box


class Tooltip:
    """Delayed keyboard/mouse description without changing control behavior.

    The tooltip is an undecorated display-only transient and is destroyed on
    focus/hover exit or when its widget is removed during a layout change.
    """
    def __init__(self, widget, message, theme, delay_ms=550):
        self.widget = widget
        self.message = str(message)
        self.theme = theme
        self.delay_ms = delay_ms
        self.job = None
        self.popup = None
        widget.bind("<Enter>", self._schedule, add="+")
        widget.bind("<Leave>", self._hide, add="+")
        widget.bind("<FocusIn>", self._schedule, add="+")
        widget.bind("<FocusOut>", self._hide, add="+")
        widget.bind("<Destroy>", self._hide, add="+")

    def _schedule(self, _event=None):
        self._hide()
        try:
            self.job = self.widget.after(self.delay_ms, self._show)
        except tk.TclError:
            self.job = None

    def _show(self):
        self.job = None
        try:
            if not self.widget.winfo_exists() or self.popup is not None:
                return
            c = colors(self.theme)
            popup = tk.Toplevel(self.widget)
            popup.withdraw()
            popup.wm_overrideredirect(True)
            popup.configure(bg=c["BORDER"])
            label = tk.Label(popup, text=self.message, bg=c["PANEL"],
                             fg=c["WHITE"], font=(FONT, 9),
                             padx=10, pady=6, justify="left",
                             wraplength=285)
            label.pack(padx=1, pady=1)
            x = self.widget.winfo_rootx() + 6
            y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5
            popup.geometry(f"+{x}+{y}")
            popup.deiconify()
            self.popup = popup
        except (tk.TclError, RuntimeError):
            self.popup = None

    def _hide(self, _event=None):
        job, self.job = self.job, None
        if job is not None:
            try:
                self.widget.after_cancel(job)
            except (tk.TclError, RuntimeError):
                pass
        popup, self.popup = self.popup, None
        if popup is not None:
            try:
                popup.destroy()
            except (tk.TclError, RuntimeError):
                pass


def tool_button(parent, title, callback, theme, *, tip=None, compact=False):
    """Consistent focusable navigation icon, with a hover/focus description."""
    widget = button(parent, title, callback, theme, compact=compact)
    if tip:
        Tooltip(widget, tip, theme)
    return widget
