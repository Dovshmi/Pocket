"""Screenshot-inspired pocket-sized launcher for the existing Pocket desktop app.

Extra Mini is a temporary launcher for a selected Normal, Mini or Dashboard.
Opening a tool restores that layout, and search remains entirely local.
"""
from __future__ import annotations

import tkinter as tk

import command_helper as ch
import pocket_design as design
import launcher_extra_ui as extra
import tool_icons

NAVIGATION = (
    ("home", "Home", "Home"),
    ("notes", "✎", "Notes"),
    ("links", "↗", "Shortcuts"),
    ("ports", "⇄", "TCP Ports"),
    ("mac", "▦", "MAC Lookup"),
    ("commands", ">_", "Commands"),
    ("subnet", "⌗", "Subnet"),
    ("clipboard", "▣", "Clipboard"),
    ("settings", "⚙", "Settings"),
)

PAGES = {
    "home": ("Pocket", "Quick access"),
    "notes": ("Notes", "Notes, phone numbers and reminders"),
    "links": ("Shortcuts", "Files, folders and websites"),
    "ports": ("TCP Ports", "On-demand connectivity checks"),
    "mac": ("MAC Lookup", "IEEE vendor lookup"),
    "commands": ("Commands", "Search, edit and copy CLI references"),
    "subnet": ("Subnet", "IPv4 networks and address ranges"),
    "clipboard": ("Clipboard", "Session-only copied text"),
    "settings": ("Settings", "Customize Pocket"),
}

TOOL_DESCRIPTIONS = {
    "notes": "Quick notes",
    "links": "Saved links",
    "ports": "TCP checks",
    "mac": "MAC vendors",
    "commands": "Run no commands",
    "subnet": "IPv4 ranges",
    "clipboard": "Saved text",
}

# Match the screenshot's primary actions, with substitutions when hidden.
FEATURED = ("commands", "notes", "clipboard", "subnet")
ICON_COLORS = {
    "commands": "#26BBFF", "notes": "#73E67D",
    "clipboard": "#C16CFF", "subnet": "#20CCF3",
    "links": "#68C9FF", "ports": "#FFBF64", "mac": "#84D8E3",
}


def visible_navigation(visible_tabs):
    """Honor hidden tools while keeping the Home and Settings entry points."""
    allowed = set(visible_tabs)
    return tuple(row for row in NAVIGATION
                 if row[0] in ("home", "settings") or row[0] in allowed)


def configured_tiles(raw):
    """Return exactly four persisted slots; None is an intentional empty tile.

    Never silently refill a deleted slot: it should remain a visible + until
    the user chooses a replacement. Legacy installations without preferences
    start with the same four defaults as before.
    """
    valid = {key for key, _icon, _name in NAVIGATION} - {"home", "settings"}
    if not isinstance(raw, (list, tuple)):
        return list(FEATURED)
    slots = []
    used = set()
    for index in range(4):
        key = raw[index] if index < len(raw) else None
        if isinstance(key, str) and key in valid and key not in used:
            slots.append(key)
            used.add(key)
        else:
            slots.append(None)
    return slots


def display_slots(visible_tabs, selected=None):
    """Fixed four-slot view; hidden tools are placeholders, not deleted."""
    enabled = set(visible_tabs)
    return tuple(key if key in enabled else None
                 for key in configured_tiles(selected))


def featured_tools(visible_tabs, selected=None, limit=4):
    """Return just the active quick actions (empty/hidden slots excluded)."""
    return tuple(key for key in display_slots(visible_tabs, selected)
                 if key is not None)[:max(0, limit)]


def remove_tile(current, index):
    """Clear one slot without shifting neighbors or changing menu visibility."""
    slots = configured_tiles(current)
    if 0 <= index < 4:
        slots[index] = None
    return slots


def choose_tile(current, index, key, visible_tabs):
    """Set a slot to a visible tool; swap duplicates instead of duplicating."""
    slots = configured_tiles(current)
    valid = {item for item in visible_tabs if item in TOOL_DESCRIPTIONS}
    if not 0 <= index < 4 or key not in valid:
        return slots
    if key in slots and slots.index(key) != index:
        other_index = slots.index(key)
        slots[other_index] = slots[index]
    slots[index] = key
    return slots


def available_tools(visible_tabs, selected=None, slot=None):
    """Candidates for a + slot. Never offer hidden or already-used tools."""
    used = set(configured_tiles(selected))
    if isinstance(slot, int) and 0 <= slot < 4:
        used.discard(configured_tiles(selected)[slot])
    allowed = set(visible_tabs)
    return tuple((key, icon, title) for key, icon, title in NAVIGATION
                 if key in allowed and key not in used and key in TOOL_DESCRIPTIONS)


