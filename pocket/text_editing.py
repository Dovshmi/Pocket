"""Reliable, local text-edit shortcuts and context menus for Pocket.

Keybindings belong to Tk input classes, not the whole application: global
note/search shortcuts and per-widget context menus remain authoritative.
Tk's RichEdit (Windows) note body stays native and handles its own shortcuts.
"""
from __future__ import annotations

import sys
import tkinter as tk

from . import menu_style

EDIT_CLASSES = ("Entry", "TEntry", "Text", "Spinbox", "TSpinbox", "TCombobox")
# Win32 virtual-key codes identify the physical letter shortcut even when
# Windows is using a non-Latin keyboard layout (e.g. Hebrew).
_WINDOWS_EDIT_KEYS = {
    0x41: "select_all",  # Ctrl+A
    0x43: "copy",        # Ctrl+C
    0x56: "paste",       # Ctrl+V
    0x58: "cut",         # Ctrl+X
    0x5A: "undo",        # Ctrl+Z (Shift: redo)
    0x59: "redo",        # Ctrl+Y
}
_LATIN_EDIT_KEYS = {
    "a": "select_all", "c": "copy", "v": "paste",
    "x": "cut", "z": "undo", "y": "redo",
}


def is_text_control(widget) -> bool:
    return widget.winfo_class() in EDIT_CLASSES


def can_edit(widget) -> bool:
    try:
        return is_text_control(widget) and str(widget.cget("state")) not in ("disabled", "readonly")
    except (tk.TclError, AttributeError):
        return False


def has_selection(widget) -> bool:
    try:
        if widget.winfo_class() == "Text":
            return bool(widget.tag_ranges("sel"))
        return bool(widget.selection_present())
    except (tk.TclError, AttributeError):
        return False


def select_all(widget):
    """Select complete Tk input content without changing application focus."""
    try:
        if widget.winfo_class() == "Text":
            widget.tag_add("sel", "1.0", "end-1c")
            widget.mark_set("insert", "1.0")
            widget.see("insert")
        else:
            widget.selection_range(0, "end")
            widget.icursor("end")
    except (tk.TclError, AttributeError):
        pass
    return "break"


def _selected_text(widget):
    if widget.winfo_class() == "Text":
        return widget.get("sel.first", "sel.last")
    return widget.get()[widget.index("sel.first"):widget.index("sel.last")]


def perform(widget, operation: str):
    """Edit the focused widget directly, without re-entering Tk key bindings.

    A nested <<Copy>>/<<Paste>> from an actual Ctrl keypress can be swallowed
    by widget/class bindings on Windows. Direct clipboard and widget operations
    also work when the user chooses a menu item instead of a key shortcut.
    """
    if not is_text_control(widget):
        return "break"
    if operation == "select_all":
        return select_all(widget)
    if operation not in ("copy", "cut", "paste", "undo", "redo"):
        return "break"
    if operation != "copy" and not can_edit(widget):
        return "break"

    try:
        if operation in ("undo", "redo"):
            if widget.winfo_class() == "Text" and bool(widget.cget("undo")):
                getattr(widget, "edit_" + operation)()
            return "break"

        if operation in ("copy", "cut"):
            if not has_selection(widget):
                return "break"
            selected = _selected_text(widget)
            widget.clipboard_clear()
            widget.clipboard_append(selected)
            if operation == "cut":
                if widget.winfo_class() == "Text" and bool(widget.cget("undo")):
                    widget.edit_separator()
                widget.delete("sel.first", "sel.last")
                if widget.winfo_class() == "Text" and bool(widget.cget("undo")):
                    widget.edit_separator()
            return "break"

        # Paste: insert at the Tk caret, replacing any selection. This is
        # deliberately not an event_generate('<<Paste>>') call.
        data = widget.clipboard_get()
        if not isinstance(data, str):
            return "break"
        text_widget = widget.winfo_class() == "Text"
        undo_enabled = text_widget and bool(widget.cget("undo"))
        if undo_enabled:
            widget.edit_separator()
        if has_selection(widget):
            widget.delete("sel.first", "sel.last")
        if text_widget:
            widget.insert("insert", data.replace("\r\n", "\n"))
        else:
            widget.insert("insert", data)
        if undo_enabled:
            widget.edit_separator()
    except (tk.TclError, AttributeError, RuntimeError):
        # Clipboard can contain non-text payloads, or the widget can be
        # destroyed while a popup menu closes. Never crash the desktop app.
        pass
    return "break"


