"""Pocket Extra: original live Excel lookup plus explicitly synced SQLite mode."""
from __future__ import annotations

import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox

from . import extra_excel_lookup as lookup
from . import extra_excel_db as db
from . import pocket_design as design


def build(app, parent):
    colors = design.colors(app.theme)
    wide = app.display_mode == "dashboard"
    compact = app.display_mode == "mini"

    def label(target, text, *, size=9, muted=False, bold=False, bg=None, **kwargs):
        return tk.Label(target, text=text, bg=bg or colors["BG"],
                        fg=colors["MUTED"] if muted else colors["WHITE"],
                        font=("Segoe UI", size, "bold" if bold else "normal"),
                        anchor="w", justify="left", **kwargs)

    label(parent, "Extra  /  Excel lookup", size=18 if wide else 13,
          bold=True).pack(fill="x", pady=(0, 5))
    label(parent, "Live Excel search or a fast, manually synced encrypted database.",
          size=9, muted=True, wraplength=650 if wide else 280).pack(
              fill="x", pady=(0, 10))

    mode_var = tk.StringVar(master=app.root,
                            value=getattr(app, "_extra_excel_mode", "local"))
    if mode_var.get() not in ("local", "database"):
        mode_var.set("local")
    mode_box = design.panel(parent, app.theme)
    mode_box.pack(fill="x", pady=(0, 10))
    mode_row = tk.Frame(mode_box, bg=colors["PANEL"])
    mode_row.pack(fill="x", padx=9, pady=8)
    label(mode_row, "SEARCH MODE", size=9, bold=True,
          bg=colors["PANEL"]).pack(side="left", padx=(0, 7))

    source = design.panel(parent, app.theme)
    source.pack(fill="x", pady=(0, 10))
    label(source, "EXCEL SOURCE  ·  ORIGINAL FILE READ ONLY",
          size=8, bold=True, bg=colors["PANEL"]).pack(
              anchor="w", padx=11, pady=(9, 6))
    path_var = tk.StringVar(master=app.root, value=getattr(app, "_extra_excel_path", ""))
    path_line = tk.Frame(source, bg=colors["PANEL"])
    path_line.pack(fill="x", padx=10, pady=(0, 9))
    path_field = design.entry(path_line, path_var, app.theme, compact=compact)
    path_field.pack(side="left", fill="x", expand=True, padx=(0, 6))

    def choose_file():
        path = filedialog.askopenfilename(
            parent=app.root, title="Choose local Excel workbook",
            filetypes=[("Excel workbooks", "*.xlsx *.xlsm *.xls *.xltx *.xltm"),
                       ("All files", "*.*")])
        if path:
            path_var.set(path)

    design.button(path_line, "Browse", choose_file, app.theme,
                  compact=True).pack(side="right")
    path_var.trace_add("write", lambda *_: setattr(app, "_extra_excel_path",
                                                  path_var.get()))

    database_panel = design.panel(parent, app.theme)
    db_top = tk.Frame(database_panel, bg=colors["PANEL"])
    db_top.pack(fill="x", padx=10, pady=(9, 6))
    db_title = label(db_top, "ENCRYPTED DATABASE  ·  MANUAL SYNC ONLY",
                     bold=True, size=8, bg=colors["PANEL"])
    db_title.pack(anchor="w")
    db_info_label = label(database_panel, "", size=8, muted=True,
                          bg=colors["PANEL"], wraplength=650 if wide else 285)
    db_info_label.pack(fill="x", padx=10, pady=(0, 7))
    db_actions = tk.Frame(database_panel, bg=colors["PANEL"])
    db_actions.pack(fill="x", padx=10, pady=(0, 9))

    search_panel = design.panel(parent, app.theme)
    search_panel.pack(fill="x", pady=(0, 10))
    label(search_panel, "SMART SEARCH", bold=True, size=9,
          bg=colors["PANEL"]).pack(anchor="w", padx=11, pady=(9, 6))
    search_var = tk.StringVar(master=app.root)
    search_line = tk.Frame(search_panel, bg=colors["PANEL"])
    search_line.pack(fill="x", padx=10, pady=(0, 6))
    entry = design.entry(search_line, search_var, app.theme, compact=compact)
    entry.pack(side="left", fill="x", expand=True, padx=(0, 6))
    label(search_panel, "Any column · group code · customer · IP · VRF · VDOM · VLAN",
          bg=colors["PANEL"], muted=True, size=8,
          wraplength=650 if wide else 270).pack(fill="x", padx=11, pady=(0, 8))

    state_label = label(parent, "", size=9, muted=True,
                        wraplength=700 if wide else 280)
    state_label.pack(fill="x", pady=(0, 8))

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
          ).pack(fill="x", padx=10, pady=(9, 6))
    results_wrap = tk.Frame(matches_panel, bg=colors["PANEL"])
    results_wrap.pack(fill="both", expand=True, padx=9, pady=(0, 9))
    result_list = tk.Listbox(
        results_wrap, height=17 if wide else (5 if compact else 8),
        bg=colors["INPUT"], fg=colors["WHITE"],
        selectbackground=colors["ACCENT_DARK"],
        selectforeground=colors["WHITE"], activestyle="none",
        highlightthickness=1, highlightbackground=colors["BORDER"],
        relief="flat", font=("Segoe UI", 9), exportselection=False)
    list_scroll = tk.Scrollbar(results_wrap, command=result_list.yview)
    result_list.configure(yscrollcommand=list_scroll.set)
    if not compact:
        list_scroll.pack(side="right", fill="y")
    result_list.pack(side="left", fill="both", expand=True)

    label(details_panel, "ALL COLUMNS / SELECTED ROW", size=9, bold=True,
          bg=colors["PANEL"]).pack(fill="x", padx=10, pady=(9, 6))
    detail_wrap = tk.Frame(details_panel, bg=colors["PANEL"])
    detail_wrap.pack(fill="both", expand=True, padx=9, pady=(0, 9))
    details = tk.Text(
        detail_wrap, height=21 if wide else (9 if compact else 13),
        width=28, wrap="word", bg=colors["INPUT"], fg=colors["WHITE"],
        selectbackground=colors["ACCENT_DARK"], highlightthickness=1,
        highlightbackground=colors["BORDER"], bd=0, relief="flat",
        font=("Segoe UI", 9), padx=10, pady=8)
    detail_scroll = tk.Scrollbar(detail_wrap, command=details.yview)
    details.configure(yscrollcommand=detail_scroll.set)
    if not compact:
        detail_scroll.pack(side="right", fill="y")
    details.pack(side="left", fill="both", expand=True)
    details.tag_configure("headline", foreground=colors["ACCENT"],
                          font=("Segoe UI", 10, "bold"))
    details.tag_configure("matched", foreground=colors["ACCENT"])
    details.configure(state="disabled")

    hits = []
    busy = False

    def set_status(text):
        if state_label.winfo_exists():
            state_label.configure(text=text)

    def show_details(index):
        if not details.winfo_exists():
            return
        details.configure(state="normal")
        details.delete("1.0", "end")
        if index is not None and 0 <= index < len(hits):
            hit = hits[index]
            details.insert("end", f"Sheet: {hit.sheet}\nRow: {hit.row}\n\n",
                           "headline")
            matching = set(hit.matched_columns)
            for field, value in hit.fields:
                details.insert("end", field + "\n",
                               "matched" if field in matching else "headline")
                details.insert("end", value + "\n\n")
        else:
            details.insert("end", "Select a result to view each populated column.")
        details.configure(state="disabled")
        details.yview_moveto(0)

    def selected(_event=None):
        chosen = result_list.curselection()
        show_details(chosen[0] if chosen else None)

    result_list.bind("<<ListboxSelect>>", selected)
    show_details(None)

    def clear_results():
        nonlocal hits
        hits = []
        result_list.delete(0, "end")
        show_details(None)

    def update_db_info():
        try:
            info = db.read_info()
            if info is None:
                db_info_label.configure(
                    text="No database. Choose a workbook and press Sync to create one.\n"
                         "Stored in: " + str(db.database_path()))
                return None
            time = info.get("updated_at", "").replace("T", " ")[:19]
            db_info_label.configure(
                text=f"{info['rows']:,} rows indexed · Last manual sync: {time} UTC\n"
                     f"Source: {info['source']}\n"
                     f"Storage: {db.database_path()}")
            return info
        except (OSError, RuntimeError) as exc:
            db_info_label.configure(text="Cannot read database: " + str(exc))
            return None

    def apply_mode():
        app._extra_excel_mode = mode_var.get()
        if mode_var.get() == "database":
            database_panel.pack(before=search_panel, fill="x", pady=(0, 9))
            update_db_info()
            set_status("Database mode: searches use the last manually synced snapshot.")
        else:
            database_panel.pack_forget()
            set_status("Local mode: searches read the current Excel workbook.")
        for key, button in mode_buttons.items():
            active = key == mode_var.get()
            button.configure(bg=colors["ACCENT_DARK"] if active else colors["CARD"],
                             fg=colors["WHITE"] if active else colors["SECONDARY"])
        clear_results()

    def change_mode(mode):
        if busy:
            set_status("Finish the current operation before changing mode.")
            return
        mode_var.set(mode)
        apply_mode()

    mode_buttons = {}
    for key, caption in (("local", "Local"), ("database", "Database")):
        button = design.button(mode_row, caption, lambda value=key: change_mode(value),
                               app.theme, compact=True)
        button.pack(side="left", padx=(0, 5))
        mode_buttons[key] = button

    def work(kind, operation, *, progress=None):
        """One worker at a time, with all Tk calls on the GUI thread."""
        nonlocal busy, hits
        if busy:
            set_status("An operation is already running.")
            return
        busy = True
        if hasattr(app, "_extra_excel_cancel"):
            app._extra_excel_cancel.set()
        cancel = threading.Event()
        app._extra_excel_cancel = cancel
        app._extra_excel_work_token = getattr(app, "_extra_excel_work_token", 0) + 1
        work_id = app._extra_excel_work_token
        search_button.configure(state="disabled")
        sync_button.configure(state="disabled")
        delete_button.configure(state="disabled")
        messages = queue.Queue(maxsize=1)
        counter = {"rows": 0}

        def worker():
            try:
                value = operation(cancel, lambda count: counter.__setitem__("rows", count))
                messages.put(("ok", value))
            except (OSError, ValueError, ImportError, RuntimeError) as exc:
                messages.put(("error", f"{type(exc).__name__}: {exc}"))
            except Exception as exc:
                messages.put(("error", "Operation failed (" +
                              type(exc).__name__ + ")."))

        threading.Thread(target=worker, daemon=True,
                         name="pocket-extra-" + kind).start()

        def poll():
            nonlocal busy, hits
            if (cancel.is_set() or work_id != app._extra_excel_work_token
                    or not state_label.winfo_exists()):
                cancel.set()
                busy = False
                return
            try:
                status, value = messages.get_nowait()
            except queue.Empty:
                if kind == "sync":
                    set_status(f"Syncing encrypted database: {counter['rows']:,} rows read…")
                app.root.after(120, poll)
                return
            busy = False
            search_button.configure(state="normal")
            sync_button.configure(state="normal")
            delete_button.configure(state="normal")
            if status == "error":
                set_status(value + (" Existing database was preserved."
                                    if kind == "sync" else ""))
                return
            if kind == "sync":
                if value is None:
                    set_status("Sync cancelled. Existing database was preserved.")
                else:
                    verified = update_db_info()
                    if verified is None:
                        set_status(
                            "Sync finished, but the index could not be opened. "
                            "Check the database status above; do not delete your "
                            "source workbook. Local search is still available.")
                    else:
                        set_status(f"Database ready: {verified['rows']:,} rows. "
                                   "Future searches will not open Excel.")
                return
            hits, capped = value
            if not hits:
                set_status("No matches found.")
                return
            for hit in hits:
                preview = next((value for field, value in hit.fields
                                if field in hit.matched_columns), "")
                preview = preview.replace("\r", " ").replace("\n", " ")
                result_list.insert("end",
                                   f"{hit.sheet} · Row {hit.row} · {preview[:56]}")
            set_status(f"{len(hits)} matching rows" +
                       (" (first results; narrow the query)" if capped else "") +
                       (". Source file not accessed." if kind == "database" else
                        ". Source file not modified."))
            result_list.selection_set(0)
            result_list.see(0)
            show_details(0)

        app.root.after(120, poll)

    def start_search(_event=None):
        term = search_var.get().strip()
        source_path = path_var.get().strip().strip('"')
        if len(term) < 2:
            set_status("Enter at least two characters to search.")
            return
        if mode_var.get() == "local":
            if not source_path:
                set_status("Choose an Excel file for Local mode.")
                return
            clear_results()
            set_status("Searching Excel locally…")
            work("local", lambda cancel, report: lookup.search_workbook(
                source_path, term, cancelled=cancel.is_set))
            return
        try:
            info = db.read_info()
            if info is None:
                set_status("No database yet. Select an Excel file and press Sync.")
                return
            if source_path and not db.same_source(source_path, info):
                set_status("Different Excel file selected. Sync it manually, "
                           "or choose the database's linked workbook.")
                return
        except (RuntimeError, OSError) as exc:
            set_status(str(exc))
            return
        clear_results()
        set_status("Searching the encrypted on-disk index…")
        work("database", lambda cancel, report: db.search_database(
            term, cancelled=cancel.is_set))

    search_button = design.button(search_line, "Search", start_search,
                                  app.theme, primary=True, compact=True)
    search_button.pack(side="right")
    entry.bind("<Return>", start_search)
    path_field.bind("<Return>", lambda _event: entry.focus_set())

    def start_sync():
        if busy:
            return
        source_path = path_var.get().strip().strip('"')
        if not source_path:
            set_status("Choose the Excel source to sync.")
            return
        if not messagebox.askyesno(
            "Create encrypted local database?",
            "This will create an OFFLINE, PERSISTENT copy of all populated Excel "
            "rows in Pocket's local data folder, encrypted for this Windows user.\n\n"
            "Programmatic access to an IRM workbook does not necessarily authorize "
            "saving a separate copy. Confirm your workplace policy permits it.\n\n"
            "Continue with a manual Sync?",
            icon="warning", parent=app.root):
            return
        set_status("Reading Excel and building the encrypted database…")
        work("sync", lambda cancel, report: db.sync_database(
            source_path, cancelled=cancel.is_set, on_progress=report))

    def delete_index():
        if busy:
            return
        if not messagebox.askyesno(
            "Delete Excel database?",
            "Delete Pocket's locally cached Excel database? The source Excel "
            "file will NOT be touched.", icon="warning", parent=app.root):
            return
        try:
            removed = db.delete_database()
            update_db_info()
            clear_results()
            set_status("Database deleted." if removed else "No database exists.")
        except OSError as exc:
            set_status("Could not delete database: " + str(exc))

    sync_button = design.button(db_actions, "Sync database", start_sync,
                                app.theme, primary=True, compact=True)
    sync_button.pack(side="left", padx=(0, 6))
    delete_button = design.button(db_actions, "Delete DB", delete_index,
                                  app.theme, compact=True)
    delete_button.pack(side="left")
    apply_mode()
    entry.focus_set()
