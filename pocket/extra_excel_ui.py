"""Pocket Extra: original live Excel lookup plus explicitly synced SQLite mode."""
from __future__ import annotations

import queue
import threading
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox

from . import extra_excel_lookup as lookup
from . import extra_excel_db as db
from . import extra_excel_presentation as presentation
from . import extra_soc_outlook as soc
from . import pocket_design as design


def session(app):
    """Only the current view and operation, never persisted or logged."""
    if not hasattr(app, "_extra_session"):
        app._extra_session = dict(query="", hits=[], selected=None, status="",
                                  list_y=0., detail_y=0., page_y=0., mode=None,
                                  busy=False, kind=None, scanned=0, total=None,
                                  indexed=0, phase="", revision=0)
    return app._extra_session


def detach(app):
    snapshot = getattr(app, "_extra_snapshot", None)
    if snapshot is not None:
        snapshot()
    app._extra_snapshot = None
    app._extra_render = None


def build(app, parent):
    state = session(app)
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
                            value=getattr(app, "_extra_excel_mode", "database"))
    if mode_var.get() not in ("local", "database"):
        mode_var.set("database")
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
    path_line.pack(fill="x", padx=9, pady=(4 if compact else 5, 3 if compact else 7))
    # Compact, read-only Excel source: show a filename and Browse, not an
    # editable input. The complete source path stays in a hover tooltip.
    source_name = label(path_line, "", size=8, muted=True,
                        bg=colors["PANEL"], cursor="hand2")
    source_name.pack(side="left", fill="x", expand=True, padx=(0, 6))
    source_tip = design.Tooltip(source_name, "", app.theme)
    def source_display():
        path = path_var.get().strip().strip('"')
        source_tip.message = path or "Select an Excel workbook for Local / Sync."
        if not path:
            return "Excel file · Extranet_2026.xlsx"
        name = Path(path).name
        if len(name) > (26 if compact else 55):
            name = name[:12 if compact else 39] + "…" + name[-10:]
        return "Excel · " + name
    def update_source_label(*_args):
        app._extra_excel_path = path_var.get()
        source_name.configure(text=source_display())

    def choose_file():
        if state["busy"]:
            return
        path = filedialog.askopenfilename(
            parent=app.root, title="Choose local Excel workbook",
            filetypes=[("Excel workbooks", "*.xlsx *.xlsm *.xls *.xltx *.xltm"),
                       ("All files", "*.*")])
        if path and not state["busy"]:
            if path != path_var.get():
                clear_results()
            path_var.set(path)

    source_name.bind("<Button-1>", lambda _event: choose_file())
    design.button(path_line, "Browse", choose_file, app.theme,
                  compact=True).pack(side="right")
    path_var.trace_add("write", update_source_label)
    update_source_label()

    # Database controls are a compact second section of the SAME Excel Source
    # panel. Keep manual sync/import/delete behavior and confirmations intact.
    db_section = tk.Frame(source, bg=colors["PANEL"])
    if not compact:
        label(db_section, "DATABASE · OFFLINE COPY", bold=True, size=8,
              bg=colors["PANEL"]).pack(anchor="w", pady=(0, 3))
    db_info_label = label(db_section, "", size=8, muted=True,
                          bg=colors["PANEL"], wraplength=650 if wide else 290)
    db_info_label.pack(fill="x", pady=(0, 2 if compact else 4))
    sync_bar = tk.Frame(db_section, height=3, bg=colors["CARD"])
    sync_fill = tk.Frame(sync_bar, bg=colors["ACCENT"])
    db_actions = tk.Frame(db_section, bg=colors["PANEL"])
    db_actions.pack(fill="x", pady=(0, 0 if compact else 1))

    search_panel = design.panel(parent, app.theme)
    search_panel.pack(fill="x", pady=(0, 6 if compact else 10))
    label(search_panel, "SMART SEARCH", bold=True, size=9,
          bg=colors["PANEL"]).pack(anchor="w", padx=11, pady=(7 if compact else 9, 4 if compact else 6))
    search_var = tk.StringVar(master=app.root, value=state["query"])
    search_line = tk.Frame(search_panel, bg=colors["PANEL"])
    search_line.pack(fill="x", padx=10, pady=(0, 4 if compact else 6))
    entry = design.entry(search_line, search_var, app.theme, compact=compact)
    entry.pack(side="left", fill="x", expand=True, padx=(0, 6))
    if not compact:
        label(search_panel, "Any column · group code · customer · IP · VRF · VDOM · VLAN",
              bg=colors["PANEL"], muted=True, size=8,
              wraplength=650 if wide else 310).pack(fill="x", padx=11, pady=(0, 8))

    results_area = tk.Frame(parent, bg=colors["BG"])
    results_area.pack(fill="x" if compact else "both", expand=not compact)
    matches_panel = design.panel(results_area, app.theme)
    details_panel = design.panel(results_area, app.theme)
    if wide:
        matches_panel.pack(side="left", fill="both", expand=True, padx=(0, 8))
        details_panel.pack(side="left", fill="both", expand=True)
    elif compact:
        matches_panel.pack(fill="x", pady=(0, 6))
        details_panel.pack(fill="x")
    else:
        matches_panel.pack(fill="both", expand=True, pady=(0, 9))
        details_panel.pack(fill="both", expand=True)

    matches_heading = tk.Frame(matches_panel, bg=colors["PANEL"])
    matches_heading.pack(fill="x", padx=10, pady=(8 if compact else 9, 5))
    # No permanent status row between SMART SEARCH and MATCHES.
    state_label = label(matches_heading, "", size=8, muted=True,
                        bg=colors["PANEL"], wraplength=145 if compact else 310)
    state_label.pack(side="right", padx=(6, 0))
    state_tooltip = design.Tooltip(state_label, "", app.theme)
    label(matches_heading, "MATCHES", size=9, bold=True, bg=colors["PANEL"]
          ).pack(side="left")
    results_wrap = tk.Frame(matches_panel, bg=colors["PANEL"])
    results_wrap.pack(fill="both", expand=True, padx=9, pady=(0, 9))
    result_list = tk.Listbox(
        results_wrap, height=17 if wide else (5 if compact else 8),
        bg=colors["INPUT"], fg=colors["WHITE"],
        selectbackground=colors["ACCENT_DARK"],
        selectforeground=colors["WHITE"], activestyle="none",
        highlightthickness=1, highlightbackground=colors["BORDER"],
        relief="flat", font=("Segoe UI", 9), exportselection=False)
    # Mini keeps a visible, intentionally thin dark scrollbar. The result
    # Listbox itself must NOT consume the mouse wheel (that gesture scrolls
    # the surrounding Pocket page), but its scrollbar and keyboard navigation
    # continue to work normally.
    list_scroll = tk.Scrollbar(
        results_wrap, command=result_list.yview,
        width=8 if compact else 12,
        bg=colors["CARD"], troughcolor=colors["INPUT"],
        activebackground=colors["CARD_HOVER"],
        highlightthickness=0, borderwidth=0, elementborderwidth=0,
        relief="flat", cursor="hand2")
    result_list.configure(yscrollcommand=list_scroll.set)
    list_scroll.pack(side="right", fill="y", padx=(3, 0) if compact else (0, 0))
    result_list.pack(side="left", fill="both", expand=True)

    if compact:
        def scroll_outer_instead_of_matches(event):
            # Pocket binds its tool-scrolling callback at the root. Listbox
            # class bindings would run before it, changing the selected rows'
            # viewport. Route the wheel directly to the outer page instead.
            canvas = getattr(app, "_tool_scroll_canvas", None)
            if canvas is not None and canvas.winfo_exists():
                delta = getattr(event, "delta", 0)
                if delta:
                    steps = (-1 if delta > 0 else 1) * max(1, abs(delta) // 120)
                elif getattr(event, "num", None) in (4, 5):
                    steps = -1 if event.num == 4 else 1
                else:
                    steps = 0
                if steps:
                    canvas.yview_scroll(steps, "units")
            return "break"
        for sequence in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            result_list.bind(sequence, scroll_outer_instead_of_matches)


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
    # Only a compact overview is shown by default; all other original Excel
    # columns are available on demand in a bounded, scrollable text area.
    detail_wrap = tk.Frame(details_panel, bg=colors["INPUT"])
    detail_wrap.pack(fill="x", padx=9, pady=(0, 7))
    overview_content = tk.Frame(detail_wrap, bg=colors["INPUT"])
    overview_content.pack(fill="x", padx=9, pady=(6, 4))
    expand_button = design.button(
        details_panel, "Show other columns", lambda: toggle_columns(),
        app.theme, compact=True)
    expanded_wrap = tk.Frame(details_panel, bg=colors["PANEL"])
    details = tk.Text(
        expanded_wrap, height=7 if compact else (11 if wide else 10),
        width=28, wrap="word", bg=colors["INPUT"], fg=colors["WHITE"],
        selectbackground=colors["ACCENT_DARK"], highlightthickness=1,
        highlightbackground=colors["BORDER"], bd=0, relief="flat",
        font=("Segoe UI", 9), padx=9, pady=5)
    detail_scroll = tk.Scrollbar(expanded_wrap, command=details.yview)
    details.configure(yscrollcommand=detail_scroll.set)
    if not compact:
        detail_scroll.pack(side="right", fill="y")
    details.pack(side="left", fill="both", expand=True)
    details.tag_configure("headline", foreground=colors["ACCENT"],
                          font=("Segoe UI", 9, "bold"))
    details.configure(state="disabled")

    hits = []
    rendered_revision = -1
    busy = state["busy"]
    page_canvas = getattr(app, "_tool_scroll_canvas", None)

    def set_status(text):
        # Keep Matches compact: counts and progress live in the heading.
        # Preserve full diagnostic messages on hover instead of allocating
        # a blank row before every search.
        state["status"] = str(text or "")
        if state_label.winfo_exists():
            full = state["status"]
            if " matching rows" in full and full.split(" ", 1)[0].isdigit():
                preview = full.split(" ", 1)[0] + " rows"
            elif len(full) > (27 if compact else 65):
                preview = full[:(25 if compact else 63)] + "…"
            else:
                preview = full
            state_label.configure(text=preview)
            state_tooltip.message = full

    def copy_fortigate(value):
        app.root.clipboard_clear()
        app.root.clipboard_append(value)
        app.root.update_idletasks()
        set_status("FortiGate IP copied to clipboard.")

    def show_compact_cell(target, cell, *, ip=False, full=False):
        line = tk.Frame(target, bg=colors["INPUT"])
        line.pack(fill="x", anchor="w")
        label(line, cell.label, size=8, muted=True, bg=colors["INPUT"]
              ).pack(anchor="w")
        if ip and cell.value != "—":
            ip_button = tk.Button(
                line, text=cell.value + "  ⧉",
                command=lambda value=cell.value: copy_fortigate(value),
                bg=colors["INPUT"], fg=colors["ACCENT"], anchor="w",
                cursor="hand2", takefocus=True, bd=0, relief="flat",
                activebackground=colors["INPUT"],
                activeforeground=colors["WHITE"],
                padx=0, pady=0, font=("Segoe UI", 9, "bold"))
            ip_button.pack(fill="x")
            design.Tooltip(ip_button, "Copy FortiGate IP", app.theme)
        else:
            label(line, cell.value, size=9, bold=True, bg=colors["INPUT"],
                  wraplength=(275 if compact else 330) if full else
                  (125 if compact else (165 if wide else 175))).pack(fill="x")
        return line

    def step_hit(direction, *, from_details=False):
        """Keyboard navigation acts on the exact selected Excel/SQLite hit."""
        if not hits:
            return "break"
        current = result_list.curselection()
        index = current[0] if current else (0 if direction > 0 else len(hits) - 1)
        target = max(0, min(len(hits) - 1, index + direction))
        result_list.selection_clear(0, "end")
        result_list.selection_set(target)
        result_list.activate(target)
        result_list.see(target)
        show_details(target)
        if from_details:
            overview_content.focus_set()
        else:
            result_list.focus_set()
        return "break"

    def bind_detail_navigation():
        # Nothing is drawn for the arrows; the details pane itself is a
        # keyboard-focusable region and can change the selected result.
        for root_widget in (details_panel, detail_heading, detail_wrap,
                            overview_content, expanded_wrap, details,
                            soc_button, expand_button):
            root_widget.configure(takefocus=True)
        overview_content.configure(takefocus=True)
        def recurse(widget):
            widget.bind("<Right>",
                        lambda _e: step_hit(+1, from_details=True))
            widget.bind("<Left>",
                        lambda _e: step_hit(-1, from_details=True))
            if isinstance(widget, (tk.Frame, tk.Label)):
                widget.bind("<Button-1>",
                            lambda _e: overview_content.focus_set(), add="+")
            for child in widget.winfo_children():
                recurse(child)
        recurse(details_panel)

    def show_details(index):
        if not overview_content.winfo_exists():
            return
        valid = index is not None and 0 <= index < len(hits)
        soc_button.configure(state="normal" if valid else "disabled")
        for widget in overview_content.winfo_children():
            widget.destroy()
        expand_button.pack_forget()
        expanded_wrap.pack_forget()
        if not valid:
            label(overview_content, "Select a result to view its details.",
                  size=8, muted=True, bg=colors["INPUT"]).pack(anchor="w")
            return
        hit = hits[index]
        quick = presentation.row_overview(hit)
        label(overview_content, f"{quick.sheet} · Row {quick.row}",
              size=8, muted=True, bg=colors["INPUT"]).pack(anchor="w", pady=(0, 4))
        show_compact_cell(overview_content, quick.customer, full=True)
        grid = tk.Frame(overview_content, bg=colors["INPUT"])
        grid.pack(fill="x", pady=(5, 0))
        for column in (0, 1):
            grid.grid_columnconfigure(column, weight=1, uniform="extra")
        for row_number, pair in enumerate(quick.pairs):
            for column, cell in enumerate(pair):
                cell_parent = tk.Frame(grid, bg=colors["INPUT"])
                cell_parent.grid(row=row_number, column=column, sticky="new",
                                 padx=(0, 5) if column == 0 else (5, 0),
                                 pady=(0, 5))
                show_compact_cell(
                    cell_parent, cell, ip=cell.label == "FortiGate IP")
        if quick.remaining:
            expanded = bool(getattr(app, "_extra_excel_columns_expanded", False))
            expand_button.configure(
                text=(f"Hide other columns ({len(quick.remaining)})" if expanded
                      else f"Show other columns ({len(quick.remaining)})"))
            expand_button.pack(fill="x", padx=9, pady=(0, 5))
            if expanded:
                expanded_wrap.pack(fill="x", padx=9, pady=(0, 8))
                details.configure(state="normal")
                details.delete("1.0", "end")
                for header, value in quick.remaining:
                    details.insert("end", header + "\n", "headline")
                    details.insert("end", value + "\n\n")
                details.configure(state="disabled")
                details.yview_moveto(0)
        bind_detail_navigation()

    def toggle_columns():
        app._extra_excel_columns_expanded = not bool(
            getattr(app, "_extra_excel_columns_expanded", False))
        selected = result_list.curselection()
        show_details(selected[0] if selected else None)

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
    # Explicit handlers keep Listbox selection/detail display synchronized
    # across different Windows/Tk keyboard event implementations.
    result_list.bind("<Up>", lambda _e: step_hit(-1))
    result_list.bind("<Down>", lambda _e: step_hit(+1))
    show_details(None)

    def clear_results():
        nonlocal hits
        hits = []
        state.update(hits=[], selected=None, list_y=0., detail_y=0.)
        state["revision"] += 1
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

    def apply_mode(*, restoring=False):
        app._extra_excel_mode = mode_var.get()
        if mode_var.get() == "database":
            db_section.pack(fill="x", padx=9, pady=(0, 4 if compact else 9))
            if not restoring:
                set_status("")
            update_db_info()
        else:
            db_section.pack_forget()
            if not restoring:
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
        if not restoring:
            clear_results()
        state["mode"] = mode_var.get()

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

    def snapshot():
        if not result_list.winfo_exists():
            return
        selected_rows = result_list.curselection()
        state.update(query=search_var.get(), selected=selected_rows[0] if selected_rows else None,
                     list_y=result_list.yview()[0], detail_y=details.yview()[0])
        if page_canvas is not None and page_canvas.winfo_exists():
            state["page_y"] = page_canvas.yview()[0]

    def restore_scroll():
        if not result_list.winfo_exists():
            return
        result_list.yview_moveto(state["list_y"])
        details.yview_moveto(state["detail_y"])
        if page_canvas is not None and page_canvas.winfo_exists():
            page_canvas.yview_moveto(state["page_y"])

    def render(*, restore=False):
        nonlocal busy, hits, rendered_revision
        if not result_list.winfo_exists():
            return
        busy = state["busy"]
        for button in (search_button, sync_button, import_button, delete_button):
            button.configure(state="disabled" if busy else "normal")
        if busy and state["kind"] == "sync":
            scanned, total = state["scanned"], state["total"]
            if state["phase"] == "verify":
                db_info_label.configure(text="Sync · verifying database…")
                if total and scanned == total:
                    sync_fill.place(relwidth=1, relheight=1)
                else:
                    sync_fill.place_forget()
            elif total and scanned <= total:
                percent = min(100, int(scanned * 100 / total))
                db_info_label.configure(text=f"Sync · {scanned:,}/{total:,} rows · {percent}%")
                sync_fill.place(relwidth=percent/100, relheight=1)
            else:
                db_info_label.configure(text=f"Sync · {scanned:,} rows scanned")
                sync_fill.place_forget()
            if not sync_bar.winfo_manager():
                sync_bar.pack(fill="x", before=db_actions, pady=(0, 2))
        else:
            if sync_bar.winfo_manager():
                sync_bar.pack_forget()
            if not busy and state["kind"] in ("sync", "import"):
                saved_status = state["status"]
                update_db_info()
                state["status"] = saved_status
        if rendered_revision != state["revision"]:
            hits = state["hits"]
            result_list.delete(0, "end")
            for hit in hits:
                preview = next((value for field, value in hit.fields
                                if field in hit.matched_columns), "")
                preview = preview.replace("\r", " ").replace("\n", " ")
                result_list.insert("end", f"{hit.sheet} · Row {hit.row} · {preview[:56]}")
            index = state["selected"]
            if index is not None and 0 <= index < len(hits):
                result_list.selection_set(index)
                result_list.activate(index)
            show_details(index)
            rendered_revision = state["revision"]
            if restore:
                app.root.after_idle(restore_scroll)
            else:
                result_list.yview_moveto(0)
        set_status(state["status"])

    def work(kind, operation, *, progress=None):
        """The worker belongs to the session, not to a disposable tab."""
        if state["busy"]:
            return
        cancel = threading.Event()
        app._extra_excel_cancel = cancel
        state.update(busy=True, kind=kind, scanned=0, total=None, indexed=0, phase="read")
        messages = queue.Queue(maxsize=1)
        progress_lock = threading.Lock()
        latest = {"indexed": 0, "scanned": 0, "total": None, "phase": "read"}

        def report(count):
            with progress_lock:
                latest["indexed"] = count

        def scan_report(scanned, total, phase):
            with progress_lock:
                latest.update(scanned=scanned, total=total, phase=phase)

        def worker():
            try:
                value = operation(cancel, report, scan_report)
                messages.put(("ok", value))
            except (OSError, ValueError, ImportError, RuntimeError) as exc:
                messages.put(("error", f"{type(exc).__name__}: {exc}"))
            except Exception as exc:
                messages.put(("error", "Operation failed (" + type(exc).__name__ + ")."))

        def refresh_visible():
            callback = getattr(app, "_extra_render", None)
            if callback is not None:
                callback()

        def poll():
            if cancel.is_set():
                state["busy"] = False
                return
            with progress_lock:
                state.update(latest)
            try:
                status, value = messages.get_nowait()
            except queue.Empty:
                refresh_visible()
                app.root.after(120, poll)
                return
            state["busy"] = False
            if status == "error":
                state["status"] = value + (" Existing database was preserved."
                                            if kind in ("sync", "import") else "")
            elif kind in ("sync", "import"):
                if value is None:
                    state["status"] = "Cancelled. Existing database was preserved."
                else:
                    state.update(hits=[], selected=None, list_y=0., detail_y=0.)
                    state["revision"] += 1
                    state["status"] = ("Database loaded successfully." if kind == "import"
                                       else "")
            else:
                new_hits, capped = value
                state.update(hits=new_hits, selected=0 if new_hits else None,
                             list_y=0., detail_y=0.)
                state["revision"] += 1
                state["status"] = (f"{len(new_hits)} matching rows" +
                                   (" (first results; narrow the query)" if capped else "")
                                   if new_hits else "No matches found.")
            refresh_visible()

        render()
        threading.Thread(target=worker, daemon=True, name="pocket-extra-" + kind).start()
        app.root.after(120, poll)

    def start_search(_event=None):
        if state["busy"]:
            return
        term = search_var.get().strip()
        state["query"] = search_var.get()
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
            work("local", lambda cancel, report, scan: lookup.search_workbook(
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
        work("database", lambda cancel, report, scan: db.search_database(
            term, cancelled=cancel.is_set))

    search_button = design.button(search_line, "Search", start_search,
                                  app.theme, primary=True, compact=True)
    search_button.pack(side="right")
    entry.bind("<Return>", start_search)

    def palette_search(term):
        if state["busy"]:
            return
        search_var.set(term)
        # Database is local; a live workbook may be on a network share.
        # For Local mode leave the query ready for an explicit Search click.
        if mode_var.get() == "database":
            start_search()
        else:
            entry.focus_set()

    app._extra_palette_search = palette_search

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
        work("sync", lambda cancel, report, scan: db.sync_database(
            source_path, cancelled=cancel.is_set, on_progress=report, on_scan=scan))

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
        work("import", lambda cancel, report, scan: db.import_database(
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
    same_mode = state["mode"] in (None, mode_var.get())
    apply_mode(restoring=same_mode)
    app._extra_snapshot = snapshot
    app._extra_render = render
    render(restore=True)

    if compact:
        # Only the externally allocated viewport determines list height.
        # Never observe parent/detail Configure events: requested heights
        # depend on the list itself and can create a geometry feedback loop.
        canvas = getattr(app, "_tool_scroll_canvas", None)
        if canvas is not None:
            from tkinter import font as tkfont
            row_pixels = tkfont.Font(root=app.root, font=result_list.cget("font")).metrics("linespace") + 2
            pending = None
            last_height = None

            def resize_matches():
                nonlocal pending, last_height
                pending = None
                if not result_list.winfo_exists() or not canvas.winfo_exists():
                    return
                height = canvas.winfo_height()
                if height <= 1 or height == last_height:
                    return
                last_height = height
                # Spend at most half of additional viewport height on matches.
                # The rest remains available for selected-row output.
                rows = max(5, min(14, 5 + max(0, height - 440) // (2 * row_pixels)))
                if int(result_list.cget("height")) != rows:
                    result_list.configure(height=rows)

            def schedule_matches(_event=None):
                nonlocal pending
                if pending is not None:
                    result_list.after_cancel(pending)
                pending = result_list.after(80, resize_matches)

            def cancel_resize(_event=None):
                nonlocal pending
                if pending is not None:
                    result_list.after_cancel(pending)
                    pending = None

            canvas.bind("<Configure>", schedule_matches, add="+")
            result_list.bind("<Destroy>", cancel_resize, add="+")
            schedule_matches()

    entry.focus_set()
