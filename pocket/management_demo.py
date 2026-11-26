"""FORMGT: guided, isolated presentation of the real Pocket UI."""
from __future__ import annotations

import json
import tempfile
import time
import tkinter as tk
from datetime import datetime, timedelta
from pathlib import Path
from tkinter import ttk


STEPS = (
    ("WELCOME", "כל הכלים במקום אחד", "סביבת עבודה קומפקטית לצד מערכות העבודה", 5500, "intro"),
    ("NOTES", "תיעוד תוך כדי שיחה", "פרטי הטיפול נשארים זמינים בלי לפתוח קובץ נוסף", 6500, "notes"),
    ("SHORTCUTS", "גישה מהירה למשאבי עבודה", "קישורים, קבצים ותהליכים במקום מרכזי", 6000, "links"),
    ("COMMANDS", "הידע המקצועי במרחק חיפוש", "איתור פקודת Cisco בלי לחפש בקובצי Excel", 8500, "commands"),
    ("SUBNET", "חישוב מהיר ומדויק", "טווח כתובות ומסכת רשת ללא מחשבון חיצוני", 8000, "subnet"),
    ("PORTS", "בדיקות מרוכזות", "תוצאות TCP לדוגמה בלבד · ללא חיבור לרשת", 8500, "ports"),
    ("MAC", "זיהוי ציוד בשניות", "חיפוש יצרן מתוך מאגר מקומי לדוגמה", 7500, "mac"),
    ("CLIPBOARD", "פחות הקלדה חוזרת", "מידע לדוגמה זמין לשימוש חוזר", 6500, "clipboard"),
    ("REMINDERS", "משימות המשך לא נשכחות", "תזכורת לחזרה ללקוח כחלק מתהליך הטיפול", 6500, "reminders"),
    ("EXTRA", "איתור מידע תפעולי", "חיפוש רשומת שירות במסד הנתונים המקומי", 9500, "extra"),
    ("WORKFLOW", "מעבר בין כלים בלי לאבד מידע", "בדיקה נוספת וחזרה לתוצאת החיפוש", 5000, "switch_extra"),
    ("EXTRA", "ממשיכים בדיוק מהמקום שעצרנו", "החיפוש והתוצאה נשמרים במעבר בין הכלים", 6500, "return_extra"),
    ("CTRL+K", "קיצור דרך לכל סביבת העבודה", "חיפוש חכם מכל כלי באמצעות המקלדת", 7500, "palette"),
    ("BUSINESS IMPACT", "פחות חיפוש. יותר טיפול.", "30 שניות חיסכון לפנייה עשויות להצטבר לשעות עבודה", 0, "summary"),
)


def simulated_ports(ip, ports, *, cancel=None, **kwargs):
    """Deliberately fake TCP statuses; no sockets or remote requests."""
    from . import network_tools as net
    for port in ports:
        if cancel is not None and cancel.is_set():
            return
        time.sleep(0.22)
        if cancel is not None and cancel.is_set():
            return
        yield {"port": port, "service": net.PORT_NAMES.get(port, "—"),
               "status": "OPEN" if port in (22, 443) else "CLOSED",
               "ms": 12 if port in (22, 443) else 35}


