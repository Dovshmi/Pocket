"""Responsive Text / Images pages for Pocket's existing Clipboard tool.

The Text page keeps the original searchable Listbox. The Images page uses a
width-aware thumbnail gallery with no search field. All state stays in RAM.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from PIL import Image, ImageTk

from . import clipboard_images
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
                                "Session-only text and images · Never saved to disk",
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

    switch = tk.Frame(app.body, bg=c["BG"])
    switch.pack(fill="x", pady=(0, 7))
    app.clipboard_page_buttons = {}
    for page, label in (("text", "Text"), ("images", "Images")):
        btn = tk.Button(
            switch, text=label, cursor="hand2", bd=0, relief="flat",
            font=("Segoe UI", 10, "bold"), takefocus=True, pady=8,
            command=lambda destination=page: show_page(app, destination))
        btn.pack(side="left", fill="x", expand=True, padx=(0, 3))
        app.clipboard_page_buttons[page] = btn

    app.clipboard_text_page = tk.Frame(app.body, bg=c["BG"])
    app.clipboard_images_page = tk.Frame(app.body, bg=c["BG"])
    _build_text_page(app, c)
    _build_images_page(app, c)
    show_page(app, getattr(app, "clipboard_page", "text"))


def _build_text_page(app, c):
    parent = app.clipboard_text_page
    app.clipboard_query = tk.StringVar()
    entry = design.entry(parent, app.clipboard_query, app.theme)
    entry.pack(fill="x", ipady=8, pady=(0, 7))
    app.clipboard_query.trace_add("write", lambda *_: app._refresh_clipboard())
    app.clipboard_status = tk.Label(
        parent, text="", bg=c["BG"], fg=c["MUTED"],
        font=("Segoe UI", 9), anchor="w")
    app.clipboard_status.pack(fill="x")
    frame = tk.Frame(parent, bg=c["BG"])
    frame.pack(fill="both", expand=True, pady=(6, 4))
    app.clipboard_list = tk.Listbox(
        frame, bg=c["PANEL"], fg=c["WHITE"],
        selectbackground=c["ACCENT_DARK"], font=("Segoe UI", 10),
        bd=0, exportselection=False)
    app.clipboard_list.pack(fill="both", expand=True)
    app.clipboard_list.bind("<Double-1>", lambda _evt: app._copy_clipboard_item())
    footer = tk.Frame(parent, bg=c["BG"])
    footer.pack(fill="x")
    for title, fn in (("Copy selected", app._copy_clipboard_item),
                      ("Pin / Unpin", app._pin_clipboard_item),
                      ("Delete", app._delete_clipboard_item)):
        _action(footer, title, fn, c).pack(side="left", padx=(0, 3))
    app._refresh_clipboard()


def _build_images_page(app, c):
    parent = app.clipboard_images_page
    app.clipboard_images_status = tk.Label(
        parent, bg=c["BG"], fg=c["MUTED"], text="0/20 images · RAM only",
        font=("Segoe UI", 9), anchor="w")
    app.clipboard_images_status.pack(fill="x", pady=(0, 3))
    area = tk.Frame(parent, bg=c["BG"])
    area.pack(fill="both", expand=True)
    canvas = tk.Canvas(
        area, bg=c["BG"], highlightthickness=0, bd=0, takefocus=0)
    canvas.pack(side="left", fill="both", expand=True)
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
        canvas.itemconfigure(window, width=event.width)
        # Rendering only on meaningful width changes avoids resize loops.
        signature = app._clipboard_gallery_signature
        if signature is None or abs(signature[0] - event.width) >= 14:
            app.root.after_idle(lambda: refresh_images(app))
    canvas.bind("<Configure>", resize)

    footer = tk.Frame(parent, bg=c["BG"])
    footer.pack(fill="x", pady=(5, 0))
    for title, action in (("Copy", lambda: copy_selected(app)),
                          ("Preview", lambda: preview_selected(app)),
                          ("Delete", lambda: delete_selected(app))):
        _action(footer, title, action, c).pack(side="left", padx=(0, 4))


def show_page(app, page):
    page = page if page in ("text", "images") else "text"
    app.clipboard_page = page  # Remember across menu/layout switches in session.
    if app.clipboard_clear_button is not None:
        app.clipboard_clear_button.configure(
            text="Clear images" if page == "images" else "Clear text")
    c = themes.palette(app.theme)
    for key, btn in app.clipboard_page_buttons.items():
        selected = key == page
        btn.configure(bg=c["ACCENT_DARK"] if selected else c["PANEL"],
                      fg=c["WHITE"] if selected else c["SECONDARY"],
                      activebackground=c["CARD_HOVER"],
                      activeforeground=c["WHITE"])
    app.clipboard_text_page.pack_forget()
    app.clipboard_images_page.pack_forget()
    panel = app.clipboard_images_page if page == "images" else app.clipboard_text_page
    panel.pack(fill="both", expand=True)
    if page == "images":
        app.root.after_idle(lambda: refresh_images(app))
    else:
        app._refresh_clipboard()


def _wheel(app, event):
    canvas = app.clipboard_images_canvas
    if not canvas.winfo_exists():
        return "break"
    steps = (-1 if event.delta > 0 else 1) if event.delta else (
        -1 if getattr(event, "num", 0) == 4 else 1)
    canvas.yview_scroll(steps * 3, "units")
    return "break"


def select_image(app, ident):
    app._clipboard_selected_image_id = ident
    c = themes.palette(app.theme)
    for key, tile in getattr(app, "_clipboard_gallery_tiles", {}).items():
        if tile.winfo_exists():
            tile.configure(highlightbackground=(
                c["ACCENT"] if key == ident else c["BORDER"]))


def refresh_images(app, *, force=False):
    canvas = getattr(app, "clipboard_images_canvas", None)
    if canvas is None or not canvas.winfo_exists():
        return
    status = app.clipboard_images_status
    if not status.winfo_exists():
        return
    status.configure(text=f"{len(app.clipboard_images)}/20 images · RAM only · " +
                     ("PAUSED" if app.settings["clipboard_paused"] else "Capture ON"))
    if getattr(app, "clipboard_page", "text") != "images":
        return
    width = canvas.winfo_width()
    if width <= 15:
        return
    ids = tuple(item["id"] for item in app.clipboard_images)
    signature = (width, ids, app.theme)
    if signature == app._clipboard_gallery_signature and not force:
        return
    app._clipboard_gallery_signature = signature
    c = themes.palette(app.theme)
    frame = app.clipboard_images_inner
    for child in frame.winfo_children():
        child.destroy()
    app._clipboard_gallery_photos = []
    app._clipboard_gallery_tiles = {}
    columns = columns_for_width(width)
    for col in range(columns):
        frame.columnconfigure(col, weight=1, uniform="thumbnail")
    card_width = max(94, (width - 10 * columns - 12) // columns)
    thumb_size = (max(65, card_width - 16), max(70, min(190, card_width * 3 // 4)))
    if app.clipboard_images and not any(
            item["id"] == getattr(app, "_clipboard_selected_image_id", None)
            for item in app.clipboard_images):
        app._clipboard_selected_image_id = app.clipboard_images[0]["id"]
    for index, item in enumerate(app.clipboard_images):
        ident = item["id"]
        tile = tk.Frame(
            frame, bg=c["PANEL"], highlightthickness=2,
            highlightbackground=c["ACCENT"] if
            ident == getattr(app, "_clipboard_selected_image_id", None)
            else c["BORDER"], cursor="hand2")
        tile.grid(row=index // columns, column=index % columns,
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
            widget.bind("<MouseWheel>", lambda event: _wheel(app, event))
            widget.bind("<Button-4>", lambda event: _wheel(app, event))
            widget.bind("<Button-5>", lambda event: _wheel(app, event))
    canvas.configure(scrollregion=canvas.bbox("all"))
    if force:
        canvas.yview_moveto(0.0)


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
        app.clipboard_images_status.configure(
            text=f'{len(app.clipboard_images)}/20 images · Copied to clipboard')
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

    _action(window, "Close preview", close_preview, c).pack(pady=(2, 10))
    window.protocol("WM_DELETE_WINDOW", close_preview)
    window.bind("<Escape>", close_preview)
    window.grab_set()
    window.focus_set()


def delete_selected(app):
    item = selected_image(app)
    if item is None:
        return
    app.clipboard_images[:] = [
        entry for entry in app.clipboard_images if entry["id"] != item["id"]]
    app._clipboard_selected_image_id = None
    refresh_images(app, force=True)


def clear_images(app):
    app.clipboard_images.clear()
    app._clipboard_selected_image_id = None
    refresh_images(app, force=True)
