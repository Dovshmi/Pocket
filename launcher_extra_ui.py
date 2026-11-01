"""Pocket Extra Mini multi-page renderer and quick-action interactions.

Keeps all complicated picker/drag logic outside the 322x256 launcher shell.
The existing window, search, theme, tray, Edit and All tools controls remain.
"""
from __future__ import annotations

import tkinter as tk

import launcher_pages as lp
import launcher_picker as picker
import pocket_design as design


def install_cards(app, cards, c):
    app.data["extra_mini_page"] = lp.page_index(app.data.get("extra_mini_page"), app._compact_pages())
    app._compact_drag = None

    def page():
        return lp.page_index(app.data.get("extra_mini_page"))

    def update_pages(state):
        app._save_compact_pages(state)

    def add(index):
        current = app._compact_pages()[page()]["tiles"][index]
        origin = page()
        picker.choose_item(app,
              lambda item: update_pages(lp.put(app._compact_pages(), origin, index, item)),
              selected=current)

    def remove(index):
        update_pages(lp.remove(app._compact_pages(), page(), index))

    def rename(index):
        tile = app._compact_pages()[page()]["tiles"][index]
        if not tile:
            return
        info = lp.lookup(tile, app.data, app.command_library, app.settings["visible_tabs"])
        origin = page()
        picker.rename_dialog(app, info["title"], "Rename quick action",
                 lambda title: update_pages(lp.rename(app._compact_pages(), origin, index, title)))

    def rename_page():
        origin = page()
        picker.rename_dialog(app, app._compact_pages()[origin]["name"],
                 "Rename page",
                 lambda name: update_pages(lp.rename_page(app._compact_pages(), origin, name)))

    def swap(origin_page, origin_index, dest_page, dest_index):
        update_pages(lp.move(app._compact_pages(), origin_page, origin_index,
                             dest_page, dest_index))

    def move_picker(index):
        origin = page()
        window = tk.Toplevel(app.root)
        window.title("Move quick action")
        window.configure(bg=c["BG"])
        window.geometry("330x300")
        window.transient(app.root)
        previous = app._modal
        app._modal = True
        def close():
            window.destroy()
            app._modal = previous
        window.protocol("WM_DELETE_WINDOW", close)
        tk.Label(window, text="Move or swap with a slot", bg=c["BG"], fg=c["WHITE"],
                 font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=12, pady=(13, 7))
        for target_page, record in enumerate(app._compact_pages() + ([{"name": "New page", "tiles": [None] * lp.SLOT_COUNT}] if len(app._compact_pages()) < lp.MAX_PAGES else [])):
            row = tk.Frame(window, bg=c["BG"])
            row.pack(fill="x", padx=10, pady=2)
            tk.Label(row, text=record["name"][:13], bg=c["BG"], fg=c["SECONDARY"],
                     width=13, anchor="w", font=("Segoe UI", 9)).pack(side="left")
            for target_index in range(lp.SLOT_COUNT):
                disabled = origin == target_page and target_index == index
                def move_to(p=target_page, s=target_index):
                    swap(origin, index, p, s)
                    close()
                button = design.button(row, str(target_index + 1), move_to, app.theme,
                                       compact=True)
                button.configure(state="disabled" if disabled else "normal")
                button.pack(side="left", padx=2)
        design.button(window, "Cancel", close, app.theme, compact=True).pack(
              side="right", padx=14, pady=12)
        window.grab_set()

    def add_next():
        slot = lp.next_free_slot(app._compact_pages())
        if slot is None:
            return
        def apply(item):
            pages, selected_page = lp.append_action(app._compact_pages(), item)
            app.data["extra_mini_page"] = selected_page
            update_pages(pages)
        picker.choose_item(app, apply)

    def menu_for(index, event):
        tile = app._compact_pages()[page()]["tiles"][index]
        menu = tk.Menu(app.root, tearoff=False, bg=c["PANEL"], fg=c["WHITE"],
                       activebackground=c["ACCENT_DARK"], activeforeground=c["WHITE"])
        if tile is None:
            menu.add_command(label="Add to tile", command=lambda: add(index))
        else:
            ready = lp.lookup(tile, app.data, app.command_library, app.settings["visible_tabs"])["status"] == "ready"
            menu.add_command(label="Open", state="normal" if ready else "disabled",
                             command=lambda: app._launch_compact_item(tile))
            menu.add_command(label="Replace", command=lambda: add(index))
            menu.add_command(label="Rename tile", command=lambda: rename(index))
            menu.add_command(label="Move to another slot", command=lambda: move_picker(index))
            menu.add_separator()
            menu.add_command(label="Remove tile", command=lambda: remove(index))
        # Tk's menu owns the pointer grab. Do not alter app._modal here:
        # menu callbacks may open the searchable Toplevel picker, and resetting
        # the flag afterwards would incorrectly unmark a live modal dialog.
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def drag(phase, index, event):
        if not app._compact_editing:
            return
        if phase == "start":
            app._compact_drag = (page(), index)
            return
        from_slot = app._compact_drag
        app._compact_drag = None
        if from_slot is None:
            return
        target = app.root.winfo_containing(event.x_root, event.y_root)
        while target is not None and not hasattr(target, "_pocket_slot"):
            target = getattr(target, "master", None)
        if target is not None:
            dest = (getattr(target, "_pocket_page", page()), target._pocket_slot)
            if dest != from_slot:
                swap(*from_slot, *dest)

    def draw_tile(index, data):
        item = lp.lookup(data, app.data, app.command_library, app.settings["visible_tabs"])
        state = item["status"]
        selected_page = page()
        editing = bool(app._compact_editing)
        frame = tk.Frame(cards, width=68, height=100, bg=c["PANEL"],
                         highlightbackground=c["BORDER"], highlightthickness=1,
                         takefocus=1)
        frame._pocket_slot = index
        frame._pocket_page = selected_page
        frame.grid(row=0, column=index, padx=(0, 5) if index < 3 else 0,
                   sticky="nsew")
        frame.grid_propagate(False)
        if state == "empty":
            button = tk.Button(frame, text="+", command=lambda: add(index),
                               bg=c["CARD"], fg=c["ACCENT"], font=("Segoe UI", 20),
                               relief="flat", bd=0, cursor="hand2")
            button.pack(fill="x", padx=7, pady=(12, 5))
            tk.Label(frame, text="Add", bg=c["PANEL"], fg=c["MUTED"],
                     font=("Segoe UI", 8)).pack()
            frame.bind("<Return>", lambda _e: add(index))
            frame.bind("<space>", lambda _e: add(index))
            frame.bind("<Button-3>", lambda e: menu_for(index, e))
            design.Tooltip(button, "Add a saved tool, note, command, template or shortcut", app.theme)
            return
        title = item["title"][:13]
        icon = tk.Label(frame, text=item["icon"], bg=c["CARD"],
                        fg=c["ACCENT"] if state == "ready" else c["MUTED"],
                        font=("Segoe UI", 14, "bold"), padx=6, pady=2)
        icon.pack(pady=(13 if editing else 7, 3))
        label = tk.Label(frame, text=title, bg=c["PANEL"],
                         fg=c["WHITE"] if state == "ready" else c["MUTED"],
                         font=("Segoe UI", 8, "bold"), wraplength=65, justify="center")
        label.pack()
        detail = tk.Label(frame, text=item["detail"][:17], bg=c["PANEL"],
                          fg=c["MUTED"], font=("Segoe UI", 7),
                          wraplength=65, justify="center")
        detail.pack(pady=3)
        design.Tooltip(frame, item["title"] + " · " + item["detail"], app.theme)
        if editing:
            remove_button = tk.Button(frame, text="×", command=lambda: remove(index),
                                      bg=c["ACCENT_DARK"], fg=c["DANGER"],
                                      activebackground=c["CARD_HOVER"],
                                      font=("Segoe UI", 10, "bold"), relief="flat",
                                      bd=0, cursor="hand2")
            remove_button.place(relx=1, x=-1, y=1, anchor="ne", width=20, height=20)
            targets = (frame, icon, label, detail)
            for target in targets:
                target.bind("<ButtonPress-1>", lambda e, i=index: drag("start", i, e))
                target.bind("<ButtonRelease-1>", lambda e, i=index: drag("end", i, e))
        else:
            def open_tile(_event=None):
                if state == "ready":
                    app._launch_compact_item(data)
            targets = (frame, icon, label, detail)
            for target in targets:
                target.configure(cursor="hand2" if state == "ready" else "arrow")
                target.bind("<Button-1>", open_tile)
            frame.bind("<Return>", open_tile)
            frame.bind("<space>", open_tile)
        for target in targets:
            target.bind("<Button-3>", lambda e, i=index: menu_for(i, e))

    def render():
        for child in cards.winfo_children():
            child.destroy()
        for col in range(lp.SLOT_COUNT):
            cards.columnconfigure(col, weight=1, uniform="quick-tile")
        state = app._compact_pages()
        selected_page = lp.page_index(page(), state)
        for index, item in enumerate(state[selected_page]["tiles"]):
            draw_tile(index, item)
        status = getattr(app, "compact_status", None)
        if status is not None and status.winfo_exists():
            status.configure(text=state[selected_page]["name"][:12] +
                             f" · {selected_page+1}/{len(state)}")
        update_pager = getattr(app, "compact_update_pager", None)
        if update_pager is not None:
            update_pager()

    def page_step(step):
        new = max(0, min(len(app._compact_pages()) - 1, page() + step))
        if new != page():
            app._set_compact_page(new)

    # Global release listener lets users drag between pages by holding a tile,
    # scrolling the wheel to switch page, then releasing over a destination.
    # Bound only once; each event resolves the current live tile widgets.
    if not getattr(app, "_compact_release_bound", False):
        def finish_drag(event):
            origin = getattr(app, "_compact_drag", None)
            if app.display_mode != "compact" or not app._compact_editing or origin is None:
                return
            app._compact_drag = None
            widget = app.root.winfo_containing(event.x_root, event.y_root)
            while widget is not None and not hasattr(widget, "_pocket_slot"):
                widget = getattr(widget, "master", None)
            if widget is not None:
                destination = (widget._pocket_page, widget._pocket_slot)
                if destination != origin:
                    app._save_compact_pages(lp.move(app._compact_pages(), *origin,
                                                    *destination))
        app.root.bind("<ButtonRelease-1>", finish_drag, add="+")
        app._compact_release_bound = True

    app.compact_render_cards = render
    app.compact_choose_item = add
    app.compact_rename_page = rename_page
    app.compact_switch_page = page_step
    app.compact_move_slot = move_picker
    app.compact_add_next = add_next
    render()


