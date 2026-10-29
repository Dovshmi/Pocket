"""PocketDesk — a Windows tray-first notes and shortcuts dashboard.

Core app uses the Python standard library. Run with pythonw.exe on Windows for no console.
Use --preview to show the popup without the tray, for testing and screenshots.
"""

from __future__ import annotations

import ctypes
import ipaddress
from datetime import datetime, timezone, timedelta
import re
import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
import time
import uuid
import webbrowser
from urllib.parse import urlsplit
import shortcut_utils as shortcuts
import shortcut_drop
import tkinter as tk
from tkinter import messagebox, filedialog, ttk

import network_tools as net
import command_helper as ch
import command_store as cs
import subnet_calculator as subnet
import icon_themes as themes
import hotkey_settings as hk
import note_sync
import native_bidi

try:
    from tkinterdnd2 import DND_FILES, DND_TEXT, TkinterDnD
except ImportError:
    DND_FILES = DND_TEXT = None
    TkinterDnD = None

APP_NAME = "PocketDesk"
WIDTH, HEIGHT = 480, 850  # Unified popup height across every tab.
BG = "#11131A"
PANEL = "#1A1D27"
CARD = "#222635"
CARD_HOVER = "#2C3143"
INPUT = "#161923"
WHITE = "#F3F4FA"
SECONDARY = "#A2A8B9"
MUTED = "#737C90"
ACCENT = "#9EA6FF"
ACCENT_DARK = "#30375E"
BORDER = "#343848"
DANGER = "#F0899C"
FONT = "Segoe UI"


def data_file() -> Path:
    base = os.environ.get("APPDATA")
    if not base:
        base = str(Path.home() / ".local" / "share")
    return Path(base) / APP_NAME / "data.json"


def new_id() -> str:
    return uuid.uuid4().hex


def normalize_window_position(raw) -> dict | None:
    """Validate a user-moved window position; missing/invalid means tray default."""
    if not isinstance(raw, dict):
        return None
    x, y = raw.get("x"), raw.get("y")
    if type(x) is not int or type(y) is not int:
        return None
    # Guard against corrupt or malicious JSON giving impossible geometry.
    if abs(x) > 100000 or abs(y) > 100000:
        return None
    return {"x": x, "y": y}


def clamp_window_position(x: int, y: int, width: int, height: int,
                          work_area: tuple[int, int, int, int]) -> tuple[int, int]:
    """Keep the whole window inside its nearest monitor's usable work area."""
    left, top, right, bottom = work_area
    return (max(left, min(x, max(left, right - width))),
            max(top, min(y, max(top, bottom - height))))


def new_note(title="Untitled note", body="", phone="") -> dict:
    return {"id": new_id(), "title": title, "body": body, "phone": phone,
            "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "pinned": False, "direction": "ltr",
            "reminder_enabled": False, "reminder_at": "", "reminder_sent_at": ""}


def ordered_notes(notes: list[dict]) -> list[dict]:
    """Pinned notes first; preserve the original order within both groups."""
    return sorted(notes, key=lambda note: not (note.get("pinned") is True))


def duplicate_note(original: dict) -> dict:
    """Copy the content but use a fresh note ID and creation time. Pin is not inherited."""
    copy = new_note(f"{original.get('title', 'Untitled note')} (copy)",
                    original.get('body', ''), original.get('phone', ''))
    copy["direction"] = normalize_note_direction(original.get("direction"))
    return copy


def normalize_note_direction(value) -> str:
    """Existing notes remain left-aligned; only explicit RTL is accepted."""
    return "rtl" if value == "rtl" else "ltr"


def display_created_at(value: str) -> str:
    """Show genuine creation timestamps in local time; never invent legacy dates."""
    if not value:
        return "Created: unknown (older note)"
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            return "Created: unknown"
        return "Created: " + parsed.astimezone().strftime("%d %b %Y, %H:%M")
    except (ValueError, TypeError, OverflowError):
        return "Created: unknown"


def export_note_for_notepad(note: dict, output_dir: Path) -> Path:
    """Save a one-off UTF-8 copy of the selected note for Windows Notepad.

    A fresh snapshot avoids overwriting previous edits made in Notepad.
    Notepad snapshots do not synchronize edits back to the application's data.
    """
    title = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", note.get("title", "Note"))
    title = title.strip(" .")[:40] or "Note"
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"PocketDesk_{title}_{stamp}_{uuid.uuid4().hex[:8]}.txt"
    target = output_dir / filename
    with target.open("x", encoding="utf-8-sig", newline="") as stream:
        stream.write(note.get("body", ""))
    return target


def note_selection_ip(selected: str) -> str | None:
    """Return a literal selected IP, with no hostname resolution or network call."""
    selected = selected.strip()
    try:
        return str(ipaddress.ip_address(selected))
    except ValueError:
        return None


def note_command_query(selected: str) -> str:
    """Compact a selection for Commands search, avoiding accidental huge queries."""
    return " ".join(selected.split())[:250]


def new_link(title, url, kind="url") -> dict:
    return {"id": new_id(), "title": title, "url": url, "kind": kind}


def default_data() -> dict:
    n = new_note("Welcome", "Your notes live here.\n\nCreate another note with + New. Everything saves automatically.")
    return {
        "notes": [n],
        "active_note": n["id"],
        "links": [
            new_link("GitHub", "https://github.com"),
            new_link("YouTube", "https://www.youtube.com"),
            new_link("Gmail", "https://mail.google.com"),
        ],
        "command_state": ch.safe_prefs({}),
        "custom_commands": [],
        "subnet": {"ip": "192.168.1.10", "prefix": "24", "split": "/26"},
        "window_position": None,
        "settings": {"visible_tabs": ["notes","links","ports","mac","commands","subnet","clipboard"]},
        "theme": "blue",
        "hotkey": hk.DEFAULT_HOTKEY.copy(),
        "tools": {"target": "192.168.1.1", "single_port": "443", "custom_ports": "",
                  "selected_ports": [22, 80, 443, 3389], "mode": "single"},
    }


VISIBLE_TABS = (("notes", "NOTES"), ("links", "SHORTCUTS"), ("ports", "PORTS"),
                ("mac", "MAC"), ("commands", "COMMANDS"), ("subnet", "SUBNET"),
                ("clipboard", "CLIPBOARD"))


def normalize_settings(raw):
    raw = raw if isinstance(raw, dict) else {}
    selected = raw.get("visible_tabs", [key for key, _ in VISIBLE_TABS])
    allowed = {key for key, _ in VISIBLE_TABS}
    if not isinstance(selected, list):
        selected = list(allowed)
    visible = [key for key, _ in VISIBLE_TABS if key in selected]
    if not visible:
        visible = ["notes"]
    return {"visible_tabs": visible}


def parse_reminder_time(date_text, time_text, now=None):
    """Validate a future local time, stored with the local UTC offset."""
    try:
        scheduled = datetime.strptime(f"{date_text.strip()} {time_text.strip()}",
                                      "%Y-%m-%d %H:%M").astimezone()
    except (ValueError, AttributeError) as exc:
        raise ValueError("Use a valid date YYYY-MM-DD and time HH:MM.") from exc
    if scheduled <= (now or datetime.now().astimezone()):
        raise ValueError("Choose a future date and time.")
    return scheduled.isoformat(timespec="minutes")


def normalize_note_reminder(note):
    """Migrate previous note records without inventing reminder times."""
    raw = note.get("reminder_at")
    try:
        when = datetime.fromisoformat(raw) if isinstance(raw, str) and raw else None
    except ValueError:
        when = None
    valid = when is not None and when.tzinfo is not None
    note["reminder_at"] = raw if valid else ""
    note["reminder_enabled"] = valid and note.get("reminder_enabled") is True
    note["reminder_sent_at"] = (note.get("reminder_sent_at", "")
                                if isinstance(note.get("reminder_sent_at", ""), str) else "")
    return note


def reminder_is_due(note, now=None):
    if not note.get("reminder_enabled") or note.get("reminder_sent_at"):
        return False
    try:
        scheduled = datetime.fromisoformat(note["reminder_at"])
        return scheduled.tzinfo is not None and scheduled <= (now or datetime.now().astimezone())
    except (ValueError, TypeError, KeyError):
        return False


def format_reminder(note):
    if not note.get("reminder_enabled"):
        return "No reminder"
    try:
        when = datetime.fromisoformat(note["reminder_at"]).astimezone()
        return when.strftime("%d %b %Y · %H:%M") + (" · sent" if note.get("reminder_sent_at") else "")
    except (ValueError, TypeError, KeyError):
        return "No reminder"


def sanitize_clipboard(value):
    """Keep only reasonable text snippets, never empty or gigantic payloads."""
    if not isinstance(value, str) or not value.strip() or len(value) > 20000:
        return None
    return value


def clipboard_add(items, value, maximum=100):
    value = sanitize_clipboard(value)
    if value is None or (items and items[0]["text"] == value):
        return items
    items[:] = [item for item in items if item["text"] != value or item.get("pinned")]
    items.insert(0, {"id": uuid.uuid4().hex, "text": value, "pinned": False,
                     "time": datetime.now().strftime("%H:%M:%S")})
    while len(items) > maximum:
        victim = next((i for i in range(len(items)-1, -1, -1) if not items[i]["pinned"]), None)
        if victim is None:
            break
        items.pop(victim)
    return items


def load_data(path: Path) -> dict:
    if not path.exists():
        return default_data()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("Root must be a JSON object")
        notes = data.get("notes")
        links = data.get("links")
        if not isinstance(notes, list) or not isinstance(links, list):
            raise ValueError("Notes and links must be lists")
        notes = [n for n in notes if isinstance(n, dict) and all(isinstance(n.get(k), str) for k in ("id", "title", "body"))]
        # Older notes have no recorded creation time. Keep it unknown instead of
        # pretending that the migration/first load was when they were created.
        for note in notes:
            if not isinstance(note.get("phone"), str):
                note["phone"] = ""
            if not isinstance(note.get("created_at"), str):
                note["created_at"] = ""
            # Only genuine boolean values are accepted for the persisted flag.
            note["pinned"] = note.get("pinned") is True
            note["direction"] = normalize_note_direction(note.get("direction"))
            normalize_note_reminder(note)
        links = [l for l in links if isinstance(l, dict) and all(isinstance(l.get(k), str) for k in ("id", "title", "url"))]
        for link in links:
            if link.get("kind") not in shortcuts.VALID_KINDS:
                link["kind"] = "url"
        if not notes:
            notes = [new_note()]
        active_id = data.get("active_note")
        if active_id not in [n["id"] for n in notes]:
            active_id = notes[0]["id"]
        tools = data.get("tools")
        if not isinstance(tools, dict):
            tools = default_data()["tools"]
        subnet_pref = data.get("subnet")
        if not isinstance(subnet_pref, dict):
            subnet_pref = {}
        subnet_pref = {
            key: value if isinstance(value, str) and len(value) <= 64 else default
            for key, value, default in (
                ("ip", subnet_pref.get("ip"), "192.168.1.10"),
                ("prefix", subnet_pref.get("prefix"), "24"),
                ("split", subnet_pref.get("split"), "/26"))
        }
        return {"notes": notes, "active_note": active_id, "links": links,
                "tools": tools, "command_state": ch.safe_prefs(data.get("command_state")),
                "custom_commands": ch.safe_custom_commands(data.get("custom_commands")),
                "subnet": subnet_pref,
                "window_position": normalize_window_position(data.get("window_position")),
                "theme": themes.valid_theme(data.get("theme")),
                "settings": normalize_settings(data.get("settings")),
                "hotkey": hk.normalize_hotkey(data.get("hotkey"))}
    except (OSError, ValueError, TypeError):
        # Keep the damaged data available for manual recovery; don't silently overwrite it.
        backup = path.with_name(f"data-corrupt-{int(time.time())}.json")
        try:
            path.rename(backup)
        except OSError:
            pass
        return default_data()


def save_data(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    with temp.open("w", encoding="utf-8") as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temp, path)


def normalize_url(raw: str) -> str:
    """Compatibility alias used by the original tests and integrations."""
    return shortcuts.normalize_url(raw)


def action_label(parent, text, command, *, fg=WHITE, bg=CARD, hover=CARD_HOVER,
                 padx=13, pady=8, font_size=10, bold=True) -> tk.Label:
    label = tk.Label(parent, text=text, font=(FONT, font_size, "bold" if bold else "normal"),
                     fg=fg, bg=bg, padx=padx, pady=pady, cursor="hand2")
    label.bind("<Button-1>", lambda _e: command())
    label.bind("<Enter>", lambda _e: label.config(bg=hover))
    label.bind("<Leave>", lambda _e: label.config(bg=bg))
    return label


