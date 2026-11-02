"""Dashboard-only Notes workspace.

A compact metadata strip and a full-height editor occupy the main workspace;
notes stay visible in a narrow, independently scrollable sidebar. All note
behavior is delegated to Pocket's existing editor, reminder and save callbacks.
Normal and Mini have separate, unchanged builders.
"""
from __future__ import annotations

import sys
import tkinter as tk
from tkinter import ttk

from . import native_bidi
from . import pocket_design as design


FONT = "Segoe UI"


def build(app):
    c = design.colors(app.theme)
    bg, panel, card = c["BG"], c["PANEL"], c["CARD"]
    border, input_bg, accent = c["BORDER"], c["INPUT"], c["ACCENT"]
    white, muted, danger = c["WHITE"], c["MUTED"], c["DANGER"]
    body = app.body

    # The Dashboard shell already has the page heading. A tall hero or a
    # second full-width note header would take room away from writing.
    workspace = tk.Frame(body, bg=bg)
    workspace.pack(fill="both", expand=True)
    workspace.grid_columnconfigure(0, minsize=208)
    workspace.grid_columnconfigure(1, weight=1)
    workspace.grid_rowconfigure(0, weight=1)

    sidebar = tk.Frame(workspace, bg=panel, highlightthickness=1,
                       highlightbackground=border, width=216)
    sidebar.grid(row=0, column=0, sticky="nsew", padx=(0, 13))
    sidebar.grid_propagate(False)
    sidebar_head = tk.Frame(sidebar, bg=panel)
    sidebar_head.pack(fill="x", padx=10, pady=(10, 8))
    tk.Label(sidebar_head, text="ALL NOTES", bg=panel, fg=white,
             font=(FONT, 9, "bold"), anchor="w").pack(side="left", fill="x", expand=True)
    design.button(sidebar_head, "+ New", app.add_note, app.theme,
                  primary=True, compact=True).pack(side="right")
    tk.Frame(sidebar, bg=border, height=1).pack(fill="x", padx=10, pady=(0, 4))

    list_holder = tk.Frame(sidebar, bg=panel)
    list_holder.pack(fill="both", expand=True, padx=(6, 5), pady=(1, 3))
    app.note_list = tk.Listbox(
        list_holder, bd=0, highlightthickness=0, activestyle="none",
        selectbackground=c["ACCENT_DARK"], selectforeground=white,
        bg=panel, fg=c["SECONDARY"], font=(FONT, 10), height=1, width=1,
        exportselection=False, relief="flat", justify="left")
    app.note_list.pack(side="left", fill="both", expand=True, padx=(2, 0))
    list_scroll = ttk.Scrollbar(list_holder, orient="vertical",
                                command=app.note_list.yview,
                                style="Pocket.Vertical.TScrollbar")
    list_scroll.pack(side="right", fill="y", padx=(3, 0))
    app.note_list.configure(yscrollcommand=list_scroll.set)
    app.note_list.bind("<<ListboxSelect>>", app._select_from_list)
    app.note_list.bind("<ButtonPress-1>", app._note_focus_field, add="+")
    app.note_list.bind("<Button-3>", app._show_note_list_menu)
    app.note_list.bind("<Control-Button-1>", app._show_note_list_menu)
    tk.Label(sidebar, text="Pinned notes appear first", bg=panel, fg=muted,
             font=(FONT, 8), anchor="w").pack(fill="x", padx=11, pady=(1, 10))

    right = tk.Frame(workspace, bg=bg)
    right.grid(row=0, column=1, sticky="nsew")
    right.grid_columnconfigure(0, weight=1)
    right.grid_rowconfigure(1, weight=1)

    # One intentionally shallow metadata strip replaces Dashboard's former
    # oversized Title/Phone block. Make Title and Phone usable at the same time.
    metadata = tk.Frame(right, bg=panel, highlightbackground=border,
                        highlightthickness=1)
    metadata.grid(row=0, column=0, sticky="ew", pady=(0, 9))
    meta_head = tk.Frame(metadata, bg=panel)
    meta_head.pack(fill="x", padx=12, pady=(8, 4))
    tk.Label(meta_head, text="NOTE DETAILS", bg=panel, fg=muted,
             font=(FONT, 8, "bold"), anchor="w").pack(side="left")
    app.created_label = tk.Label(meta_head, text="", bg=panel, fg=muted,
                                 font=(FONT, 8), anchor="e")
    app.created_label.pack(side="right")

    fields = tk.Frame(metadata, bg=panel)
    fields.pack(fill="x", padx=12)
    fields.grid_columnconfigure(0, weight=3)
    fields.grid_columnconfigure(1, weight=2, minsize=185)

    title_group = tk.Frame(fields, bg=panel)
    title_group.grid(row=0, column=0, sticky="ew", padx=(0, 11))
    tk.Label(title_group, text="TITLE", bg=panel, fg=muted,
             font=(FONT, 8, "bold"), anchor="w").pack(fill="x", pady=(0, 3))
    app.title_var = tk.StringVar()
    app.title_entry = tk.Entry(
        title_group, textvariable=app.title_var, bg=input_bg, fg=white,
        insertbackground=white, selectbackground=c["ACCENT_DARK"],
        relief="flat", highlightthickness=1, highlightbackground=border,
        highlightcolor=accent, font=(FONT, 10, "bold"))
    app.title_entry.pack(fill="x", ipady=5)
    app.title_entry.bind("<ButtonPress-1>", app._note_focus_field, add="+")
    app.title_var.trace_add("write", app._change_note_title)

    phone_group = tk.Frame(fields, bg=panel)
    phone_group.grid(row=0, column=1, sticky="ew")
    tk.Label(phone_group, text="PHONE", bg=panel, fg=muted,
             font=(FONT, 8, "bold"), anchor="w").pack(fill="x", pady=(0, 3))
    phone_line = tk.Frame(phone_group, bg=panel)
    phone_line.pack(fill="x")
    app.phone_var = tk.StringVar()
    app.phone_entry = tk.Entry(
        phone_line, textvariable=app.phone_var, bg=input_bg, fg=white,
        insertbackground=white, selectbackground=c["ACCENT_DARK"],
        relief="flat", highlightthickness=1, highlightbackground=border,
        highlightcolor=accent, font=(FONT, 9), width=8)
    app.phone_entry.pack(side="left", fill="x", expand=True, ipady=6)
    app.phone_entry.bind("<ButtonPress-1>", app._note_focus_field, add="+")
    design.button(phone_line, "Copy", app._copy_phone, app.theme,
                  compact=True).pack(side="right", padx=(6, 0))
    app.phone_var.trace_add("write", app._change_note_phone)

    reminder_row = tk.Frame(metadata, bg=panel)
    reminder_row.pack(fill="x", padx=11, pady=(5, 7))
    app.reminder_action = design.button(
        reminder_row, "☐ Notify me", app._toggle_active_note_reminder,
        app.theme, compact=True)
    app.reminder_action.pack(side="left")
    app.reminder_detail = tk.Label(reminder_row, text="", bg=panel, fg=muted,
                                    font=(FONT, 8), cursor="hand2", anchor="e")
    app.reminder_detail.pack(side="right", fill="x", expand=True)
    app.reminder_detail.bind("<Button-1>",
                             lambda _event: app._edit_active_note_reminder())

    # The editor owns almost all remaining height. Native Win32 RichEdit is
    # created against the same host as the Tk fallback, so the existing
    # direction/focus/caret behavior works across both Windows and Linux.
    editor = tk.Frame(right, bg=panel, highlightbackground=border,
                      highlightthickness=1)
    editor.grid(row=1, column=0, sticky="nsew")
    editor_head = tk.Frame(editor, bg=panel)
    editor_head.pack(fill="x", padx=12, pady=(9, 6))
    tk.Label(editor_head, text="EDITOR", bg=panel, fg=white,
             font=(FONT, 10, "bold"), anchor="w").pack(side="left")
    tk.Label(editor_head, text="Autosaves as you type", bg=panel, fg=muted,
             font=(FONT, 8), anchor="e").pack(side="right")
    app.note_body = tk.Text(
        editor, wrap="word", undo=True, bg=input_bg, fg="#D7DAE6",
        insertbackground=accent, selectbackground=c["ACCENT_DARK"],
        relief="flat", bd=0, font=(FONT, 11), height=1, width=1,
        highlightthickness=1, highlightbackground=border,
        highlightcolor=accent, padx=12, pady=12)
    app.note_body.pack(fill="both", expand=True, padx=12)
    app.bidi_editor = None
    if sys.platform == "win32":
        try:
            app.bidi_editor = native_bidi.NativeBidiEditor(
                editor, background=input_bg, foreground="#D7DAE6",
                context_menu=app._show_note_context_menu)
        except (OSError, RuntimeError) as exc:
            print(f"Pocket native Dashboard note editor unavailable: {exc}",
                  file=sys.stderr)
    app.note_direction_var = tk.StringVar(value="ltr")
    app.note_body.tag_configure("note_alignment", justify="left")
    app.note_body.bind("<<Modified>>", app._change_note_body)
    app.note_body.bind("<Button-3>", app._show_note_context_menu)
    app.note_body.bind("<Control-Button-1>", app._show_note_context_menu)
    app.note_body.bind("<Control-a>", app._select_all_note_text)
    footer = tk.Frame(editor, bg=panel)
    footer.pack(fill="x", padx=12, pady=(7, 9))
    app.save_status = tk.Label(footer, text="Autosaved", bg=panel, fg=muted,
                               font=(FONT, 8))
    app.save_status.pack(side="left")
    design.button(footer, "Delete", app.delete_note,
                  app.theme, compact=True).pack(side="right", padx=(7, 0))
    design.button(footer, "Open in Notepad", app.open_notepad,
                  app.theme, compact=True).pack(side="right")

    # Keep original note selection, autosave, timestamps, reminders and BiDi.
    app.refresh_note_list()
    app._load_selected_note()
