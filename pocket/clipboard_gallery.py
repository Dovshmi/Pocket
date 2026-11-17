"""Responsive Text / Images pages for Pocket's existing Clipboard tool.

The Text page keeps the original searchable Listbox. The Images page uses a
width-aware thumbnail gallery. Optional Database mode persists daily local
history; RAM mode remains fully ephemeral.
"""
from __future__ import annotations

import tkinter as tk
from . import menu_style
from tkinter import messagebox, ttk

from PIL import Image, ImageTk

from . import clipboard_images
from . import clipboard_routing
from . import icon_themes as themes
from . import pocket_design as design


def columns_for_width(width):
    """One large column in Mini, more columns as the workspace gets wider."""
    return max(1, min(5, int(width) // 205))


def pinned_first(items):
    """Stable display order: pinned clipboard text first, otherwise newest first.

    Preserve the session history order within each group. This is a view-only
    sort: the underlying RAM history and pin flags are not mutated or saved.
    """
    return sorted(items, key=lambda item: not item.get("pinned", False))


def text_row_label(item):
    """Display clipboard text without the legacy three-space left indent.

    Pinned entries keep their visible star; ordinary entries begin at the
    native Listbox text inset, matching other Pocket input panels.
    """
    preview = " ".join(item["text"].split())[:65]
    return ("★ " if item["pinned"] else "") + preview


def _action(parent, title, callback, colors):
    return tk.Button(
        parent, text=title, command=callback, relief="flat", bd=0,
        bg=colors["PANEL"], fg=colors["ACCENT"],
        activebackground=colors["CARD_HOVER"],
        activeforeground=colors["WHITE"], cursor="hand2",
        padx=7, pady=7, font=("Segoe UI", 8, "bold"),
        highlightthickness=1, highlightbackground=colors["BORDER"],
        takefocus=True)


def build(app):
    c = themes.palette(app.theme)
    stored = app.settings.get("clipboard_storage") == "database"
    header = app._section_title(
        app.body, "Clipboard history",
        "LOCAL DATABASE · Saved on this PC" if stored else "RAM only · Never saved to disk",
        "Clear text", app._clear_clipboard)
    app.clipboard_clear_button = next(
        (child for child in header.winfo_children() if isinstance(child, tk.Button)),
        None)
    # Place both native dropdowns on ONE compact row, including in Mini mode.
    # The date picker is intentionally hidden while RAM-only mode is selected.
    controls = tk.Frame(app.body, bg=c["BG"])
    controls.pack(fill="x", pady=(2, 5))
    left = tk.Frame(controls, bg=c["BG"])
    left.pack(side="left", padx=(0, 6))
    tk.Label(left, text="Storage", bg=c["BG"], fg=c["SECONDARY"],
             font=("Segoe UI", 8)).pack(side="left", padx=(0, 4))
    app.clipboard_storage_select = ttk.Combobox(
        left, style="Pocket.TCombobox", state="readonly",
        values=("RAM", "DATABASE"), width=9, takefocus=True)
    app.clipboard_storage_select.set("DATABASE" if stored else "RAM")
    app.clipboard_storage_select.pack(side="left")

    def select_storage(_event=None):
        chosen = app.clipboard_storage_select.get().strip().lower()
        app._clipboard_use_storage(chosen)
        return "break"

    app.clipboard_storage_select.bind("<<ComboboxSelected>>", select_storage)

    app.clipboard_history_row = tk.Frame(controls, bg=c["BG"])
    tk.Label(app.clipboard_history_row, text="Date", bg=c["BG"],
             fg=c["SECONDARY"], font=("Segoe UI", 8)).pack(
                 side="left", padx=(0, 4))
    app.clipboard_day_select = ttk.Combobox(
        app.clipboard_history_row, style="Pocket.TCombobox",
        state="readonly", width=11 if app.display_mode == "mini" else 18,
        takefocus=True)
    app.clipboard_day_select.pack(side="left")

    def selected_day(_event=None):
        picked = app.clipboard_day_select.get()
        app._clipboard_choose_day(picked[-10:])
        return "break"

    app.clipboard_day_select.bind("<<ComboboxSelected>>", selected_day)
    if stored:
        app.clipboard_history_row.pack(side="left", padx=(2, 0))
    privacy = tk.Frame(app.body, bg=c["BG"])
    privacy.pack(fill="x", pady=(0, 6))
    app.clipboard_pause_button = design.button(
        privacy, "Resume capture" if app.settings["clipboard_paused"]
        else "Pause capture", app._toggle_clipboard_pause,
        app.theme, compact=True)
    app.clipboard_pause_button.pack(side="left")
    tk.Label(
        privacy, text="Sensitive-text filter: " +
        ("On" if app.settings["clipboard_sensitive_filter"] else "Off"),
        bg=c["BG"], fg=c["MUTED"], font=("Segoe UI", 8)
    ).pack(side="right")

    # Same compact labelled switch used by Local / DashDash. No full-width tabs.
    switch = tk.Frame(app.body, bg=c["BG"])
    switch.pack(side="top", anchor="e", pady=(0, 4))
    app.clipboard_page_buttons = {}
    left = tk.Button(
        switch, text="Text", cursor="hand2", bd=0, relief="flat",
        font=("Segoe UI", 8, "bold"), takefocus=True,
        bg=c["BG"], padx=2, pady=1,
        command=lambda: show_page(app, "text"))
    left.pack(side="left", padx=(0, 5))
    app.clipboard_page_buttons["text"] = left
    toggle = tk.Canvas(
        switch, width=44, height=22, bg=c["BG"], bd=0,
        highlightthickness=1, highlightbackground=c["BG"],
        highlightcolor=c["ACCENT"], takefocus=True, cursor="hand2")
    toggle.pack(side="left")
    app.clipboard_page_toggle = toggle
    right = tk.Button(
        switch, text="Images", cursor="hand2", bd=0, relief="flat",
        font=("Segoe UI", 8, "bold"), takefocus=True,
        bg=c["BG"], padx=2, pady=1,
        command=lambda: show_page(app, "images"))
    right.pack(side="left", padx=(5, 0))
    app.clipboard_page_buttons["images"] = right

    def flip_page(_event=None):
        show_page(app, "text" if app.clipboard_page == "images" else "images")
        toggle.focus_set()
        return "break"

    toggle.bind("<Button-1>", flip_page)
    toggle.bind("<space>", flip_page)
    toggle.bind("<Return>", flip_page)

    app.clipboard_text_page = tk.Frame(app.body, bg=c["BG"])
    app.clipboard_images_page = tk.Frame(app.body, bg=c["BG"])
    _build_text_page(app, c)
    _build_images_page(app, c)
    # Date paging is optional and keeps old records accessible without loading
    # all of them into memory. Keep the controls narrow in Mini.
    nav = tk.Frame(app.body, bg=c["BG"])
    app.clipboard_page_navigation = nav
    app.clipboard_prev_button = tk.Button(
        nav, text="‹ Prev", command=lambda: app._clipboard_turn_page(-1),
        bg=c["CARD"], fg=c["SECONDARY"], relief="flat", bd=0,
        font=("Segoe UI", 8), cursor="hand2", padx=5, pady=2)
    app.clipboard_prev_button.pack(side="left")
    app.clipboard_page_status = tk.Label(
        nav, bg=c["BG"], fg=c["SECONDARY"], font=("Segoe UI", 8))
    app.clipboard_page_status.pack(side="left", padx=6)
    app.clipboard_next_button = tk.Button(
        nav, text="Next ›", command=lambda: app._clipboard_turn_page(1),
        bg=c["CARD"], fg=c["SECONDARY"], relief="flat", bd=0,
        font=("Segoe UI", 8), cursor="hand2", padx=5, pady=2)
    app.clipboard_next_button.pack(side="left")
    show_page(app, getattr(app, "clipboard_page", "text"))
    refresh_history_selector(app)
    refresh_page_navigation(app)


def _build_text_page(app, c):
    parent = app.clipboard_text_page
    # Compact search: less height and only part of the width, leaving more room
    # for the text history in both Mini and Normal.
    app.clipboard_query = tk.StringVar()
    search_row = tk.Frame(parent, bg=c["BG"])
    search_row.pack(fill="x", pady=(0, 4))
    entry = design.entry(search_row, app.clipboard_query, app.theme, compact=True)
    app.clipboard_query_entry = entry
    entry.configure(width=20)
    entry.pack(side="left", fill="x", expand=False, ipady=3)
    app.clipboard_query.trace_add("write", lambda *_: app._refresh_clipboard())

    app.clipboard_status = tk.Label(
        parent, text="", bg=c["BG"], fg=c["MUTED"],
        font=("Segoe UI", 9), anchor="w")
    app.clipboard_status.pack(fill="x", pady=(0, 2))

    footer = tk.Frame(parent, bg=c["BG"])
    # In Mini, reserve the bottom row before allocating the list's flexible
    # space. The actions remain visible at the bottom even on short monitors.
    if app.display_mode == "mini":
        footer.pack(side="bottom", fill="x", pady=(4, 0))
    else:
        footer.pack(fill="x", pady=(3, 3))
    for title, fn in (("Copy", app._copy_clipboard_item),
                      ("Pin / Unpin", app._pin_clipboard_item),
                      ("Delete", app._delete_clipboard_item)):
        _action(footer, title, fn, c).pack(side="left", padx=(0, 3))
    app.clipboard_text_actions = footer

    frame = tk.Frame(parent, bg=c["BG"])
    frame.pack(fill="both", expand=True, pady=(3, 0))
    # Match the 1px themed border used by Pocket's other input fields.
    # Tk's default Listbox highlight ring is thicker/bright on Windows,
    # making the Clipboard history look slightly offset from adjacent tools.
    app.clipboard_list = tk.Listbox(
        frame, bg=c["PANEL"], fg=c["WHITE"],
        selectbackground=c["ACCENT_DARK"], font=("Segoe UI", 10),
        bd=0, relief="flat", highlightthickness=1,
        highlightbackground=c["BORDER"], highlightcolor=c["ACCENT"],
        selectborderwidth=0, activestyle="none", exportselection=False)
    app.clipboard_list.pack(fill="both", expand=True)
    app.clipboard_list.bind("<Double-1>", lambda _evt: app._copy_clipboard_item())

    def copy_text(_event=None):
        app._copy_clipboard_item()
        return "break"

    def text_menu(event):
        listing = app.clipboard_list
        if listing.size():
            index = listing.nearest(event.y)
            box = listing.bbox(index)
            if box and box[1] <= event.y < box[1] + box[3]:
                listing.selection_clear(0, tk.END)
                listing.selection_set(index)
                listing.activate(index)
            else:
                listing.selection_clear(0, tk.END)
        selected = app._selected_clipboard_item()
        menu = build_text_context_menu(app, c, selected)
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()
        return "break"

    app.clipboard_list.bind("<Control-c>", copy_text)
    app.clipboard_list.bind("<Control-C>", copy_text)
    app.clipboard_list.bind("<Return>", copy_text)
    app.clipboard_list.bind("<Button-3>", text_menu)
    app.clipboard_list.bind("<Control-Button-1>", text_menu)
    # Also callable from GUI regression tests without requiring an OS click.
    app.clipboard_text_context_menu = text_menu
    app._refresh_clipboard()



def build_text_context_menu(app, colors, selected):
    """Explicitly grouped actions, showing only valid Pocket destinations."""
    c = colors
    content = selected["text"] if selected else ""
    destinations = clipboard_routing.destination_values(content)
    enabled = set(app.settings["visible_tabs"])
    style = dict(
        tearoff=False, bg=c["PANEL"], fg=c["WHITE"],
        activebackground=c["ACCENT_DARK"], activeforeground=c["WHITE"],
        disabledforeground=c["MUTED"], bd=1, relief="flat",
        font=("Segoe UI", 9))
    menu = menu_style.Menu(app.root, **style)
    menu.add_command(
        label="Copy full text", accelerator="Ctrl+C",
        command=app._copy_clipboard_item,
        state="normal" if selected else "disabled")
    if selected:
        menu.add_command(
            label="Unpin from history" if selected["pinned"] else "Pin in history",
            command=app._pin_clipboard_item)
    else:
        menu.add_command(label="Pin in history", state="disabled")
    menu.add_command(
        label="Delete from history", command=app._delete_clipboard_item,
        state="normal" if selected else "disabled")
    menu.add_separator()
    if selected:
        pocket = menu_style.Menu(menu, **style)
        labels = (
            ("ports", "Prepare TCP port check"),
            ("mac", "Open MAC lookup with address"),
            ("subnet", "Open Subnet Calculator"),
            ("notes", "Create a new Note from text"))
        for destination, label in labels:
            if destination in enabled and destination in destinations:
                pocket.add_command(
                    label=label,
                    command=lambda tool=destination, data=content:
                        clipboard_routing.send_to_tool(app, tool, data))
        pocket.add_command(
            label="TRANSLATE EN/HE",
            command=lambda value=content: app._convert_clipboard_text(value))
        if pocket.index("end") is not None:
            menu.add_cascade(label="Use text in Pocket", menu=pocket)
        else:
            pocket.destroy()
            menu.add_command(
                label="No compatible Pocket tools enabled", state="disabled")
    else:
        menu.add_command(
            label="Select an entry to use Pocket tools", state="disabled")
    return menu


def _build_images_page(app, c):
    parent = app.clipboard_images_page
    app.clipboard_images_status = tk.Label(
        parent, bg=c["BG"], fg=c["MUTED"], text=f"0/{app.settings['clipboard_image_limit']} images · RAM only",
        font=("Segoe UI", 9), anchor="w")
    app.clipboard_images_status.pack(fill="x", pady=(0, 3))
    footer = tk.Frame(parent, bg=c["BG"])
    footer.pack(fill="x", pady=(4, 4))
    for title, action in (("Copy", lambda: copy_selected(app)),
                          ("Preview", lambda: preview_selected(app)),
                          ("Delete", lambda: delete_selected(app))):
        _action(footer, title, action, c).pack(side="left", padx=(0, 4))
    area = tk.Frame(parent, bg=c["BG"])
    area.pack(fill="both", expand=True)
    canvas = tk.Canvas(
        area, bg=c["BG"], highlightthickness=0, bd=0, takefocus=1)
    canvas.pack(side="left", fill="both", expand=True)
    # Mini is a single horizontal carousel. The existing vertical grid and
    # scrollbar are kept unchanged for Normal and Dashboard.
    if app.display_mode != "mini":
        scroll = ttk.Scrollbar(
            area, orient="vertical", command=canvas.yview,
            style="Pocket.Vertical.TScrollbar")
        scroll.pack(side="right", fill="y")
        canvas.configure(yscrollcommand=scroll.set)
    inner = tk.Frame(canvas, bg=c["BG"])
    window = canvas.create_window((0, 0), window=inner, anchor="nw")
    app.clipboard_images_canvas = canvas
    app.clipboard_images_inner = inner
    app._clipboard_gallery_photos = []
    app._clipboard_gallery_tiles = {}
    app._clipboard_gallery_signature = None
    inner.bind("<Configure>", lambda _e: canvas.configure(
        scrollregion=canvas.bbox("all")))

    def resize(event):
        if app.display_mode == "mini":
            # Width=0 lets the interior grow to the full combined card width,
            # instead of squeezing the entire gallery into the viewport.
            canvas.itemconfigure(window, width=0)
        else:
            canvas.itemconfigure(window, width=event.width)
        signature = app._clipboard_gallery_signature
        # Mini thumbnails also adapt to the remaining height on small screens.
        if (signature is None or abs(signature[0] - event.width) >= 14
                or (app.display_mode == "mini"
                    and abs(signature[1] - event.height) >= 14)):
            app.root.after_idle(lambda: refresh_images(app))
    canvas.bind("<Configure>", resize)

    def image_key_copy(_event=None):
        copy_selected(app)
        return "break"

    canvas.bind("<Control-c>", image_key_copy)
    canvas.bind("<Control-C>", image_key_copy)
    canvas.bind("<Return>", lambda _e: (preview_selected(app), "break")[1])
    canvas.bind("<Delete>", lambda _e: (delete_selected(app), "break")[1])
    canvas.bind("<Left>", lambda _e: move_selection(app, -1))
    canvas.bind("<Right>", lambda _e: move_selection(app, 1))
    for widget in (canvas, inner):
        widget.bind("<MouseWheel>", lambda e: _wheel(app, e))
        widget.bind("<Shift-MouseWheel>", lambda e: _wheel(app, e))
        widget.bind("<Button-4>", lambda e: _wheel(app, e))
        widget.bind("<Button-5>", lambda e: _wheel(app, e))


def refresh_history_selector(app):
    """Refresh available saved dates without recursively changing the view."""
    if not hasattr(app, "clipboard_day_select"):
        return
    if app.settings.get("clipboard_storage") != "database":
        return
    page = getattr(app, "clipboard_page", "text")
    from . import clipboard_database as db
    today = db.today()
    dates = app.clipboard_database.days(
        page, days=app.settings["clipboard_autodelete_days"])
    if today not in dates:
        dates.insert(0, today)
    values = [("Today · " + date if date == today else date) for date in dates]
    selector = app.clipboard_day_select
    selector["values"] = values
    selected = app._clipboard_view_days.get(page, today)
    if selected not in dates:
        selected = today
        app._clipboard_view_days[page] = today
        app._clipboard_load_day(page, today)
    selector.set("Today · " + selected if selected == today else selected)
    if hasattr(app, "clipboard_clear_button") and app.clipboard_clear_button:
        app.clipboard_clear_button.configure(
            text="Clear day images" if page == "images" else "Clear day text")


def refresh_page_navigation(app):
    """The page controls provide access beyond the visible 10–100 items."""
    row = getattr(app, "clipboard_page_navigation", None)
    if row is None:
        return
    database = app.settings.get("clipboard_storage") == "database"
    if database:
        if not row.winfo_manager():
            row.pack(fill="x", pady=(1, 2))
        page = getattr(app, "clipboard_page", "text")
        offset = getattr(app, "_clipboard_page_index", {}).get(page, 0)
        limit = app.settings["clipboard_text_display_limit" if page == "text"
                             else "clipboard_db_image_display_limit"]
        app.clipboard_page_status.configure(
            text=f"Items {offset + 1}–{offset + limit} · {page.title()}")
        app.clipboard_prev_button.configure(state="normal" if offset else "disabled")
    elif row.winfo_manager():
        row.pack_forget()


def show_page(app, page):
    page = page if page in ("text", "images") else "text"
    app.clipboard_page = page  # Remember across menu/layout switches in session.
    refresh_history_selector(app)
    refresh_page_navigation(app)
    if app.clipboard_clear_button is not None:
        on_disk = app.settings.get("clipboard_storage") == "database"
        app.clipboard_clear_button.configure(
            text=("Clear day images" if page == "images" else "Clear day text")
            if on_disk else
            ("Clear images" if page == "images" else "Clear text"))
    c = themes.palette(app.theme)
    for key, btn in app.clipboard_page_buttons.items():
        selected = key == page
        btn.configure(bg=c["BG"], fg=c["WHITE"] if selected else c["MUTED"],
                      activebackground=c["BG"], activeforeground=c["WHITE"])
    toggle = app.clipboard_page_toggle
    toggle.delete("all")
    fill = c["ACCENT"] if page == "images" else c["CARD_HOVER"]
    toggle.create_oval(2, 2, 21, 20, fill=fill, outline=fill)
    toggle.create_rectangle(11, 2, 33, 20, fill=fill, outline=fill)
    toggle.create_oval(23, 2, 42, 20, fill=fill, outline=fill)
    x = 31 if page == "images" else 13
    toggle.create_oval(x - 8, 3, x + 8, 19, fill=c["WHITE"], outline="")
    app.clipboard_text_page.pack_forget()
    app.clipboard_images_page.pack_forget()
    panel = app.clipboard_images_page if page == "images" else app.clipboard_text_page
    panel.pack(fill="both", expand=True)
    if page == "images":
        def activate_images():
            canvas = getattr(app, "clipboard_images_canvas", None)
            if (canvas is not None and canvas.winfo_exists()
                    and canvas.winfo_ismapped()
                    and app.current_tab == "clipboard"
                    and app.clipboard_page == "images"):
                refresh_images(app)
                # Only Images owns these keystrokes; text search never does.
                canvas.focus_set()
        app.root.after_idle(activate_images)
    else:
        app._refresh_clipboard()


def _wheel(app, event):
    if not app.clipboard_images_canvas.winfo_exists():
        return "break"
    forward = (event.delta < 0) if getattr(event, "delta", 0) else (
        getattr(event, "num", 0) == 5)
    if app.display_mode == "mini":
        # A regular mouse wheel selects the neighboring horizontal card.
        # No dragging, extra arrows, or additional UI controls.
        move_selection(app, 1 if forward else -1)
    else:
        app.clipboard_images_canvas.yview_scroll(
            (1 if forward else -1) * 3, "units")
    return "break"


def _selection_index(app):
    ident = getattr(app, "_clipboard_selected_image_id", None)
    return next((i for i, item in enumerate(app.clipboard_images)
                 if item["id"] == ident), -1)


def _update_status(app):
    label = getattr(app, "clipboard_images_status", None)
    if label is None or not label.winfo_exists():
        return
    count = len(app.clipboard_images)
    maximum = app.settings["clipboard_image_limit"]
    stored = app.settings.get("clipboard_storage") == "database"
    capture = "PAUSED" if app.settings["clipboard_paused"] else "Capture ON"
    if app.display_mode == "mini":
        index = _selection_index(app)
        label.configure(text=(
            f"{index + 1 if index >= 0 else 0} / {count} selected · "
            f"{count} shown · {capture}" if stored else
            f"{index + 1 if index >= 0 else 0} / {count} selected · "
            f"{count}/{maximum} images · {capture}"))
    else:
        label.configure(
            text=f"{count} shown · DATABASE · {capture}" if stored else
                 f"{count}/{maximum} images · RAM only · {capture}")


def _ensure_selected_visible(app):
    """Scroll the selected card into view without changing the selection."""
    if (app.current_tab != "clipboard" or app.clipboard_page != "images"):
        return
    canvas = getattr(app, "clipboard_images_canvas", None)
    if canvas is None or not canvas.winfo_exists() or not canvas.winfo_ismapped():
        return
    tile = getattr(app, "_clipboard_gallery_tiles", {}).get(
        getattr(app, "_clipboard_selected_image_id", None))
    if tile is None or not tile.winfo_exists():
        return
    bounds = canvas.bbox("all")
    if bounds is None:
        return
    viewport = canvas.winfo_width() if app.display_mode == "mini" else canvas.winfo_height()
    if viewport <= 1:
        return
    if app.display_mode == "mini":
        span = max(1, bounds[2] - bounds[0])
        # Center whenever possible, clamp to the last fully visible card.
        target = tile.winfo_x() + tile.winfo_width() / 2 - viewport / 2
        target = max(0, min(target, max(0, span - viewport)))
        canvas.xview_moveto(target / span)
    else:
        span = max(1, bounds[3] - bounds[1])
        top = canvas.canvasy(0)
        bottom = top + viewport
        tile_top = tile.winfo_y()
        tile_bottom = tile_top + tile.winfo_height()
        if tile_top < top:
            canvas.yview_moveto(max(0, tile_top) / span)
        elif tile_bottom > bottom:
            canvas.yview_moveto(max(0, tile_bottom - viewport) / span)


def _scroll_to_selection_later(app):
    app.root.after_idle(lambda: _ensure_selected_visible(app))


def select_image(app, ident):
    if not any(item["id"] == ident for item in app.clipboard_images):
        return
    app._clipboard_selected_image_id = ident
    canvas = getattr(app, "clipboard_images_canvas", None)
    if canvas is not None and canvas.winfo_exists():
        canvas.focus_set()
    c = themes.palette(app.theme)
    for key, tile in getattr(app, "_clipboard_gallery_tiles", {}).items():
        if tile.winfo_exists():
            tile.configure(highlightbackground=(
                c["ACCENT"] if key == ident else c["BORDER"]))
    _update_status(app)
    _scroll_to_selection_later(app)


def move_selection(app, step):
    """Left/right keyboard navigation in Images only; no wrapping at edges."""
    if (app.current_tab != "clipboard" or app.clipboard_page != "images"):
        return None
    if not app.clipboard_images:
        return "break"
    current = _selection_index(app)
    index = (max(0, min(len(app.clipboard_images) - 1, current + step))
             if current >= 0 else 0)
    select_image(app, app.clipboard_images[index]["id"])
    return "break"


def refresh_images(app, *, force=False):
    canvas = getattr(app, "clipboard_images_canvas", None)
    if canvas is None or not canvas.winfo_exists():
        return
    status = app.clipboard_images_status
    if not status.winfo_exists():
        return
    if getattr(app, "clipboard_page", "text") != "images":
        _update_status(app)
        return
    width = canvas.winfo_width()
    height = canvas.winfo_height()
    if width <= 15:
        return
    ids = tuple(item["id"] for item in app.clipboard_images)
    signature = (width, height if app.display_mode == "mini" else 0, ids, app.theme)
    if signature == app._clipboard_gallery_signature and not force:
        _update_status(app)
        _scroll_to_selection_later(app)
        return
    app._clipboard_gallery_signature = signature
    c = themes.palette(app.theme)
    frame = app.clipboard_images_inner
    for child in frame.winfo_children():
        child.destroy()
    app._clipboard_gallery_photos = []
    app._clipboard_gallery_tiles = {}
    horizontal = app.display_mode == "mini"
    columns = len(app.clipboard_images) if horizontal else columns_for_width(width)
    if not horizontal:
        for col in range(columns):
            frame.columnconfigure(col, weight=1, uniform="thumbnail")
    card_width = (max(140, min(245, int(width * 0.77))) if horizontal
                  else max(94, (width - 10 * columns - 12) // columns))
    thumb_size = (
        (card_width - 16, max(42, min(140, height - 42))) if horizontal
        else (max(65, card_width - 16),
              max(70, min(190, card_width * 3 // 4))))
    if app.clipboard_images and not any(
            item["id"] == getattr(app, "_clipboard_selected_image_id", None)
            for item in app.clipboard_images):
        app._clipboard_selected_image_id = app.clipboard_images[0]["id"]
    _update_status(app)
    for index, item in enumerate(app.clipboard_images):
        ident = item["id"]
        tile = tk.Frame(
            frame, bg=c["PANEL"], highlightthickness=2,
            highlightbackground=c["ACCENT"] if
            ident == getattr(app, "_clipboard_selected_image_id", None)
            else c["BORDER"], cursor="hand2")
        tile.grid(row=0 if horizontal else index // columns,
                  column=index if horizontal else index % columns,
                  sticky="nsew", padx=3, pady=3)
        app._clipboard_gallery_tiles[ident] = tile
        try:
            picture = clipboard_images.decode_image(_image_payload(app, item))
            picture.thumbnail(thumb_size, Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(picture, master=app.root)
        except (OSError, ValueError, MemoryError):
            continue
        app._clipboard_gallery_photos.append(photo)
        label = tk.Label(
            tile, image=photo, bg=c["PANEL"], cursor="hand2",
            width=thumb_size[0], height=thumb_size[1])
        label.pack(fill="x", padx=3, pady=(4, 2))
        caption = tk.Label(
            tile, text=f'{item["time"]} · {item["width"]}×{item["height"]}',
            bg=c["PANEL"], fg=c["SECONDARY"], font=("Segoe UI", 8))
        caption.pack(pady=(0, 5))
        for widget in (tile, label, caption):
            widget.bind("<Button-1>", lambda _e, i=ident: select_image(app, i))
            widget.bind("<Double-1>", lambda _e, i=ident: (
                select_image(app, i), preview_selected(app)))
            widget.bind("<Button-3>", lambda event, i=ident: image_menu(app, event, i))
            widget.bind("<MouseWheel>", lambda event: _wheel(app, event))
            widget.bind("<Button-4>", lambda event: _wheel(app, event))
            widget.bind("<Button-5>", lambda event: _wheel(app, event))
    canvas.configure(scrollregion=canvas.bbox("all"))
    _scroll_to_selection_later(app)


def image_menu(app, event, ident):
    """Right-click any thumbnail to select and copy it, even in Mini."""
    select_image(app, ident)
    c = themes.palette(app.theme)
    menu = menu_style.Menu(app.root, tearoff=False, bg=c["PANEL"], fg=c["WHITE"],
                   activebackground=c["ACCENT_DARK"],
                   activeforeground=c["WHITE"])
    menu.add_command(label="Copy image", command=lambda: copy_selected(app))
    menu.add_command(label="Preview", command=lambda: preview_selected(app))
    menu.add_command(label="Delete", command=lambda: delete_selected(app))
    try:
        menu.tk_popup(event.x_root, event.y_root)
    finally:
        menu.grab_release()
    return "break"


def selected_image(app):
    ident = getattr(app, "_clipboard_selected_image_id", None)
    return next((item for item in app.clipboard_images if item["id"] == ident), None)


def _image_payload(app, item):
    if "data" in item:
        return item["data"]  # RAM screenshot, already in memory.
    return app.clipboard_database.image_data(item)  # One disk read on demand.


def copy_selected(app):
    item = selected_image(app)
    if item is None:
        return
    try:
        clipboard_images.copy_image(_image_payload(app, item))
        app._clipboard_sequence = clipboard_images.sequence_number()
        _update_status(app)
        label = app.clipboard_images_status
        label.configure(text=label.cget("text") + " · Copied")
    except (OSError, MemoryError, ValueError) as exc:
        messagebox.showerror("Image clipboard", str(exc), parent=app.root)


def preview_selected(app):
    item = selected_image(app)
    if item is None:
        return
    c = themes.palette(app.theme)
    try:
        picture = clipboard_images.decode_image(_image_payload(app, item))
    except (OSError, ValueError, MemoryError) as exc:
        messagebox.showerror("Image preview", str(exc), parent=app.root)
        return
    max_width = max(260, min(1120, app.root.winfo_screenwidth() - 100))
    max_height = max(200, min(760, app.root.winfo_screenheight() - 140))
    picture.thumbnail((max_width - 36, max_height - 80), Image.Resampling.LANCZOS)
    previous_modal = app._modal
    app._modal = True
    window = tk.Toplevel(app.root)
    window.title(f'Pocket · Image {item["width"]}×{item["height"]}')
    window.configure(bg=c["BG"])
    window.transient(app.root)
    photo = ImageTk.PhotoImage(picture, master=window)
    display = tk.Label(window, image=photo, bg=c["BG"])
    display.image = photo
    display.pack(fill="both", expand=True, padx=12, pady=(12, 5))
    def close_preview(_event=None):
        if window.winfo_exists():
            window.destroy()
        app._modal = previous_modal
        canvas = getattr(app, "clipboard_images_canvas", None)
        if (app.current_tab == "clipboard" and app.clipboard_page == "images"
                and canvas is not None and canvas.winfo_exists()):
            # Return keyboard ownership to Images after dismissing the preview.
            app.root.after_idle(canvas.focus_set)

    _action(window, "Close preview", close_preview, c).pack(pady=(2, 10))
    window.protocol("WM_DELETE_WINDOW", close_preview)
    window.bind("<Escape>", close_preview)
    window.grab_set()
    window.focus_set()


def delete_selected(app):
    item = selected_image(app)
    if item is None:
        return
    previous_index = _selection_index(app)
    if (app.settings.get("clipboard_storage") == "database"
            and not app._clipboard_delete_image(item)):
        return
    app.clipboard_images[:] = [
        entry for entry in app.clipboard_images if entry["id"] != item["id"]]
    app._clipboard_selected_image_id = (
        app.clipboard_images[min(previous_index, len(app.clipboard_images) - 1)]["id"]
        if app.clipboard_images else None)
    refresh_images(app, force=True)
    if app.settings.get("clipboard_storage") == "database":
        refresh_history_selector(app)
        refresh_images(app, force=True)


def clear_images(app):
    if (app.settings.get("clipboard_storage") == "database"
            and not app._clipboard_clear_images()):
        return
    app.clipboard_images.clear()
    app._clipboard_selected_image_id = None
    refresh_images(app, force=True)
    if app.settings.get("clipboard_storage") == "database":
        refresh_history_selector(app)
        refresh_images(app, force=True)
