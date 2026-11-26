"""Keyboard-first, themed local command palette."""
import tkinter as tk
from tkinter import ttk
from . import command_palette as palette
from . import icon_themes, tool_icons, text_editing, native_inputs, palette_preferences as prefs

def open_palette(app):
    old = getattr(app, "_quick_search_dialog", None)
    if old is not None and old.winfo_exists():
        old.attributes("-topmost", True)
        old.lift()
        native_inputs.focus_tk_input(app._palette_entry)
        return "break"
    c = icon_themes.palette(app.theme)
    dialog = tk.Toplevel(app.root)
    app._quick_search_dialog = dialog
    was_modal = app._modal
    app._modal = True
    dialog.withdraw()
    dialog.title("Pocket Search")
    dialog.overrideredirect(not native_inputs.IS_WINDOWS)
    if native_inputs.IS_WINDOWS:
        # A managed tool window is activatable by Windows; the previous
        # override-redirect popup could retain the owner EDIT keyboard HWND.
        dialog.attributes("-toolwindow", True)
    dialog.transient(app.root)
    # Pocket itself is topmost in normal tray operation. A transient
    # override-redirect child must also be topmost to appear above its owner.
    dialog.attributes("-topmost", True)
    dialog.configure(bg=c["BORDER"])
    dialog.resizable(False, False)
    saved = prefs.normalize(app.settings)
    position = saved["palette_position"]
    anchor = (position["x"], position["y"]) if position else (
        app.root.winfo_rootx(), app.root.winfo_rooty())
    area = app._screen_work_area(*anchor)
    width, height = prefs.dimensions(area, 6)
    x, y = anchor if position else (anchor[0] + (app.root.winfo_width()-width)//2, anchor[1]+40)
    x, y = prefs.clamp(x, y, width, height, area)
    dialog.geometry(f"{width}x{height}{x:+d}{y:+d}")
    prefs.apply_opacity(dialog, saved["palette_opacity"])
    initial_xy = (x, y)
    moving = [None]
    ready = [False]
    pending_save = [None]

    def store_position():
        pending_save[0] = None
        if not ready[0] or not dialog.winfo_exists() or not app.settings.get("palette_remember_position", True):
            return
        px, py = prefs.window_xy(dialog)
        value = {"x": px, "y": py}
        if app.settings.get("palette_position") != value:
            app.settings["palette_position"] = value
            save = getattr(app, "schedule_save", None)
            if callable(save):
                save()

    def position_changed(event):
        if event.widget is dialog and ready[0]:
            if pending_save[0] is not None:
                dialog.after_cancel(pending_save[0])
            pending_save[0] = dialog.after(200, store_position)

    def drag_begin(event):
        px, py = prefs.window_xy(dialog)
        moving[0] = (event.x_root - px, event.y_root - py)

    def drag_move(event):
        if moving[0] is not None:
            prefs.move(dialog, event.x_root-moving[0][0], event.y_root-moving[0][1])

    def drag_end(event):
        moving[0] = None
        px, py = prefs.window_xy(dialog)
        work = app._screen_work_area(event.x_root, event.y_root)
        px, py = prefs.clamp(px, py, dialog.winfo_width(), dialog.winfo_height(), work)
        prefs.move(dialog, px, py)
        store_position()

    dialog.bind("<Configure>", position_changed, add="+")
    frame = tk.Frame(dialog, bg=c["BG"])
    frame.pack(fill="both", expand=True, padx=1, pady=1)
    tk.Frame(frame, bg=c["ACCENT"], height=2).pack(fill="x")
    # The only header is a tiny drag rail, not a title/toolbar.
    grip = tk.Canvas(frame, height=12, bg=c["BG"], bd=0,
                     highlightthickness=0, cursor="fleur")
    grip.pack(fill="x", padx=1)
    def draw_grip(event):
        grip.delete("all")
        mid = event.width // 2
        grip.create_line(mid-14, 6, mid+14, 6, fill=c["MUTED"],
                         width=2, capstyle="round")
    grip.bind("<Configure>", draw_grip)
    grip.bind("<ButtonPress-1>", drag_begin)
    grip.bind("<B1-Motion>", drag_move)
    grip.bind("<ButtonRelease-1>", drag_end)
    query = tk.StringVar(master=dialog)
    # Use a real Win32 search EDIT, with navigation marshalled to Tk.
    # Non-Windows keeps the ordinary Tk Entry.
    search = tk.Frame(frame, bg=c["INPUT"], highlightthickness=1,
                      highlightbackground=c["BORDER"])
    search.pack(fill="x", padx=14)
    glass = tool_icons.label(search, "search", c["ACCENT"], c["INPUT"], size=26)
    glass.pack(side="left", padx=(10, 5))
    entry = native_inputs.Entry(search, textvariable=query, exportselection=False, bg=c["INPUT"], fg=c["WHITE"],
                     insertbackground=c["WHITE"], selectbackground=c["ACCENT_DARK"],
                     relief="flat", bd=0, highlightthickness=0,
                     font=("Segoe UI", 15))
    app._palette_entry = entry
    app.root._pocket_palette_target = entry
    entry.pack(side="left", fill="x", expand=True, padx=(2, 8), ipady=10)
    entry.bind("<FocusIn>", lambda _e: search.configure(highlightbackground=c["ACCENT"]))
    entry.bind("<FocusOut>", lambda _e: search.configure(highlightbackground=c["BORDER"]))
    glass.bind("<Button-1>", lambda _e: native_inputs.focus_tk_input(entry))
    # Widget-level handlers run before Tk class / toplevel shortcuts.
    undo_stack, redo_stack = [], []
    previous = [query.get()]
    replaying = [False]

    def remember(*_):
        value = query.get()
        if value != previous[0]:
            if not replaying[0]:
                undo_stack.append(previous[0])
                del undo_stack[:-100]
                redo_stack.clear()
            previous[0] = value

    query.trace_add("write", remember)

    def edit(operation):
        if getattr(entry, "native_hwnd", None):
            entry.sync_native()
        if operation in ("undo", "redo"):
            source, target = ((undo_stack, redo_stack) if operation == "undo"
                              else (redo_stack, undo_stack))
            if source:
                target.append(query.get())
                replaying[0] = True
                try:
                    query.set(source.pop())
                    entry.icursor("end")
                finally:
                    replaying[0] = False
            return "break"
        return text_editing.perform(entry, operation)

    def edit_key(event):
        operation = text_editing._shortcut_operation(event)
        if operation:
            return edit(operation)

    entry.bind("<Control-KeyPress>", edit_key)
    for key in "acvxyz":
        entry.bind(f"<Control-KeyPress-{key}>", edit_key)
    entry.bind("<Control-Shift-KeyPress-Z>", edit_key)

    def delete_word(_event=None):
        if getattr(entry, "native_hwnd", None):
            entry.sync_native()
            if entry.selection_present():
                entry.native_action("delete")
            else:
                import ctypes, re
                start, end = ctypes.c_uint32(), ctypes.c_uint32()
                entry._send(native_inputs.EM_GETSEL, ctypes.addressof(start), ctypes.addressof(end))
                prefix = entry.get().encode("utf-16-le")[:start.value * 2].decode("utf-16-le", errors="ignore")
                match = re.search(r"\S+\s*$|\s+$", prefix)
                if match:
                    offset = len(prefix[:match.start()].encode("utf-16-le")) // 2
                    entry._send(native_inputs.EM_SETSEL, offset, start.value)
                    entry.native_action("delete")
            return "break"
        if entry.selection_present():
            entry.delete("sel.first", "sel.last")
        else:
            import re
            index = entry.index("insert")
            match = re.search(r"\S+\s*$|\s+$", entry.get()[:index])
            if match:
                entry.delete(match.start(), index)
        return "break"

    entry.bind("<Control-BackSpace>", delete_word)

    def context_menu(event):
        menu = tk.Menu(dialog, tearoff=False, bg=c["PANEL"], fg=c["WHITE"])
        for caption, operation in (("Copy", "copy"), ("Paste", "paste"), ("Cut", "cut"),
                                   ("Select All", "select_all"), ("Undo", "undo"), ("Redo", "redo")):
            menu.add_command(label=caption, command=lambda op=operation: edit(op))
        menu.bind("<Unmap>", lambda _e: menu.after_idle(menu.destroy))
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()
        return "break"

    entry.bind("<Button-3>", context_menu)
    status = tk.Label(frame, bg=c["BG"], fg=c["MUTED"], anchor="w",
                      font=("Segoe UI", 8, "bold"))
    status.pack(fill="x", padx=15, pady=(10, 5))
    footer = tk.Frame(frame, bg=c["BG"])
    footer.pack(side="bottom", fill="x", padx=12, pady=7)
    tk.Label(footer, text="↑ ↓ Navigate  ·  Enter Open  ·  Tab Complete  ·  Esc Close", bg=c["BG"],
             fg=c["MUTED"], font=("Segoe UI", 8)).pack(side="left")
    list_frame = tk.Frame(frame, bg=c["BG"])
    list_frame.pack(fill="both", expand=True, padx=14)
    results = tk.Canvas(list_frame, name="palette_results", bg=c["BG"], highlightthickness=0, bd=0,
                        takefocus=True, yscrollincrement=48)
    scroll = ttk.Scrollbar(list_frame, command=results.yview,
                           style="Pocket.Vertical.TScrollbar")
    results.configure(yscrollcommand=scroll.set)
    results.pack(side="left", fill="both", expand=True)
    matches = []
    selected = [0]
    images = {}
    row_height = 48

    def photo(name, size):
        key = (name, size)
        if key not in images:
            images[key] = tool_icons.icon_image(dialog, name, c["ACCENT"], size=size)
        return images[key]

    def shorten(value, limit):
        value = " ".join(str(value).split())
        return value if len(value) <= limit else value[:max(1, limit-1)] + "…"

    def draw(_event=None):
        if not results.winfo_exists():
            return
        results.delete("all")
        w = max(100, results.winfo_width())
        if not matches:
            results.create_text(12, 23, text="No matching tools or actions",
                                fill=c["MUTED"], anchor="w", font=("Segoe UI", 10))
        for index, hit in enumerate(matches):
            top_y = index * row_height
            active = index == selected[0]
            surface = c["ACCENT_DARK"] if active else c["PANEL"]
            results.create_rectangle(1, top_y+1, w-2, top_y+45,
                                     fill=surface, outline="")
            results.create_image(24, top_y+23, image=photo(palette.result_icon(hit), 23))
            # Keep titles and descriptions distinct; fit narrow screens too.
            chars = max(10, (w-75)//7)
            results.create_text(46, top_y+14, anchor="w", fill=c["WHITE"],
                                text=shorten(hit["title"], chars),
                                font=("Segoe UI", 10, "bold"))
            results.create_text(46, top_y+32, anchor="w", fill=c["SECONDARY"],
                                text=shorten(hit["subtitle"], chars+8),
                                font=("Segoe UI", 8))
            if active:
                results.create_text(w-16, top_y+22, text="↵", fill=c["ACCENT"],
                                    font=("Segoe UI", 12))
        results.configure(scrollregion=(0, 0, w, max(row_height, len(matches)*row_height)))

    def update_preview():
        hit = matches[selected[0]] if matches and selected[0] < len(matches) else None
        name = palette.search_icon(query.get(), hit)
        glass.configure(image=photo(name, 26))
        glass.image = photo(name, 26)
        draw()

    def reveal_selection():
        y = selected[0] * row_height
        total = max(row_height, len(matches)*row_height)
        first = results.canvasy(0)
        visible = results.winfo_height()
        if y < first:
            results.yview_moveto(y/total)
        elif y+row_height > first+visible:
            results.yview_moveto(max(0, y+row_height-visible)/total)

    def select_at(event):
        index = int(results.canvasy(event.y)//row_height)
        if 0 <= index < len(matches):
            selected[0] = index
            update_preview()
            native_inputs.focus_tk_input(entry)
        return "break"

    def wheel(event):
        step = -1 if getattr(event, "num", None) == 4 or getattr(event, "delta", 0) > 0 else 1
        results.yview_scroll(step, "units")
        return "break"

    results.bind("<Configure>", draw)
    results.bind("<Button-1>", select_at)
    for sequence in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
        results.bind(sequence, wheel)

    def resize_for_results():
        px, py = prefs.window_xy(dialog) if ready[0] else initial_xy
        work = app._screen_work_area(px, py)
        w, h = prefs.dimensions(work, len(matches))
        # Footer and header stay fixed; only six results fit before scrolling.
        dialog.geometry(f"{w}x{h}")
        if ready[0]:
            px, py = prefs.clamp(px, py, w, h, work)
            prefs.move(dialog, px, py)
        if len(matches) > 6:
            if not scroll.winfo_manager():
                scroll.pack(side="right", fill="y", before=results)
        else:
            scroll.pack_forget()

    def refresh(*_args):
        matches[:] = palette.results(app.data, app.command_library, query.get(),
                                     app.settings["visible_tabs"], app.settings)
        selected[0] = 0
        results.yview_moveto(0)
        status.configure(text=("ACTION MODE" if query.get().lstrip().startswith((">", "<")) else
                               "QUICK ACTIONS" if not query.get().strip() else "SEARCH RESULTS")
                              + f"  ·  {len(matches)}")
        resize_for_results()
        update_preview()

    def restore_owner_focus():
        """Return keyboard ownership to Pocket, not the previously active app."""
        if not app.root.winfo_exists() or app.root.state() != "normal":
            return
        app.root.lift()
        app.root.focus_force()

    def close(_event=None, *, launching=False):
        if app._quick_search_dialog is not dialog:
            return "break"
        # Keep auto-hide suppressed during the native focus handoff. Destroying
        # an active topmost popup alone can leave the owner visible but unfocused.
        if pending_save[0] is not None:
            dialog.after_cancel(pending_save[0])
        store_position()
        app.root._pocket_palette_target = None
        if dialog.winfo_exists():
            dialog.destroy()
        app._quick_search_dialog = None
        app._palette_entry = None
        try:
            restore_owner_focus()
        finally:
            app._modal = was_modal
        if not launching:
            def settle_owner():
                # Never steal focus from a newly opened palette or another
                # Pocket modal. Retry after Windows finishes destroying the popup.
                if (app._quick_search_dialog is None and not app._modal
                        and app.root.winfo_exists() and app.root.state() == "normal"
                        and app.root.focus_displayof() is None):
                    restore_owner_focus()
            app.root.after_idle(settle_owner)
        return "break"

    def launch(_event=None):
        if getattr(entry, "native_hwnd", None):
            entry.sync_native()
        if matches and selected[0] < len(matches):
            hit = matches[selected[0]]
            if hit["kind"] == "completion":
                query.set(hit["id"])
                entry.icursor("end")
                entry.focus_set()
                return "break"
            close(launching=True)
            app._run_palette_action(hit)
        return "break"

    def move(step):
        if matches:
            selected[0] = (selected[0] + step) % len(matches)
            update_preview()
            reveal_selection()
        return "break"

    query.trace_add("write", refresh)
    for widget in (entry, results, dialog):
        widget.bind("<Escape>", close)
        widget.bind("<Return>", launch)
    def complete(_event=None):
        choices = palette.completions(query.get(), app.settings["visible_tabs"])
        if choices:
            hit = matches[selected[0]] if matches else {}
            value = hit["id"] if hit.get("kind") == "completion" else choices[0]
            query.set(value)
            entry.icursor("end")
        return "break" if query.get().lstrip().startswith((">", "<")) else None

    entry.bind("<Tab>", complete)
    entry.bind("<Down>", lambda _e: move(1))
    entry.bind("<Up>", lambda _e: move(-1))
    def double_click(event):
        select_at(event)
        return launch()
    results.bind("<Double-1>", double_click)
    dialog.protocol("WM_DELETE_WINDOW", close)
    if getattr(entry, "native_hwnd", None):
        entry.set_palette_keys({
            "enter": launch, "escape": close, "tab": complete,
            "up": lambda: move(-1), "down": lambda: move(1),
            "focus": lambda: native_inputs.focus_tk_input(entry),
            "undo": lambda: edit("undo"), "redo": lambda: edit("redo"),
            "delete_word": delete_word,
        })
    refresh()
    dialog.deiconify()
    dialog.update_idletasks()
    prefs.remove_window_chrome(dialog)
    prefs.move(dialog, *initial_xy)
    ready[0] = True
    dialog.lift()
    # Flush the source edit before moving actual Windows keyboard ownership.
    native_inputs.sync_all_native()
    native_inputs.focus_tk_input(entry)

    def raise_after_map():
        if app._quick_search_dialog is dialog and dialog.winfo_exists():
            dialog.attributes("-topmost", True)
            prefs.remove_window_chrome(dialog)
            dialog.lift()
            native_inputs.focus_tk_input(entry)

    def verify_focus():
        if app._quick_search_dialog is not dialog or not dialog.winfo_exists():
            return
        focused = app.root.focus_get()
        # Do not steal focus from results or an external application. Retry
        # only if another Pocket input still owns focus after the handoff.
        bidi = getattr(app, "bidi_editor", None)
        if (not getattr(entry, "has_native_focus", lambda: False)() and (
                native_inputs.has_native_focus()
                or (bidi is not None and bidi.winfo_exists() and bidi.has_focus())
                or (focused is not None and focused.winfo_toplevel() == app.root))):
            native_inputs.focus_tk_input(entry)

    dialog.after_idle(raise_after_map)
    dialog.after(60, verify_focus)
    return "break"