def search_items(data, command_library, query, visible_tabs, limit=4):
    """Pure, bounded local search across tools, saved notes/links and CLI.

    No app state is changed and no web or network operations occur. Returning a
    hit navigates to its existing editor rather than silently opening a URL or
    executing a command.
    """
    text = ch.normalize(query)
    if not text:
        return []
    allowed = set(visible_tabs)
    results = []
    for key, _icon, name in NAVIGATION:
        if key in ("home",) or (key != "settings" and key not in allowed):
            continue
        words = name + " " + PAGES[key][1] + " " + TOOL_DESCRIPTIONS.get(key, "")
        if text in ch.normalize(words):
            results.append({"kind": "tool", "destination": key, "id": key,
                            "title": name, "subtitle": "Open tool"})

    if "notes" in allowed:
        for note in data.get("notes", ()):
            if not isinstance(note, dict):
                continue
            title, body = note.get("title", ""), note.get("body", "")
            if isinstance(title, str) and isinstance(body, str) and (
                    text in ch.normalize(title) or text in ch.normalize(body)):
                results.append({"kind": "note", "destination": "notes",
                                "id": note.get("id"), "title": title or "Untitled note",
                                "subtitle": "Saved note"})
                if len(results) >= limit + 3:
                    break

    if "links" in allowed:
        for shortcut in data.get("links", ()):
            if not isinstance(shortcut, dict):
                continue
            title, url = shortcut.get("title", ""), shortcut.get("url", "")
            if isinstance(title, str) and isinstance(url, str) and (
                    text in ch.normalize(title) or text in ch.normalize(url)):
                results.append({"kind": "shortcut", "destination": "links",
                                "id": shortcut.get("id"), "title": title or "Shortcut",
                                "subtitle": "Saved shortcut"})
                if len(results) >= limit + 5:
                    break

    if "commands" in allowed:
        for command in ch.find_commands(command_library, query=text)[:limit]:
            results.append({"kind": "command", "destination": "commands",
                            "id": command["id"], "title": command["description"] or command["machine"],
                            "subtitle": command["machine"] + " · CLI",
                            "query": text})
    return results[:max(1, limit)]


def _label(parent, text, *, bg, fg, size=9, bold=False, **kwargs):
    return tk.Label(parent, text=text, bg=bg, fg=fg,
                    font=("Segoe UI", size, "bold" if bold else "normal"), **kwargs)


def _show_tools(app, widget):
    """All available tools are reachable, even though only four are featured."""
    c = app._compact_colors
    menu = tk.Menu(app.root, tearoff=False, bg=c["PANEL"], fg=c["WHITE"],
                   activebackground=c["ACCENT_DARK"], activeforeground=c["WHITE"],
                   bd=1, relief="flat")
    for key, icon, name in visible_navigation(app.settings["visible_tabs"]):
        if key == "home":
            continue
        if key == "settings":
            menu.add_separator()
        menu.add_command(label=name, command=lambda dest=key:
                         app._open_compact_tool(dest))
    try:
        menu.tk_popup(widget.winfo_rootx() + widget.winfo_width() - 115,
                      widget.winfo_rooty() - 7)
    finally:
        menu.grab_release()


def _launch_hit(app, result):
    """Open the matching item in the existing, fully functional Mini tool."""
    app._open_compact_tool(result["destination"], result)


