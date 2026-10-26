"""PocketDesk — a Windows tray-first notes and shortcuts dashboard.

Core app uses the Python standard library. Run with pythonw.exe on Windows for no console.
Use --preview to show the popup without the tray, for testing and screenshots.
"""

from __future__ import annotations

import ctypes
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
import tkinter as tk
from tkinter import messagebox, filedialog, ttk

import network_tools as net

APP_NAME = "PocketDesk"
WIDTH, HEIGHT = 480, 668
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


def new_note(title="Untitled note", body="", phone="") -> dict:
    return {"id": new_id(), "title": title, "body": body, "phone": phone}


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
        "tools": {"target": "192.168.1.1", "single_port": "443", "custom_ports": "",
                  "selected_ports": [22, 80, 443, 3389], "mode": "single"},
    }


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
        # v1.1 data had no phone field or shortcut kind. Upgrade it in memory.
        for note in notes:
            if not isinstance(note.get("phone"), str):
                note["phone"] = ""
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
        return {"notes": notes, "active_note": active_id, "links": links,
                "tools": tools}
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
        self.events = queue.Queue()
        self.tray = None
        self._save_job = None
        self._loading_note = False
        self._modal = False
        self.pinned = False
        self.current_tab = "notes"
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

        self.root = tk.Tk()
        self.root.title("PocketDesk")
        self.root.configure(bg=BG)
        self.root.geometry(f"{WIDTH}x{HEIGHT}")
        self.root.resizable(False, False)
        self.root.protocol("WM_DELETE_WINDOW", self.hide)
        if not preview:
            self.root.overrideredirect(True)
            self.root.attributes("-topmost", True)
        try:
            self.root.iconbitmap(str(self.asset_path("app.ico")))
        except (tk.TclError, OSError):
            pass
        self._build_shell()
        self.show_tab("notes")
        self.root.bind("<Control-n>", lambda _e: self.add_note())
        self.root.bind("<Control-s>", lambda _e: self._write_now())
        self.root.bind("<Escape>", lambda _e: self.hide())
        self.root.bind("<FocusOut>", self._focus_lost)
        self.root.after(120, self._poll_events)
        if not preview and sys.platform == "win32":
            self.root.withdraw()
            self.tray = WindowsTray(self.asset_path("app.ico"), self.events)
            self.tray.start()
            self.root.after(250, self._check_tray)
        else:
            self.root.after(50, lambda: self._place_popup(None))

    @staticmethod
    def asset_path(name):
        return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent)) / "assets" / name

    def _build_shell(self):
        outer = tk.Frame(self.root, bg=BG, highlightthickness=1, highlightbackground=BORDER)
        outer.pack(fill="both", expand=True)
        header = tk.Frame(outer, bg=BG, height=77)
        header.pack(fill="x", padx=20, pady=(15, 10))
        header.pack_propagate(False)
        icon = tk.Label(header, text="▦", fg="#11131A", bg=ACCENT,
                        font=(FONT, 17, "bold"), width=3, height=2)
        icon.pack(side="left", padx=(0, 12))
        labels = tk.Frame(header, bg=BG)
        labels.pack(side="left", fill="y", expand=True)
        tk.Label(labels, text="pocketdesk.", font=(FONT, 19, "bold"), fg=WHITE,
                 bg=BG, anchor="w").pack(anchor="w", pady=(2, 0))
        tk.Label(labels, text="Notes, shortcuts and network tools.",
                 font=(FONT, 9), fg=MUTED, bg=BG).pack(anchor="w", pady=(1, 0))
        self.pin_button = action_label(header, "PIN", self.toggle_pin, fg=SECONDARY, bg=PANEL,
                                       padx=10, pady=7, font_size=8)
        self.pin_button.pack(side="right", padx=(5, 0), anchor="n", pady=(5, 0))
        action_label(header, "×", self.hide, fg=MUTED, bg=BG, hover=PANEL,
                     padx=8, pady=2, font_size=17).pack(side="right", anchor="n", pady=(4, 0))

        tabs = tk.Frame(outer, bg=BG, height=42)
        tabs.pack(fill="x", padx=20)
        tabs.pack_propagate(False)
        self.tab_buttons = {}
        for key, label in (("notes", "NOTES"), ("links", "SHORTCUTS"),
                           ("ports", "PORT CHECK"), ("mac", "MAC VENDORS")):
            button = action_label(tabs, label, lambda k=key: self.show_tab(k),
                                  bg=BG, hover=PANEL, fg=SECONDARY, padx=9, pady=8, font_size=9)
            button.pack(side="left", padx=(0, 4))
            self.tab_buttons[key] = button
        tk.Frame(outer, height=1, bg=BORDER).pack(fill="x")

        self.body = tk.Frame(outer, bg=BG)
        self.body.pack(fill="both", expand=True, padx=17, pady=(17, 8))
        tk.Frame(outer, height=1, bg=BORDER).pack(fill="x")
        footer = tk.Frame(outer, bg=BG, height=59)
        self.footer = footer
        footer.pack(fill="x", padx=20)
        footer.pack_propagate(False)
        action_label(footer, "Open Windows Notepad  ↗", self.open_notepad,
                     fg=SECONDARY, bg=BG, hover=PANEL, font_size=9, padx=6, pady=6,
                     bold=False).pack(side="left", pady=11)
        tk.Label(footer, text="LOCAL & PRIVATE", font=(FONT, 8, "bold"),
                 fg=MUTED, bg=BG).pack(side="right")

    def show_tab(self, which):
        if which in ("ports", "mac"):
            self.footer.pack_forget()  # Network tools benefit from additional results space.
        elif not self.footer.winfo_manager():
            self.footer.pack(fill="x", padx=20)
        if self.current_tab == "mac" and hasattr(self, "mac_input") and self.mac_input.winfo_exists():
            self.mac_draft = self.mac_input.get("1.0", "end-1c")
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
        sidebar = tk.Frame(main, bg=PANEL, width=144, highlightbackground=BORDER, highlightthickness=1)
        sidebar.pack(side="left", fill="y", padx=(0, 10))
        sidebar.pack_propagate(False)
        tk.Label(sidebar, text="ALL NOTES", font=(FONT, 8, "bold"), fg=MUTED,
                 bg=PANEL).pack(anchor="w", padx=11, pady=(14, 9))
        self.note_list = tk.Listbox(sidebar, bd=0, highlightthickness=0, activestyle="none",
                                    selectbackground=ACCENT_DARK, selectforeground=WHITE,
                                    bg=PANEL, fg=SECONDARY, font=(FONT, 10), height=1, width=1,
                                    exportselection=False, relief="flat", justify="left")
        self.note_list.pack(fill="both", expand=True, padx=5, pady=(0, 10))
        self.note_list.bind("<<ListboxSelect>>", self._select_from_list)
        editor = tk.Frame(main, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        editor.pack(side="left", fill="both", expand=True)
        tk.Label(editor, text="TITLE", font=(FONT, 8, "bold"), fg=MUTED,
                 bg=PANEL).pack(anchor="w", padx=12, pady=(14, 5))
        self.title_var = tk.StringVar()
        self.title_entry = tk.Entry(editor, textvariable=self.title_var, bg=INPUT, fg=WHITE,
                                    insertbackground=WHITE, highlightthickness=1,
                                    highlightbackground=BORDER, highlightcolor=ACCENT,
                                    relief="flat", font=(FONT, 11, "bold"))
        self.title_entry.pack(fill="x", padx=12, ipady=9)
        self.title_var.trace_add("write", self._change_note_title)
        tk.Label(editor, text="PHONE NUMBER", font=(FONT, 8, "bold"), fg=MUTED,
                 bg=PANEL).pack(anchor="w", padx=12, pady=(11, 4))
        phone_row = tk.Frame(editor, bg=PANEL)
        phone_row.pack(fill="x", padx=12)
        self.phone_var = tk.StringVar()
        self.phone_entry = tk.Entry(phone_row, textvariable=self.phone_var, bg=INPUT, fg=WHITE,
                                    insertbackground=WHITE, highlightthickness=1,
                                    highlightbackground=BORDER, highlightcolor=ACCENT,
                                    relief="flat", font=(FONT, 9), width=8)
        self.phone_entry.pack(side="left", fill="x", expand=True, ipady=8)
        action_label(phone_row, "Copy", self._copy_phone, fg=ACCENT, bg=CARD,
                     padx=12, pady=8, font_size=9).pack(side="left", padx=(6, 0))
        self.phone_var.trace_add("write", self._change_note_phone)
        tk.Label(editor, text="NOTE", font=(FONT, 8, "bold"), fg=MUTED,
                 bg=PANEL).pack(anchor="w", padx=12, pady=(9, 5))
        self.note_body = tk.Text(editor, wrap="word", undo=True, bg=INPUT, fg="#D7DAE6",
                                 insertbackground=ACCENT, selectbackground=ACCENT_DARK,
                                 relief="flat", bd=0, font=(FONT, 10), height=1, width=1,
                                 highlightthickness=1, highlightbackground=BORDER,
                                 highlightcolor=ACCENT, padx=10, pady=12)
        self.note_body.pack(fill="both", expand=True, padx=12)
        self.note_body.bind("<<Modified>>", self._change_note_body)
        editor_footer = tk.Frame(editor, bg=PANEL)
        editor_footer.pack(fill="x", padx=10, pady=9)
        self.save_status = tk.Label(editor_footer, text="Autosaved", font=(FONT, 8), fg=MUTED, bg=PANEL)
        self.save_status.pack(side="left")
        action_label(editor_footer, "Delete", self.delete_note, fg=DANGER, bg=PANEL,
                     hover=CARD, padx=6, pady=4, font_size=8).pack(side="right")
        self.refresh_note_list()
        self._load_selected_note()

    def active_note(self):
        for note in self.data["notes"]:
            if note["id"] == self.data["active_note"]:
                return note
        return None

    def refresh_note_list(self):
        if not hasattr(self, "note_list") or not self.note_list.winfo_exists():
            return
        self._loading_note = True
        self.note_list.delete(0, tk.END)
        for i, n in enumerate(self.data["notes"]):
            self.note_list.insert(tk.END, "  " + (n["title"].strip() or "Untitled")[:19])
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
        self.phone_var.set(n.get("phone", ""))
        self.note_body.delete("1.0", tk.END)
        self.note_body.insert("1.0", n["body"])
        self.note_body.edit_modified(False)
        self._loading_note = False
        self.save_status.config(text="Autosaved", fg=MUTED)

    def _select_from_list(self, _event):
        if self._loading_note:
            return
        indexes = self.note_list.curselection()
        if not indexes or indexes[0] >= len(self.data["notes"]):
            return
        self.data["active_note"] = self.data["notes"][indexes[0]]["id"]
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

    def _change_note_body(self, _event=None):
        if not self.note_body.edit_modified():
            return
        self.note_body.edit_modified(False)
        if self._loading_note:
            return
        note = self.active_note()
        if note is not None:
            note["body"] = self.note_body.get("1.0", "end-1c")
            self._edit_dirty()

    def _edit_dirty(self):
        if self.current_tab == "notes":
            self.save_status.config(text="Saving…", fg=ACCENT)
        self.schedule_save()

    def add_note(self):
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
        self._modal = True
        try:
            confirmed = messagebox.askyesno("Delete note", "Delete this note permanently?", parent=self.root)
        finally:
            self._modal = False
        if not confirmed:
            return
        active = self.data["active_note"]
        self.data["notes"] = [n for n in self.data["notes"] if n["id"] != active]
        if not self.data["notes"]:
            self.data["notes"] = [new_note()]
        self.data["active_note"] = self.data["notes"][0]["id"]
        self.refresh_note_list()
        self._load_selected_note()
        self.schedule_save()

    def _build_links(self):
        self._section_title(self.body, "Quick shortcuts", "Websites, files and folders", "+ Add", lambda: self._toggle_link_form(None))
        self.form_holder = tk.Frame(self.body, bg=BG)
        self.form_holder.pack(fill="x")
        frame = tk.Frame(self.body, bg=BG)
        frame.pack(fill="both", expand=True)
        canvas = tk.Canvas(frame, bg=BG, highlightthickness=0, bd=0)
        scroll = tk.Scrollbar(frame, orient="vertical", command=canvas.yview, bg=CARD)
        canvas.configure(yscrollcommand=scroll.set)
        canvas.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        self._scroll_canvas = canvas
        self.links_stack = tk.Frame(canvas, bg=BG)
        win = canvas.create_window((0, 0), window=self.links_stack, anchor="nw")
        self.links_stack.bind("<Configure>", lambda _e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(win, width=e.width))
        canvas.bind("<Enter>", lambda _e: canvas.bind_all("<MouseWheel>", self._mousewheel))
        canvas.bind("<Leave>", lambda _e: canvas.unbind_all("<MouseWheel>"))
        self.refresh_links()

    def _mousewheel(self, event):
        if self._scroll_canvas and self._scroll_canvas.winfo_exists():
            self._scroll_canvas.yview_scroll(int(-event.delta / 120), "units")

    def refresh_links(self):
        if self.current_tab != "links":
            return
        for child in self.links_stack.winfo_children():
            child.destroy()
        if not self.data["links"]:
            tk.Label(self.links_stack, text="No shortcuts yet. Add a website, file or folder above.",
                     fg=SECONDARY, bg=BG, font=(FONT, 10), wraplength=360).pack(pady=25)
        for link in self.data["links"]:
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
        actions = tk.Frame(tile, bg=PANEL)
        actions.pack(side="right", padx=(0, 8))
        action_label(actions, "↗", lambda item=link: self.open_shortcut(item),
                     fg=ACCENT, bg=PANEL, hover=CARD, padx=7, pady=5, font_size=15).pack(side="left")
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

    def _copy_url(self, url):
        self.root.clipboard_clear()
        self.root.clipboard_append(url)

    def _delete_link(self, item):
        self.data["links"] = [l for l in self.data["links"] if l["id"] != item["id"]]
        self.refresh_links()
        self.schedule_save()

    def _toggle_link_form(self, item):
        for child in self.form_holder.winfo_children():
            child.destroy()
        self.edit_link_id = item["id"] if item else None
        panel = tk.Frame(self.form_holder, bg=PANEL, highlightthickness=1,
                         highlightbackground=ACCENT_DARK)
        panel.pack(fill="x", pady=(0, 13))
        tk.Label(panel, text="EDIT SHORTCUT" if item else "NEW SHORTCUT", fg=ACCENT, bg=PANEL,
                 font=(FONT, 9, "bold")).pack(anchor="w", padx=14, pady=(12, 6))
        title_var = tk.StringVar(value=item["title"] if item else "")
        target_var = tk.StringVar(value=item["url"] if item else "")
        kind_var = tk.StringVar(value=item.get("kind", "url") if item else "url")
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
        self.root.after(30, title_entry.focus_set)

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
        self.edit_link_id = None

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

    def _tree(self, parent, columns, widths):
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
        tree = ttk.Treeview(container, columns=columns, show="headings", height=4,
                            style="Pocket.Treeview")
        for col, width in zip(columns, widths):
            tree.heading(col, text=col)
            tree.column(col, width=width, minwidth=50, anchor="w", stretch=True)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        return tree

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

    def open_notepad(self):
        if sys.platform == "win32":
            try:
                subprocess.Popen(["notepad.exe"])
            except OSError as exc:
                messagebox.showerror("Notepad", str(exc), parent=self.root)
        else:
            messagebox.showinfo("Windows only", "This launches Notepad on Windows.", parent=self.root)

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
        if self.preview or self.pinned or self._modal:
            return
        self.root.after(170, self._maybe_hide)

    def _maybe_hide(self):
        if self.preview or self.pinned or self._modal:
            return
        if self.root.state() == "normal" and self.root.focus_displayof() is None:
            self.hide()

    def _place_popup(self, xy):
        self.root.update_idletasks()
        if xy and sys.platform == "win32":
            x, y = xy
            area = monitor_work_area(x, y)
            left, top, right, bottom = area
            px = max(left + 8, min(x - WIDTH + 32, right - WIDTH - 8))
            py = (bottom - HEIGHT - 9) if y > (top + bottom) / 2 else (top + 9)
        else:
            px = max(0, self.root.winfo_screenwidth() - WIDTH - 35)
            py = max(0, self.root.winfo_screenheight() - HEIGHT - 85)
        self.root.geometry(f"{WIDTH}x{HEIGHT}+{px}+{py}")

    def show(self, xy=None):
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
        if self.root.state() == "withdrawn":
            self.show(xy)
        else:
            self.hide()

    def _poll_events(self):
        try:
            while True:
                event = self.events.get_nowait()
                name, xy = event
                if name == "toggle":
                    self.toggle(xy)
                elif name == "show":
                    self.show(xy)
                elif name == "notepad":
                    self.open_notepad()
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


class WindowsTray:
    """Tiny Windows Shell_NotifyIcon wrapper; no pip packages required."""

    WM_TRAY = 0x8000 + 37
    WM_CLOSE = 0x0010
    WM_DESTROY = 0x0002
    WM_LBUTTONUP = 0x0202
    WM_LBUTTONDBLCLK = 0x0203
    WM_RBUTTONUP = 0x0205
    WM_CONTEXTMENU = 0x007B
    NIM_ADD = 0x0
    NIM_DELETE = 0x2
    NIF_MESSAGE = 0x1
    NIF_ICON = 0x2
    NIF_TIP = 0x4

    def __init__(self, icon_path: Path, events):
        self.icon_path = icon_path
        self.events = events
        self.error = None
        self.hwnd = None
        self._proc = None
        self._thread = None

    def start(self):
        self._thread = threading.Thread(target=self._main, name="PocketDeskTray", daemon=True)
        self._thread.start()

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
        nid.szTip = "PocketDesk — Notes, Shortcuts & Network Tools"

        def cursor():
            point = wintypes.POINT()
            user.GetCursorPos(ctypes.byref(point))
            return (point.x, point.y)

        def popup_menu(hwnd):
            menu = user.CreatePopupMenu()
            if not menu:
                return
            try:
                user.AppendMenuW(menu, 0x0, 101, "Open dashboard")
                user.AppendMenuW(menu, 0x0, 102, "Open Windows Notepad")
                user.AppendMenuW(menu, 0x800, 0, None)  # separator
                user.AppendMenuW(menu, 0x0, 103, "Exit PocketDesk")
                x, y = cursor()
                user.SetForegroundWindow(hwnd)
                cmd = user.TrackPopupMenu(menu, 0x100 | 0x2, x, y, 0, hwnd, None)
                if cmd:
                    self.events.put(({101: "show", 102: "notepad", 103: "quit"}[cmd], (x, y)))
                    user.PostMessageW(hwnd, 0, 0, 0)
            finally:
                user.DestroyMenu(menu)

        @WNDPROC
        def window_proc(hwnd, msg, wp, lp):
            if msg == taskbar_created:
                shell.Shell_NotifyIconW(self.NIM_ADD, ctypes.byref(nid))
                return 0
            if msg == self.WM_TRAY:
                action = int(lp) & 0xFFFF
                if action in (self.WM_LBUTTONUP, self.WM_LBUTTONDBLCLK):
                    # Win32 may send two events on double click; the UI uses single click.
                    if action == self.WM_LBUTTONUP:
                        self.events.put(("toggle", cursor()))
                elif action in (self.WM_RBUTTONUP, self.WM_CONTEXTMENU):
                    popup_menu(hwnd)
                return 0
            if msg == self.WM_DESTROY:
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
        if not shell.Shell_NotifyIconW(self.NIM_ADD, ctypes.byref(nid)):
            raise ctypes.WinError()
        try:
            msg = wintypes.MSG()
            while user.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
                user.TranslateMessage(ctypes.byref(msg))
                user.DispatchMessageW(ctypes.byref(msg))
        finally:
            user.DestroyIcon(hicon)
            self.hwnd = None


if __name__ == "__main__":
    PocketDesk(preview="--preview" in sys.argv).run()