def _shortcut_operation(event):
    """Resolve Ctrl accelerators for both Latin and Hebrew Windows layouts."""
    # AltGr usually synthesizes Ctrl+Alt. It must not trigger edit commands.
    if event.state & 0x0008:
        return None
    if sys.platform == "win32":
        operation = _WINDOWS_EDIT_KEYS.get(event.keycode)
        # Do not reinterpret an unrelated key using a translated keysym.
        if operation is None:
            return None
    else:
        operation = _LATIN_EDIT_KEYS.get(str(event.keysym).lower())
    if operation == "undo" and event.state & 0x0001:
        return "redo"   # Ctrl+Shift+Z
    return operation


def handle_shortcut(event):
    """One per-class handler; returns break only for supported edit commands."""
    operation = _shortcut_operation(event)
    if operation is None:
        return None
    # Do not eat Ctrl+Z in a Tk Entry that lacks undo, or any disabled field.
    if operation in ("undo", "redo"):
        if event.widget.winfo_class() != "Text":
            return None
        try:
            if not bool(event.widget.cget("undo")):
                return None
        except tk.TclError:
            return None
    return perform(event.widget, operation)


def install(root, context_callback, focus_callback):
    """Install class handlers once; respect specialized widget bindings."""
    for widget_class in EDIT_CLASSES:
        # One handler recognizes all edit shortcuts, including Windows VK
        # codes when keysym is not Latin. Other Ctrl shortcuts fall through.
        root.bind_class(widget_class, "<Control-KeyPress>", handle_shortcut, add="+")

        def right_click(event):
            widget = event.widget
            if widget.bind("<Button-3>"):
                return None
            return context_callback(event)

        def click_focus(event):
            widget = event.widget
            if widget.bind("<ButtonPress-1>"):
                return None
            return focus_callback(event)

        root.bind_class(widget_class, "<Button-3>", right_click, add="+")
        root.bind_class(widget_class, "<ButtonPress-1>", click_focus, add="+")


def make_menu(root, widget, colors, dispatch):
    """Create a compact menu only for inputs without existing context menus."""
    options = dict(tearoff=False, bg=colors["PANEL"], fg=colors["WHITE"],
                   disabledforeground=colors["MUTED"],
                   activebackground=colors["ACCENT_DARK"],
                   activeforeground=colors["WHITE"], bd=1,
                   relief="flat", font=("Segoe UI", 9))
    menu = menu_style.Menu(root, **options)
    writable = can_edit(widget)
    selected = has_selection(widget)
    try:
        root.clipboard_get()
        has_text_clipboard = True
    except (tk.TclError, RuntimeError):
        has_text_clipboard = False

    if widget.winfo_class() == "Text" and bool(widget.cget("undo")) and writable:
        menu.add_command(label="Undo", accelerator="Ctrl+Z",
                         command=lambda: dispatch("undo"))
        menu.add_command(label="Redo", accelerator="Ctrl+Y / Ctrl+Shift+Z",
                         command=lambda: dispatch("redo"))
        menu.add_separator()

    menu.add_command(label="Cut", accelerator="Ctrl+X",
                     state="normal" if writable and selected else "disabled",
                     command=lambda: dispatch("cut"))
    menu.add_command(label="Copy", accelerator="Ctrl+C",
                     state="normal" if selected else "disabled",
                     command=lambda: dispatch("copy"))
    menu.add_command(label="Paste", accelerator="Ctrl+V",
                     state="normal" if writable and has_text_clipboard else "disabled",
                     command=lambda: dispatch("paste"))
    menu.add_separator()
    menu.add_command(label="Select all", accelerator="Ctrl+A",
                     command=lambda: dispatch("select_all"))
    return menu