def seed_profile(api, folder):
    """Create a new synthetic profile and index; never import a real library."""
    from openpyxl import Workbook
    from . import extra_excel_db, reminder_store
    data = api["default_data"]()
    data["settings"].update(display_mode="mini", window_profile="Mini",
                            clipboard_paused=True, clipboard_storage="ram",
                            quick_slots_enabled=False, convert_enabled=False)
    data["last_tab"] = "notes"
    note = api["new_note"]("DEMO-1042 | Business connectivity",
        "DEMO DATA ONLY\nCustomer reports application unavailable.\n"
        "Service: DEMO-1042 | Cisco router\n"
        "Lab subnet: 192.0.2.0/26\n"
        "Example TCP results: 443 OPEN; 8080 CLOSED (simulated).\n"
        "Next action: confirm application service with customer.")
    data["notes"] = [note]
    data["active_note"] = note["id"]
    data["links"] = [api["new_link"]("Network procedures (demo)", "https://example.invalid/procedures"),
                     api["new_link"]("Service knowledge base (demo)", "https://example.invalid/kb")]
    data["shortcut_folders"] = api["shortcut_folders"].normalize(None, data["links"])
    data["reminders"] = [reminder_store.make_reminder("DEMO-1042 | Customer follow-up",
        "Confirm service status with the customer (example only).",
        (datetime.now().astimezone() + timedelta(days=1)).isoformat())]
    data["tools"].update(target="192.0.2.10", source="local", mac_source="local",
                         ports_input="22,443,8080")
    api["save_data"](folder / "data.json", data)
    commands = [
        ("Cisco", "Interfaces", "Display interface addresses and status", "show ip interface brief"),
        ("Cisco", "Routing", "Display routing table", "show ip route"),
        ("Cisco", "Diagnostics", "Display system logs", "show logging"),
        ("Cisco", "VLAN / L2", "Display MAC address table", "show mac address-table"),
        ("Juniper SRX", "Interfaces", "Display interfaces", "show interfaces terse"),
        ("Fortigate", "Routing", "Display routing table", "get router info routing-table all"),
    ]
    (folder / "commands.json").write_text(json.dumps({"schema": 1, "commands": [
        dict(id="demo-"+str(i), machine=m, category=c, description=d, command=cmd)
        for i, (m,c,d,cmd) in enumerate(commands)]}, ensure_ascii=False), encoding="utf-8")
    (folder / "vendors.json").write_text(json.dumps({"updated":"DEMO",
        "vendors":{"00000C":["Cisco Systems, Inc.", "MA-L"]}}), encoding="utf-8")
    book = Workbook()
    sheet = book.active
    sheet.title = "Demo services"
    sheet.append(["Circuit ID", "Customer", "Group ID", "VRF", "Site", "Device", "IP address"])
    sheet.append(["DEMO-1042", "Example Business", "DEMO-G01", "DEMO-VRF", "Training site A", "Cisco", "192.0.2.10"])
    sheet.append(["DEMO-1043", "Example Business", "DEMO-G02", "DEMO-VRF", "Training site B", "Juniper", "192.0.2.20"])
    path = folder / "demo-services.xlsx"
    book.save(path)
    book.close()
    extra_excel_db.sync_database(path, db_path=folder / extra_excel_db.FILE_NAME)
    return path