class PocketDesk:
    def __init__(self, *, preview=False):
        self.preview = preview
        self.path = data_file()
        self.data = load_data(self.path)
        self.settings = normalize_settings(self.data.get("settings"))
        self.data["settings"] = self.settings
        self.clipboard_items = []  # Session-only: never write copied text to disk.
        self._clipboard_last = None
        self._clipboard_job = None
        self.theme = themes.valid_theme(self.data.get("theme"))
        self._apply_palette(self.theme)
        self.theme_icons = themes.ensure_icons(self.path.parent / "icons")
        self.events = queue.Queue()
        self.hotkey = hk.normalize_hotkey(self.data.get("hotkey"))
        self.hotkey_available = True
        self.tray = None
        self._save_job = None
        self._loading_note = False
        self._notepad_sessions = {}  # Per-note working files; not persisted in data.json.
        self._bidi_editor_active = False
        self._modal = False
        self.pinned = False
        self.current_tab = "notes"
        self._last_tray_xy = None
        self._dragging_window = False
        self._drag_moved = False
        self._drag_origin = None
        self._header_context_menu = None
        self.edit_link_id = None
        self._scroll_canvas = None
        self.vendor_file = self.path.parent / "vendors.json"
        self.vendors, self.vendor_date = net.load_vendor_database(self.vendor_file)
        self.mac_results = []
        self.mac_draft = "00:00:0C:12:34:56\n00-1B-63-12-34-56\nAABB.CCDD.EEFF"
        self.port_results = []
        self.scanning = False
        self.scan_token = 0
        self.scan_cancel = threading.Event()
        self.updating_vendors = False
        self.port_inputs_expanded = True
        # One writable library; the EXE's bundled copy is only a seed.
        install = (Path(sys.executable).resolve().parent if getattr(sys, "frozen", False)
                   else Path(__file__).resolve().parent)
        self.commands_error = None
        try:
            self.commands_file = cs.resolve_library(install, self.path.parent,
                                                     self.bundle_path())
            cs.read_document(self.commands_file)
            if self.data["custom_commands"]:
                cs.migrate_custom(self.commands_file, self.data["custom_commands"])
                # Keep the old copies until data.json is successfully saved.
                self.data["custom_commands"] = []
                save_data(self.path, self.data)
        except (OSError, ValueError) as exc:
            self.commands_error = str(exc)
            self.commands_file = None
        self.bundled_commands = ch.load_library(self.commands_file) if self.commands_file else []
        self.machine_catalog = ch.load_machine_names(self.commands_file) if self.commands_file else []
        self.command_library = ch.merged_commands(self.bundled_commands, self.data["custom_commands"])
        self.command_filtered = []
        self.selected_command_id = None
        self.command_mode = "all"
        self.command_draft_id = None
        self._note_rows = []
        self.subnet_details = None
        self.subnet_children = []

        # tkinterdnd2 supports native Windows Explorer and browser drops.
        # The app still opens if the optional dependency has not been installed.
        self.dnd_available = False
        if TkinterDnD is not None:
            try:
                self.root = TkinterDnD.Tk()
                self.dnd_available = True
            except (tk.TclError, RuntimeError):
                self.root = tk.Tk()
        else:
            self.root = tk.Tk()
        self.root.title("Pocket")
        self.root.configure(bg=BG)
        self.root.geometry(f"{WIDTH}x{HEIGHT}")
        self.root.resizable(False, False)
        self.root.protocol("WM_DELETE_WINDOW", self.hide)
        if not preview:
            self.root.overrideredirect(True)
            self.root.attributes("-topmost", True)
        try:
            self.root.iconbitmap(str(self.theme_icons[self.theme]["ico"]))
        except (tk.TclError, OSError):
            pass
        self._build_shell()
        self.show_tab("notes")
        self.root.bind("<Control-n>", lambda _e: self.add_note())
        self.root.bind("<Control-s>", lambda _e: self._write_now())
        self.root.bind("<Escape>", lambda _e: self.hide())
        self.root.bind("<FocusOut>", self._focus_lost)
        self.root.after(120, self._poll_events)
        self.root.after(650, self._clipboard_poll)
        self.root.after(2500, self._reminder_poll)
        self.root.after(1200, self._notepad_poll)
        self.root.after(350, self._bidi_poll)
        if not preview and sys.platform == "win32":
            self.root.withdraw()
            self.tray = WindowsTray(self.theme_icons[self.theme]["ico"], self.events, self.hotkey)
            self.tray.start()
            self.root.after(250, self._check_tray)
        else:
            self.root.after(50, lambda: self._place_popup(None))

    @staticmethod
    def bundle_path(*parts):
        return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent)).joinpath(*parts)

    @staticmethod
    def asset_path(name):
        return PocketDesk.bundle_path("assets", name)

    @staticmethod
    def _apply_palette(name):
        colors = themes.palette(name)
        globals().update(colors)
        action_label.__kwdefaults__.update(fg=colors["WHITE"], bg=colors["CARD"], hover=colors["CARD_HOVER"])

    def _choose_theme(self, name):
        name = themes.valid_theme(name)
        if name == self.theme:
            return
        self._flush_current_note()
        self.theme = name
        self.data["theme"] = name
        self._apply_palette(name)
        self.root.configure(bg=BG)
        try:
            self.root.iconbitmap(str(self.theme_icons[name]["ico"]))
        except (tk.TclError, OSError):
            pass
        if self.tray:
            self.tray.set_icon(self.theme_icons[name]["ico"])
        for child in self.root.winfo_children():
            child.destroy()
        self._header_context_menu = None
        self._build_shell()
        self.show_tab(self.current_tab)
        self._write_now()

    def _show_theme_menu(self, event=None):
        menu = tk.Menu(self.root, tearoff=False, bg=PANEL, fg=WHITE,
                       activebackground=ACCENT_DARK, activeforeground=WHITE)
        for key in themes.THEME_ORDER:
            menu.add_command(label=("● " if key == self.theme else "    ") + themes.THEMES[key]["name"],
                             command=lambda chosen=key: self.root.after_idle(self._choose_theme, chosen))
        self._modal = True
        try:
            x = event.x_root if event else self.header_icon.winfo_rootx()
            y = event.y_root if event else self.header_icon.winfo_rooty()+self.header_icon.winfo_height()
            menu.tk_popup(x, y)
        finally:
            menu.grab_release()
            self._modal = False

    def _hotkey_hint(self):
        return hk.hotkey_label(self.hotkey) + "  ·  Show / hide  ✎"

    def _open_hotkey_picker(self, _event=None):
        if getattr(self, "_hotkey_picker", None) and self._hotkey_picker.winfo_exists():
            self._hotkey_picker.lift()
            return "break"
        self._modal = True
        dialog = tk.Toplevel(self.root)
        self._hotkey_picker = dialog
        dialog.title("Pocket · Popup shortcut")
        dialog.configure(bg=BG)
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.geometry(f"390x425+{self.root.winfo_x()+30}+{self.root.winfo_y()+90}")
        selected = self.hotkey.copy()
        flags = {key: tk.BooleanVar(value=selected[key]) for key in ("ctrl","shift","alt","win")}
        key_var = tk.StringVar(value=selected["key"])
        tk.Label(dialog, text="Choose a popup shortcut", font=(FONT, 14, "bold"),
                 fg=WHITE, bg=BG).pack(anchor="w", padx=18, pady=(18, 4))
        tk.Label(dialog, text="Choose modifiers and click a key below.",
                 fg=MUTED, bg=BG).pack(anchor="w", padx=18)
        mods = tk.Frame(dialog, bg=BG)
        mods.pack(fill="x", padx=16, pady=(14, 8))
        for key, label in (("ctrl","Ctrl"),("shift","Shift"),("alt","Alt"),("win","Win")):
            tk.Checkbutton(mods, text=label, variable=flags[key], bg=BG, fg=WHITE,
                           activebackground=BG, activeforeground=ACCENT, selectcolor=PANEL,
                           font=(FONT, 9)).pack(side="left")
        keys = tk.Frame(dialog, bg=BG)
        keys.pack(fill="both", expand=True, padx=15)
        options = ("*", "P", "K", "N", "Space", "F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8", "F9", "F10", "F11", "F12")
        options = tuple(k for k in options if k in hk.KEYS)
        buttons = {}
        def select(key):
            key_var.set(key)
            for name, button in buttons.items():
                button.config(bg=ACCENT_DARK if name == key else CARD,
                              fg=ACCENT if name == key else WHITE)
        for i, key in enumerate(options):
            button = tk.Button(keys, text=key, command=lambda k=key: select(k),
                               bg=CARD, fg=WHITE, relief="flat", width=5, cursor="hand2")
            button.grid(row=i//6, column=i%6, padx=3, pady=4, sticky="ew")
            buttons[key] = button
        select(key_var.get())
        tk.Label(dialog, text="For another letter or digit, click a key below:",
                 fg=MUTED, bg=BG, font=(FONT, 8)).pack(anchor="w", padx=18)
        letters = tk.Frame(dialog, bg=BG)
        letters.pack(fill="x", padx=18, pady=(2, 4))
        key_choices = ttk.Combobox(letters, values=hk.KEYS, state="readonly",
                                   textvariable=key_var, width=8)
        key_choices.pack(side="left")
        status = tk.Label(dialog, text="", fg=DANGER, bg=BG, font=(FONT, 8))
        status.pack(anchor="w", padx=18)
        actions = tk.Frame(dialog, bg=BG)
        actions.pack(fill="x", padx=18, pady=(6, 14))
        def close():
            self._modal = False
            dialog.destroy()
        def save():
            candidate = {name: var.get() for name,var in flags.items()}
            candidate["key"] = key_var.get()
            if not (candidate["ctrl"] or candidate["alt"] or candidate["win"]):
                status.config(text="Select Ctrl, Alt or Win to avoid bare global keys.")
                return
            if candidate == self.hotkey:
                close()
                return
            if self.tray and not self.tray.error:
                # Windows registration is checked by the tray thread first.
                self.tray.set_hotkey(candidate)
                status.config(text="Applying shortcut…", fg=ACCENT)
                close()
            else:
                self.hotkey = candidate
                self.data["hotkey"] = candidate.copy()
                self.shortcut_hint.config(text=self._hotkey_hint(), fg=MUTED)
                self._write_now()
                close()
        tk.Button(actions, text="Cancel", command=close, bg=CARD, fg=WHITE,
                  relief="flat", padx=12).pack(side="right")
        tk.Button(actions, text="Save shortcut", command=save, bg=ACCENT, fg="#10131C",
                  relief="flat", padx=12).pack(side="right", padx=(0,8))
        dialog.protocol("WM_DELETE_WINDOW", close)
        dialog.grab_set()
        return "break"

    def _build_shell(self):
        outer = tk.Frame(self.root, bg=BG, highlightthickness=1, highlightbackground=BORDER)
        outer.pack(fill="both", expand=True)
        header = tk.Frame(outer, bg=BG, height=77, cursor="fleur")
        header.pack(fill="x", padx=20, pady=(15, 10))
        header.pack_propagate(False)
        self._header_photo = tk.PhotoImage(file=str(self.theme_icons[self.theme]["png"])).subsample(10, 10)
        icon = tk.Label(header, image=self._header_photo, bg=BG, cursor="hand2")
        self.header_icon = icon
        icon.bind("<Button-1>", self._show_theme_menu)
        icon.bind("<Button-3>", self._show_theme_menu)
        icon.pack(side="left", padx=(0, 12))
        labels = tk.Frame(header, bg=BG, cursor="fleur")
        labels.pack(side="left", fill="y", expand=True)
        app_title = tk.Label(labels, text="Pocket", font=(FONT, 19, "bold"), fg=WHITE,
                             bg=BG, anchor="w", cursor="fleur")
        app_title.pack(anchor="w", pady=(2, 0))
        self.shortcut_hint = tk.Label(labels, text=self._hotkey_hint(),
                                      font=(FONT, 9), fg=MUTED, bg=BG, cursor="fleur")
        self.shortcut_hint.pack(anchor="w", pady=(1, 0))
        # Dragging on the header behaves like a regular title bar. The PIN and
        # close controls are intentionally excluded so their clicks work normally.
        self.shortcut_hint.config(cursor="hand2")
        self.shortcut_hint.bind("<Button-1>", self._open_hotkey_picker)
        for handle in (header, labels, app_title):
            handle.bind("<ButtonPress-1>", self._begin_window_drag)
            handle.bind("<B1-Motion>", self._continue_window_drag)
            handle.bind("<ButtonRelease-1>", self._finish_window_drag)
            handle.bind("<Button-3>", self._show_header_menu)
        self.pin_button = action_label(header, "PIN", self.toggle_pin, fg=SECONDARY, bg=PANEL,
                                       padx=10, pady=7, font_size=8)
        self.pin_button.pack(side="right", padx=(5, 0), anchor="n", pady=(5, 0))
        action_label(header, "×", self.hide, fg=MUTED, bg=BG, hover=PANEL,
                     padx=8, pady=2, font_size=17).pack(side="right", anchor="n", pady=(4, 0))

        tabs = tk.Frame(outer, bg=BG, height=42)
        tabs.pack(fill="x", padx=20)
        tabs.pack_propagate(False)
        self.tab_buttons = {}
        # Settings remains accessible even if all regular tabs are hidden.
        for key, label in VISIBLE_TABS:
            if key not in self.settings["visible_tabs"]:
                continue
            if len(self.tab_buttons) >= 5:
                break

            button = action_label(tabs, label, lambda k=key: self.show_tab(k),
                                  bg=BG, hover=PANEL, fg=SECONDARY, padx=5, pady=8, font_size=8)
            button.pack(side="left", padx=(0, 2))
            self.tab_buttons[key] = button
        extras = [pair for pair in VISIBLE_TABS
                  if pair[0] in self.settings["visible_tabs"] and pair[0] not in self.tab_buttons]
        if extras:
            action_label(tabs, "MORE ▾", self._show_more_menu, bg=BG,
                         hover=PANEL, fg=SECONDARY, padx=4, pady=8, font_size=8).pack(side="left")
        action_label(tabs, "⚙", lambda: self.show_tab("settings"), bg=BG,
                     hover=PANEL, fg=ACCENT, padx=5, pady=8, font_size=11).pack(side="right")
        tk.Frame(outer, height=1, bg=BORDER).pack(fill="x")

        self.body = tk.Frame(outer, bg=BG)
        self.body.pack(fill="both", expand=True, padx=17, pady=(17, 8))
        # No shared footer: its former Notepad action lives in the Notes editor.
        # The reclaimed height gives the Notes body and Shortcuts list more room.

    def show_tab(self, which):
        self._flush_current_note()
        if self.current_tab == "mac" and hasattr(self, "mac_input") and self.mac_input.winfo_exists():
            self.mac_draft = self.mac_input.get("1.0", "end-1c")
        if which not in self.settings["visible_tabs"] and which != "settings":
            which = "settings"
        self.current_tab = which
        for child in self.body.winfo_children():
            child.destroy()
        for key, button in self.tab_buttons.items():
            button.config(fg=ACCENT if key == which else SECONDARY,
                          bg=ACCENT_DARK if key == which else BG)
        if which == "notes":
            self._build_notes()
        elif which == "links":
            self._build_links()
        elif which == "ports":
            self._build_ports()
        elif which == "mac":
            self._build_mac()
        elif which == "commands":
            self._build_commands()
        elif which == "subnet":
            self._build_subnet()
        elif which == "clipboard":
            self._build_clipboard()
        elif which == "settings":
            self._build_settings()
        # Preserve a user-moved position when changing tabs.
        self._place_popup(self._last_tray_xy)

    def _show_more_menu(self):
        menu = tk.Menu(self.root, tearoff=False, bg=PANEL, fg=WHITE,
                       activebackground=ACCENT_DARK, activeforeground=WHITE)
        for key, label in VISIBLE_TABS:
            if key in self.settings["visible_tabs"] and key not in self.tab_buttons:
                menu.add_command(label=label, command=lambda k=key: self.show_tab(k))
        menu.tk_popup(self.root.winfo_rootx()+165, self.root.winfo_rooty()+132)

    def _set_visible_tab(self, key, enabled):
        current = self.settings["visible_tabs"]
        if enabled and key not in current:
            current.append(key)
        elif not enabled and key in current:
            if len(current) == 1:
                self._warning("Menus", "At least one tool must remain visible.")
                self._build_settings_refresh()
                return
            current.remove(key)
        if key == "clipboard":
            self._clipboard_last = None
        self._build_shell_refresh()
        self.schedule_save()

    def _build_shell_refresh(self):
        for child in self.root.winfo_children():
            child.destroy()
        self._header_context_menu = None
        self._build_shell()
        self.show_tab(self.current_tab)

    def _build_settings_refresh(self):
        self.show_tab("settings")

    def _build_settings(self):
        tk.Label(self.body, text="Settings", font=(FONT, 16, "bold"),
                 bg=BG, fg=WHITE).pack(anchor="w")
        tk.Label(self.body, text="Choose which tools appear in Pocket",
                 bg=BG, fg=MUTED, font=(FONT, 9)).pack(anchor="w", pady=(3, 18))
        tk.Label(self.body, text="VISIBLE MENUS", bg=BG, fg=SECONDARY,
                 font=(FONT, 9, "bold")).pack(anchor="w", pady=(6, 10))
        for key, label in VISIBLE_TABS:
            value = tk.BooleanVar(value=key in self.settings["visible_tabs"])
            tk.Checkbutton(self.body, text=label.title(), variable=value,
                           bg=BG, fg=WHITE, activebackground=BG,
                           activeforeground=WHITE, selectcolor=PANEL,
                           command=lambda k=key,v=value:self._set_visible_tab(k,v.get())
                           ).pack(anchor="w", pady=5)
        tk.Label(self.body,
                 text="Clipboard monitoring is automatic whenever Clipboard is visible. "
                      "Hide that menu to stop capturing new copied text.",
                 bg=BG, fg=MUTED, font=(FONT, 9), wraplength=415,
                 justify="left").pack(anchor="w", pady=(18, 8))
        tk.Label(self.body,
                 text="Notifications are scheduled for individual notes. "
                      "They appear while Pocket runs in the system tray.",
                 bg=BG, fg=MUTED, font=(FONT, 9), wraplength=415,
                 justify="left").pack(anchor="w", pady=8)

    def _clipboard_poll(self):
        if "clipboard" in self.settings["visible_tabs"]:
            try:
                value = self.root.clipboard_get()
                if isinstance(value, str) and value != self._clipboard_last:
                    self._clipboard_last = value
                    before = len(self.clipboard_items)
                    clipboard_add(self.clipboard_items, value)
                    if self.current_tab == "clipboard" and (len(self.clipboard_items) != before or self.clipboard_items):
                        self._refresh_clipboard()
            except (tk.TclError, RuntimeError):
                pass
        self._clipboard_job = self.root.after(600, self._clipboard_poll)

    def _build_clipboard(self):
        self._section_title(self.body, "Clipboard history", "Session-only text · Never saved to disk",
                            "Clear all", self._clear_clipboard)
        self.clipboard_query = tk.StringVar()
        entry = self._entry(self.body, self.clipboard_query)
        entry.pack(fill="x", ipady=9, pady=(0, 9))
        self.clipboard_query.trace_add("write", lambda *_:self._refresh_clipboard())
        self.clipboard_status = tk.Label(self.body, text="", bg=BG, fg=MUTED, font=(FONT, 9))
        self.clipboard_status.pack(anchor="w")
        frame = tk.Frame(self.body, bg=BG)
        frame.pack(fill="both", expand=True, pady=8)
        self.clipboard_list = tk.Listbox(frame, bg=PANEL, fg=WHITE, selectbackground=ACCENT_DARK,
                                        font=(FONT, 10), bd=0, exportselection=False)
        self.clipboard_list.pack(fill="both", expand=True)
        self.clipboard_list.bind("<Double-1>", lambda _e:self._copy_clipboard_item())
        actions = tk.Frame(self.body, bg=BG)
        actions.pack(fill="x")
        for title, callback in (("Copy selected", self._copy_clipboard_item),
                                ("Pin / Unpin", self._pin_clipboard_item),
                                ("Delete", self._delete_clipboard_item)):
            action_label(actions, title, callback, fg=ACCENT, bg=PANEL,
                         font_size=8, padx=8).pack(side="left", padx=(0, 5))
        self._refresh_clipboard()

    def _refresh_clipboard(self):
        if not hasattr(self, "clipboard_list") or not self.clipboard_list.winfo_exists():
            return
        query = self.clipboard_query.get().casefold()
        self._clipboard_filtered = [item for item in self.clipboard_items if query in item["text"].casefold()]
        self.clipboard_list.delete(0, tk.END)
        for item in self._clipboard_filtered:
            preview = " ".join(item["text"].split())[:65]
            self.clipboard_list.insert(tk.END, ("★ " if item["pinned"] else "   ") + preview)
        self.clipboard_status.config(text=f"{len(self._clipboard_filtered)} entries · capture " +
                                     ("ON" if "clipboard" in self.settings["visible_tabs"] else "OFF"))

    def _selected_clipboard_item(self):
        if not hasattr(self, "clipboard_list"):
            return None
        selection = self.clipboard_list.curselection()
        return self._clipboard_filtered[selection[0]] if selection else None

    def _copy_clipboard_item(self):
        item = self._selected_clipboard_item()
        if item:
            self.root.clipboard_clear()
            self.root.clipboard_append(item["text"])
            self._clipboard_last = item["text"]

    def _pin_clipboard_item(self):
        item = self._selected_clipboard_item()
        if item:
            item["pinned"] = not item["pinned"]
            self._refresh_clipboard()

    def _delete_clipboard_item(self):
        item = self._selected_clipboard_item()
        if item:
            self.clipboard_items.remove(item)
            self._refresh_clipboard()

    def _clear_clipboard(self):
        self.clipboard_items.clear()
        self._refresh_clipboard()

    def _section_title(self, parent, title, desc, button_text, button_action):
        heading = tk.Frame(parent, bg=BG)
        heading.pack(fill="x", pady=(1, 14))
        words = tk.Frame(heading, bg=BG)
        words.pack(side="left", fill="x", expand=True)
        tk.Label(words, text=title, bg=BG, fg=WHITE, font=(FONT, 15, "bold")).pack(anchor="w")
        tk.Label(words, text=desc, bg=BG, fg=MUTED, font=(FONT, 9)).pack(anchor="w", pady=(4, 0))
        action_label(heading, button_text, button_action, fg="#121622", bg=ACCENT,
                     hover="#BBC0FF", padx=12, pady=9, font_size=9).pack(side="right")

    def _build_notes(self):
        self._section_title(self.body, "My notes", "Ideas, reminders, quick thoughts", "+ New", self.add_note)
        main = tk.Frame(self.body, bg=BG)
        main.pack(fill="both", expand=True, pady=(0, 5))

        # Top row: note details on the left, note picker on the right.
        top_row = tk.Frame(main, bg=BG)
        top_row.pack(fill="x")

        details = tk.Frame(top_row, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        details.pack(side="left", fill="x", expand=True)

        sidebar = tk.Frame(top_row, bg=PANEL, width=144, height=154,
                           highlightbackground=BORDER, highlightthickness=1)
        sidebar.pack(side="right", fill="y", padx=(10, 0))
        sidebar.pack_propagate(False)
        tk.Label(sidebar, text="ALL NOTES", font=(FONT, 8, "bold"), fg=MUTED,
                 bg=PANEL).pack(anchor="w", padx=11, pady=(14, 9))
        self.note_list = tk.Listbox(sidebar, bd=0, highlightthickness=0, activestyle="none",
                                    selectbackground=ACCENT_DARK, selectforeground=WHITE,
                                    bg=PANEL, fg=SECONDARY, font=(FONT, 10), height=1, width=1,
                                    exportselection=False, relief="flat", justify="left")
        self.note_list.pack(fill="both", expand=True, padx=5, pady=(0, 10))
        self.note_list.bind("<<ListboxSelect>>", self._select_from_list)
        self.note_list.bind("<Button-3>", self._show_note_list_menu)
        self.note_list.bind("<Control-Button-1>", self._show_note_list_menu)

        title_row = tk.Frame(details, bg=PANEL)
        title_row.pack(fill="x", padx=12, pady=(12, 5))
        tk.Label(title_row, text="TITLE", font=(FONT, 8, "bold"), fg=MUTED,
                 bg=PANEL).pack(side="left")
        self.created_label = tk.Label(title_row, text="", font=(FONT, 7), fg=MUTED,
                                      bg=PANEL, anchor="e")
        self.created_label.pack(side="right")
        self.title_var = tk.StringVar()
        self.title_entry = tk.Entry(details, textvariable=self.title_var, bg=INPUT, fg=WHITE,
                                    insertbackground=WHITE, highlightthickness=1,
                                    highlightbackground=BORDER, highlightcolor=ACCENT,
                                    relief="flat", font=(FONT, 11, "bold"))
        self.title_entry.pack(fill="x", padx=12, ipady=9)
        self.title_var.trace_add("write", self._change_note_title)

        phone_row = tk.Frame(details, bg=PANEL)
        phone_row.pack(fill="x", padx=12, pady=(8, 12))
        tk.Label(phone_row, text="PHONE", font=(FONT, 8, "bold"), fg=MUTED,
                 bg=PANEL).pack(side="left", padx=(0, 7))
        self.phone_var = tk.StringVar()
        self.phone_entry = tk.Entry(phone_row, textvariable=self.phone_var, bg=INPUT, fg=WHITE,
                                    insertbackground=WHITE, highlightthickness=1,
                                    highlightbackground=BORDER, highlightcolor=ACCENT,
                                    relief="flat", font=(FONT, 9), width=8)
        self.phone_entry.pack(side="left", fill="x", expand=True, ipady=4)
        action_label(phone_row, "Copy", self._copy_phone, fg=ACCENT, bg=CARD,
                     padx=9, pady=4, font_size=8).pack(side="left", padx=(6, 0))
        self.phone_var.trace_add("write", self._change_note_phone)
        reminders = tk.Frame(details, bg=PANEL)
        reminders.pack(fill="x", padx=10, pady=(0, 4))
        self.reminder_action = action_label(reminders, "☐ Notify me", self._toggle_active_note_reminder,
                                            bg=PANEL, fg=ACCENT, padx=4, pady=2, font_size=8)
        self.reminder_action.pack(side="left")
        self.reminder_detail = tk.Label(reminders, text="", bg=PANEL, fg=MUTED, font=(FONT, 8), cursor="hand2")
        self.reminder_detail.pack(side="right")
        self.reminder_detail.bind("<Button-1>", lambda _e:self._edit_active_note_reminder())

        # Bottom block: full-width note editor.
        editor = tk.Frame(main, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        editor.pack(fill="both", expand=True, pady=(10, 0))
        tk.Label(editor, text="NOTE", font=(FONT, 8, "bold"), fg=MUTED,
                 bg=PANEL).pack(anchor="w", padx=12, pady=(10, 5))
        self.note_body = tk.Text(editor, wrap="word", undo=True, bg=INPUT, fg="#D7DAE6",
                                 insertbackground=ACCENT, selectbackground=ACCENT_DARK,
                                 relief="flat", bd=0, font=(FONT, 10), height=1, width=1,
                                 highlightthickness=1, highlightbackground=BORDER,
                                 highlightcolor=ACCENT, padx=10, pady=12)
        self.note_body.pack(fill="both", expand=True, padx=12)
        self.bidi_editor = None
        if sys.platform == "win32":
            try:
                self.bidi_editor = native_bidi.NativeBidiEditor(
                    editor, background=INPUT, foreground="#D7DAE6",
                    context_menu=self._show_note_context_menu)
            except (OSError, RuntimeError) as exc:
                print(f"Pocket native RTL editor unavailable: {exc}", file=sys.stderr)
        self.note_direction_var = tk.StringVar(value="ltr")
        self.note_body.tag_configure("note_alignment", justify="left")
        self.note_body.bind("<<Modified>>", self._change_note_body)
        self.note_body.bind("<Button-3>", self._show_note_context_menu)
        # Right-click with a trackpad/alternate mouse mappings.
        self.note_body.bind("<Control-Button-1>", self._show_note_context_menu)
        self.note_body.bind("<Control-a>", self._select_all_note_text)
        editor_footer = tk.Frame(editor, bg=PANEL)
        editor_footer.pack(fill="x", padx=10, pady=9)
        self.save_status = tk.Label(editor_footer, text="Autosaved", font=(FONT, 8), fg=MUTED, bg=PANEL)
        self.save_status.pack(side="left")
        action_label(editor_footer, "Delete", self.delete_note, fg=DANGER, bg=PANEL,
                     hover=CARD, padx=5, pady=4, font_size=8).pack(side="right")
        action_label(editor_footer, "Open in Notepad ↗", self.open_notepad,
                     fg=ACCENT, bg=PANEL, hover=CARD,
                     padx=5, pady=4, font_size=8).pack(side="right", padx=(0, 4))
        self.refresh_note_list()
        self._load_selected_note()

    def _flush_current_note(self):
        """Commit any pending Text widget changes before changing the active note.

        Tk's <<Modified>> notification may not run before a fast click/right-click.
        """
        if self._loading_note or self.current_tab != "notes":
            return
        note = self.active_note()
        if note is None or not hasattr(self, "note_body") or not self.note_body.winfo_exists():
            return
        text = self._editor_text()
        if note["body"] != text:
            note["body"] = text
            self.schedule_save()

    def active_note(self):
        for note in self.data["notes"]:
            if note["id"] == self.data["active_note"]:
                return note
        return None

    def refresh_note_list(self):
        if not hasattr(self, "note_list") or not self.note_list.winfo_exists():
            return
        self._loading_note = True
        self._note_rows = ordered_notes(self.data["notes"])
        self.note_list.delete(0, tk.END)
        for i, n in enumerate(self._note_rows):
            marker = "★ " if n.get("pinned") else "  "
            self.note_list.insert(tk.END, marker + (n["title"].strip() or "Untitled")[:18])
            if n["id"] == self.data["active_note"]:
                self.note_list.selection_set(i)
                self.note_list.activate(i)
        self._loading_note = False

    def _load_selected_note(self):
        if self.current_tab != "notes":
            return
        n = self.active_note()
        if not n:
            return
        self._loading_note = True
        self.title_var.set(n["title"])
        self.created_label.config(text=display_created_at(n.get("created_at", "")))
        self.phone_var.set(n.get("phone", ""))
        self.reminder_action.config(text="☑ Notify me" if n.get("reminder_enabled") else "☐ Notify me")
        self.reminder_detail.config(text=format_reminder(n))
        self.note_body.delete("1.0", tk.END)
        self.note_body.insert("1.0", n["body"])
        if self.bidi_editor is not None:
            self.bidi_editor.set_text(n["body"])
        self._apply_note_direction(n)
        self.note_body.edit_modified(False)
        self._loading_note = False
        self.save_status.config(text="Autosaved", fg=MUTED)

    def _select_from_list(self, _event):
        if self._loading_note:
            return
        indexes = self.note_list.curselection()
        if not indexes or indexes[0] >= len(self._note_rows):
            return
        self._flush_current_note()
        self.data["active_note"] = self._note_rows[indexes[0]]["id"]
        self._load_selected_note()
        self.schedule_save()

    def _show_note_list_menu(self, event):
        """Right-click the exact row under the pointer, not the last active note."""
        index = self.note_list.nearest(event.y)
        bounds = self.note_list.bbox(index)
        if not bounds or not (bounds[1] <= event.y < bounds[1] + bounds[3]):
            return "break"
        if index >= len(self._note_rows):
            return "break"
        target = self._note_rows[index]
        self._flush_current_note()
        self.data["active_note"] = target["id"]
        self.refresh_note_list()
        self._load_selected_note()
        self.schedule_save()
        menu = self._build_note_list_menu(target["id"])
        previous = getattr(self, "_note_picker_context_menu", None)
        if previous is not None and previous.winfo_exists():
            previous.unpost()
            previous.destroy()
        self._note_picker_context_menu = menu
        was_modal = self._modal
        self._modal = True

        def on_unmap(_event):
            if self._note_picker_context_menu is menu:
                self._modal = was_modal

        menu.bind("<Unmap>", on_unmap)
        try:
            menu.tk_popup(event.x_root, event.y_root)
        except tk.TclError:
            self._modal = was_modal
        finally:
            menu.grab_release()
        return "break"

    def _build_note_list_menu(self, note_id: str):
        note = next((n for n in self.data["notes"] if n["id"] == note_id), None)
        menu = tk.Menu(self.root, tearoff=False, bg=PANEL, fg=WHITE,
                       activebackground=ACCENT_DARK, activeforeground=WHITE,
                       bd=1, relief="flat", font=(FONT, 9))
        if note:
            menu.add_command(label="Unpin from top" if note.get("pinned") else "Pin to top",
                             command=lambda: self._toggle_note_pin(note_id))
            menu.add_command(label="Duplicate note", command=lambda: self._duplicate_note(note_id))
            menu.add_checkbutton(label="Notify me…", onvalue=True, offvalue=False,
                                 variable=tk.BooleanVar(value=note.get("reminder_enabled", False)),
                                 command=lambda: self._toggle_note_reminder(note_id))
            if note.get("reminder_enabled"):
                menu.add_command(label="Change notification time…",
                                 command=lambda: self._edit_note_reminder(note_id))
            menu.add_separator()
            menu.add_command(label="Delete note…", command=lambda: self._delete_note_by_id(note_id))
        return menu

    def _toggle_active_note_reminder(self):
        note = self.active_note()
        if note:
            self._toggle_note_reminder(note["id"])

    def _edit_active_note_reminder(self):
        note = self.active_note()
        if note:
            self._edit_note_reminder(note["id"])

    def _toggle_note_reminder(self, note_id):
        note = next((n for n in self.data["notes"] if n["id"] == note_id), None)
        if not note:
            return
        if note.get("reminder_enabled"):
            note.update(reminder_enabled=False, reminder_at="", reminder_sent_at="")
            self._refresh_note_reminder_ui()
            self.schedule_save()
        else:
            self._edit_note_reminder(note_id)

    def _refresh_note_reminder_ui(self):
        if self.current_tab == "notes":
            self.refresh_note_list()
            self._load_selected_note()

    def _edit_note_reminder(self, note_id):
        note = next((n for n in self.data["notes"] if n["id"] == note_id), None)
        if not note:
            return
        if getattr(self, "_reminder_dialog", None) and self._reminder_dialog.winfo_exists():
            self._reminder_dialog.lift()
            return
        self._flush_current_note()
        self._modal = True
        dialog = tk.Toplevel(self.root)
        self._reminder_dialog = dialog
        dialog.title("Pocket · Note notification")
        dialog.configure(bg=BG)
        dialog.resizable(False, False)
        dialog.geometry(f"390x305+{max(0,self.root.winfo_x()+35)}+{max(0,self.root.winfo_y()+110)}")
        dialog.transient(self.root)
        try:
            existing = datetime.fromisoformat(note["reminder_at"]).astimezone()
            if existing <= datetime.now().astimezone():
                existing = datetime.now().astimezone() + timedelta(hours=1)
        except (ValueError, KeyError, TypeError):
            existing = datetime.now().astimezone() + timedelta(hours=1)
        date_var = tk.StringVar(value=existing.strftime("%Y-%m-%d"))
        time_var = tk.StringVar(value=existing.strftime("%H:%M"))
        tk.Label(dialog, text="Notify me about this note", bg=BG, fg=WHITE,
                 font=(FONT, 14, "bold")).pack(anchor="w", padx=20, pady=(18, 4))
        tk.Label(dialog, text=note["title"][:60], bg=BG, fg=MUTED,
                 font=(FONT, 9)).pack(anchor="w", padx=20, pady=(0, 13))
        fields = tk.Frame(dialog, bg=BG)
        fields.pack(fill="x", padx=20)
        for label, var in (("DATE  YYYY-MM-DD", date_var), ("TIME  HH:MM (24h)", time_var)):
            line = tk.Frame(fields, bg=BG)
            line.pack(fill="x", pady=(0, 9))
            tk.Label(line, text=label, bg=BG, fg=SECONDARY,
                     font=(FONT, 9), width=20, anchor="w").pack(side="left")
            self._entry(line, var).pack(side="right", fill="x", expand=True, ipady=5)
        tk.Label(dialog, text="Local computer time. Pocket must be running in the tray.",
                 bg=BG, fg=MUTED, font=(FONT, 8), wraplength=350).pack(anchor="w", padx=20, pady=10)
        actions = tk.Frame(dialog, bg=BG)
        actions.pack(fill="x", padx=20, pady=(2, 10))

        def close():
            self._modal = False
            dialog.destroy()

        def save():
            try:
                when = parse_reminder_time(date_var.get(), time_var.get())
            except ValueError as exc:
                messagebox.showwarning("Invalid notification time", str(exc), parent=dialog)
                return
            note.update(reminder_enabled=True, reminder_at=when, reminder_sent_at="")
            self._refresh_note_reminder_ui()
            self._write_now()
            close()

        action_label(actions, "Cancel", close, fg=SECONDARY, bg=PANEL,
                     font_size=9).pack(side="right", padx=(8, 0))
        action_label(actions, "Save reminder", save, fg="#121622", bg=ACCENT,
                     font_size=9).pack(side="right")
        dialog.protocol("WM_DELETE_WINDOW", close)
        dialog.bind("<Escape>", lambda _e: close())
        dialog.grab_set()

    def _toggle_note_pin(self, note_id: str):
        target = next((n for n in self.data["notes"] if n["id"] == note_id), None)
        if target is None:
            return
        target["pinned"] = not target.get("pinned", False)
        self.refresh_note_list()
        self.schedule_save()

    def _duplicate_note(self, note_id: str):
        self._flush_current_note()
        for index, note in enumerate(self.data["notes"]):
            if note["id"] == note_id:
                copy = duplicate_note(note)
                self.data["notes"].insert(index + 1, copy)
                self.data["active_note"] = copy["id"]
                self.refresh_note_list()
                self._load_selected_note()
                self.schedule_save()
                return

    def _delete_note_by_id(self, note_id: str):
        if not any(n["id"] == note_id for n in self.data["notes"]):
            return
        self._modal = True
        try:
            confirmed = messagebox.askyesno("Delete note", "Delete this note permanently?",
                                            parent=self.root)
        finally:
            self._modal = False
        if not confirmed:
            return
        self.data["notes"] = [n for n in self.data["notes"] if n["id"] != note_id]
        self._notepad_sessions.pop(note_id, None)
        if not self.data["notes"]:
            self.data["notes"] = [new_note()]
        if self.data["active_note"] == note_id:
            self.data["active_note"] = ordered_notes(self.data["notes"])[0]["id"]
        self.refresh_note_list()
        self._load_selected_note()
        self.schedule_save()

    def _change_note_title(self, *_args):
        if self._loading_note or self.current_tab != "notes":
            return
        note = self.active_note()
        if note is not None:
            note["title"] = self.title_var.get()
            self.refresh_note_list()
            self._edit_dirty()

    def _change_note_phone(self, *_args):
        if self._loading_note or self.current_tab != "notes":
            return
        note = self.active_note()
        if note is not None:
            note["phone"] = self.phone_var.get()
            self._edit_dirty()

    def _copy_phone(self):
        try:
            number = shortcuts.validate_phone_number(self.phone_var.get())
        except ValueError as exc:
            self._warning("Phone number", str(exc))
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(number)
        self.save_status.config(text="Number copied", fg=ACCENT)

    def _editor_text(self):
        return self.bidi_editor.get_text() if self._bidi_active() else self.note_body.get("1.0", "end-1c")

    def _bidi_active(self):
        return self.bidi_editor is not None and self._bidi_editor_active and self.current_tab == "notes"

    def _bidi_poll(self):
        try:
            if self._bidi_active() and not self._loading_note:
                note = self.active_note()
                if note is not None:
                    content = self.bidi_editor.get_text()
                    if note["body"] != content:
                        note["body"] = content
                        self._edit_dirty()
        finally:
            if self.root.winfo_exists():
                self.root.after(350, self._bidi_poll)

    def _selected_note_text(self) -> str:
        if self._bidi_active():
            return self.bidi_editor.get_selected()
        try:
            return self.note_body.get("sel.first", "sel.last")
        except tk.TclError:
            return ""

    def _select_all_note_text(self, _event=None):
        if self._bidi_active():
            self.bidi_editor.select_all()
            return "break"
        self.note_body.tag_add("sel", "1.0", "end-1c")
        self.note_body.mark_set("insert", "1.0")
        self.note_body.see("insert")
        return "break"

    def _note_edit_action(self, operation: str):
        """Use Tk editing primitives, which preserve the editor's undo history."""
        try:
            if self._bidi_active():
                self.bidi_editor.edit_action(operation)
                return
            if operation == "undo":
                self.note_body.edit_undo()
            elif operation == "redo":
                self.note_body.edit_redo()
            elif operation in ("cut", "copy", "paste"):
                self.note_body.event_generate(f"<<{operation.capitalize()}>>")
        except tk.TclError:
            # An empty undo/redo history is normal.
            pass

    def _copy_entire_note(self):
        content = self._editor_text()
        self.root.clipboard_clear()
        self.root.clipboard_append(content)
        self.save_status.config(text="Note copied", fg=ACCENT)

    def _insert_note_timestamp(self):
        if self._bidi_active():
            self.bidi_editor.replace_selection(datetime.now().strftime("%Y-%m-%d %H:%M"))
            self.bidi_editor.focus_set()
            return
        self.note_body.insert("insert", datetime.now().strftime("%Y-%m-%d %H:%M"))
        self.note_body.focus_set()

    def _check_selected_note_ip(self, ip: str):
        """Open a prepared port check; never initiate a network scan."""
        self.show_tab("ports")
        self.host_var.set(ip)
        self.root.after_idle(self.root.focus_force)

    def _find_selected_note_command(self, query: str):
        """Search across all machine models, not only the previously selected one."""
        self.show_tab("commands")
        self.machine_var.set(ch.ALL_MACHINES)
        self.command_category_var.set(ch.ALL_CATEGORIES)
        self.command_mode = "all"
        self._style_command_modes()
        self._command_placeholder_active = False
        self.command_search_entry.config(fg=WHITE)
        self.command_query.set(query)
        self.command_search_entry.focus_set()
        self.command_search_entry.icursor(tk.END)

    def _build_note_context_menu(self):
        """Build menu from the current selection; also used by UI regression tests."""
        selected = self._selected_note_text()
        valid_ip = note_selection_ip(selected)
        lookup = note_command_query(selected)
        menu = tk.Menu(self.root, tearoff=False, bg=PANEL, fg=WHITE,
                       activebackground=ACCENT_DARK, activeforeground=WHITE,
                       bd=1, relief="flat", font=(FONT, 9))
        for title, key, action in (
            ("Undo", "Ctrl+Z", lambda: self._note_edit_action("undo")),
            ("Redo", "Ctrl+Y", lambda: self._note_edit_action("redo")),
        ):
            menu.add_command(label=f"{title}     {key}", command=action)
        menu.add_separator()
        menu.add_command(label="Cut     Ctrl+X", state="normal" if selected else "disabled",
                         command=lambda: self._note_edit_action("cut"))
        menu.add_command(label="Copy     Ctrl+C", state="normal" if selected else "disabled",
                         command=lambda: self._note_edit_action("copy"))
        try:
            self.root.clipboard_get()
            paste_ready = True
        except tk.TclError:
            paste_ready = False
        menu.add_command(label="Paste     Ctrl+V", state="normal" if paste_ready else "disabled",
                         command=lambda: self._note_edit_action("paste"))
        menu.add_command(label="Select all     Ctrl+A", command=self._select_all_note_text)
        menu.add_separator()
        menu.add_radiobutton(label="Right to Left (עברית)", variable=self.note_direction_var,
                             value="rtl", command=lambda: self._set_note_direction("rtl"))
        menu.add_radiobutton(label="Left to Right (English)", variable=self.note_direction_var,
                             value="ltr", command=lambda: self._set_note_direction("ltr"))
        menu.add_separator()
        menu.add_command(label="Copy entire note", command=self._copy_entire_note)
        menu.add_command(label="Insert date & time", command=self._insert_note_timestamp)
        menu.add_command(label="Open in Notepad", command=self.open_notepad)
        if valid_ip or lookup:
            menu.add_separator()
        if valid_ip:
            menu.add_command(label=f"Check selected IP  ({valid_ip})",
                             command=lambda target=valid_ip: self._check_selected_note_ip(target))
        if lookup:
            menu.add_command(label="Find selection in Commands",
                             command=lambda text=lookup: self._find_selected_note_command(text))
        return menu

    def _show_note_context_menu(self, event):
        """Post the menu without destroying it before Windows can render it."""
        old = getattr(self, "_note_context_menu", None)
        if old is not None and old.winfo_exists():
            old.unpost()
            old.destroy()

        menu = self._build_note_context_menu()
        self._note_context_menu = menu
        was_modal = self._modal
        self._modal = True  # Prevent focus-loss auto-hide while menu is shown.

        def on_unmap(_event):
            if self._note_context_menu is menu:
                self._modal = was_modal

        menu.bind("<Unmap>", on_unmap)
        try:
            menu.tk_popup(event.x_root, event.y_root)
        except tk.TclError:
            self._modal = was_modal
        finally:
            menu.grab_release()
        return "break"

    def _apply_note_direction(self, note):
        """Use Windows RichEdit BiDi for Hebrew rather than Tk justification."""
        direction = normalize_note_direction(note.get("direction"))
        self.note_direction_var.set(direction)
        self._bidi_editor_active = direction == "rtl" and self.bidi_editor is not None
        self.note_body.tag_configure("note_alignment", justify="left")
        if self._bidi_editor_active:
            self.note_body.pack_forget()
            self.bidi_editor.pack(fill="both", expand=True, padx=12, before=self.save_status.master)
            self.bidi_editor.set_direction("rtl")
        else:
            if self.bidi_editor is not None:
                self.bidi_editor.pack_forget()
            self.note_body.pack(fill="both", expand=True, padx=12, before=self.save_status.master)

    def _set_note_direction(self, direction):
        note = self.active_note()
        if note is None:
            return
        self._flush_current_note()
        content = note["body"]
        note["direction"] = normalize_note_direction(direction)
        self._loading_note = True
        try:
            self.note_body.delete("1.0", tk.END)
            self.note_body.insert("1.0", content)
            if self.bidi_editor is not None:
                self.bidi_editor.set_text(content)
            self._apply_note_direction(note)
            self.note_body.edit_modified(False)
        finally:
            self._loading_note = False
        if self._bidi_active():
            self.bidi_editor.focus_set()
        else:
            self.note_body.focus_set()
        self.schedule_save()

    def _change_note_body(self, _event=None):
        if not self.note_body.edit_modified():
            return
        self.note_body.edit_modified(False)
        if self._loading_note:
            return
        note = self.active_note()
        if note is not None:
            note["body"] = self._editor_text()
            self._edit_dirty()

    def _edit_dirty(self):
        if self.current_tab == "notes":
            self.save_status.config(text="Saving…", fg=ACCENT)
        self.schedule_save()

    def add_note(self):
        self._flush_current_note()
        self.data["notes"].insert(0, new_note())
        self.data["active_note"] = self.data["notes"][0]["id"]
        if self.current_tab != "notes":
            self.show_tab("notes")
        else:
            self.refresh_note_list()
            self._load_selected_note()
        self.title_entry.focus_set()
        self.title_entry.selection_range(0, tk.END)
        self.schedule_save()

    def delete_note(self):
        self._delete_note_by_id(self.data["active_note"])

    def _build_links(self):
        self._section_title(self.body, "Quick shortcuts", "Websites, files and folders", "+ Add", lambda: self._toggle_link_form(None))
        search_row = tk.Frame(self.body, bg=BG)
        search_row.pack(fill="x", pady=(0, 8))
        tk.Label(search_row, text="⌕", bg=BG, fg=MUTED, font=(FONT, 14)).pack(side="left", padx=(0, 6))
        self.link_query = tk.StringVar()
        search = self._entry(search_row, self.link_query)
        search.config(font=(FONT, 9))
        search.pack(side="left", fill="x", expand=True, ipady=5)
        self.link_query.trace_add("write", lambda *_: self.refresh_links())
        tk.Label(search_row, text="Search shortcuts", fg=MUTED, bg=BG,
                 font=(FONT, 8)).pack(side="right", padx=(8, 0))
        self.form_holder = tk.Frame(self.body, bg=BG)
        # Explicit drop area: nothing is saved until the user confirms the form.
        self.drop_panel = tk.Frame(self.body, bg=PANEL, highlightbackground=ACCENT_DARK,
                                   highlightthickness=1, height=74)
        self.drop_panel.pack(fill="x", pady=(0, 12))
        self.drop_panel.pack_propagate(False)
        self.drop_title = tk.Label(self.drop_panel, text="↓  DROP WEBSITE, FILE OR FOLDER HERE",
                                   font=(FONT, 9, 'bold'), fg=ACCENT, bg=PANEL)
        self.drop_title.pack(pady=(12, 3))
        self.drop_hint = tk.Label(self.drop_panel, text=(
            "PIN the popup before dragging from Explorer or your browser" if self.dnd_available
            else "Drag & drop unavailable · Install tkinterdnd2 (see README)"),
            font=(FONT, 8), fg=MUTED, bg=PANEL)
        self.drop_hint.pack()
        for widget in (self.drop_panel, self.drop_title, self.drop_hint):
            self._register_shortcut_drop(widget)
        # The form is NOT packed until it is shown. An empty packed form can
        # retain its former requested height after Save/Cancel on Tk 8.6,
        # leaving a large blank gap above the shortcut cards.
        frame = tk.Frame(self.body, bg=BG)
        frame.pack(fill="both", expand=True)
        canvas = tk.Canvas(frame, bg=BG, highlightthickness=0, bd=0)
        scroll = tk.Scrollbar(frame, orient="vertical", command=canvas.yview, bg=CARD)
        canvas.configure(yscrollcommand=scroll.set)
        canvas.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        self._scroll_canvas = canvas
        self.links_stack = tk.Frame(canvas, bg=BG)
        self._register_shortcut_drop(canvas)
        self._register_shortcut_drop(self.links_stack)
        win = canvas.create_window((0, 0), window=self.links_stack, anchor="nw")
        self.links_stack.bind("<Configure>", lambda _e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(win, width=e.width))
        canvas.bind("<Enter>", lambda _e: canvas.bind_all("<MouseWheel>", self._mousewheel))
        canvas.bind("<Leave>", lambda _e: canvas.unbind_all("<MouseWheel>"))
        self.refresh_links()

    def _register_shortcut_drop(self, widget):
        """Register both Explorer file drops and browser URL/text drops."""
        if not self.dnd_available:
            return
        try:
            widget.drop_target_register(DND_FILES, DND_TEXT)
            widget.dnd_bind('<<DropEnter>>', self._drop_enter, add='+')
            widget.dnd_bind('<<DropLeave>>', self._drop_leave, add='+')
            widget.dnd_bind('<<Drop>>', self._shortcut_dropped, add='+')
        except tk.TclError:
            # Unsupported native TkDnD runtime; regular shortcut creation works.
            self.dnd_available = False
            if hasattr(self, 'drop_hint') and self.drop_hint.winfo_exists():
                self.drop_hint.config(text='Drag & drop unavailable · Install tkinterdnd2 (see README)')

    def _drop_enter(self, _event):
        if self.current_tab == 'links' and self.drop_panel.winfo_exists():
            self.drop_panel.config(highlightbackground=ACCENT, bg=ACCENT_DARK)
            self.drop_title.config(bg=ACCENT_DARK)
            self.drop_hint.config(bg=ACCENT_DARK)
        return 'copy'

    def _drop_leave(self, _event):
        if self.current_tab == 'links' and self.drop_panel.winfo_exists():
            self.drop_panel.config(highlightbackground=ACCENT_DARK, bg=PANEL)
            self.drop_title.config(bg=PANEL)
            self.drop_hint.config(bg=PANEL)

    def _shortcut_dropped(self, event):
        """A native drop opens an editable draft; it never writes the data file."""
        if self.current_tab != 'links':
            return 'refuse_drop'
        self._drop_leave(event)
        try:
            suggestion = shortcut_drop.guess_shortcut(event.data, splitlist=self.root.tk.splitlist)
        except (ValueError, OSError) as exc:
            self._warning('Shortcut drop', str(exc))
            return 'refuse_drop'
        self._toggle_link_form(None, draft=suggestion)
        self.drop_title.config(text='✓  READY TO SAVE — REVIEW BELOW')
        self.drop_hint.config(text='Edit the suggested name or target, then click Save shortcut')
        if self._scroll_canvas and self._scroll_canvas.winfo_exists():
            self._scroll_canvas.yview_moveto(0)
        return 'copy'

    def _mousewheel(self, event):
        if self._scroll_canvas and self._scroll_canvas.winfo_exists():
            self._scroll_canvas.yview_scroll(int(-event.delta / 120), "units")

    def refresh_links(self):
        if self.current_tab != "links":
            return
        for child in self.links_stack.winfo_children():
            child.destroy()
        matches = hk.filter_shortcuts(self.data["links"], self.link_query.get())
        if not matches:
            tk.Label(self.links_stack, text=("No matching shortcuts." if self.data["links"] else "No shortcuts yet. Add a website, file or folder above."),
                     fg=SECONDARY, bg=BG, font=(FONT, 10), wraplength=360).pack(pady=25)
        for link in matches:
            self._link_tile(link)

    def _link_tile(self, link):
        tile = tk.Frame(self.links_stack, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        tile.pack(fill="x", pady=(0, 10), padx=(2, 6), ipady=6)
        kind = link.get("kind", "url")
        badge_text = {"url": "↗", "file": "▤", "folder": "▣"}.get(kind, "↗")
        tk.Label(tile, text=badge_text, bg=ACCENT_DARK, fg=ACCENT,
                 font=(FONT, 17, "bold"), width=3, height=2).pack(side="left", padx=(12, 10))
        desc = tk.Frame(tile, bg=PANEL)
        desc.pack(side="left", fill="both", expand=True)
        title = tk.Label(desc, text=link["title"], anchor="w", fg=WHITE, bg=PANEL,
                         font=(FONT, 11, "bold"), cursor="hand2")
        title.pack(fill="x", pady=(3, 2))
        target = link["url"]
        summary = urlsplit(target).netloc if kind == "url" else target
        tk.Label(desc, text=f"{kind.upper()}  •  {summary[:28]}", anchor="w", fg=MUTED, bg=PANEL,
                 font=(FONT, 8)).pack(fill="x")
        title.bind("<Button-1>", lambda _e, item=link: self.open_shortcut(item))
        self._register_shortcut_drop(tile)
        self._register_shortcut_drop(title)
        actions = tk.Frame(tile, bg=PANEL)
        actions.pack(side="right", padx=(0, 8))
        action_label(actions, "↗", lambda item=link: self.open_shortcut(item),
                     fg=ACCENT, bg=PANEL, hover=CARD, padx=7, pady=5, font_size=15).pack(side="left")
        action_label(actions, "⧉", lambda item=link: self._copy_shortcut(item),
                     fg=SECONDARY, bg=PANEL, hover=CARD, padx=6, pady=5, font_size=13).pack(side="left")
        action_label(actions, "···", lambda item=link: self._show_link_menu(item),
                     fg=MUTED, bg=PANEL, hover=CARD, padx=7, pady=5, font_size=12).pack(side="left")

    def _show_link_menu(self, item):
        kind = item.get("kind", "url")
        menu = tk.Menu(self.root, tearoff=False, bg=PANEL, fg=WHITE,
                       activebackground=ACCENT_DARK, activeforeground=WHITE)
        menu.add_command(label="Edit shortcut", command=lambda: self._toggle_link_form(item))
        menu.add_command(label="Copy URL" if kind == "url" else "Copy path",
                         command=lambda: self._copy_url(item["url"]))
        menu.add_separator()
        menu.add_command(label="Delete shortcut", command=lambda: self._delete_link(item))
        x, y = self.root.winfo_pointerxy()
        try:
            menu.tk_popup(x, y)
        finally:
            menu.grab_release()

    def _copy_shortcut(self, item):
        """Copy a URL or local path directly from its shortcut card."""
        self._copy_url(item["url"])

    def _copy_url(self, url):
        self.root.clipboard_clear()
        self.root.clipboard_append(url)

    def _delete_link(self, item):
        self.data["links"] = [l for l in self.data["links"] if l["id"] != item["id"]]
        self.refresh_links()
        self.schedule_save()

    def _toggle_link_form(self, item, *, draft=None):
        for child in self.form_holder.winfo_children():
            child.destroy()
        self.edit_link_id = item["id"] if item else None
        # Insert the form above the scrollable cards only while editing.
        # Packing a blank holder permanently causes a ~280px stale-height gap.
        self.form_holder.pack(fill="x", before=self._scroll_canvas.master)
        panel = tk.Frame(self.form_holder, bg=PANEL, highlightthickness=1,
                         highlightbackground=ACCENT_DARK)
        panel.pack(fill="x", pady=(0, 13))
        tk.Label(panel, text="EDIT SHORTCUT" if item else "NEW SHORTCUT", fg=ACCENT, bg=PANEL,
                 font=(FONT, 9, "bold")).pack(anchor="w", padx=14, pady=(12, 6))
        title_var = tk.StringVar(value=item["title"] if item else (draft or {}).get('title', ''))
        target_var = tk.StringVar(value=item["url"] if item else (draft or {}).get('url', ''))
        kind_var = tk.StringVar(value=item.get("kind", "url") if item else (draft or {}).get('kind', 'url'))
        kinds = tk.Frame(panel, bg=PANEL)
        kinds.pack(fill="x", padx=11, pady=(0, 6))
        for value, label in (("url", "Website"), ("file", "File"), ("folder", "Folder")):
            tk.Radiobutton(kinds, text=label, value=value, variable=kind_var,
                           bg=PANEL, fg=WHITE, activebackground=PANEL, activeforeground=ACCENT,
                           selectcolor=INPUT, font=(FONT, 9), highlightthickness=0,
                           command=lambda: update_kind()).pack(side="left", padx=(0, 8))
        tk.Label(panel, text="SHORTCUT NAME", fg=SECONDARY, bg=PANEL,
                 font=(FONT, 8)).pack(anchor="w", padx=14)
        title_entry = self._entry(panel, title_var)
        title_entry.pack(fill="x", padx=14, pady=(4, 9), ipady=6)
        tk.Label(panel, text="TARGET", fg=SECONDARY, bg=PANEL,
                 font=(FONT, 8)).pack(anchor="w", padx=14)
        path_row = tk.Frame(panel, bg=PANEL)
        path_row.pack(fill="x", padx=14, pady=(4, 9))
        target_entry = self._entry(path_row, target_var)
        target_entry.pack(side="left", fill="x", expand=True, ipady=6)
        browse_button = action_label(path_row, "Browse...", lambda: self._browse_shortcut(kind_var, target_var, title_var),
                                     bg=CARD, fg=ACCENT, padx=9, pady=7, font_size=8)
        hint = tk.Label(panel, fg=MUTED, bg=PANEL, font=(FONT, 8), anchor="w")
        hint.pack(fill="x", padx=14, pady=(0, 6))

        def update_kind():
            if kind_var.get() == "url":
                browse_button.pack_forget()
                hint.config(text="https://example.com  •  opens in your browser")
            else:
                browse_button.pack(side="right", padx=(6, 0))
                hint.config(text="Opens locally on this PC (path must exist)")
        update_kind()
        actions = tk.Frame(panel, bg=PANEL)
        actions.pack(anchor="e", padx=14, pady=(0, 12))
        action_label(actions, "Cancel", self._close_form, fg=SECONDARY,
                     bg=PANEL, hover=CARD, font_size=9).pack(side="left", padx=7)
        action_label(actions, "Save shortcut", lambda: self._save_link(title_var.get(), target_var.get(), kind_var.get()),
                     fg="#121622", bg=ACCENT, hover="#BBC0FF", font_size=9).pack(side="left")
        self.root.after(30, lambda: title_entry.focus_set() if title_entry.winfo_exists() else None)

    def _browse_shortcut(self, kind_var, target_var, title_var):
        kind = kind_var.get()
        if kind == "url":
            return
        self._modal = True
        try:
            if kind == "file":
                target = filedialog.askopenfilename(parent=self.root, title="Choose a file shortcut")
            else:
                target = filedialog.askdirectory(parent=self.root, title="Choose a folder shortcut")
        finally:
            self._modal = False
        if target:
            target_var.set(target)
            if not title_var.get().strip():
                title_var.set(Path(target).name or target)

    def _close_form(self):
        for child in self.form_holder.winfo_children():
            child.destroy()
        # Crucial: remove the holder itself from the pack layout. Simply
        # deleting its children leaves an empty space on some Tk builds.
        self.form_holder.pack_forget()
        self.edit_link_id = None
        if self.drop_title.winfo_exists():
            self.drop_title.config(text="↓  DROP WEBSITE, FILE OR FOLDER HERE")
        if self.drop_hint.winfo_exists():
            self.drop_hint.config(text=(
                "PIN the popup before dragging from Explorer or your browser"
                if self.dnd_available else
                "Drag & drop unavailable · Install tkinterdnd2 (see README)"))
        if self._scroll_canvas and self._scroll_canvas.winfo_exists():
            self._scroll_canvas.yview_moveto(0)

    def _save_link(self, title, target, kind="url"):
        title = title.strip()
        if not title:
            self._warning("Missing name", "Give your shortcut a name.")
            return
        try:
            target = shortcuts.normalize_shortcut(kind, target)
        except (ValueError, OSError) as exc:
            self._warning("Invalid shortcut", str(exc))
            return
        edited = False
        for item in self.data["links"]:
            if item["id"] == self.edit_link_id:
                item.update(title=title, url=target, kind=kind)
                edited = True
                break
        if not edited:
            self.data["links"].insert(0, new_link(title, target, kind))
        self._close_form()
        self.refresh_links()
        self.schedule_save()

    def open_shortcut(self, item):
        try:
            shortcuts.launch_shortcut(item.get("kind", "url"), item["url"])
        except (ValueError, OSError) as exc:
            self._warning("Unable to open shortcut", str(exc))
            return
        if not self.pinned:
            self.hide()

    # ---- TCP port checker -------------------------------------------------

    def _warning(self, title, message):
        self._modal = True
        try:
            messagebox.showwarning(title, message, parent=self.root)
        finally:
            self._modal = False

    @staticmethod
    def _entry(parent, value, *, width=None):
        e = tk.Entry(parent, textvariable=value, bg=INPUT, fg=WHITE,
                     insertbackground=WHITE, highlightthickness=1,
                     highlightbackground=BORDER, highlightcolor=ACCENT,
                     relief="flat", font=(FONT, 10), width=width or 1)
        return e

    def _tree(self, parent, columns, widths, *, rows=4, aligns=None):
        style = ttk.Style(self.root)
        style.configure("Pocket.Treeview", background=PANEL, foreground=WHITE,
                        fieldbackground=PANEL, rowheight=27, borderwidth=0,
                        font=(FONT, 9))
        style.configure("Pocket.Treeview.Heading", background=CARD,
                        foreground=SECONDARY, relief="flat", font=(FONT, 9, "bold"))
        style.map("Pocket.Treeview", background=[("selected", ACCENT_DARK)],
                  foreground=[("selected", WHITE)])
        container = tk.Frame(parent, bg=BG)
        container.pack(fill="both", expand=True, pady=(8, 0))
        tree = ttk.Treeview(container, columns=columns, show="headings", height=rows,
                            style="Pocket.Treeview")
        if aligns is None:
            aligns = ("w",) * len(columns)
        for col, width, align in zip(columns, widths, aligns):
            tree.heading(col, text=col, anchor=align)
            tree.column(col, width=width, minwidth=50, anchor=align, stretch=True)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        return tree

    def _build_commands(self):
        self._section_title(self.body, "Command helper", "Find · Customize · Copy", "+ New", self._add_custom_command)
        backup_row = tk.Frame(self.body, bg=BG)
        backup_row.pack(fill="x", pady=(0, 8))
        action_label(backup_row, "Backup ▾", self._show_command_backup_menu, fg=ACCENT,
                     bg=PANEL, hover=CARD, padx=12, pady=6, font_size=9).pack(side="right")
        prefs = self.data["command_state"]
        names = [ch.ALL_MACHINES] + ch.machines_for(self.command_library, self.machine_catalog)
        machine = prefs.get("machine")
        self.machine_var = tk.StringVar(value=machine if machine in names else ch.ALL_MACHINES)
        self.machine_picker = ttk.Combobox(self.body, values=names, textvariable=self.machine_var,
                                           state="readonly", font=(FONT, 10), height=18)
        self.machine_picker.pack(fill="x", ipady=4, pady=(0, 8))
        self.machine_picker.bind("<<ComboboxSelected>>", self._change_machine)

        self.command_query = tk.StringVar()
        search_box = tk.Frame(self.body, bg=BG)
        search_box.pack(fill="x", pady=(0, 7))
        self.command_search_entry = self._entry(search_box, self.command_query)
        self.command_search_entry.config(font=(FONT, 10), fg=MUTED)
        self._command_placeholder = "Search command or purpose  (e.g. ping, ניתוב)"
        self._command_placeholder_active = True
        self.command_search_entry.insert(0, self._command_placeholder)
        self.command_search_entry.bind('<FocusIn>', self._command_focus_in)
        self.command_search_entry.bind('<FocusOut>', self._command_focus_out)
        self.command_search_entry.pack(fill="x", expand=True, ipady=9)
        self.command_query.trace_add('write', lambda *_: self._refresh_command_results())
        self.root.bind('<Control-f>', self._focus_command_search)

        filterrow = tk.Frame(self.body, bg=BG)
        filterrow.pack(fill="x", pady=(0, 2))
        self.command_category_var = tk.StringVar(value=ch.ALL_CATEGORIES)
        self.command_category_picker = ttk.Combobox(
            filterrow, textvariable=self.command_category_var, state="readonly", width=19,
            values=[ch.ALL_CATEGORIES]+ch.categories_for(self.command_library, self.machine_var.get()),
            font=(FONT, 9))
        self.command_category_picker.pack(side="left", fill="x", expand=True, ipady=3, padx=(0, 7))
        self.command_category_picker.bind('<<ComboboxSelected>>', lambda _event:self._refresh_command_results())
        self.command_modes = {}
        for mode,label in [('all','All'),('favorites','★ Saved'),('recent','Recent')]:
            btn = action_label(filterrow, label, lambda m=mode:self._set_command_mode(m),
                               fg=SECONDARY, bg=PANEL, hover=CARD, padx=7, pady=7, font_size=8)
            btn.pack(side="left", padx=(0, 3))
            self.command_modes[mode] = btn

        result_head = tk.Frame(self.body, bg=BG)
        result_head.pack(fill="x", pady=(3, 2))
        self.command_count = tk.Label(result_head, text="", bg=BG, fg=MUTED,
                                      font=(FONT, 8), anchor="w")
        self.command_count.pack(side="left")
        tk.Label(result_head, text="Select → edit → copy", bg=BG, fg=MUTED,
                 font=(FONT, 8)).pack(side="right")
        details = tk.Frame(self.body, bg=PANEL, highlightbackground=BORDER,
                           highlightthickness=1)
        details.pack(side="bottom", fill="x", pady=(6, 0))
        line = tk.Frame(details, bg=PANEL)
        line.pack(fill="x", padx=11, pady=(7, 1))
        self.command_machine_tag = tk.Label(line, text="SELECT A COMMAND", fg=ACCENT, bg=PANEL,
                                            font=(FONT, 8, 'bold'))
        self.command_machine_tag.pack(side='left')
        self.command_category_tag = tk.Label(line, text="", fg=MUTED, bg=PANEL,
                                             font=(FONT, 8))
        self.command_category_tag.pack(side='right')
        self.command_description_label = tk.Label(details, text="Select a result to view its command.",
                                                   fg=WHITE, bg=PANEL, font=(FONT, 9),
                                                   wraplength=410, justify='left', anchor='w')
        self.command_description_label.pack(fill='x', padx=11, pady=(2, 4))
        tk.Label(details, text='EDIT BEFORE COPYING  ·  CHANGES HERE ARE TEMPORARY',
                 fg=MUTED, bg=PANEL, font=(FONT, 7, 'bold'), anchor='w').pack(fill='x', padx=11, pady=(1, 4))
        self.command_code = tk.Text(details, height=6, wrap='word', undo=True, bg=INPUT, fg='#D3E4FF',
                                    font=('Consolas', 9), bd=0, padx=9, pady=5,
                                    highlightthickness=1, highlightbackground=BORDER)
        self.command_code.pack(fill='x', padx=11)
        self.command_code.bind('<Control-a>', self._command_select_all)
        self.command_code.bind('<Control-Return>', lambda _e: (self._copy_command(), 'break')[1])
        bottom = tk.Frame(details, bg=PANEL)
        bottom.pack(fill='x', padx=8, pady=(4, 6))
        self.command_star = action_label(bottom, '☆ Save', self._toggle_command_favorite,
                                         fg=SECONDARY, bg=PANEL, hover=CARD, font_size=8, padx=5, pady=4)
        self.command_star.pack(side='left')
        self.command_edit = action_label(bottom, 'Edit saved', self._edit_custom_command,
                                         fg=ACCENT, bg=PANEL, hover=CARD, font_size=8, padx=5, pady=4)
        self.command_edit.pack(side='left')
        self.command_delete = action_label(bottom, 'Delete', self._delete_custom_command,
                                           fg=DANGER, bg=PANEL, hover=CARD, font_size=8, padx=5, pady=4)
        self.command_delete.pack(side='left')
        self.command_reset = action_label(bottom, 'Reset', self._reset_command_draft,
                                          fg=SECONDARY, bg=PANEL, hover=CARD, font_size=8, padx=5, pady=4)
        self.command_reset.pack(side='left')
        action_label(bottom, 'Copy edited', self._copy_command, fg='#121622', bg=ACCENT,
                     hover='#BBC0FF', font_size=9, padx=8, pady=4).pack(side='right')
        self.command_feedback = tk.Label(details, text='Offline · Nothing is executed',
                                         fg=MUTED, bg=PANEL, font=(FONT, 8))
        self.command_feedback.pack(anchor='w', padx=12, pady=(0, 5))
        # Command first (left), description second (right); align Hebrew purposes to the right.
        self.command_tree = self._tree(self.body, ('Command', 'Purpose / Description'),
                                       (230, 185), rows=8, aligns=('w', 'e'))
        self.command_tree.bind('<<TreeviewSelect>>', self._select_command)
        self.command_tree.bind('<Double-1>', lambda _event: self._focus_command_editor())
        self.command_tree.bind('<Return>', lambda _event: self._focus_command_editor())
        self._style_command_modes()
        self._refresh_command_results()

    def _show_command_backup_menu(self):
        menu = tk.Menu(self.root, tearoff=False, bg=PANEL, fg=WHITE,
                       activebackground=ACCENT_DARK, activeforeground=WHITE)
        menu.add_command(label="Create new backup", command=self._create_command_backup)
        menu.add_command(label="Use existing backup", command=self._restore_command_backup)
        menu.tk_popup(self.root.winfo_rootx()+WIDTH-165, self.root.winfo_rooty()+195)

    def _create_command_backup(self):
        if not self.commands_file:
            self._warning("Backup", "Command library is unavailable.")
            return
        try:
            backup = cs.create_backup(self.commands_file)
            messagebox.showinfo("Commands backup", f"Backup created:\\n{backup}", parent=self.root)
        except (OSError, ValueError) as exc:
            self._warning("Backup failed", str(exc))

    def _restore_command_backup(self):
        if not self.commands_file:
            self._warning("Restore", "Command library is unavailable.")
            return
        self._modal = True
        try:
            filename = filedialog.askopenfilename(parent=self.root, title="Use existing commands backup",
                initialdir=str(self.commands_file.parent / "backups"),
                filetypes=[("JSON backup", "*.json")])
            if not filename:
                return
            if not messagebox.askyesno("Restore commands",
                    "Replace the active command library with the selected backup?\\n"
                    "Current commands will be overwritten. No automatic backup will be created.",
                    parent=self.root):
                return
            cs.restore_backup(self.commands_file, Path(filename))
            self._reload_command_library()
            self._refresh_command_catalog()
            messagebox.showinfo("Restore complete", "Command library restored.", parent=self.root)
        except (OSError, ValueError) as exc:
            self._warning("Restore failed", str(exc))
        finally:
            self._modal = False

    def _command_focus_in(self, _event=None):
        if self._command_placeholder_active:
            self._command_placeholder_active = False
            self.command_query.set('')
            self.command_search_entry.config(fg=WHITE)

    def _command_focus_out(self, _event=None):
        if not self.command_query.get():
            self._command_placeholder_active = True
            self.command_search_entry.config(fg=MUTED)
            self.command_query.set(self._command_placeholder)

    def _actual_command_query(self):
        return '' if self._command_placeholder_active and self.command_query.get() == self._command_placeholder else self.command_query.get()

    def _focus_command_search(self, _event=None):
        if self.current_tab == 'commands' and self.command_search_entry.winfo_exists():
            self.command_search_entry.focus_set()
            return 'break'

    def _clear_command_search(self):
        self.command_query.set('')
        self._focus_command_search()

    def _change_machine(self, _event=None):
        machine = self.machine_var.get()
        self.data['command_state']['machine'] = machine
        self.command_category_picker['values'] = [ch.ALL_CATEGORIES] + ch.categories_for(self.command_library, machine)
        self.command_category_var.set(ch.ALL_CATEGORIES)
        self._refresh_command_results()
        self.schedule_save()

    def _set_command_mode(self, mode):
        self.command_mode = mode
        self._style_command_modes()
        self._refresh_command_results()

    def _style_command_modes(self):
        for mode, button in self.command_modes.items():
            button.config(fg=ACCENT if self.command_mode == mode else SECONDARY,
                          bg=ACCENT_DARK if self.command_mode == mode else PANEL)

    def _refresh_command_results(self):
        if self.current_tab != 'commands' or not hasattr(self,'command_tree') or not self.command_tree.winfo_exists():
            return
        prefs = self.data['command_state']
        matches = ch.find_commands(self.command_library, query=self._actual_command_query(),
                                    machine=self.machine_var.get(), category=self.command_category_var.get(),
                                    mode=self.command_mode, favorites=prefs['favorites'], recent=prefs['recent'])
        self.command_filtered = matches[:ch.MAX_RESULTS]
        self.command_count.config(text=f"{len(matches)} results" +
                                  (f" · first {ch.MAX_RESULTS}" if len(matches)>ch.MAX_RESULTS else ''))
        selected = self.selected_command_id
        for iid in self.command_tree.get_children():
            self.command_tree.delete(iid)
        for item in self.command_filtered:
            desc = item['description'].replace('\n',' ')
            cmd = item['command'].replace('\n','  /  ')
            if self.machine_var.get() == ch.ALL_MACHINES:
                desc = f"{item['machine']} · {desc}"
            self.command_tree.insert('', 'end', iid=item['id'], values=(cmd, desc))
        if selected and self.command_tree.exists(selected):
            self.command_tree.selection_set(selected)
        elif self.command_filtered:
            self.command_tree.selection_set(self.command_filtered[0]['id'])
            self.selected_command_id = self.command_filtered[0]['id']
        else:
            self.selected_command_id = None
        self._render_command_details()
        if not self.command_filtered and self.machine_var.get() != ch.ALL_MACHINES:
            self.command_description_label.config(
                text="No matching reference commands. Use + New to add your own.")

    def _select_command(self, _event=None):
        selection = self.command_tree.selection()
        if selection:
            self.selected_command_id = selection[0]
            self._render_command_details()

    def _selected_command(self):
        for entry in self.command_filtered:
            if entry['id'] == self.selected_command_id:
                return entry
        return None

    def _command_select_all(self, _event=None):
        self.command_code.tag_add('sel', '1.0', 'end-1c')
        return 'break'

    def _focus_command_editor(self):
        if self._selected_command():
            self.command_code.focus_set()
            self.command_code.mark_set('insert', 'end-1c')

    def _reset_command_draft(self):
        item = self._selected_command()
        if item:
            self.command_code.delete('1.0', tk.END)
            self.command_code.insert('1.0', item['command'])
            self.command_feedback.config(text='Restored the saved command', fg=MUTED)
            self.command_code.focus_set()

    def _render_command_details(self):
        item = self._selected_command()
        self.command_code.delete('1.0', tk.END)
        if item:
            self.command_machine_tag.config(text=item['machine'] + ('  ·  MY COMMAND' if item.get('origin') == 'custom' else ''))
            self.command_category_tag.config(text=item['category'])
            self.command_description_label.config(text=item['description'])
            self.command_code.insert('1.0', item['command'])
            favorite = item['id'] in self.data['command_state']['favorites']
            self.command_star.config(text='★ Saved' if favorite else '☆ Save')
            if self.commands_file is not None:
                self.command_edit.pack(side='left', after=self.command_star)
                self.command_delete.pack(side='left', after=self.command_edit)
            else:
                self.command_edit.pack_forget()
                self.command_delete.pack_forget()
        else:
            self.command_machine_tag.config(text='NO RESULTS')
            self.command_category_tag.config(text='')
            self.command_description_label.config(text='Try another machine, keyword or category.')
            self.command_star.config(text='☆ Save')
            self.command_edit.pack_forget()
            self.command_delete.pack_forget()
        self.command_draft_id = item['id'] if item else None
        self.command_feedback.config(text='Draft edits are temporary · use Edit saved to save · Never executed', fg=MUTED)

    def _toggle_command_favorite(self):
        item=self._selected_command()
        if not item:
            return
        favs=self.data['command_state']['favorites']
        if item['id'] in favs:
            favs.remove(item['id'])
        else:
            favs.append(item['id'])
        self.schedule_save()
        if self.command_mode == 'favorites':
            self._refresh_command_results()
        else:
            self.command_star.config(text='★ Saved' if item['id'] in favs else '☆ Save')

    def _copy_command(self):
        item = self._selected_command() if self.current_tab == 'commands' else None
        if not item:
            return
        text = self.command_code.get('1.0', 'end-1c')
        if not text.strip():
            self._warning('Empty command', 'Enter command text before copying.')
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        prefs=self.data['command_state']
        prefs['recent']=ch.updated_recent(prefs['recent'],item['id'])
        self.schedule_save()
        self.command_feedback.config(text='Copied EDITED text · Not executed', fg=ACCENT)
        # Do not rebuild Recent results here: that would discard the edit after copying.

    def _refresh_command_catalog(self, *, machine=None, select_id=None):
        self.command_library = ch.merged_commands(self.bundled_commands, self.data['custom_commands'])
        self.machine_picker['values'] = [ch.ALL_MACHINES] + ch.machines_for(self.command_library, self.machine_catalog)
        if machine is not None:
            self.machine_var.set(machine)
            self.data['command_state']['machine'] = machine
        self.command_category_picker['values'] = [ch.ALL_CATEGORIES] + ch.categories_for(self.command_library, self.machine_var.get())
        self.command_category_var.set(ch.ALL_CATEGORIES)
        if hasattr(self, 'command_search_entry'):
            self._command_placeholder_active = False
            self.command_search_entry.config(fg=WHITE)
            self.command_query.set('')
        self.command_mode = 'all'
        self._style_command_modes()
        self.selected_command_id = select_id
        self._refresh_command_results()
        self.schedule_save()

    def _add_custom_command(self):
        self._show_custom_editor()

    def _edit_custom_command(self):
        item = self._selected_command()
        if item:
            self._show_custom_editor(item)

    def _delete_custom_command(self):
        item = self._selected_command()
        if not item:
            return
        self._modal = True
        try:
            yes = messagebox.askyesno('Delete custom command',
                f"Delete this command from {item['machine']}?\n\n{item['description']}\n\nThis cannot be undone.", parent=self.root)
        finally:
            self._modal = False
        if not yes:
            return
        if not self._save_library_change(lambda: cs.delete_command(self.commands_file, item)):
            return
        self._reload_command_library()
        prefs = self.data['command_state']
        prefs['favorites'] = [x for x in prefs['favorites'] if x != item['id']]
        prefs['recent'] = [x for x in prefs['recent'] if x != item['id']]
        self._refresh_command_catalog(machine=item['machine'])

    def _reload_command_library(self):
        self.bundled_commands = ch.load_library(self.commands_file) if self.commands_file else []
        self.machine_catalog = ch.load_machine_names(self.commands_file) if self.commands_file else []

    def _save_library_change(self, operation):
        if self.commands_file is None:
            self._warning('Command library unavailable',
                          self.commands_error or 'No writable commands.json found.')
            return False
        try:
            operation()
            return True
        except (OSError, ValueError, KeyError) as exc:
            self._warning('Could not save command', str(exc))
            return False

    def _show_custom_editor(self, entry=None):
        # Dialog protects the tray popup against disappearing when the form gains focus.
        if self.commands_file is None:
            self._warning('Command library unavailable',
                          self.commands_error or 'Place commands.json in the commands folder.')
            return
        current_machine = self.machine_var.get()
        self._modal = True
        dialog = tk.Toplevel(self.root)
        dialog.title('Edit command' if entry else 'Add command')
        dialog.configure(bg=BG)
        dialog.geometry('460x485')
        dialog.minsize(440, 460)
        left = max(0, min(self.root.winfo_rootx() + 10, self.root.winfo_screenwidth() - 460))
        top = max(0, min(self.root.winfo_rooty() + 65, self.root.winfo_screenheight() - 485 - 30))
        dialog.geometry(f'+{left}+{top}')
        dialog.transient(self.root)
        try:
            dialog.iconbitmap(str(self.asset_path('app.ico')))
        except (OSError, tk.TclError):
            pass
        dialog.grab_set()
        pane = tk.Frame(dialog, bg=BG)
        pane.pack(fill='both', expand=True, padx=18, pady=14)
        tk.Label(pane, text='EDIT COMMAND' if entry else 'NEW MACHINE COMMAND', bg=BG, fg=WHITE,
                 font=(FONT, 13, 'bold')).pack(anchor='w', pady=(0, 6))
        tk.Label(pane, text='Saved to commands.json · Manual backups only · Never executed', bg=BG, fg=MUTED,
                 font=(FONT, 9)).pack(anchor='w', pady=(0, 11))

        def labelled(text):
            tk.Label(pane, text=text, bg=BG, fg=SECONDARY, font=(FONT, 8, 'bold')).pack(anchor='w', pady=(6, 3))
        labelled('MACHINE')
        device = tk.StringVar(value=entry['machine'] if entry else (current_machine if current_machine != ch.ALL_MACHINES else ''))
        picker = ttk.Combobox(pane, textvariable=device, state='normal', font=(FONT, 10),
                              values=ch.machines_for(self.command_library, self.machine_catalog))
        picker.pack(fill='x', ipady=3)
        labelled('PURPOSE / DESCRIPTION  (also searchable)')
        purpose = tk.StringVar(value=entry['description'] if entry else '')
        purpose_input = self._entry(pane, purpose)
        purpose_input.pack(fill='x', ipady=6)
        labelled('CATEGORY')
        category = tk.StringVar(value=entry['category'] if entry else 'Custom')
        category_picker = ttk.Combobox(pane, textvariable=category, state='normal', font=(FONT, 10),
                                       values=ch.categories_for(self.command_library, device.get()) or ['Custom'])
        category_picker.pack(fill='x', ipady=3)
        labelled('COMMAND  (multiline allowed)')
        command_box = tk.Text(pane, wrap='word', height=4, undo=True, bg=INPUT, fg=WHITE,
                              font=('Consolas', 10), insertbackground=ACCENT, bd=0,
                              highlightbackground=BORDER, highlightthickness=1, padx=8, pady=7)
        command_box.pack(fill='both', expand=True)
        if entry:
            # Start from the current on-screen draft so edits can be saved intentionally.
            visible_draft = (self.command_code.get('1.0', 'end-1c')
                             if self.command_draft_id == entry['id'] else entry['command'])
            command_box.insert('1.0', visible_draft)
        tk.Label(pane, text='Avoid storing passwords, private keys or secrets in commands.',
                 bg=BG, fg=MUTED, font=(FONT, 8)).pack(anchor='w', pady=(7, 0))
        actions = tk.Frame(pane, bg=BG)
        actions.pack(fill='x', pady=(9, 0))

        def close():
            if dialog.winfo_exists():
                try:
                    dialog.grab_release()
                except tk.TclError:
                    pass
                dialog.destroy()
            self._modal = False
            try:
                self.root.focus_force()
            except tk.TclError:
                pass

        def store():
            try:
                record = ch.validate_custom_command(device.get(), category.get(), purpose.get(),
                    command_box.get('1.0', 'end-1c'))
                if entry:
                    record['id'] = entry['id']
            except ValueError as exc:
                messagebox.showwarning('Check command details', str(exc), parent=dialog)
                return
            if not self._save_library_change(
                    lambda: cs.save_command(self.commands_file, record, original=entry)):
                return
            self._reload_command_library()
            close()
            self._refresh_command_catalog(machine=record['machine'], select_id=record['id'])

        dialog.protocol('WM_DELETE_WINDOW', close)
        dialog.bind('<Escape>', lambda _e: close())
        action_label(actions, 'Cancel', close, bg=PANEL, fg=SECONDARY,
                     padx=12, pady=7).pack(side='right', padx=(8, 0))
        action_label(actions, 'Save command', store, bg=ACCENT, fg='#121622',
                     padx=12, pady=7).pack(side='right')
        dialog.after(40, lambda: purpose_input.focus_set() if purpose_input.winfo_exists() else None)

    def _build_ports(self):
        self._section_title(self.body, "TCP port checker", "Check one IP and selected TCP ports", "Export CSV", self._export_ports)
        tools = self.data["tools"]
        self.host_var = tk.StringVar(value=tools.get("target", "192.168.1.1"))
        self.single_port_var = tk.StringVar(value=tools.get("single_port", "443"))
        self.custom_ports_var = tk.StringVar(value=tools.get("custom_ports", ""))
        self.port_mode = tk.StringVar(value=tools.get("mode", "single"))

        label = tk.Label(self.body, text="TARGET IP (IPv4 or IPv6)", bg=BG, fg=MUTED,
                         font=(FONT, 8, "bold"))
        label.pack(anchor="w", pady=(0, 5))
        self._entry(self.body, self.host_var).pack(fill="x", ipady=8, pady=(0, 10))
        self.host_var.trace_add("write", lambda *_: self._remember_port_preferences())

        modes = tk.Frame(self.body, bg=BG)
        modes.pack(fill="x", pady=(0, 6))
        self.port_modes = modes
        for mode, label in (("single", "Single port"), ("selected", "Selected ports")):
            tk.Radiobutton(modes, text=label, variable=self.port_mode, value=mode,
                           command=self._port_mode_changed, fg=WHITE, bg=BG,
                           selectcolor=PANEL, activebackground=BG,
                           activeforeground=ACCENT, font=(FONT, 9),
                           highlightthickness=0).pack(side="left", padx=(0, 13))
        self.port_options_button = action_label(modes, "Hide ports", self._toggle_port_inputs,
                                                fg=ACCENT, bg=BG, hover=PANEL,
                                                padx=6, pady=4, font_size=8)
        self.port_options_button.pack(side="right")

        self.port_single_frame = tk.Frame(self.body, bg=BG)
        self.port_selected_frame = tk.Frame(self.body, bg=BG)
        tk.Label(self.port_single_frame, text="TCP PORT  (1–65535)", bg=BG, fg=MUTED,
                 font=(FONT, 8, "bold")).pack(anchor="w", pady=(3, 5))
        self._entry(self.port_single_frame, self.single_port_var).pack(fill="x", ipady=8, pady=(0, 9))
        self.single_port_var.trace_add("write", lambda *_: self._remember_port_preferences())
        tk.Label(self.port_selected_frame, text="COMMON PORTS", bg=BG, fg=MUTED,
                 font=(FONT, 8, "bold")).pack(anchor="w", pady=(1, 6))
        checks = tk.Frame(self.port_selected_frame, bg=BG)
        checks.pack(fill="x")
        self.port_checks = {}
        chosen = tools.get("selected_ports", [22, 80, 443, 3389])
        if not isinstance(chosen, list):
            chosen = []
        for i, (port, service) in enumerate(net.COMMON_PORTS):
            flag = tk.BooleanVar(value=port in chosen)
            self.port_checks[port] = flag
            tk.Checkbutton(checks, text=f"{port} {service}", variable=flag,
                           command=self._remember_port_preferences, bg=BG, fg=WHITE,
                           activebackground=BG, activeforeground=WHITE,
                           selectcolor=PANEL, font=(FONT, 8),
                           highlightthickness=0, anchor="w", width=12
                           ).grid(row=i//4, column=i%4, sticky="w")
        tk.Label(self.port_selected_frame, text="ADDITIONAL PORTS  (e.g. 8000, 8443, 9000-9003)",
                 bg=BG, fg=MUTED, font=(FONT, 8, "bold")).pack(anchor="w", pady=(9, 5))
        self._entry(self.port_selected_frame, self.custom_ports_var).pack(fill="x", ipady=7, pady=(0, 8))
        self.custom_ports_var.trace_add("write", lambda *_: self._remember_port_preferences())
        self._port_mode_changed()

        commands = tk.Frame(self.body, bg=BG)
        commands.pack(fill="x", pady=(4, 3))
        action_label(commands, "Run TCP check", self._start_scan, fg="#121622",
                     bg=ACCENT, hover="#BBC0FF", font_size=9).pack(side="left")
        action_label(commands, "Stop", self._stop_scan, fg=SECONDARY,
                     bg=BG, hover=CARD, font_size=9).pack(side="left", padx=(8, 0))
        self.scan_info = tk.Label(self.body, text="Connect test only • No UDP scanning",
                                  bg=BG, fg=MUTED, font=(FONT, 9), anchor="w")
        self.scan_info.pack(fill="x", pady=(9, 1))
        self.port_tree = self._tree(self.body, ("Port", "Service", "TCP status", "Time"),
                                    (72, 115, 117, 73))
        for result in sorted(self.port_results, key=lambda item: item["port"]):
            self._add_port_result(result)
        if self.scanning:
            self.scan_info.config(text="Scan is running…", fg=ACCENT)

    def _port_mode_changed(self):
        self.port_single_frame.pack_forget()
        self.port_selected_frame.pack_forget()
        if self.port_mode.get() == "single":
            self.port_options_button.pack_forget()
            self.port_single_frame.pack(fill="x", after=self.port_modes)
        else:
            self.port_options_button.pack(side="right")
            self.port_options_button.config(text="Hide ports" if self.port_inputs_expanded else "Edit ports")
            if self.port_inputs_expanded:
                self.port_selected_frame.pack(fill="x", after=self.port_modes)
        self._remember_port_preferences()

    def _toggle_port_inputs(self):
        self.port_inputs_expanded = not self.port_inputs_expanded
        self._port_mode_changed()

    def _remember_port_preferences(self):
        self.data["tools"] = {
            "target": self.host_var.get(), "single_port": self.single_port_var.get(),
            "custom_ports": self.custom_ports_var.get(), "mode": self.port_mode.get(),
            "selected_ports": [p for p, flag in self.port_checks.items() if flag.get()]
            if hasattr(self, "port_checks") else self.data["tools"].get("selected_ports", []),
        }
        self.schedule_save()

    def _start_scan(self):
        if self.scanning:
            self._warning("TCP check", "A scan is already running. Stop it before starting another.")
            return
        try:
            ip = net.parse_target(self.host_var.get())
            if self.port_mode.get() == "single":
                ports = net.parse_ports(self.single_port_var.get())
                if len(ports) != 1:
                    raise ValueError("Single-port mode accepts exactly one port.")
            else:
                ports = [p for p, v in self.port_checks.items() if v.get()]
                if self.custom_ports_var.get().strip():
                    ports.extend(net.parse_ports(self.custom_ports_var.get()))
                ports = sorted(set(ports))
                if not ports:
                    raise ValueError("Select at least one TCP port or enter additional ports.")
                if len(ports) > net.MAX_PORTS:
                    raise ValueError(f"Maximum {net.MAX_PORTS} ports per check.")
        except ValueError as exc:
            self._warning("Invalid scan input", str(exc))
            return
        self.port_results = []
        for item in self.port_tree.get_children():
            self.port_tree.delete(item)
        if self.port_mode.get() == "selected":
            # Let the result table expand after the user has selected ports.
            self.port_inputs_expanded = False
            self._port_mode_changed()
        self.scanning = True
        self.scan_cancel = threading.Event()
        self.scan_token += 1
        token = self.scan_token
        self.scan_info.config(text=f"Checking {len(ports)} TCP port(s) on {ip}…", fg=ACCENT)

        def worker():
            try:
                for result in net.scan_tcp_ports(ip, ports, cancel=self.scan_cancel):
                    self.events.put(("port_result", (token, result)))
            except Exception as exc:
                self.events.put(("port_error", (token, str(exc))))
            finally:
                self.events.put(("port_done", token))
        threading.Thread(target=worker, name="PocketDeskTcpScan", daemon=True).start()

    def _stop_scan(self):
        if self.scanning:
            self.scan_cancel.set()
            if self.current_tab == "ports":
                self.scan_info.config(text="Stopping scan…", fg=SECONDARY)

    def _add_port_result(self, item):
        port = item["port"]
        self.port_tree.insert("", "end", values=(port, item["service"], item["status"],
                                                   f"{item['ms']} ms"))

    def _export_ports(self):
        if not self.port_results:
            self._warning("Export ports", "Run a TCP check first.")
            return
        self._export_results("pocketdesk-ports.csv", ["port", "service", "status", "ms"],
                             sorted(self.port_results, key=lambda item: item["port"]))

    # ---- Offline IPv4 subnet calculator -----------------------------------

    def _build_subnet(self):
        self._section_title(self.body, "Subnet calculator", "IPv4 · CIDR · Address ranges", "Copy summary", self._copy_subnet_summary)
        inputs = tk.Frame(self.body, bg=BG)
        inputs.pack(fill="x", pady=(0, 7))
        tk.Label(inputs, text="IP ADDRESS", bg=BG, fg=MUTED, font=(FONT, 8, "bold")).grid(row=0, column=0, sticky="w", pady=(0, 5))
        tk.Label(inputs, text="CIDR / MASK", bg=BG, fg=MUTED, font=(FONT, 8, "bold")).grid(row=0, column=1, sticky="w", padx=(10, 0), pady=(0, 5))
        prefs = self.data["subnet"]
        self.subnet_ip_var = tk.StringVar(value=prefs["ip"])
        self.subnet_prefix_var = tk.StringVar(value=prefs["prefix"])
        self._entry(inputs, self.subnet_ip_var).grid(row=1, column=0, sticky="ew", ipady=9)
        self._entry(inputs, self.subnet_prefix_var).grid(row=1, column=1, sticky="ew", padx=(10, 0), ipady=9)
        inputs.columnconfigure(0, weight=3)
        inputs.columnconfigure(1, weight=2)
        for child in inputs.winfo_children():
            if isinstance(child, tk.Entry):
                child.bind("<Return>", lambda _e: self._calculate_subnet())

        first_actions = tk.Frame(self.body, bg=BG)
        first_actions.pack(fill="x", pady=(1, 10))
        action_label(first_actions, "Calculate", self._calculate_subnet, fg="#121622", bg=ACCENT,
                     hover="#BBC0FF", padx=12, pady=8, font_size=9).pack(side="left")
        action_label(first_actions, "Copy network", self._copy_subnet_network, fg=ACCENT,
                     bg=PANEL, hover=CARD, padx=10, pady=7, font_size=8).pack(side="left", padx=(9, 0))
        self.subnet_status = tk.Label(first_actions, text="", bg=BG, fg=MUTED, font=(FONT, 8), anchor="e")
        self.subnet_status.pack(side="right", fill="x", expand=True)

        card = tk.Frame(self.body, bg=PANEL, highlightthickness=1, highlightbackground=BORDER)
        card.pack(fill="x")
        tk.Label(card, text="NETWORK DETAILS", fg=SECONDARY, bg=PANEL,
                 font=(FONT, 8, "bold")).pack(anchor="w", padx=12, pady=(11, 7))
        facts = tk.Frame(card, bg=PANEL)
        facts.pack(fill="x", padx=12, pady=(0, 9))
        self.subnet_fact_labels = {}
        rows = (
            ("Network", "cidr"), ("Mask", "mask"), ("Wildcard", "wildcard"),
            ("Broadcast", "broadcast"), ("First usable", "first"), ("Last usable", "last"),
            ("Usable hosts", "usable"), ("Total addresses", "total"),
        )
        for i, (name, key) in enumerate(rows):
            tk.Label(facts, text=name, bg=PANEL, fg=MUTED, font=(FONT, 9), anchor="w").grid(
                row=i, column=0, sticky="w", pady=3)
            output = tk.Label(facts, text="—", bg=PANEL, fg=WHITE,
                              font=(FONT, 9, "bold"), anchor="e")
            output.grid(row=i, column=1, sticky="e", pady=3)
            self.subnet_fact_labels[key] = output
        facts.columnconfigure(1, weight=1)

        tk.Label(self.body, text="SUBDIVIDE THE NETWORK", bg=BG, fg=SECONDARY,
                 font=(FONT, 8, "bold")).pack(anchor="w", pady=(16, 8))
        subnet_actions = tk.Frame(self.body, bg=BG)
        subnet_actions.pack(fill="x")
        tk.Label(subnet_actions, text="New prefix", fg=MUTED, bg=BG,
                 font=(FONT, 9)).pack(side="left", padx=(0, 8))
        self.subnet_split_var = tk.StringVar(value=prefs["split"])
        self.subnet_split_choice = ttk.Combobox(subnet_actions, textvariable=self.subnet_split_var,
                                                 state="readonly", width=6,
                                                 values=[f"/{n}" for n in range(24, 33)])
        self.subnet_split_choice.pack(side="left")
        action_label(subnet_actions, "Split", self._split_subnet, fg="#121622", bg=ACCENT,
                     hover="#BBC0FF", padx=9, pady=6, font_size=8).pack(side="left", padx=(9, 0))
        action_label(subnet_actions, "Copy selected", self._copy_selected_subnet, fg=ACCENT,
                     bg=PANEL, hover=CARD, padx=7, pady=6, font_size=8).pack(side="right")
        self.subnet_split_info = tk.Label(self.body, text="", bg=BG, fg=MUTED,
                                          font=(FONT, 8), anchor="w")
        self.subnet_split_info.pack(fill="x", pady=(9, 0))
        self.subnet_tree = self._tree(self.body, ("Subnets", "Hosts", "Usable range"),
                                       (142, 70, 205), rows=6, aligns=("w", "center", "w"))
        self.subnet_tree.bind("<Double-1>", lambda _e: self._copy_selected_subnet())
        self._calculate_subnet()

    def _calculate_subnet(self):
        try:
            details = subnet.calculate(self.subnet_ip_var.get(), self.subnet_prefix_var.get())
        except ValueError as exc:
            self.subnet_details = None
            self.subnet_status.config(text="Invalid input", fg=DANGER)
            self.subnet_split_info.config(text=str(exc), fg=DANGER)
            for output in self.subnet_fact_labels.values():
                output.config(text="—")
            self._clear_subnet_rows()
            return
        self.subnet_details = details
        for key, output in self.subnet_fact_labels.items():
            value = details[key]
            output.config(text=f"{value:,}" if isinstance(value, int) else str(value))
        self.subnet_status.config(text="Calculated locally", fg=ACCENT)
        available = [f"/{n}" for n in range(details["prefix"], 33)]
        previously = self.subnet_split_var.get()
        self.subnet_split_choice.config(values=available)
        self.subnet_split_var.set(previously if previously in available else available[min(2, len(available)-1)])
        self._split_subnet()
        self._remember_subnet()

    def _clear_subnet_rows(self):
        self.subnet_children = []
        for iid in self.subnet_tree.get_children():
            self.subnet_tree.delete(iid)

    def _split_subnet(self):
        self._clear_subnet_rows()
        if not self.subnet_details:
            return
        try:
            child = subnet.split_subnets(self.subnet_details["cidr"], self.subnet_split_var.get())
        except ValueError as exc:
            self.subnet_split_info.config(text=str(exc), fg=DANGER)
            return
        self.subnet_children = child['rows']
        self._remember_subnet()
        for row in self.subnet_children:
            self.subnet_tree.insert("", tk.END,
                                    values=(row['cidr'], f"{row['usable']:,}", row['range']))
        count = f"{child['count']:,} subnet(s)"
        self.subnet_split_info.config(text=(f"{count} · showing first {child['shown']}" if child['truncated']
                                           else count), fg=MUTED)

    def _remember_subnet(self):
        self.data["subnet"] = {"ip": self.subnet_ip_var.get(),
                               "prefix": self.subnet_prefix_var.get(),
                               "split": self.subnet_split_var.get()}
        self.schedule_save()

    def _copy_subnet_network(self):
        if self.subnet_details:
            self._copy_subnet_text(self.subnet_details['cidr'])

    def _copy_subnet_summary(self):
        if self.subnet_details:
            self._copy_subnet_text(subnet.summary_text(self.subnet_details))

    def _copy_selected_subnet(self):
        selection = self.subnet_tree.selection()
        if not selection:
            self.subnet_status.config(text="Choose a subnet first", fg=DANGER)
            return
        self._copy_subnet_text(str(self.subnet_tree.item(selection[0], "values")[0]))

    def _copy_subnet_text(self, text: str):
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.subnet_status.config(text="Copied", fg=ACCENT)

    # ---- IEEE bulk MAC address vendor lookup ------------------------------

    def _build_mac(self):
        self._section_title(self.body, "Bulk MAC vendors", "Identify manufacturers from MAC prefixes", "Update IEEE DB", self._update_vendors)
        status_line = tk.Frame(self.body, bg=BG)
        status_line.pack(fill="x", pady=(0, 12))
        self.vendor_info = tk.Label(status_line, text=self._vendor_summary(), bg=BG,
                                    fg=MUTED, anchor="w", font=(FONT, 8))
        self.vendor_info.pack(side="left", fill="x", expand=True)
        action_label(status_line, "Import CSV", self._import_vendors, fg=ACCENT,
                     bg=PANEL, hover=CARD, padx=8, pady=5, font_size=8).pack(side="right")
        tk.Label(self.body, text="PASTE MAC ADDRESSES  (one per line or comma-separated)",
                 bg=BG, fg=MUTED, font=(FONT, 8, "bold")).pack(anchor="w", pady=(0, 6))
        self.mac_input = tk.Text(self.body, bg=INPUT, fg=WHITE, insertbackground=ACCENT,
                                 relief="flat", highlightthickness=1,
                                 highlightbackground=BORDER, highlightcolor=ACCENT,
                                 font=("Consolas", 10), wrap="none", height=6, padx=9, pady=8)
        self.mac_input.pack(fill="x", pady=(0, 10))
        self.mac_input.insert("1.0", self.mac_draft)
        actions = tk.Frame(self.body, bg=BG)
        actions.pack(fill="x")
        action_label(actions, "Check vendors", self._run_mac_lookup, fg="#121622", bg=ACCENT,
                     hover="#BBC0FF", font_size=9).pack(side="left", padx=(0, 7))
        action_label(actions, "Copy results", self._copy_mac_results, fg=SECONDARY,
                     bg=PANEL, hover=CARD, font_size=9).pack(side="left", padx=(0, 6))
        action_label(actions, "Export CSV", self._export_mac, fg=SECONDARY,
                     bg=PANEL, hover=CARD, font_size=9).pack(side="left")
        self.mac_info = tk.Label(self.body, text="Up to 5,000 addresses per batch • Lookups stay local",
                                  bg=BG, fg=MUTED, font=(FONT, 9), anchor="w")
        self.mac_info.pack(fill="x", pady=(12, 4))
        self.mac_tree = self._tree(self.body, ("MAC address", "Vendor / result", "Registry"),
                                   (133, 213, 80))
        for item in self.mac_results[:500]:
            self.mac_tree.insert("", "end", values=(item["mac"], item["vendor"], item["registry"]))
        if len(self.mac_results) > 500:
            self.mac_info.config(text="Showing first 500 rows; export/copy includes all results")

    def _vendor_summary(self):
        return (f"IEEE database: {len(self.vendors):,} prefixes • Updated {self.vendor_date}"
                if self.vendors else f"IEEE database: {self.vendor_date} • Click Update IEEE DB")

    def _update_vendors(self):
        if self.updating_vendors:
            return
        self.updating_vendors = True
        if self.current_tab == "mac":
            self.vendor_info.config(text="Downloading registries from IEEE…", fg=ACCENT)
        def worker():
            try:
                count = net.download_ieee_database(
                    self.vendor_file, lambda note: self.events.put(("vendor_progress", note)))
                self.events.put(("vendor_done", count))
            except Exception as exc:
                self.events.put(("vendor_error", str(exc)))
        threading.Thread(target=worker, name="PocketDeskIEEEUpdate", daemon=True).start()

    def _import_vendors(self):
        if self.updating_vendors:
            return
        self._modal = True
        try:
            files = filedialog.askopenfilenames(parent=self.root,
                                                title="Import official IEEE registry CSV files",
                                                filetypes=[("CSV files", "*.csv")])
        finally:
            self._modal = False
        if not files:
            return
        self.updating_vendors = True
        if self.current_tab == "mac":
            self.vendor_info.config(text="Importing IEEE assignments…", fg=ACCENT)
        def worker():
            try:
                count = net.import_ieee_csv_files([Path(p) for p in files], self.vendor_file)
                self.events.put(("vendor_done", count))
            except Exception as exc:
                self.events.put(("vendor_error", str(exc)))
        threading.Thread(target=worker, name="PocketDeskIEEEImport", daemon=True).start()

    def _run_mac_lookup(self):
        self.mac_draft = self.mac_input.get("1.0", "end-1c")
        try:
            self.mac_results = net.batch_lookup(self.mac_draft, self.vendors)
        except ValueError as exc:
            self._warning("MAC lookup", str(exc))
            return
        for item in self.mac_tree.get_children():
            self.mac_tree.delete(item)
        for item in self.mac_results[:500]:
            self.mac_tree.insert("", "end", values=(item["mac"], item["vendor"], item["registry"]))
        valid = sum(result["vendor"] != "Invalid MAC" for result in self.mac_results)
        message = f"{valid}/{len(self.mac_results)} valid • {len(self.mac_results)} rows"
        if len(self.mac_results) > 500:
            message += " • Showing first 500; exports contain all"
        self.mac_info.config(text=message, fg=ACCENT)

    def _copy_mac_results(self):
        if not self.mac_results:
            self._warning("Copy results", "Check a list of MAC addresses first.")
            return
        lines = ["MAC Address\tVendor\tRegistry".replace("\t", "	")]
        for result in self.mac_results:
            lines.append("	".join((result["mac"], result["vendor"], result["registry"])))
        self.root.clipboard_clear()
        self.root.clipboard_append("\n".join(lines))
        self.mac_info.config(text=f"Copied {len(self.mac_results)} results to clipboard", fg=ACCENT)

    def _export_mac(self):
        if not self.mac_results:
            self._warning("Export MAC lookup", "Check a list of MAC addresses first.")
            return
        self._export_results("pocketdesk-mac-vendors.csv",
                             ["input", "mac", "vendor", "registry"], self.mac_results)

    def _export_results(self, filename, columns, rows):
        self._modal = True
        try:
            chosen = filedialog.asksaveasfilename(parent=self.root, title="Export CSV",
                                                  defaultextension=".csv", initialfile=filename,
                                                  filetypes=[("CSV files", "*.csv")])
        finally:
            self._modal = False
        if not chosen:
            return
        try:
            net.export_csv(Path(chosen), columns, rows)
        except OSError as exc:
            self._warning("Export failed", str(exc))

    def open_link(self, url):
        webbrowser.open(url)
        if not self.pinned:
            self.hide()

    def _import_notepad_body(self, note, content):
        """Apply saved external edits without destroying the note's other fields."""
        note["body"] = content
        if (self.current_tab == "notes" and self.data["active_note"] == note["id"]
                and hasattr(self, "note_body") and self.note_body.winfo_exists()):
            self._loading_note = True
            try:
                self.note_body.delete("1.0", tk.END)
                self.note_body.insert("1.0", content)
                if self.bidi_editor is not None:
                    self.bidi_editor.set_text(content)
                self._apply_note_direction(note)
                self.note_body.edit_modified(False)
                self.note_body.edit_reset()
            finally:
                self._loading_note = False
        self.schedule_save()

    def _notepad_poll(self):
        """Import Notepad changes after Ctrl+S; protect simultaneous Pocket edits."""
        try:
            notes_by_id = {note["id"]: note for note in self.data["notes"]}
            for note_id, session in list(self._notepad_sessions.items()):
                note = notes_by_id.get(note_id)
                if note is None:
                    self._notepad_sessions.pop(note_id, None)
                    continue
                path = session["path"]
                try:
                    external = note_sync.read_text(path)
                except FileNotFoundError:
                    # A deleted working file may be recreated on the next Open.
                    self._notepad_sessions.pop(note_id, None)
                    continue
                except (OSError, UnicodeError) as exc:
                    print(f"Pocket Notepad read failed: {exc}", file=sys.stderr)
                    continue
                if external == session["baseline"] or external == session.get("dismissed"):
                    continue
                # Flush the current widget before comparing versions. A modified
                # event might still be waiting in Tk's event queue.
                if self.current_tab == "notes" and self.data["active_note"] == note_id:
                    self._flush_current_note()
                if note["body"] != session["baseline"]:
                    self._modal = True
                    try:
                        answer = messagebox.askyesnocancel(
                            "Note changed in two places",
                            "This note changed in both Pocket and Notepad.\\n\\n"
                            "Yes: use Notepad's saved text.\\n"
                            "No: use Pocket's text (a recovery copy of Notepad is kept).\\n"
                            "Cancel: leave both versions unchanged.",
                            parent=self.root)
                    finally:
                        self._modal = False
                    if answer is None:
                        session["dismissed"] = external
                        continue
                    if answer is False:
                        try:
                            recovery = note_sync.preserve_conflict(path, external)
                            note_sync.write_text(path, note["body"])
                        except OSError as exc:
                            messagebox.showerror("Notepad sync failed", str(exc), parent=self.root)
                            session["dismissed"] = external
                            continue
                        session["baseline"] = note["body"]
                        session["dismissed"] = None
                        print(f"Pocket preserved external edit at {recovery}", file=sys.stderr)
                        continue
                self._import_notepad_body(note, external)
                session["baseline"] = external
                session["dismissed"] = None
        finally:
            if self.root.winfo_exists():
                self.root.after(1200, self._notepad_poll)

    def open_notepad(self):
        """Edit a note using its stable local file; saved changes sync into Pocket."""
        if sys.platform != "win32":
            messagebox.showinfo("Windows only", "Opening notes in Windows Notepad requires Windows.",
                                parent=self.root)
            return
        note = self.active_note()
        if not note:
            return
        self._flush_current_note()
        folder = self.path.parent / "notepad"
        try:
            path = note_sync.note_path(folder, note["id"])
            session = self._notepad_sessions.get(note["id"])
            if session is None:
                if path.exists():
                    external = note_sync.read_text(path)
                    if external != note["body"]:
                        self._modal = True
                        try:
                            answer = messagebox.askyesnocancel(
                                "Existing Notepad edits",
                                "A saved Notepad file differs from this Pocket note.\\n\\n"
                                "Yes: import the Notepad version.\\n"
                                "No: use Pocket's version (preserve a recovery copy).\\n"
                                "Cancel: do not open.",
                                parent=self.root)
                        finally:
                            self._modal = False
                        if answer is None:
                            return
                        if answer:
                            self._import_notepad_body(note, external)
                        else:
                            note_sync.preserve_conflict(path, external)
                            note_sync.write_text(path, note["body"])
                else:
                    note_sync.write_text(path, note["body"])
                self._notepad_sessions[note["id"]] = {"path": path, "baseline": note["body"]}
            # Reopening a session must never overwrite unsaved Notepad edits.
            subprocess.Popen(["notepad.exe", str(path)])
        except (OSError, ValueError, UnicodeError) as exc:
            messagebox.showerror("Notepad", str(exc), parent=self.root)

    def toggle_pin(self):
        self.pinned = not self.pinned
        self.pin_button.config(text="PINNED" if self.pinned else "PIN",
                               bg=ACCENT_DARK if self.pinned else PANEL,
                               fg=ACCENT if self.pinned else SECONDARY)

    def schedule_save(self):
        if self._save_job is not None:
            self.root.after_cancel(self._save_job)
        self._save_job = self.root.after(550, self._write_now)

    def _write_now(self):
        if self._save_job is not None:
            self.root.after_cancel(self._save_job)
            self._save_job = None
        try:
            save_data(self.path, self.data)
        except OSError as exc:
            if self.current_tab == "notes":
                self.save_status.config(text="Save failed!", fg=DANGER)
            print(f"PocketDesk save failed: {exc}", file=sys.stderr)
            return
        if self.current_tab == "notes":
            self.save_status.config(text="Autosaved", fg=MUTED)

    def _check_tray(self):
        if self.tray and self.tray.error:
            self.root.deiconify()
            self.root.overrideredirect(False)
            messagebox.showwarning("System tray unavailable",
                                   "PocketDesk could not start its tray icon. Running as a normal window.\n\n" + str(self.tray.error),
                                   parent=self.root)

    def _focus_lost(self, _event):
        if self.preview or self.pinned or self._modal or self._dragging_window:
            return
        self.root.after(170, self._maybe_hide)

    def _maybe_hide(self):
        if self.preview or self.pinned or self._modal or self._dragging_window:
            return
        if self.root.state() == "normal" and self.root.focus_displayof() is None:
            self.hide()

    def _screen_work_area(self, x: int, y: int) -> tuple[int, int, int, int]:
        if sys.platform == "win32":
            return monitor_work_area(x, y)
        return (0, 0, self.root.winfo_screenwidth(), self.root.winfo_screenheight())

    def _place_popup(self, xy):
        """Restore the user's position, or anchor to the tray until first drag.

        Clamp to the nearest available monitor after screen/resolution changes.
        All tabs use the same height, so changing tabs won't move the window.
        """
        self.root.update_idletasks()
        saved = normalize_window_position(self.data.get("window_position"))
        if saved is not None:
            px, py = saved["x"], saved["y"]
            left, top, right, bottom = self._screen_work_area(px + WIDTH // 2, py + HEIGHT // 2)
            height = min(HEIGHT, max(420, bottom - top - 16))
            px, py = clamp_window_position(px, py, WIDTH, height, (left, top, right, bottom))
        elif xy and sys.platform == "win32":
            x, y = xy
            left, top, right, bottom = self._screen_work_area(x, y)
            height = min(HEIGHT, max(420, bottom - top - 16))
            px = max(left + 8, min(x - WIDTH + 32, right - WIDTH - 8))
            py = (bottom - height - 9) if y > (top + bottom) / 2 else (top + 9)
        else:
            screen_h = self.root.winfo_screenheight()
            height = min(HEIGHT, max(420, screen_h - 85))
            px = max(0, self.root.winfo_screenwidth() - WIDTH - 35)
            py = max(0, screen_h - height - 85)
        if self.current_tab == "commands" and hasattr(self, "command_tree") and self.command_tree.winfo_exists():
            self.command_code.configure(height=6 if height >= 770 else 5)
            visible_rows = max(2, min(8, 8 + (height - HEIGHT) // 27))
            self.command_tree.configure(height=visible_rows)
        self.root.geometry(f"{WIDTH}x{height}{px:+d}{py:+d}")

    def _begin_window_drag(self, event):
        self._dragging_window = True
        self._drag_moved = False
        self._drag_origin = (event.x_root, event.y_root,
                             self.root.winfo_x(), self.root.winfo_y())

    def _continue_window_drag(self, event):
        if not self._dragging_window or self._drag_origin is None:
            return
        start_x, start_y, left, top = self._drag_origin
        dx, dy = event.x_root - start_x, event.y_root - start_y
        if not self._drag_moved and max(abs(dx), abs(dy)) < 3:
            return
        self._drag_moved = True
        px, py = left + dx, top + dy
        self.root.geometry(f"{px:+d}{py:+d}")

    def _finish_window_drag(self, event):
        if not self._dragging_window:
            return
        try:
            self._continue_window_drag(event)
            if self._drag_moved:
                px, py = self.root.winfo_x(), self.root.winfo_y()
                area = self._screen_work_area(event.x_root, event.y_root)
                px, py = clamp_window_position(px, py, self.root.winfo_width(),
                                                self.root.winfo_height(), area)
                self.root.geometry(f"{px:+d}{py:+d}")
                self.data["window_position"] = {"x": px, "y": py}
                self._flush_current_note()
                self._write_now()
        finally:
            self._drag_origin = None
            self._drag_moved = False
            self._dragging_window = False

    def reset_window_position(self):
        """Restore the original tray-anchored placement, including after monitor changes."""
        self.data["window_position"] = None
        self._place_popup(self._last_tray_xy)
        self._flush_current_note()
        self._write_now()

    def _show_header_menu(self, event):
        if self._header_context_menu is None:
            self._header_context_menu = tk.Menu(self.root, tearoff=False, bg=PANEL, fg=WHITE,
                                                activebackground=ACCENT_DARK, activeforeground=WHITE,
                                                bd=1, relief="flat")
            self._header_context_menu.add_command(label="Reset window position",
                                                  command=self.reset_window_position)
        try:
            self._header_context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self._header_context_menu.grab_release()

    def show(self, xy=None):
        self._last_tray_xy = xy
        self._place_popup(xy)
        self.root.deiconify()
        self.root.lift()
        if not self.preview:
            self.root.attributes("-topmost", True)
        self.root.focus_force()

    def hide(self):
        self._write_now()
        if self.preview or not self.tray or self.tray.error:
            self.root.iconify()
        else:
            self.root.withdraw()

    def toggle(self, xy=None):
        # The tray icon and global hotkey use the same action. The latter
        # must also reopen an iconified window if the tray is unavailable.
        if self.root.state() in ("withdrawn", "iconic"):
            self.show(xy)
        else:
            self.hide()

    def _reminder_poll(self):
        """Deliver a due reminder only once; durable state survives restart."""
        for note in self.data["notes"]:
            if reminder_is_due(note):
                note["reminder_sent_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
                self._write_now()
                title = "Pocket reminder · " + (note.get("title") or "Note")[:40]
                message = (note.get("body") or "Open Pocket to view the note").strip()[:200]
                if self.tray and not self.tray.error:
                    self.tray.notify(title, message, note_id=note["id"])
                else:
                    self.events.put(("note_reminder", (note["id"], title, message)))
                self._refresh_note_reminder_ui()
        self.root.after(1500, self._reminder_poll)

    def _notify(self, title, message):
        if self.tray and not self.tray.error:
            self.tray.notify(title, message)

    def _poll_events(self):
        try:
            while True:
                event = self.events.get_nowait()
                name, xy = event
                if name == "toggle":
                    self.toggle(xy)
                elif name == "show":
                    self.show(xy)
                elif name == "hotkey_error":
                    self.hotkey_available = False
                    self.shortcut_hint.config(text="Hotkey unavailable · click to change", fg=DANGER)
                elif name == "hotkey_changed":
                    self.hotkey_available = True
                    self.hotkey = hk.normalize_hotkey(xy)
                    self.data["hotkey"] = self.hotkey.copy()
                    self.shortcut_hint.config(text=self._hotkey_hint(), fg=MUTED)
                    self.schedule_save()
                elif name == "hotkey_conflict":
                    self._warning("Shortcut unavailable", "That keyboard shortcut is already in use. Your previous shortcut remains active.")
                elif name == "port_result":
                    token, result = xy
                    if token == self.scan_token:
                        self.port_results.append(result)
                        if self.current_tab == "ports":
                            self._add_port_result(result)
                            self.scan_info.config(text=f"Checked {len(self.port_results)} port(s)…", fg=ACCENT)
                elif name == "port_error":
                    token, error = xy
                    if token == self.scan_token and self.current_tab == "ports":
                        self.scan_info.config(text=f"Scan error: {error[:55]}", fg=DANGER)
                elif name == "port_done":
                    if xy == self.scan_token:
                        self.scanning = False
                        if self.current_tab == "ports":
                            total = len(self.port_results)
                            opened = sum(item["status"] == "OPEN" for item in self.port_results)
                            self.scan_info.config(text=f"Finished • {opened} open of {total} tested",
                                                  fg=ACCENT if opened else SECONDARY)
                elif name == "vendor_progress":
                    if self.current_tab == "mac":
                        self.vendor_info.config(text=xy, fg=ACCENT)
                elif name == "vendor_done":
                    self.updating_vendors = False
                    self.vendors, self.vendor_date = net.load_vendor_database(self.vendor_file)
                    if self.current_tab == "mac":
                        self.vendor_info.config(text=self._vendor_summary(), fg=ACCENT)
                elif name == "vendor_error":
                    self.updating_vendors = False
                    if self.current_tab == "mac":
                        self.vendor_info.config(text="Update failed — try Import CSV (see README)", fg=DANGER)
                elif name == "note_reminder":
                    note_id, title, message = xy
                    if self.preview or not self.tray or self.tray.error:
                        self.show()
                        messagebox.showinfo(title, message, parent=self.root)
                elif name == "open_reminder":
                    self.show()
                    if "notes" in self.settings["visible_tabs"]:
                        self.data["active_note"] = xy
                        self.show_tab("notes")
                elif name == "quit":
                    self.quit()
        except queue.Empty:
            pass
        self.root.after(100, self._poll_events)

    def quit(self):
        self.scan_cancel.set()
        self._write_now()
        if self.tray:
            self.tray.stop()
        self.root.destroy()

    def run(self):
        self.root.mainloop()


def monitor_work_area(x, y):
    """Return work area of the monitor containing the tray click."""
    from ctypes import wintypes

    class MONITORINFO(ctypes.Structure):
        _fields_ = [("cbSize", wintypes.DWORD), ("rcMonitor", wintypes.RECT),
                    ("rcWork", wintypes.RECT), ("dwFlags", wintypes.DWORD)]

    u = ctypes.windll.user32
    u.MonitorFromPoint.argtypes = [wintypes.POINT, wintypes.DWORD]
    u.MonitorFromPoint.restype = wintypes.HANDLE
    u.GetMonitorInfoW.argtypes = [wintypes.HANDLE, ctypes.POINTER(MONITORINFO)]
    u.GetMonitorInfoW.restype = wintypes.BOOL
    monitor = u.MonitorFromPoint(wintypes.POINT(x, y), 2)  # MONITOR_DEFAULTTONEAREST
    info = MONITORINFO()
    info.cbSize = ctypes.sizeof(info)
    if monitor and u.GetMonitorInfoW(monitor, ctypes.byref(info)):
        r = info.rcWork
        return r.left, r.top, r.right, r.bottom
    return (0, 0, u.GetSystemMetrics(0), u.GetSystemMetrics(1))


# RegisterHotKey makes the combination available even while another app has
# focus. Shift+8 is '*' on standard layouts; VK_MULTIPLY supports numpad '*'.
# Registration is per running process and cannot override another program's
# existing registration of the same key combination.
HOTKEY_MODIFIERS = 0x0002 | 0x0004 | 0x4000  # CONTROL | SHIFT | NOREPEAT
TOGGLE_HOTKEY_BINDINGS = ((0xB10, 0x38), (0xB11, 0x6A))  # 8 and NUMPAD MULTIPLY


def register_toggle_hotkeys(register, hwnd):
    """Register supported key combinations; return only successful IDs.

    This helper can be tested without Win32. A failed binding never prevents
    the normal tray icon from starting.
    """
    registered = set()
    for hotkey_id, virtual_key in TOGGLE_HOTKEY_BINDINGS:
        if register(hwnd, hotkey_id, HOTKEY_MODIFIERS, virtual_key):
            registered.add(hotkey_id)
    return registered


class WindowsTray:
    """Tiny Windows Shell_NotifyIcon + global hotkey wrapper; no pip packages required."""

    WM_TRAY = 0x8000 + 37
    WM_ICON_UPDATE = 0x8000 + 38
    NIM_MODIFY = 0x1
    WM_CLOSE = 0x0010
    WM_DESTROY = 0x0002
    WM_HOTKEY = 0x0312
    WM_LBUTTONUP = 0x0202
    WM_LBUTTONDBLCLK = 0x0203
    WM_RBUTTONUP = 0x0205
    WM_CONTEXTMENU = 0x007B
    NIM_ADD = 0x0
    NIM_DELETE = 0x2
    NIF_MESSAGE = 0x1
    NIF_ICON = 0x2
    NIF_TIP = 0x4

    WM_HOTKEY_CHANGE = 0x8000 + 39
    WM_NOTIFICATION = 0x8000 + 40
    NIF_INFO = 0x10

    def __init__(self, icon_path: Path, events, hotkey=None):
        self.icon_path = icon_path
        self.events = events
        self.error = None
        self.hwnd = None
        self._proc = None
        self._thread = None
        self.hotkey_ids = set()
        self._pending_icon = None
        self.hotkey = hk.normalize_hotkey(hotkey)
        self._pending_hotkey = None
        self._pending_notification = None
        self._active_reminder_id = None

    def start(self):
        self._thread = threading.Thread(target=self._main, name="PocketDeskTray", daemon=True)
        self._thread.start()

    def set_icon(self, path: Path):
        self._pending_icon = path
        if self.hwnd:
            ctypes.windll.user32.PostMessageW(self.hwnd, self.WM_ICON_UPDATE, 0, 0)

    def set_hotkey(self, value):
        self._pending_hotkey = hk.normalize_hotkey(value)
        if self.hwnd:
            ctypes.windll.user32.PostMessageW(self.hwnd, self.WM_HOTKEY_CHANGE, 0, 0)

    def notify(self, title, message, note_id=None):
        self._pending_notification = (str(title)[:63], str(message)[:255], note_id)
        if self.hwnd:
            ctypes.windll.user32.PostMessageW(self.hwnd, self.WM_NOTIFICATION, 0, 0)

    def stop(self):
        if self.hwnd:
            ctypes.windll.user32.PostMessageW(self.hwnd, self.WM_CLOSE, 0, 0)

    def _main(self):
        try:
            self._message_loop()
        except Exception as exc:
            self.error = exc

    def _message_loop(self):
        from ctypes import wintypes
        import ctypes.wintypes

        LRESULT = ctypes.c_ssize_t
        WNDPROC = ctypes.WINFUNCTYPE(LRESULT, wintypes.HWND, wintypes.UINT,
                                      wintypes.WPARAM, wintypes.LPARAM)

        class WNDCLASSW(ctypes.Structure):
            _fields_ = [("style", wintypes.UINT), ("lpfnWndProc", WNDPROC),
                        ("cbClsExtra", ctypes.c_int), ("cbWndExtra", ctypes.c_int),
                        ("hInstance", wintypes.HINSTANCE), ("hIcon", wintypes.HICON),
                        ("hCursor", wintypes.HANDLE), ("hbrBackground", wintypes.HBRUSH),
                        ("lpszMenuName", wintypes.LPCWSTR), ("lpszClassName", wintypes.LPCWSTR)]

        class GUID(ctypes.Structure):
            _fields_ = [("Data1", wintypes.DWORD), ("Data2", wintypes.WORD),
                        ("Data3", wintypes.WORD), ("Data4", ctypes.c_ubyte * 8)]

        class NOTIFYICONDATAW(ctypes.Structure):
            _fields_ = [("cbSize", wintypes.DWORD), ("hWnd", wintypes.HWND),
                        ("uID", wintypes.UINT), ("uFlags", wintypes.UINT),
                        ("uCallbackMessage", wintypes.UINT), ("hIcon", wintypes.HICON),
                        ("szTip", wintypes.WCHAR * 128), ("dwState", wintypes.DWORD),
                        ("dwStateMask", wintypes.DWORD), ("szInfo", wintypes.WCHAR * 256),
                        ("uTimeoutOrVersion", wintypes.UINT), ("szInfoTitle", wintypes.WCHAR * 64),
                        ("dwInfoFlags", wintypes.DWORD), ("guidItem", GUID),
                        ("hBalloonIcon", wintypes.HICON)]

        user = ctypes.windll.user32
        kernel = ctypes.windll.kernel32
        shell = ctypes.windll.shell32
        kernel.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
        kernel.GetModuleHandleW.restype = wintypes.HMODULE
        user.RegisterClassW.argtypes = [ctypes.POINTER(WNDCLASSW)]
        user.RegisterClassW.restype = wintypes.ATOM
        user.CreateWindowExW.argtypes = [wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR,
                                         wintypes.DWORD, ctypes.c_int, ctypes.c_int,
                                         ctypes.c_int, ctypes.c_int, wintypes.HWND,
                                         wintypes.HMENU, wintypes.HINSTANCE, wintypes.LPVOID]
        user.CreateWindowExW.restype = wintypes.HWND
        user.DefWindowProcW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
        user.DefWindowProcW.restype = LRESULT
        user.LoadImageW.argtypes = [wintypes.HINSTANCE, wintypes.LPCWSTR, wintypes.UINT,
                                    ctypes.c_int, ctypes.c_int, wintypes.UINT]
        user.LoadImageW.restype = wintypes.HANDLE
        shell.Shell_NotifyIconW.argtypes = [wintypes.DWORD, ctypes.POINTER(NOTIFYICONDATAW)]
        shell.Shell_NotifyIconW.restype = wintypes.BOOL
        user.GetCursorPos.argtypes = [ctypes.POINTER(wintypes.POINT)]
        user.GetCursorPos.restype = wintypes.BOOL
        user.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
        user.PostMessageW.restype = wintypes.BOOL
        user.RegisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT]
        user.RegisterHotKey.restype = wintypes.BOOL
        user.UnregisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int]
        user.UnregisterHotKey.restype = wintypes.BOOL
        user.GetMessageW.argtypes = [ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT]
        user.GetMessageW.restype = wintypes.BOOL
        user.AppendMenuW.argtypes = [wintypes.HMENU, wintypes.UINT, ctypes.c_size_t, wintypes.LPCWSTR]
        user.AppendMenuW.restype = wintypes.BOOL
        user.TrackPopupMenu.argtypes = [wintypes.HMENU, wintypes.UINT, ctypes.c_int, ctypes.c_int,
                                        ctypes.c_int, wintypes.HWND, ctypes.c_void_p]
        user.TrackPopupMenu.restype = wintypes.UINT

        hinstance = kernel.GetModuleHandleW(None)
        hicon = user.LoadImageW(None, str(self.icon_path), 1, 32, 32, 0x10)
        if not hicon:
            raise RuntimeError("Failed to load tray icon")
        class_name = f"PocketDeskTray_{os.getpid()}"
        taskbar_created = user.RegisterWindowMessageW("TaskbarCreated")
        nid = NOTIFYICONDATAW()
        nid.cbSize = ctypes.sizeof(nid)
        nid.uID = 1
        nid.uFlags = self.NIF_MESSAGE | self.NIF_ICON | self.NIF_TIP
        nid.uCallbackMessage = self.WM_TRAY
        nid.hIcon = hicon
        nid.szTip = "Pocket — " + hk.hotkey_label(self.hotkey) + " to toggle"

        def cursor():
            point = wintypes.POINT()
            user.GetCursorPos(ctypes.byref(point))
            return (point.x, point.y)

        def popup_menu(hwnd):
            menu = user.CreatePopupMenu()
            if not menu:
                return
            try:
                user.AppendMenuW(menu, 0x0, 101, "Open Pocket   (" + hk.hotkey_label(self.hotkey) + ")")
                user.AppendMenuW(menu, 0x800, 0, None)  # separator
                user.AppendMenuW(menu, 0x0, 103, "Exit Pocket")
                x, y = cursor()
                user.SetForegroundWindow(hwnd)
                cmd = user.TrackPopupMenu(menu, 0x100 | 0x2, x, y, 0, hwnd, None)
                if cmd:
                    self.events.put(({101: "show", 103: "quit"}[cmd], (x, y)))
                    user.PostMessageW(hwnd, 0, 0, 0)
            finally:
                user.DestroyMenu(menu)

        @WNDPROC
        def window_proc(hwnd, msg, wp, lp):
            if msg == taskbar_created:
                shell.Shell_NotifyIconW(self.NIM_ADD, ctypes.byref(nid))
                return 0
            if msg == self.WM_ICON_UPDATE:
                nonlocal hicon
                if self._pending_icon:
                    new_icon = user.LoadImageW(None, str(self._pending_icon), 1, 32, 32, 0x10)
                    if new_icon:
                        old_icon = hicon
                        nid.hIcon = new_icon
                        if shell.Shell_NotifyIconW(self.NIM_MODIFY, ctypes.byref(nid)):
                            hicon = new_icon
                            user.DestroyIcon(old_icon)
                        else:
                            nid.hIcon = old_icon
                            user.DestroyIcon(new_icon)
                return 0
            if msg == self.WM_NOTIFICATION:
                notice = self._pending_notification
                self._pending_notification = None
                if notice:
                    nid.szInfoTitle, nid.szInfo = notice[:2]
                    self._active_reminder_id = notice[2]
                    nid.dwInfoFlags = 0x1
                    nid.uFlags = self.NIF_MESSAGE | self.NIF_ICON | self.NIF_TIP | self.NIF_INFO
                    shell.Shell_NotifyIconW(self.NIM_MODIFY, ctypes.byref(nid))
                    nid.uFlags = self.NIF_MESSAGE | self.NIF_ICON | self.NIF_TIP
                return 0
            if msg == self.WM_HOTKEY_CHANGE:
                candidate = self._pending_hotkey
                if candidate:
                    # Validate the new combination before dropping the working one.
                    # Alternating IDs also supports multiple successive edits.
                    base = 0xB20 if all(i < 0xB20 for i in self.hotkey_ids) else 0xB10
                    bindings = hk.bindings(candidate, base)
                    new_ids = set()
                    if candidate == self.hotkey:
                        new_ids = self.hotkey_ids.copy()
                    else:
                        for hotkey_id, mods, key in bindings:
                            if user.RegisterHotKey(hwnd, hotkey_id, mods, key):
                                new_ids.add(hotkey_id)
                    if new_ids:
                        if candidate != self.hotkey:
                            for old in tuple(self.hotkey_ids):
                                user.UnregisterHotKey(hwnd, old)
                        self.hotkey_ids = new_ids
                        self.hotkey = candidate
                        nid.szTip = "Pocket — " + hk.hotkey_label(candidate) + " to toggle"
                        shell.Shell_NotifyIconW(self.NIM_MODIFY, ctypes.byref(nid))
                        self.events.put(("hotkey_changed", candidate))
                    else:
                        self.events.put(("hotkey_conflict", None))
                self._pending_hotkey = None
                return 0
            if msg == self.WM_HOTKEY:
                if int(wp) in self.hotkey_ids:
                    # Tkinter must be touched only by its main thread.
                    self.events.put(("toggle", None))
                return 0
            if msg == self.WM_TRAY:
                action = int(lp) & 0xFFFF
                if action in (self.WM_LBUTTONUP, self.WM_LBUTTONDBLCLK):
                    # Win32 may send two events on double click; the UI uses single click.
                    if action == self.WM_LBUTTONUP:
                        self.events.put(("toggle", cursor()))
                elif action == 0x0405 and self._active_reminder_id:
                    # NIN_BALLOONUSERCLICK: open the note whose reminder was clicked.
                    self.events.put(("open_reminder", self._active_reminder_id))
                    self._active_reminder_id = None
                elif action in (self.WM_RBUTTONUP, self.WM_CONTEXTMENU):
                    popup_menu(hwnd)
                return 0
            if msg == self.WM_DESTROY:
                for hotkey_id in tuple(self.hotkey_ids):
                    user.UnregisterHotKey(hwnd, hotkey_id)
                self.hotkey_ids.clear()
                self.hwnd = None
                shell.Shell_NotifyIconW(self.NIM_DELETE, ctypes.byref(nid))
                user.PostQuitMessage(0)
                return 0
            return user.DefWindowProcW(hwnd, msg, wp, lp)

        self._proc = window_proc  # prevent garbage collection
        window_class = WNDCLASSW()
        window_class.lpfnWndProc = self._proc
        window_class.hInstance = hinstance
        window_class.lpszClassName = class_name
        if not user.RegisterClassW(ctypes.byref(window_class)):
            raise ctypes.WinError()
        hwnd = user.CreateWindowExW(0, class_name, "PocketDeskTray", 0, 0, 0, 0, 0,
                                    None, None, hinstance, None)
        if not hwnd:
            raise ctypes.WinError()
        self.hwnd = hwnd
        nid.hWnd = hwnd
        self.hotkey_ids = set()
        for hotkey_id, mods, key in hk.bindings(self.hotkey):
            if user.RegisterHotKey(hwnd, hotkey_id, mods, key):
                self.hotkey_ids.add(hotkey_id)
        if self._pending_icon:
            user.PostMessageW(hwnd, self.WM_ICON_UPDATE, 0, 0)
        if not self.hotkey_ids:
            self.events.put(("hotkey_error", None))
        if not shell.Shell_NotifyIconW(self.NIM_ADD, ctypes.byref(nid)):
            user.DestroyWindow(hwnd)  # also unregisters the hotkeys
            raise ctypes.WinError()
        try:
            msg = wintypes.MSG()
            while user.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
                user.TranslateMessage(ctypes.byref(msg))
                user.DispatchMessageW(ctypes.byref(msg))
        finally:
            # DestroyWindow triggers WM_DESTROY and UnregisterHotKey on the
            # tray thread; do not leave a global shortcut registered on exit.
            if self.hwnd:
                user.DestroyWindow(hwnd)
            user.DestroyIcon(hicon)
            self.hwnd = None


if __name__ == "__main__":
    PocketDesk(preview="--preview" in sys.argv).run()
