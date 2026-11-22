"""Pocket Extra: original live Excel lookup plus explicitly synced SQLite mode."""
from __future__ import annotations

import queue
import threading
from datetime import datetime
import tkinter as tk
from tkinter import filedialog, messagebox

from . import extra_excel_lookup as lookup
from . import extra_excel_db as db
from . import extra_soc_outlook as soc
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

    # Mini already displays the Extra tab in the shell: avoid redundant
    # headings that force the result panels below the fold.
    if not compact:
        label(parent, "Extra  /  Excel lookup", size=18 if wide else 13,
              bold=True).pack(fill="x", pady=(0, 5))
        label(parent, "Search live Excel or a manually synced local database.",
              size=9, muted=True, wraplength=650 if wide else 350).pack(
                  fill="x", pady=(0, 10))

    mode_var = tk.StringVar(master=app.root,
                            value=getattr(app, "_extra_excel_mode", "local"))
    if mode_var.get() not in ("local", "database"):
        mode_var.set("local")
    mode_box = design.panel(parent, app.theme)
    mode_box.pack(fill="x", pady=(0, 6 if compact else 10))
    mode_row = tk.Frame(mode_box, bg=colors["PANEL"])
    mode_row.pack(fill="x", padx=8, pady=5 if compact else 8)
    # One real switch on the right, with minimal text explaining the modes.
    # Unlike two unrelated buttons, the slider always communicates a single
    # mutually exclusive Local (live Excel) / Database (offline) state.
    mode_choices = tk.Frame(mode_row, bg=colors["PANEL"])
    mode_choices.pack(side="right", padx=(2, 0))
    local_caption = label(mode_choices, "Local", size=8,
                          bg=colors["PANEL"])
    local_caption.pack(side="left", padx=(0, 4))
    mode_switch = tk.Canvas(
        mode_choices, width=40, height=20, bg=colors["PANEL"],
        bd=0, relief="flat", highlightthickness=1,
        highlightbackground=colors["PANEL"], takefocus=True,
        cursor="hand2")
    mode_switch.pack(side="left")
    database_caption = label(mode_choices, "Database", size=8,
                             bg=colors["PANEL"])
    database_caption.pack(side="left", padx=(4, 0))
    label(mode_row, "MODE: Live / Offline", size=8, bold=True,
          bg=colors["PANEL"]).pack(side="left", padx=(2, 0))

    source = design.panel(parent, app.theme)
    source.pack(fill="x", pady=(0, 6 if compact else 10))
    if not compact:
        label(source, "EXCEL SOURCE  ·  ORIGINAL FILE READ ONLY",
              size=8, bold=True, bg=colors["PANEL"]).pack(
                  anchor="w", padx=11, pady=(9, 6))
    path_var = tk.StringVar(master=app.root, value=getattr(app, "_extra_excel_path", ""))
    path_line = tk.Frame(source, bg=colors["PANEL"])
    path_line.pack(fill="x", padx=9, pady=(6 if compact else 0, 7 if compact else 9))
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
    label(source, "Excel file · e.g. Extranet_2026.xlsx", size=8, muted=True,
          bg=colors["PANEL"], wraplength=290 if compact else 630
          ).pack(fill="x", padx=10, pady=(0, 6))

    database_panel = design.panel(parent, app.theme)
    db_top = tk.Frame(database_panel, bg=colors["PANEL"])
    if not compact:
        db_top.pack(fill="x", padx=10, pady=(9, 4))
        label(db_top, "DATABASE", bold=True, size=8,
              bg=colors["PANEL"]).pack(anchor="w")
    db_info_label = label(database_panel, "", size=8, muted=True,
                          bg=colors["PANEL"], wraplength=650 if wide else 285)
    db_info_label.pack(fill="x", padx=10, pady=(7 if compact else 0, 5))
    db_actions = tk.Frame(database_panel, bg=colors["PANEL"])
    db_actions.pack(fill="x", padx=9, pady=(0, 7 if compact else 9))

    search_panel = design.panel(parent, app.theme)
    search_panel.pack(fill="x", pady=(0, 6 if compact else 10))
    label(search_panel, "SMART SEARCH", bold=True, size=9,
          bg=colors["PANEL"]).pack(anchor="w", padx=11, pady=(7 if compact else 9, 4 if compact else 6))
    search_var = tk.StringVar(master=app.root)
    search_line = tk.Frame(search_panel, bg=colors["PANEL"])
    search_line.pack(fill="x", padx=10, pady=(0, 4 if compact else 6))
    entry = design.entry(search_line, search_var, app.theme, compact=compact)
    entry.pack(side="left", fill="x", expand=True, padx=(0, 6))
    if not compact:
        label(search_panel, "Any column · group code · customer · IP · VRF · VDOM · VLAN",
              bg=colors["PANEL"], muted=True, size=8,
              wraplength=650 if wide else 310).pack(fill="x", padx=11, pady=(0, 8))

    state_label = label(parent, "", size=9, muted=True,
                        wraplength=700 if wide else 280)
    state_label.pack(fill="x", pady=(0, 5 if compact else 8))

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

    detail_heading = tk.Frame(details_panel, bg=colors["PANEL"])
    detail_heading.pack(fill="x", padx=10, pady=(7 if compact else 9, 5))
    # One Outlook action beside the selected-row heading. It is enabled only
    # when the results list has a selected row; no mail is sent by Pocket.
    soc_button = design.button(
        detail_heading, "Outlook · SOC", lambda: create_soc_draft(),
        app.theme, compact=True, primary=True)
    soc_button.pack(side="right", padx=(5, 0))
    soc_button.configure(state="disabled")
    label(detail_heading, "SELECTED ROW" if compact else "ALL COLUMNS / SELECTED ROW",
          size=9, bold=True, bg=colors["PANEL"]).pack(
              side="left", fill="x", expand=True)
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
        soc_button.configure(state="normal" if index is not None
                             and 0 <= index < len(hits) else "disabled")
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

    def create_soc_draft():
        """Only the selected row is used; no recipient or send action."""
        chosen = result_list.curselection()
        if not chosen or not 0 <= chosen[0] < len(hits):
            set_status("Select a search result before opening an SOC draft.")
            return
        hit = hits[chosen[0]]
        draft = soc.make_soc_draft(hit)
        missing = draft.details.missing()
        if missing:
            should_open = messagebox.askyesno(
                "SOC draft · missing details",
                "Some information was not found in this row:\n\n" +
                "\n".join("• " + field for field in missing) +
                "\n\nPocket will leave these fields for you to complete "
                "in Outlook. Open the draft?",
                parent=app.root, icon="warning")
            if not should_open:
                return
        try:
            launched = soc.open_draft(draft)
        except soc.OutlookUnavailable as exc:
            set_status("Outlook draft could not be opened.")
            messagebox.showerror("SOC / Outlook", str(exc), parent=app.root)
            return
        # Never set a recipient, save the mail or submit it automatically.
        set_status("SOC draft opened in Outlook." if launched == "outlook" else
                   "SOC draft opened in the default Windows email app.")

    result_list.bind("<<ListboxSelect>>", selected)
    show_details(None)

    def clear_results():
        nonlocal hits
        hits = []
        result_list.delete(0, "end")
        show_details(None)

    def update_db_info():
        """Only the timestamp and success state; no source paths or row counts."""
        try:
            info = db.read_info()
            if info is None:
                db_info_label.configure(text="Last sync: —  ·  No database")
                return None
            raw_time = info.get("updated_at", "")
            try:
                moment = datetime.fromisoformat(raw_time.replace("Z", "+00:00"))
                moment = moment.astimezone()
                date_label = moment.strftime("%d/%m/%Y %H:%M")
            except (ValueError, TypeError, OverflowError):
                date_label = "Unknown"
            db_info_label.configure(
                text=f"Last sync: {date_label}  ·  ✓ Success")
            return info
        except (OSError, RuntimeError) as exc:
            db_info_label.configure(text="Last sync: —  ·  ✕ Failed")
            set_status(str(exc))
            return None

    def apply_mode():
        app._extra_excel_mode = mode_var.get()
        if mode_var.get() == "database":
            database_panel.pack(before=search_panel, fill="x",
                                pady=(0, 6 if compact else 9))
            set_status("")
            update_db_info()
        else:
            database_panel.pack_forget()
            set_status("")
        # Render a single switch, not two mode buttons.
        database_active = mode_var.get() == "database"
        mode_switch.delete("all")
        rail = colors["ACCENT_DARK"] if database_active else colors["CARD"]
        mode_switch.create_oval(2, 2, 21, 20, fill=rail, outline=rail)
        mode_switch.create_rectangle(11, 2, 30, 20, fill=rail, outline=rail)
        mode_switch.create_oval(20, 2, 39, 20, fill=rail, outline=rail)
        thumb_x = 29 if database_active else 12
        mode_switch.create_oval(thumb_x - 8, 3, thumb_x + 8, 19,
                                fill=colors["WHITE"], outline=colors["WHITE"])
        local_caption.configure(
            fg=colors["WHITE"] if not database_active else colors["MUTED"])
        database_caption.configure(
            fg=colors["WHITE"] if database_active else colors["MUTED"])
        clear_results()

    def change_mode(mode):
        if busy:
            set_status("Finish the current operation before changing mode.")
            return
        mode_var.set(mode)
        apply_mode()

    def toggle_mode(_event=None):
        mode_switch.focus_set()
        change_mode("local" if mode_var.get() == "database" else "database")
        return "break"

    mode_switch.bind("<Button-1>", toggle_mode)
    mode_switch.bind("<space>", toggle_mode)
    mode_switch.bind("<Return>", toggle_mode)
    mode_switch.bind(
        "<FocusIn>", lambda _event: mode_switch.configure(
            highlightbackground=colors["ACCENT"]))
    mode_switch.bind(
        "<FocusOut>", lambda _event: mode_switch.configure(
            highlightbackground=colors["PANEL"]))
    # The text beside the switch is also a clickable target.
    for caption, value in ((local_caption, "local"),
                           (database_caption, "database")):
        caption.bind("<Button-1>", lambda _event, choice=value: change_mode(choice))
        caption.configure(cursor="hand2")

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
        import_button.configure(state="disabled")
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
                    set_status(f"Syncing SQLite database: {counter['rows']:,} rows read…")
                app.root.after(120, poll)
                return
            busy = False
            search_button.configure(state="normal")
            sync_button.configure(state="normal")
            delete_button.configure(state="normal")
            import_button.configure(state="normal")
            if status == "error":
                if kind in ("sync", "import"):
                    update_db_info()
                set_status(value + (" Existing database was preserved."
                                    if kind in ("sync", "import") else ""))
                return
            if kind in ("sync", "import"):
                if value is None:
                    set_status("Cancelled. Existing database was preserved.")
                else:
                    verified = update_db_info()
                    if verified is None:
                        set_status("Unable to read the new database. Check status above.")
                    else:
                        set_status("Database loaded successfully." if kind == "import"
                                   else "Sync completed successfully.")
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
            # An imported portable database may reference an Excel path from a
            # different machine. Searching it never requires the Excel source.
            # The Excel field above is used only by Local and manual Sync.
        except (RuntimeError, OSError) as exc:
            set_status(str(exc))
            return
        clear_results()
        set_status("Searching the local SQLite index…")
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
            "Create plain SQLite database?",
            "This creates an OFFLINE, UNENCRYPTED copy of all populated Excel "
            "rows in Pocket's local data folder as normal, readable SQLite.\n\n"
            "Programmatic access to an IRM workbook does not necessarily authorize "
            "saving a separate copy. Confirm your workplace policy permits it.\n\n"
            "Continue with a manual Sync?",
            icon="warning", parent=app.root):
            return
        set_status("Syncing from Excel…")
        work("sync", lambda cancel, report: db.sync_database(
            source_path, cancelled=cancel.is_set, on_progress=report))

    def load_index():
        """Import an existing Pocket Extra SQLite file after full validation."""
        if busy:
            return
        selected_file = filedialog.askopenfilename(
            parent=app.root, title="Load Pocket Extra database",
            filetypes=[("Pocket SQLite database", "*.sqlite3 *.sqlite *.db *.db3"),
                       ("All files", "*.*")])
        if not selected_file:
            return
        if not messagebox.askyesno(
            "Load database?",
            "Load this existing Pocket Extra database into the local Pocket "
            "data folder? The selected file will remain unchanged.\n\n"
            "The current Pocket database will only be replaced after successful "
            "validation. This is a readable, unencrypted local SQLite file.",
            icon="question", parent=app.root):
            return
        clear_results()
        set_status("Validating and loading database…")
        work("import", lambda cancel, report: db.import_database(
            selected_file, cancelled=cancel.is_set))

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

    sync_button = design.button(db_actions, "Sync", start_sync,
                                app.theme, primary=True, compact=True)
    sync_button.pack(side="left", padx=(0, 4))
    # Place destructive actions at the far right; Sync stays on the left.
    delete_button = design.button(db_actions, "Delete", delete_index,
                                  app.theme, compact=True)
    delete_button.pack(side="right")
    import_button = design.button(db_actions, "Load DB", load_index,
                                  app.theme, compact=True)
    import_button.pack(side="right", padx=(0, 4))
    apply_mode()
    entry.focus_set()