class Presentation:
    """A lightweight, in-window guided tour; all widgets live in Pocket's root."""
    BG = "#101b30"
    CARD = "#172943"
    ACCENT = "#79e4cf"
    TEXT = "#f5f8ff"
    MUTED = "#b0c1d9"

    def __init__(self, app, api, workbook, *, auto_start=True):
        self.app, self.api, self.workbook = app, api, workbook
        self.index = -1
        self.job = None
        self.pending = set()
        self.paused = False
        self.closed = False
        self.smoke = not auto_start
        self.footer = self.overlay = None
        self.error = ""
        self.action_pending = False
        self.action = None
        self.deadline = 0
        self.remaining = 0
        self.root = app.root
        self.root.title("Pocket | FORMGT — DEMO ONLY")
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.bind("<Escape>", lambda e: self.close())
        self.root.bind("<F5>", lambda e: self.restart())
        self.root.bind("<F6>", lambda e: self.toggle())
        self.root.bind("<F7>", lambda e: self.previous())
        self.root.bind("<F8>", lambda e: self.next())
        self.root.bind("<F9>", lambda e: self.explain())
        self.ensure_chrome()
        if auto_start:
            self.job = self.root.after(700, self.next)

    def widget_alive(self, widget):
        return widget is not None and widget.winfo_exists()

    def ensure_chrome(self):
        if not self.widget_alive(self.footer):
            # Reserve only one slim row, rather than covering tool content.
            outer = next(w for w in self.root.winfo_children()
                         if w.winfo_manager() == "pack")
            self.footer = tk.Frame(self.root, bg=self.BG)
            self.footer.pack(side="bottom", fill="x", before=outer)
            self.track = tk.Canvas(self.footer, height=3, bg="#293a50",
                                   highlightthickness=0, bd=0)
            self.track.pack(fill="x")
            self.track.bind("<Configure>", lambda e: self.draw_progress())
            bar = tk.Frame(self.footer, bg=self.BG)
            bar.pack(fill="x", padx=5, pady=3)
            self.step_label = tk.Label(bar, bg=self.BG, fg=self.ACCENT,
                font=("Segoe UI", 8, "bold"), text="FORMGT")
            self.step_label.pack(side="left", padx=(2, 3))
            for text, handler in (("×", self.close), ("?", self.explain),
                                  ("↻", self.restart), ("Next", self.next)):
                self.button(bar, text, handler).pack(side="right", padx=1)
            self.pause_button = self.button(bar, "Pause", self.toggle)
            self.pause_button.pack(side="right", padx=1)
            self.button(bar, "Back", self.previous).pack(side="right", padx=1)
        if not self.widget_alive(self.overlay):
            self.overlay = tk.Frame(self.root, bg=self.CARD,
                                    highlightbackground=self.ACCENT, highlightthickness=1)
            self.kicker = tk.Label(self.overlay, bg=self.CARD, fg=self.ACCENT,
                                   anchor="w", font=("Segoe UI", 9, "bold"))
            self.kicker.pack(fill="x", padx=11, pady=(6, 0))
            self.heading = tk.Label(self.overlay, bg=self.CARD, fg=self.TEXT,
                                    anchor="e", justify="right", font=("Segoe UI", 13, "bold"))
            self.heading.pack(fill="x", padx=11, pady=(2, 0))
            self.detail = tk.Label(self.overlay, bg=self.CARD, fg=self.MUTED,
                                   anchor="e", justify="right", font=("Segoe UI", 10))
            self.detail.pack(fill="x", padx=11, pady=(1, 7))
            for w in (self.overlay, self.kicker, self.heading, self.detail):
                w.bind("<Button-1>", lambda e: self.hide_card())
        self.draw_progress()

    def button(self, parent, label, handler):
        return tk.Button(parent, text=label, command=handler, bg="#243852", fg=self.TEXT,
                         activebackground="#385778", activeforeground=self.TEXT,
                         relief="flat", bd=0, padx=7, pady=2, cursor="hand2",
                         font=("Segoe UI", 9, "bold"), takefocus=True)

    def draw_progress(self):
        if not self.widget_alive(self.footer):
            return
        self.track.delete("all")
        width = self.track.winfo_width()
        self.track.create_rectangle(0, 0, width * max(0, self.index+1)/len(STEPS),
                                    3, fill=self.ACCENT, outline="")

    def later(self, ms, callback):
        """Cancel stale delayed actions when a presenter skips or restarts."""
        marker = [None]
        def run():
            self.pending.discard(marker[0])
            if not self.closed:
                callback()
        marker[0] = self.root.after(ms, run)
        self.pending.add(marker[0])

    def cancel(self):
        if self.job is not None:
            self.root.after_cancel(self.job)
            self.job = None
        for marker in self.pending:
            self.root.after_cancel(marker)
        self.pending.clear()

    def hide_card(self):
        if self.widget_alive(self.overlay):
            self.overlay.place_forget()

    def explain(self):
        if self.index < 0:
            return
        self.ensure_chrome()
        name, headline, detail, _, key = STEPS[self.index]
        self.kicker.configure(text=f"FORMGT  /  {self.index+1:02d}   {name}")
        self.heading.configure(text=headline, wraplength=max(260, self.root.winfo_width()-42))
        if key == "summary":
            detail = ("30 sec × 20 calls × 50 agents × 22 days = 183 hours/month\n"
                      "תרחיש להמחשה בלבד · לא תוצאות מדידה")
        if self.error:
            detail = self.error
        self.detail.configure(text=detail, wraplength=max(260, self.root.winfo_width()-42))
        # Header/nav only; reveal the underlying tool before its action runs.
        self.overlay.place(relx=0, rely=0, x=6, y=5, relwidth=1, width=-12)
        self.overlay.lift()

    def next(self):
        if self.index == len(STEPS)-1:
            return
        self.go(self.index+1)

    def previous(self):
        self.go(max(0, self.index-1))

    def toggle(self):
        if self.index < 0 or self.index == len(STEPS)-1:
            return
        if self.paused:
            self.paused = False
            self.pause_button.configure(text="Pause")
            if self.error:
                self.go(self.index)
                return
            if self.action_pending:
                self.perform_action()
            self.hide_card()
            self.schedule(max(1000, self.remaining))
        else:
            self.remaining = max(0, int((self.deadline-time.monotonic())*1000))
            self.paused = True
            self.cancel()
            self.pause_button.configure(text="Play")
            self.step_label.configure(text=f"{self.index+1:02d}/{len(STEPS):02d} · PAUSE")

    def restart(self):
        self.cancel()
        self.paused = False
        self.go(0)

    def schedule(self, delay):
        self.deadline = time.monotonic() + delay/1000
        self.job = self.root.after(delay, self.next)

    def close_palette(self):
        dialog = getattr(self.app, "_quick_search_dialog", None)
        if dialog is not None and dialog.winfo_exists():
            # Invoke the palette's real close handler (native focus cleanup).
            handler = dialog.protocol("WM_DELETE_WINDOW")
            if handler:
                dialog.tk.call(handler)

    def show_tool(self, key):
        a = self.app
        if a.display_mode != "mini" and key != "summary":
            a._set_display_mode("mini")
        if key == "ports":
            if a.scanning:
                a.scan_cancel.set()
                a.scan_token += 1
                a.scanning = False
            a.port_results = []
        if key == "mac":
            a.mac_results = []
        if key == "extra":
            state = self.api["extra_excel_ui"].session(a)
            if not state["busy"]:
                self.api["extra_excel_ui"].detach(a)
                state.update(query="", hits=[], selected=None, status="", page_y=0., list_y=0., detail_y=0.)
                state["revision"] += 1
        if key == "summary":
            a._set_display_mode("dashboard")
            a.show_tab("home" if a.display_mode == "dashboard" else "notes")
        else:
            tab = {"intro":"notes", "palette":"notes", "switch_extra":"subnet",
                   "return_extra":"extra"}.get(key, key)
            a.show_tab(tab)
        self.ensure_chrome()

    def go(self, index):
        self.cancel()
        self.close_palette()
        self.hide_card()
        self.index = index
        self.error = ""
        self.action_pending = True
        _, _, _, delay, key = STEPS[index]
        self.action = key
        try:
            self.show_tool(key)
            self.root.update_idletasks()
            self.step_label.configure(text=f"{index+1:02d}/{len(STEPS):02d} · " + ("SIM" if key == "ports" else "DEMO"))
            self.pause_button.configure(text="Play" if self.paused else "Ⅱ")
            self.explain()
            if self.smoke:
                self.hide_card()
                self.perform_action()
            elif not self.paused:
                if key != "summary":
                    self.later(2600, self.hide_card)
                    self.later(2800, self.perform_action)
                else:
                    self.action_pending = False
            else:
                self.hide_card()
                self.perform_action()
            if delay and not self.paused:
                self.schedule(delay)
        except Exception as exc:
            self.fail(exc)

    def fail(self, exc):
        self.cancel()
        self.paused = True
        self.error = f"Demo paused: {type(exc).__name__}: {exc}"
        self.ensure_chrome()
        self.pause_button.configure(text="Play")
        self.explain()

    def scroll_to(self, widget=None, fraction=None):
        a = self.app
        canvas = getattr(a, "_tool_scroll_canvas", None)
        if not self.widget_alive(canvas):
            return
        self.root.update_idletasks()
        if fraction is not None:
            canvas.yview_moveto(fraction)
        elif self.widget_alive(widget):
            region = canvas.bbox("all")
            if region and region[3] > region[1]:
                y = widget.winfo_rooty()-canvas.winfo_rooty()+canvas.canvasy(0)
                canvas.yview_moveto(max(0, (y-16)/(region[3]-region[1])))

    def perform_action(self):
        if not self.action_pending:
            return
        self.action_pending = False
        try:
            self.apply(self.action)
        except Exception as exc:
            self.fail(exc)

    def apply(self, key):
        a = self.app
        if key == "commands":
            a._command_focus_in()
            a.command_query.set("show ip interface brief")
            a._refresh_command_results()
        elif key == "subnet":
            a.subnet_ip_var.set("192.0.2.10")
            a.subnet_prefix_var.set("26")
            a._calculate_subnet()
            if not self.smoke:
                self.later(900, lambda: self.scroll_to(a.subnet_fact_labels["cidr"]))
        elif key == "ports":
            # A quick jump/replay must not leave a previous simulated scan active.
            if a.scanning:
                a.scan_cancel.set()
                a.scan_token += 1
                a.scanning = False
            a.port_source.set("local")
            a.host_var.set("192.0.2.10")
            a.ports_var.set("22,443,8080")
            a._start_scan()
            if not self.smoke:
                self.later(1400, lambda: self.scroll_to(a.port_tree))
        elif key == "mac":
            a.mac_source.set("local")
            a.mac_input.delete("1.0", "end")
            a.mac_input.insert("1.0", "00:00:0C:12:34:56")
            a._run_mac_lookup()
            if not self.smoke:
                self.later(900, lambda: self.scroll_to(a.mac_tree))
        elif key == "extra":
            a._extra_excel_path = str(self.workbook)
            a._extra_palette_search("DEMO-1042")
            if not self.smoke:
                self.later(1500, lambda: self.scroll_to(fraction=0.48))
        elif key == "return_extra":
            # Manual jumps may reach this chapter before the first search.
            state = self.api["extra_excel_ui"].session(a)
            if not state["hits"] and not state["busy"]:
                a._extra_palette_search("DEMO-1042")
            if not self.smoke:
                self.later(1000, lambda: self.scroll_to(fraction=0.48))
        elif key == "palette":
            a._open_global_search()
            a._palette_entry.insert(0, "> subnet 192.0.2.10/26")
            if not self.smoke:
                self.later(2400, self.execute_palette_demo)
        elif key == "summary":
            self.explain()

    def execute_palette_demo(self):
        a = self.app
        dialog = getattr(a, "_quick_search_dialog", None)
        if not self.widget_alive(dialog):
            return
        hit = self.api["command_palette"].command("subnet 192.0.2.10/26", a.settings)
        if hit is None:
            self.fail(ValueError("Demo palette action not recognized"))
            return
        self.close_palette()
        a._run_palette_action(hit)

    def close(self):
        if self.closed:
            return
        self.closed = True
        self.cancel()
        self.app._extra_excel_cancel.set()
        self.app.scan_cancel.set()
        self.app.tasks.stop()
        self.root.destroy()


