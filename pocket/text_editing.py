"""Shared Tk text-edit controls for Pocket's on-demand desktop UI.

Class bindings apply to newly created Entry/Text widgets in every layout.
Widget-specific right-click menus (Notes, pickers, RichEdit) take precedence.
No clipboard polling or network access is performed here.
"""
from __future__ import annotations

import tkinter as tk

from . import menu_style

EDIT_CLASSES = ("Entry", "TEntry", "Text", "Spinbox", "TSpinbox", "TCombobox")


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
    """Return 'break' to prevent Tk's class shortcut undoing the selection."""
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


def perform(widget, operation: str):
    """Dispatch through native Tk edit events (preserves undo where supported)."""
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
        elif operation == "copy":
            if has_selection(widget):
                widget.event_generate("<<Copy>>")
        elif operation == "cut":
            if has_selection(widget):
                widget.event_generate("<<Cut>>")
        else:
            widget.event_generate("<<Paste>>")
    except (tk.TclError, AttributeError):
        pass
    return "break"


def install(root, context_callback, focus_callback):
    """Install once; preserve all pre-existing widget-specific bindings."""
    for widget_class in EDIT_CLASSES:
        root.bind_class(widget_class, "<Control-a>",
                        lambda event: select_all(event.widget))
        for key, operation in (("c", "copy"), ("x", "cut"), ("v", "paste")):
            root.bind_class(widget_class, "<Control-" + key + ">",
                            lambda event, action=operation: perform(event.widget, action))

        def right_click(event):
            widget = event.widget
            # Existing widget-owned menus are authoritative. In particular,
            # Notes' RichEdit and picker context menus must remain unchanged.
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
    """Create a compact menu for a plain editable/selectable text field."""
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
        menu.add_command(label="Redo", accelerator="Ctrl+Y",
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
