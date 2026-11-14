"""Lightweight native Pocket menus with unmistakable disabled actions.

Only the font of disabled entries changes; their Tk state, accelerator,
keyboard handling and command callbacks remain native and unchanged.
The style is applied to submenus as well as to top-level context menus.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import font as tkfont


class Menu(tk.Menu):
    """Drop-in tk.Menu that strikes through disabled labels automatically."""

    def __init__(self, master=None, cnf=None, **kwargs):
        super().__init__(master, cnf or {}, **kwargs)
        self._pocket_disabled_font = None
        self._pocket_original_fonts = {}

    def _sync_disabled_style(self, index):
        try:
            resolved = self.index(index)
            if resolved is None or self.type(resolved) == "separator":
                return
            if self.entrycget(resolved, "state") == "disabled":
                if self._pocket_disabled_font is None:
                    base = self.cget("font") or "TkMenuFont"
                    self._pocket_disabled_font = tkfont.Font(root=self, font=base)
                    self._pocket_disabled_font.configure(overstrike=True)
                if resolved not in self._pocket_original_fonts:
                    self._pocket_original_fonts[resolved] = self.entrycget(
                        resolved, "font")
                super().entryconfigure(
                    resolved, font=self._pocket_disabled_font)
            elif resolved in self._pocket_original_fonts:
                super().entryconfigure(
                    resolved, font=self._pocket_original_fonts.pop(resolved))
        except tk.TclError:
            # A native menu can disappear during a window/layout refresh.
            return

    def add(self, itemType, cnf=None, **kwargs):
        super().add(itemType, cnf or {}, **kwargs)
        self._sync_disabled_style("end")

    def entryconfigure(self, index, cnf=None, **kwargs):
        result = super().entryconfigure(index, cnf, **kwargs)
        options = cnf if isinstance(cnf, dict) else {}
        if "state" in options or "state" in kwargs:
            self._sync_disabled_style(index)
        return result

    entryconfig = entryconfigure