def _tile(parent, app, c, index, key, editing, remove_action, picker_action):
    """Always render one of four stable slots, including an actionable +."""
    tile = tk.Frame(parent, width=68, height=102, bg=c["PANEL"],
                    highlightbackground=c["BORDER"], highlightthickness=1,
                    takefocus=1)
    tile.grid(row=0, column=index, padx=(0, 5) if index < 3 else 0,
              sticky="nsew")
    tile.grid_propagate(False)
    if key is None:
        add = tk.Button(tile, text="+", command=lambda: picker_action(index),
                        bg=c["CARD"], fg=c["ACCENT"], activebackground=c["ACCENT_DARK"],
                        activeforeground=c["WHITE"], relief="flat", bd=0,
                        cursor="hand2", font=("Segoe UI", 21), padx=0, pady=0)
        add.pack(fill="x", padx=7, pady=(13, 7))
        design.Tooltip(add, "Choose an enabled tool for this empty slot", app.theme)
        _label(tile, "Add tool", bg=c["PANEL"], fg=c["SECONDARY"],
               size=8).pack()
        return tile

    icon = next(row[1] for row in NAVIGATION if row[0] == key)
    title = next(row[2] for row in NAVIGATION if row[0] == key)
    accent = ICON_COLORS.get(key, c["ACCENT"])
    glyph = _label(tile, icon, bg=c["CARD"], fg=accent, size=16, bold=True,
                   padx=8, pady=2, cursor="hand2" if not editing else "arrow")
    glyph.pack(pady=(13 if editing else 7, 5))
    label = _label(tile, "Subnet" if key == "subnet" else title,
                   bg=c["PANEL"], fg=c["WHITE"], size=8, bold=True,
                   cursor="hand2" if not editing else "arrow", anchor="center")
    label.pack(fill="x")
    detail = _label(tile, TOOL_DESCRIPTIONS[key],
                    bg=c["PANEL"], fg=c["MUTED"], size=7, wraplength=66,
                    justify="center", cursor="hand2" if not editing else "arrow")
    detail.pack(fill="x", padx=1, pady=(3, 0))

    design.Tooltip(tile, f"{title} · {PAGES[key][1]}", app.theme)
    if editing:
        remove = tk.Button(tile, text="×", command=lambda: remove_action(index),
                           bg=c["ACCENT_DARK"], fg=c["DANGER"],
                           activebackground=c["CARD_HOVER"],
                           activeforeground=c["WHITE"], font=("Segoe UI", 10, "bold"),
                           relief="flat", bd=0, highlightthickness=0, cursor="hand2",
                           padx=0, pady=0)
        remove.place(relx=1.0, x=-2, y=2, anchor="ne", width=20, height=20)
        design.Tooltip(remove, f"Remove {title} from this slot · does not delete data", app.theme)
    else:
        widgets = (tile, glyph, label, detail)
        def hover(active):
            bg = c["CARD_HOVER"] if active else c["PANEL"]
            tile.configure(bg=bg)
            label.configure(bg=bg)
            detail.configure(bg=bg)
        tile.bind("<Return>", lambda _event, dest=key: app._open_compact_tool(dest))
        tile.bind("<space>", lambda _event, dest=key: app._open_compact_tool(dest))
        for target in widgets:
            target.configure(cursor="hand2")
            target.bind("<Button-1>", lambda _event, dest=key: app._open_compact_tool(dest))
            target.bind("<Enter>", lambda _event: hover(True))
            target.bind("<Leave>", lambda _event: hover(False))
    return tile


def focus_search(app):
    """Local Ctrl+K shortcut works only when launcher is currently visible."""
    if app.display_mode == "compact" and app.current_tab == "home":
        entry = getattr(app, "compact_search_entry", None)
        if entry is not None and entry.winfo_exists():
            entry.focus_set()
            return "break"
    return None