def install_pager(app, footer, c):
    """Only display dots for pages containing saved actions."""
    nav = tk.Frame(footer, bg=c["BG"])
    nav.pack(side="left", fill="y", padx=(0, 3))
    prev = tk.Button(nav, text="<", command=lambda: app.compact_switch_page(-1),
                     bg=c["BG"], fg=c["ACCENT"], relief="flat", bd=0,
                     font=("Segoe UI", 10, "bold"), cursor="hand2")
    prev.pack(side="left", padx=1)
    dots = tk.Frame(nav, bg=c["BG"])
    dots.pack(side="left")
    following = tk.Button(nav, text=">", command=lambda: app.compact_switch_page(1),
                          bg=c["BG"], fg=c["ACCENT"], relief="flat", bd=0,
                          font=("Segoe UI", 10, "bold"), cursor="hand2")
    following.pack(side="left", padx=1)
    app.compact_page_buttons = []

    def update():
        pages = app._compact_pages()
        selected = lp.page_index(app.data.get("extra_mini_page"), pages)
        controls = app.compact_page_buttons
        if len(controls) != len(pages):
            for child in dots.winfo_children():
                child.destroy()
            controls.clear()
            for index in range(len(pages)):
                control = tk.Button(
                    dots, text="●", command=lambda p=index: app._set_compact_page(p),
                    bg=c["BG"], fg=c["MUTED"], font=("Segoe UI", 7),
                    relief="flat", bd=0, padx=2, cursor="hand2")
                control.pack(side="left")
                controls.append(control)
                design.Tooltip(control, f"Page {index + 1}", app.theme)
        for index, control in enumerate(controls):
            control.configure(fg=c["ACCENT"] if index == selected else c["MUTED"])
        prev.configure(state="normal" if selected > 0 else "disabled")
        following.configure(state="normal" if selected + 1 < len(pages) else "disabled")

    app.compact_update_pager = update
    update()


def handle_wheel(app, event):
    """Handle only Extra Mini tile-area wheel events, not active search fields."""
    if app.display_mode != "compact" or app._modal:
        return None
    if not getattr(app, "compact_placeholder_active", True):
        if getattr(app, "compact_matches", []):
            return None
    # Suppress wheel over the search field, where users may move the caret.
    widget = event.widget
    if widget is getattr(app, "compact_search_entry", None):
        return None
    direction = -1 if (event.delta > 0 if getattr(event, "delta", 0)
                       else getattr(event, "num", 5) == 4) else 1
    app.compact_switch_page(direction)
    return "break"
