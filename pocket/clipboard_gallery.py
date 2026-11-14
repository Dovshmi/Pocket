"""Responsive Text / Images pages for Pocket's existing Clipboard tool.

The Text page keeps the original searchable Listbox. The Images page uses a
width-aware thumbnail gallery with no search field. All state stays in RAM.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from PIL import Image, ImageTk

from . import clipboard_images
from . import clipboard_routing
from . import icon_themes as themes
from . import pocket_design as design


def columns_for_width(width):
    """One large column in Mini, more columns as the workspace gets wider."""
    return max(1, min(5, int(width) // 205))


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
    header = app._section_title(app.body, "Clipboard history",
                                "RAM only · Never saved to disk",
                                "Clear text", app._clear_clipboard)
    app.clipboard_clear_button = next(
        (child for child in header.winfo_children() if isinstance(child, tk.Button)),
        None)
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
    show_page(app, getattr(app, "clipboard_page", "text"))


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
    app.clipboard_list = tk.Listbox(
        frame, bg=c["PANEL"], fg=c["WHITE"],
        selectbackground=c["ACCENT_DARK"], font=("Segoe UI", 10),
        bd=0, exportselection=False)
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
        content = selected["text"] if selected else ""
        destinations = clipboard_routing.destination_values(content)
        enabled = set(app.settings["visible_tabs"])
        menu = tk.Menu(app.root, tearoff=False, bg=c["PANEL"], fg=c["WHITE"],
                       activebackground=c["ACCENT_DARK"],
                       activeforeground=c["WHITE"])
        menu.add_command(
            label="Copy to Clipboard", command=app._copy_clipboard_item,
            state="normal" if selected else "disabled")
        menu.add_command(label="Pin / Unpin", command=app._pin_clipboard_item,
                         state="normal" if selected else "disabled")
        menu.add_command(label="Delete", command=app._delete_clipboard_item,
                         state="normal" if selected else "disabled")
        menu.add_separator()
        for destination, label in (
                ("ports", "Send to TCP Ports"),
                ("mac", "Send to MAC Lookup"),
                ("subnet", "Send to Subnet Calculator"),
                ("notes", "Open as new Note")):
            can_send = destination in enabled and destination in destinations
            menu.add_command(
                label=label, state="normal" if can_send else "disabled",
                command=lambda tool=destination, data=content:
                    clipboard_routing.send_to_tool(app, tool, data))
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


def _build_images_page(app, c):
    parent = app.clipboard_images_page
    app.clipboard_images_status = tk.Label(
        parent, bg=c["BG"], fg=c["MUTED"], text="0/20 images · RAM only",
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


def show_page(app, page):
    page = page if page in ("text", "images") else "text"
    app.clipboard_page = page  # Remember across menu/layout switches in session.
    if app.clipboard_clear_button is not None:
        app.clipboard_clear_button.configure(
            text="Clear images" if page == "images" else "Clear text")
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
    capture = "PAUSED" if app.settings["clipboard_paused"] else "Capture ON"
    if app.display_mode == "mini":
        index = _selection_index(app)
        label.configure(text=(
            f"{index + 1 if index >= 0 else 0} / {count} selected · "
            f"{count}/20 images · {capture}"))
    else:
        label.configure(text=f"{count}/20 images · RAM only · {capture}")


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
        picture = clipboard_images.decode_image(item["data"])
        picture.thumbnail(thumb_size, Image.Resampling.LANCZOS)
        photo = ImageTk.PhotoImage(picture, master=app.root)
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
    menu = tk.Menu(app.root, tearoff=False, bg=c["PANEL"], fg=c["WHITE"],
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


def copy_selected(app):
    item = selected_image(app)
    if item is None:
        return
    try:
        clipboard_images.copy_image(item["data"])
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
    picture = clipboard_images.decode_image(item["data"])
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
    app.clipboard_images[:] = [
        entry for entry in app.clipboard_images if entry["id"] != item["id"]]
    app._clipboard_selected_image_id = (
        app.clipboard_images[min(previous_index, len(app.clipboard_images) - 1)]["id"]
        if app.clipboard_images else None)
    refresh_images(app, force=True)


def clear_images(app):
    app.clipboard_images.clear()
    app._clipboard_selected_image_id = None
    refresh_images(app, force=True)
