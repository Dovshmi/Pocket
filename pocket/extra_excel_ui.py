"""Pocket Extra menu: a themed, local, read-only Excel search page."""
from __future__ import annotations

import queue
import threading
import tkinter as tk
from tkinter import filedialog

from . import extra_excel_lookup as lookup
from . import pocket_design as design


def build(app, parent):
    colors = design.colors(app.theme)
    wide = app.display_mode == "dashboard"
    compact = app.display_mode == "mini"

    def label(target, text, *, size=9, muted=False, bold=False, bg=None, **kwargs):
        return tk.Label(
            target, text=text, bg=bg or colors["BG"],
            fg=colors["MUTED"] if muted else colors["WHITE"],
            font=("Segoe UI", size, "bold" if bold else "normal"),
            anchor="w", justify="left", **kwargs)

    title = label(parent, "Extra  /  Excel lookup", size=18 if wide else 13, bold=True)
    title.pack(fill="x", pady=(0, 5))
    label(parent, "Offline read-only search. Protected workbooks use Excel automatically.",
          size=9, muted=True, wraplength=650 if wide else 280).pack(fill="x", pady=(0, 11))

    source = design.panel(parent, app.theme)
    source.pack(fill="x", pady=(0, 11))
    label(source, "EXCEL SOURCE  ·  READ ONLY", size=9, bold=True,
          bg=colors["PANEL"]).pack(anchor="w", padx=11, pady=(10, 7))

    path_var = tk.StringVar(master=app.root, value=getattr(app, "_extra_excel_path", ""))
    path_line = tk.Frame(source, bg=colors["PANEL"])
    path_line.pack(fill="x", padx=10, pady=(0, 9))
    path_field = design.entry(path_line, path_var, app.theme, compact=compact)
    path_field.pack(side="left", fill="x", expand=True, padx=(0, 6))

    def choose_file():
        file_path = filedialog.askopenfilename(
            parent=app.root, title="Choose a read-only Excel workbook",
            filetypes=[("Excel workbooks", "*.xlsx *.xlsm *.xls *.xltx *.xltm"),
                       ("All files", "*.*")])
        if file_path:
            path_var.set(file_path)

    design.button(path_line, "Browse", choose_file, app.theme,
                  compact=True).pack(side="right")
    path_var.trace_add("write", lambda *_: setattr(app, "_extra_excel_path",
                                                  path_var.get()))

    lookup_box = design.panel(parent, app.theme)
    lookup_box.pack(fill="x", pady=(0, 11))
    label(lookup_box, "SMART SEARCH", size=9, bold=True, bg=colors["PANEL"]
          ).pack(anchor="w", padx=11, pady=(10, 7))
    search_var = tk.StringVar(master=app.root)
    search_line = tk.Frame(lookup_box, bg=colors["PANEL"])
    search_line.pack(fill="x", padx=10, pady=(0, 7))
    entry = design.entry(search_line, search_var, app.theme, compact=compact)
    entry.pack(side="left", fill="x", expand=True, padx=(0, 6))
    label(lookup_box, "Any column: group code, customer, IP, VRF, VDOM, VLAN or text.",
          bg=colors["PANEL"], muted=True, size=8,
          wraplength=640 if wide else 260).pack(fill="x", padx=11, pady=(0, 10))

    state_label = label(parent, "", size=9, muted=True,
                        wraplength=700 if wide else 280)
    state_label.pack(fill="x", pady=(0, 9))

    results_area = tk.Frame(parent, bg=colors["BG"])
    results_area.pack(fill="both", expand=True)
    matches_panel = design.panel(results_area, app.theme)
    details_panel = design.panel(results_area, app.theme)
    if wide:
        matches_panel.pack(side="left", fill="both", expand=True, padx=(0, 8))
        details_panel.pack(side="left", fill="both", expand=True)
    else:
        matches_panel.pack(fill="both", expand=True, pady=(0, 9))
        details_panel.pack(fill="both", expand=True)

    label(matches_panel, "MATCHES", size=9, bold=True, bg=colors["PANEL"]
          ).pack(fill="x", padx=10, pady=(10, 7))
    results_wrap = tk.Frame(matches_panel, bg=colors["PANEL"])
    results_wrap.pack(fill="both", expand=True, padx=9, pady=(0, 10))
    result_list = tk.Listbox(
        results_wrap, height=17 if wide else (5 if compact else 8),
        bg=colors["INPUT"], fg=colors["WHITE"],
        selectbackground=colors["ACCENT_DARK"],
        selectforeground=colors["WHITE"], activestyle="none",
        highlightthickness=1, highlightbackground=colors["BORDER"],
        relief="flat", font=("Segoe UI", 9), exportselection=False)
    list_scroll = tk.Scrollbar(results_wrap, command=result_list.yview)
    result_list.configure(yscrollcommand=list_scroll.set)
    list_scroll.pack(side="right", fill="y")
    result_list.pack(side="left", fill="both", expand=True)

    label(details_panel, "ALL COLUMNS  /  SELECTED ROW", size=9, bold=True,
          bg=colors["PANEL"]).pack(fill="x", padx=10, pady=(10, 7))
    detail_wrap = tk.Frame(details_panel, bg=colors["PANEL"])
    detail_wrap.pack(fill="both", expand=True, padx=9, pady=(0, 10))
    details = tk.Text(
        detail_wrap, height=21 if wide else (9 if compact else 13),
        width=28, wrap="word", bg=colors["INPUT"], fg=colors["WHITE"],
        selectbackground=colors["ACCENT_DARK"], highlightthickness=1,
        highlightbackground=colors["BORDER"], bd=0, relief="flat",
        font=("Segoe UI", 9), padx=10, pady=8)
    detail_scroll = tk.Scrollbar(detail_wrap, command=details.yview)
    details.configure(yscrollcommand=detail_scroll.set)
    detail_scroll.pack(side="right", fill="y")
    details.pack(side="left", fill="both", expand=True)
    details.tag_configure("headline", foreground=colors["ACCENT"],
                          font=("Segoe UI", 10, "bold"))
    details.tag_configure("matched", foreground=colors["ACCENT"])
    details.configure(state="disabled")

    hits = []
    job_token = getattr(app, "_extra_excel_work_token", 0)

    def show_details(index):
        details.configure(state="normal")
        details.delete("1.0", "end")
        if index is not None and 0 <= index < len(hits):
            hit = hits[index]
            details.insert("end", f"Sheet: {hit.sheet}\nRow: {hit.row}\n\n", "headline")
            matched = set(hit.matched_columns)
            for field, value in hit.fields:
                details.insert("end", f"{field}\n",
                               "matched" if field in matched else "headline")
                details.insert("end", f"{value}\n\n")
        else:
            details.insert("end", "Select a result to view every populated column.")
        details.configure(state="disabled")
        details.yview_moveto(0)

    def selected(_event=None):
        chosen = result_list.curselection()
        show_details(chosen[0] if chosen else None)

    result_list.bind("<<ListboxSelect>>", selected)
    show_details(None)

    def set_status(message):
        if state_label.winfo_exists():
            state_label.configure(text=message)

    def start_search(_event=None):
        nonlocal hits, job_token
        text = search_var.get().strip()
        file_path = path_var.get().strip().strip('"')
        if not file_path:
            set_status("Select a local Excel workbook first.")
            return
        if not text:
            set_status("Enter a search term first.")
            return
        if len(text) < 2:
            set_status("Enter at least two characters for a useful search.")
            return
        app._extra_excel_path = file_path  # Session memory only. Not in data.json.
        if hasattr(app, "_extra_excel_cancel"):
            app._extra_excel_cancel.set()
        cancel = threading.Event()
        app._extra_excel_cancel = cancel
        app._extra_excel_work_token = getattr(app, "_extra_excel_work_token", 0) + 1
        job_token = app._extra_excel_work_token
        current_job = job_token
        hits = []
        result_list.delete(0, "end")
        show_details(None)
        set_status("Searching locally (Microsoft Excel may open a protected book in the background)…")
        run_button.configure(state="disabled")
        pending = queue.Queue(maxsize=1)

        def worker():
            try:
                result = lookup.search_workbook(
                    file_path, text, cancelled=cancel.is_set)
                pending.put(("ok", result))
            except (OSError, ValueError, ImportError, RuntimeError) as exc:
                # Never log workbook contents, cells or search terms.
                pending.put(("error", f"{type(exc).__name__}: {exc}"))
            except Exception as exc:
                pending.put(("error", "Could not read this workbook (" +
                             type(exc).__name__ + ")."))

        threading.Thread(target=worker, daemon=True,
                         name="pocket-extra-excel-lookup").start()

        def poll():
            nonlocal hits
            if cancel.is_set() or current_job != app._extra_excel_work_token:
                return
            if not state_label.winfo_exists():
                cancel.set()
                return
            try:
                kind, payload = pending.get_nowait()
            except queue.Empty:
                app.root.after(100, poll)
                return
            run_button.configure(state="normal")
            if kind == "error":
                set_status(payload)
                return
            hits, capped = payload
            if not hits:
                set_status("No matches found across the workbook.")
                return
            for hit in hits:
                preview = next((value for field, value in hit.fields
                                if field in hit.matched_columns), "")
                preview = preview.replace("\n", " ").replace("\r", " ")
                result_list.insert("end",
                                   f"{hit.sheet}  ·  Row {hit.row}  ·  {preview[:56]}")
            suffix = " (first results; limit reached)" if capped else ""
            set_status(f"{len(hits)} matching rows found{suffix}. No files were modified.")
            result_list.selection_set(0)
            result_list.see(0)
            show_details(0)

        app.root.after(100, poll)

    run_button = design.button(search_line, "Search", start_search, app.theme,
                               primary=True, compact=True)
    run_button.pack(side="right")
    entry.bind("<Return>", start_search)
    path_field.bind("<Return>", lambda _event: entry.focus_set())
    entry.focus_set()
