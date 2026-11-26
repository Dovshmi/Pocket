"""Keyboard-first, themed local command palette."""
import tkinter as tk
from tkinter import ttk
from . import command_palette as palette
from . import icon_themes, pocket_design as design, tool_icons

def open_palette(app):
    old = getattr(app, "_quick_search_dialog", None)
    if old is not None and old.winfo_exists():
        old.attributes("-topmost", True)
        old.lift()
        app._palette_entry.focus_force()
        return "break"
    c = icon_themes.palette(app.theme)
    dialog = tk.Toplevel(app.root)
    app._quick_search_dialog = dialog
    was_modal = app._modal
    app._modal = True
    dialog.withdraw()
    dialog.title("Pocket · Command Palette")
    dialog.overrideredirect(True)
    dialog.transient(app.root)
    # Pocket itself is topmost in normal tray operation. A transient
    # override-redirect child must also be topmost to appear above its owner.
    dialog.attributes("-topmost", True)
    dialog.configure(bg=c["BORDER"])
    dialog.resizable(False, False)
    area = app._screen_work_area(app.root.winfo_rootx(), app.root.winfo_rooty())
    width = min(520, max(240, area[2]-area[0]-20))
    height = min(390, max(240, area[3]-area[1]-20))
    x = max(area[0]+5, min(app.root.winfo_rootx()+(app.root.winfo_width()-width)//2, area[2]-width-5))
    y = max(area[1]+5, min(app.root.winfo_rooty()+40, area[3]-height-5))
    dialog.geometry(f"{width}x{height}{x:+d}{y:+d}")
    frame = tk.Frame(dialog, bg=c["BG"])
    frame.pack(fill="both", expand=True, padx=1, pady=1)
    tk.Frame(frame, bg=c["ACCENT"], height=2).pack(fill="x")
    top = tk.Frame(frame, bg=c["BG"])
    top.pack(fill="x", padx=14, pady=(12, 8))
    tk.Label(top, text="Pocket Command Palette", bg=c["BG"], fg=c["WHITE"],
             font=("Segoe UI", 12, "bold")).pack(side="left")
    design.button(top, "×", lambda: close(), app.theme, compact=True).pack(side="right")
    tk.Label(top, text="Ctrl+K", bg=c["CARD"], fg=c["SECONDARY"],
             font=("Segoe UI", 8), padx=6, pady=3).pack(side="right", padx=(0, 6))
    query = tk.StringVar(master=dialog)
    # Keep palette navigation in Tk: native EDIT controls consume Return,
    # Escape and arrow keys before Tk can dispatch their bindings.
    search = tk.Frame(frame, bg=c["INPUT"], highlightthickness=1,
                      highlightbackground=c["BORDER"])
    search.pack(fill="x", padx=14)
    glass = tk.Canvas(search, width=26, height=28, bg=c["INPUT"],
                      highlightthickness=0, bd=0)
    glass.create_oval(7, 6, 18, 17, outline=c["MUTED"], width=2)
    glass.create_line(16, 15, 21, 20, fill=c["MUTED"], width=2)
    glass.pack(side="left", padx=(4, 0))
    entry = tk.Entry(search, textvariable=query, bg=c["INPUT"], fg=c["WHITE"],
                     insertbackground=c["WHITE"], selectbackground=c["ACCENT_DARK"],
                     relief="flat", bd=0, highlightthickness=0,
                     font=("Segoe UI", 12))
    app._palette_entry = entry
    entry.pack(side="left", fill="x", expand=True, padx=(2, 8), ipady=8)
    entry.bind("<FocusIn>", lambda _e: search.configure(highlightbackground=c["ACCENT"]))
    entry.bind("<FocusOut>", lambda _e: search.configure(highlightbackground=c["BORDER"]))
    glass.bind("<Button-1>", lambda _e: entry.focus_set())
    status = tk.Label(frame, bg=c["BG"], fg=c["MUTED"], anchor="w",
                      font=("Segoe UI", 8))
    status.pack(fill="x", padx=14, pady=(9, 5))
    footer = tk.Frame(frame, bg=c["BG"])
    footer.pack(side="bottom", fill="x", padx=12, pady=8)
    tk.Label(footer, text="↑ ↓ Select · Enter run · Ctrl+X / Esc close", bg=c["BG"],
             fg=c["MUTED"], font=("Segoe UI", 8)).pack(side="left")
    preview = tk.Frame(frame, bg=c["PANEL"])
    preview.pack(side="bottom", fill="x", padx=12, pady=(4, 0))
    icon = tk.Label(preview, bg=c["PANEL"])
    icon.pack(side="left", padx=6, pady=4)
    detail = tk.Label(preview, bg=c["PANEL"], fg=c["SECONDARY"],
                      font=("Segoe UI", 8), anchor="w", justify="left", wraplength=width-75)
    detail.pack(side="left", fill="x", expand=True, pady=4)
    list_frame = tk.Frame(frame, bg=c["BG"])
    list_frame.pack(fill="both", expand=True, padx=14)
    results = tk.Listbox(list_frame, bg=c["PANEL"], fg=c["WHITE"],
                         selectbackground=c["ACCENT_DARK"], selectforeground=c["WHITE"],
                         borderwidth=0, highlightthickness=0, font=("Segoe UI", 11),
                         exportselection=False, activestyle="none")
    scroll = ttk.Scrollbar(list_frame, command=results.yview,
                           style="Pocket.Vertical.TScrollbar")
    scroll.pack(side="right", fill="y")
    results.configure(yscrollcommand=scroll.set)
    results.pack(side="left", fill="both", expand=True)
    matches = []

    def update_preview(_event=None):
        chosen = results.curselection()
        if not chosen or chosen[0] >= len(matches):
            detail.configure(text="Type a tool, note, CLI command, IP or > action.")
            icon.configure(image="")
            return
        hit = matches[chosen[0]]
        detail.configure(text=hit["title"] + " · " + hit["subtitle"])
        icon.image = tool_icons.icon_image(icon, hit.get("destination") or "settings", c["ACCENT"], size=20)
        icon.configure(image=icon.image)

    def refresh(*_args):
        matches[:] = palette.results(app.data, app.command_library, query.get(),
                                     app.settings["visible_tabs"], app.settings)
        results.delete(0, "end")
        for hit in matches:
            mark = "›" if hit["kind"] == "action" else "·"
            results.insert("end", f"{mark}  {hit['title']}    ·  {hit['subtitle']}")
        if matches:
            results.selection_set(0)
        status.configure(text=("COMMANDS" if query.get().lstrip().startswith(">") else
                               "QUICK ACTIONS" if not query.get().strip() else "SEARCH RESULTS")
                              + f"  ·  {len(matches)}")
        update_preview()

    def close(_event=None):
        if dialog.winfo_exists():
            dialog.destroy()
        app._quick_search_dialog = None
        app._modal = was_modal
        return "break"

    def launch(_event=None):
        chosen = results.curselection()
        if chosen and chosen[0] < len(matches):
            hit = matches[chosen[0]]
            close()
            app._run_palette_action(hit)
        return "break"

    def move(step):
        if matches:
            current = results.curselection()
            index = ((current[0] if current else 0) + step) % len(matches)
            results.selection_clear(0, "end")
            results.selection_set(index)
            results.activate(index)
            results.see(index)
            update_preview()
        return "break"

    design.button(footer, "Close", close, app.theme, compact=True).pack(side="right")
    design.button(footer, "Open", launch, app.theme, primary=True, compact=True).pack(side="right", padx=4)
    query.trace_add("write", refresh)
    results.bind("<<ListboxSelect>>", update_preview)
    for widget in (entry, results, dialog):
        widget.bind("<Escape>", close)
        widget.bind("<Control-x>", close)
        widget.bind("<Control-X>", close)
        widget.bind("<Return>", launch)
    entry.bind("<Down>", lambda _e: move(1))
    entry.bind("<Up>", lambda _e: move(-1))
    results.bind("<Double-1>", launch)
    dialog.protocol("WM_DELETE_WINDOW", close)
    refresh()
    dialog.deiconify()
    dialog.update_idletasks()
    dialog.lift()
    entry.focus_force()

    def raise_after_map():
        if dialog.winfo_exists():
            dialog.attributes("-topmost", True)
            dialog.lift()
            entry.focus_force()
    dialog.after_idle(raise_after_map)
    return "break"