def run(api, *, smoke=False):
    """Run the isolated demo automatically from the FORMGT application entry."""
    from . import portable_storage, network_tools, dashdash_ports, dashdash_mac
    from . import extra_soc_outlook
    from tkinter import filedialog
    with tempfile.TemporaryDirectory(prefix="Pocket-FORMGT-") as tmp:
        folder = Path(tmp)
        # Process-local routing, including the database module and command library.
        portable_storage.data_directory = lambda *a, **kw: folder
        portable_storage.is_portable = lambda *a, **kw: True
        network_tools.scan_tcp_ports = simulated_ports
        dashdash_ports.check_remote_ports = lambda ip, ports, **kw: list(simulated_ports(ip, ports))
        def blocked(*args, **kwargs):
            raise RuntimeError("Disabled in FORMGT demo")
        dashdash_mac.lookup_remote_macs = blocked
        network_tools.download_ieee_database = blocked
        def block_outlook(*args, **kwargs):
            raise extra_soc_outlook.OutlookUnavailable("Outlook is disabled in FORMGT demo")
        extra_soc_outlook.open_draft = block_outlook
        # Never browse the host's workbooks or write exports from this demo.
        filedialog.askopenfilename = lambda *a, **kw: ""
        filedialog.askopenfilenames = lambda *a, **kw: ()
        filedialog.asksaveasfilename = lambda *a, **kw: ""
        filedialog.askdirectory = lambda *a, **kw: ""
        workbook = seed_profile(api, folder)
        class DemoApp(api["PocketDesk"]):
            def hide(self):
                controller = getattr(self, "_formgt", None)
                if controller is not None:
                    controller.close()
                else:
                    self.root.destroy()
            def _clipboard_poll(self):
                pass
            def _reminder_poll(self):
                pass
            def open_shortcut(self, item):
                pass
            def open_link(self, url):
                pass
            def open_notepad(self):
                pass
            def _update_vendors(self):
                pass
        app = DemoApp(preview=True)
        for snippet in ("DEMO-1042", "192.0.2.10", "show ip interface brief"):
            api["clipboard_add"](app.clipboard_items, snippet)
        presentation = Presentation(app, api, workbook, auto_start=not smoke)
        app._formgt = presentation
        if smoke:
            try:
                presentation.paused = True
                for i, step in enumerate(STEPS):
                    presentation.go(i)
                    app.root.update()
                    deadline = time.monotonic() + 12
                    while (app.scanning or api["extra_excel_ui"].session(app)["busy"]):
                        if time.monotonic() > deadline:
                            raise AssertionError("Demo worker timed out: " + step[4])
                        app.root.update()
                        time.sleep(0.03)
                    if presentation.error:
                        raise AssertionError(presentation.error)
                    if step[4] != "summary":
                        assert app.display_mode == "mini", "Expected Mini mode"
                    assert presentation.footer.winfo_ismapped(), "Missing integrated controller"
                    if step[4] in ("extra", "return_extra"):
                        state = api["extra_excel_ui"].session(app)
                        assert state["hits"] and state["query"] == "DEMO-1042", "EXTRA demo record missing"
                        assert state["selected"] == 0, "EXTRA selection missing"
                    if step[4] == "palette":
                        assert app._quick_search_dialog is not None, "Palette did not open"
                        presentation.execute_palette_demo()
                        assert app.current_tab == "subnet", "Palette action did not navigate"
                    if step[4] == "commands":
                        assert app.command_filtered, "CLI results missing"
                    if step[4] == "subnet":
                        assert app.subnet_details, "Subnet calculation missing"
                    if step[4] == "ports":
                        assert len(app.port_results) == 3, "Simulated TCP results missing"
                    if step[4] == "mac":
                        assert app.mac_results, "MAC results missing"
                    if step[4] == "summary":
                        assert presentation.overlay.winfo_ismapped(), "Missing final impact card"
                presentation.restart()
                app.root.update()
                assert app.display_mode == "mini", "Replay did not restore Mini"
                assert presentation.footer.winfo_ismapped(), "Replay controller missing"
                print("FORMGT smoke: all presentation steps completed")
            finally:
                presentation.close()
        else:
            app.run()
    return 0