def build_shell(app, colors):
    """Construct the screenshot-inspired 322x256 floating tray launcher."""
    c = dict(colors)
    app._compact_colors = c
    app.tab_buttons = {}  # The full tool menu is available via All tools.
    outer = tk.Frame(app.root, bg=c["BG"], highlightthickness=1,
                     highlightbackground=c["BORDER"], bd=0)
    outer.pack(fill="both", expand=True)

    header = tk.Frame(outer, bg=c["BG"], height=36, cursor="fleur")
    header.pack(fill="x", padx=10, pady=(6, 2))
    header.pack_propagate(False)
    app._header_photo = tk.PhotoImage(
        file=str(app.theme_icons[app.theme]["png"])).subsample(23, 23)
    icon = tk.Label(header, image=app._header_photo, bg=c["BG"], cursor="hand2")
    icon.pack(side="left", padx=(0, 7))
    app.header_icon = icon
    icon.bind("<Button-1>", app._show_theme_menu)
    icon.bind("<Button-3>", app._show_theme_menu)
    name = _label(header, "Pocket", bg=c["BG"], fg=c["WHITE"], bold=True,
                  size=12, cursor="fleur")
    name.pack(side="left", fill="y")
    for widget in (header, name):
        widget.bind("<ButtonPress-1>", app._begin_window_drag)
        widget.bind("<B1-Motion>", app._continue_window_drag)
        widget.bind("<ButtonRelease-1>", app._finish_window_drag)
        widget.bind("<Button-3>", app._show_header_menu)
    for symbol, action in (("×", app.hide), ("↗", app._expand_from_extra_mini)):
        button = tk.Button(header, text=symbol, command=action, relief="flat", bd=0,
                           bg=c["BG"], fg=c["MUTED"], activebackground=c["CARD"],
                           activeforeground=c["WHITE"], cursor="hand2",
                           font=("Segoe UI", 11), padx=5, pady=0,
                           highlightthickness=0)
        button.pack(side="right", padx=(1, 0))
    app.pin_button = tk.Label(header, text="PINNED" if app.pinned else "PIN",
                              bg=c["ACCENT_DARK"] if app.pinned else c["BG"],
                              fg=c["ACCENT"] if app.pinned else c["MUTED"],
                              font=("Segoe UI", 7), cursor="hand2", padx=3)
    app.pin_button.pack(side="right", padx=(0, 5))
    app.pin_button.bind("<Button-1>", lambda _event: app.toggle_pin())
    # Hotkey customization updates this label in settings; no extra top bar.
    app.shortcut_hint = _label(header, app._hotkey_hint(), bg=c["BG"], fg=c["MUTED"])

    search = tk.Frame(outer, bg=c["INPUT"], highlightbackground=c["BORDER"],
                      highlightthickness=1, height=32)
    search.pack(fill="x", padx=10, pady=(3, 8))
    search.pack_propagate(False)
    tool_icons.label(search, "commands", c["SECONDARY"], c["INPUT"], size=18).pack(
        side="left", padx=(7, 4))
    app.compact_query = tk.StringVar()
    entry = tk.Entry(search, textvariable=app.compact_query, font=("Segoe UI", 8),
                     bg=c["INPUT"], fg=c["WHITE"], insertbackground=c["WHITE"],
                     relief="flat", bd=0, highlightthickness=0)
    entry.pack(side="left", fill="both", expand=True)
    app.compact_search_entry = entry
    app.compact_placeholder = "Search tools, notes, commands..."
    entry.insert(0, app.compact_placeholder)
    app.compact_placeholder_active = True
    def enter_focus(_event=None):
        if app.compact_placeholder_active:
            app.compact_placeholder_active = False
            entry.delete(0, tk.END)
    def leave_focus(_event=None):
        if not entry.get():
            app.compact_placeholder_active = True
            entry.insert(0, app.compact_placeholder)
    entry.bind("<FocusIn>", enter_focus)
    entry.bind("<FocusOut>", leave_focus)
    hint = _label(search, "Ctrl+K", bg=c["CARD"], fg=c["MUTED"],
                  size=7, padx=4, pady=2, cursor="hand2")
    hint.pack(side="right", padx=(3, 5))
    hint.bind("<Button-1>", lambda _event: entry.focus_set())

    area = tk.Frame(outer, bg=c["BG"], height=106)
    area.pack(fill="x", padx=10)
    area.pack_propagate(False)
    cards = tk.Frame(area, bg=c["BG"])
    cards.pack(fill="both", expand=True)
    app.compact_cards = cards

    extra.install_cards(app, cards, c)
    render_cards = app.compact_render_cards
    results = tk.Frame(area, bg=c["BG"])
    app.compact_results = results
    app.compact_matches = []
    app.compact_match_index = 0

    def render_results(*_args):
        query = "" if app.compact_placeholder_active else entry.get().strip()
        if query and getattr(app, "_compact_editing", False):
            app._compact_editing = False
            render_cards()
            if getattr(app, "compact_edit_button", None) is not None:
                app.compact_edit_button.configure(text="Edit")
        if not query:
            results.pack_forget()
            cards.pack(fill="both", expand=True)
            app.compact_matches = []
            return
        cards.pack_forget()
        results.pack(fill="both", expand=True)
        for child in results.winfo_children():
            child.destroy()
        matches = search_items(app.data, app.command_library, query,
                               app.settings["visible_tabs"], limit=4)
        app.compact_matches = matches
        app.compact_match_index = 0
        if not matches:
            _label(results, "No local matches. Try All tools.",
                   bg=c["BG"], fg=c["MUTED"], size=9).pack(anchor="w", pady=10)
        for index, hit in enumerate(matches):
            caption = f"{hit['title'][:30]}   ·   {hit['subtitle'][:18]}"
            action = tk.Button(results, text=caption, anchor="w", relief="flat",
                               bd=0, bg=c["ACCENT_DARK"] if index == 0 else c["PANEL"],
                               fg=c["WHITE"], activebackground=c["CARD_HOVER"],
                               activeforeground=c["WHITE"], padx=9, pady=3,
                               cursor="hand2", font=("Segoe UI", 8),
                               command=lambda item=hit: _launch_hit(app, item))
            action.pack(fill="x", pady=(0, 2))
        app.compact_result_buttons = results.winfo_children()

    def select_step(delta):
        matches = app.compact_matches
        if not matches:
            return "break"
        app.compact_match_index = (app.compact_match_index + delta) % len(matches)
        for i, button in enumerate(app.compact_result_buttons):
            button.configure(bg=c["ACCENT_DARK"] if i == app.compact_match_index else c["PANEL"])
        return "break"

    def accept(_event=None):
        if app.compact_matches:
            _launch_hit(app, app.compact_matches[app.compact_match_index])
        return "break"

    def clear(_event=None):
        if app.compact_placeholder_active:
            app.hide()
        elif entry.get():
            entry.delete(0, tk.END)
        else:
            leave_focus()
        return "break"

    entry.bind("<Return>", accept)
    entry.bind("<Down>", lambda _e: select_step(1))
    entry.bind("<Up>", lambda _e: select_step(-1))
    entry.bind("<Escape>", clear)
    app.compact_query.trace_add("write", render_results)

    tk.Frame(outer, bg=c["BORDER"], height=1).pack(
        fill="x", padx=10, pady=(4, 0))
    footer = tk.Frame(outer, bg=c["BG"], height=41)
    footer.pack(fill="x", padx=11, pady=(4, 4))
    footer.pack_propagate(False)
    extra.install_pager(app, footer, c)
    app.compact_status = _label(footer, "", bg=c["BG"], fg=c["MUTED"],
                                size=7, anchor="w")
    app.compact_status.pack(side="left", fill="y", padx=(1, 0))
    app.compact_status.bind("<Button-3>", lambda _e: app.compact_rename_page())
    app.compact_status.bind("<Button-1>", lambda _e:
                            app.compact_rename_page() if app._compact_editing else None)
    design.Tooltip(app.compact_status, "Right-click, or click while editing, to rename page", app.theme)
    all_button = tk.Button(footer, text="All tools ▾", relief="flat", bd=0,
                           bg=c["CARD"], fg=c["ACCENT"], activebackground=c["CARD_HOVER"],
                           activeforeground=c["WHITE"], padx=7, pady=5,
                           cursor="hand2", highlightthickness=0, font=("Segoe UI", 8))
    all_button.configure(command=lambda: _show_tools(app, all_button))
    all_button.pack(side="right")
    def toggle_edit():
        app._compact_editing = not bool(getattr(app, "_compact_editing", False))
        if app._compact_editing:
            app.compact_placeholder_active = True
            entry.delete(0, tk.END)
            entry.insert(0, app.compact_placeholder)
            results.pack_forget()
            cards.pack(fill="both", expand=True)
        edit_btn.configure(text="Done" if app._compact_editing else "Edit")
        render_cards()
    edit_btn = tk.Button(
        footer, text="Done" if getattr(app, "_compact_editing", False) else "Edit",
        command=toggle_edit, relief="flat", bd=0, bg=c["ACCENT_DARK"],
        fg=c["ACCENT"], activebackground=c["CARD_HOVER"],
        activeforeground=c["WHITE"], padx=7, pady=5,
        cursor="hand2", highlightthickness=0, font=("Segoe UI", 8, "bold"))
    edit_btn.pack(side="right", padx=(0, 6))
    add_action = tk.Button(footer, text="+", command=app.compact_add_next,
                           bg=c["CARD"], fg=c["ACCENT"], relief="flat", bd=0,
                           font=("Segoe UI", 10, "bold"), cursor="hand2", padx=5)
    add_action.pack(side="right", padx=(0, 5))
    design.Tooltip(add_action, "Add an action; a new page appears when needed", app.theme)
    design.Tooltip(edit_btn, "Arrange or edit quick actions", app.theme)
    design.Tooltip(all_button, "Access every enabled Pocket tool", app.theme)
    app.compact_edit_button = edit_btn
    render_cards()
    if getattr(app, "_compact_editing", False):
        render_cards()
    app.body = tk.Frame(outer, bg=c["BG"])
    app._mini_root_body = app.body
    app.compact_render_results = render_results
    app.compact_handle_wheel = lambda event: extra.handle_wheel(app, event)


def style_nav(app, selected):
    """The tiny launcher has only Home; tool navigation expands into Mini."""
    return None


def build_home(app):
    """All home controls are built by build_shell and stay functional."""
    return None
