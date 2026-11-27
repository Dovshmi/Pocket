"""FORMGT: guided, isolated presentation of the real Pocket UI."""
from __future__ import annotations

import json
import ipaddress
import sys
import tempfile
import time
import tkinter as tk
from datetime import datetime, timedelta
from pathlib import Path


SPEEDS = (0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 3.0)
DEFAULT_SCENARIO = {"customer": "Orion Logistics", "circuit": "90021400",
                    "vrf": "VRF-BUS-ERP", "public_ip": "192.0.2.52"}
WAN_IP = "10.178.24.14"
MACS = ("00:00:0C:24:71:11", "00:01:42:24:71:12",
        "00:80:9F:24:71:13", "00:09:0F:24:71:14")
VENDORS = {"00000C": ["Cisco Systems, Inc.", "MA-L"],
           "000142": ["Cisco Systems, Inc.", "MA-L"],
           "00809F": ["Alcatel-Lucent Enterprise (ALE)", "MA-L"],
           "00090F": ["Fortinet, Inc. (FortiGate)", "MA-L"]}


def load_scenario():
    """Read presentation-only overrides beside the EXE/source, never commit them."""
    base = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parents[1]
    path = base / "formgt-scenario.local.json"
    if not path.is_file():
        return dict(DEFAULT_SCENARIO)
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict) or set(data) != set(DEFAULT_SCENARIO):
        raise ValueError("Invalid FORMGT scenario fields")
    if any(not isinstance(v, str) or not v.strip() or len(v) > 80 or not v.isprintable() for v in data.values()):
        raise ValueError("Invalid FORMGT scenario values")
    if not data["circuit"].isascii() or not data["circuit"].isdigit():
        raise ValueError("Circuit must contain digits only")
    data["public_ip"] = str(ipaddress.IPv4Address(data["public_ip"]))
    return data


STEPS = (
    ("WELCOME", "כל הכלים. מקום אחד.", "סביבת עבודה אחת שמרכזת את הכלים הדרושים לנציג.", 5500, "intro"),
    ("NOTES", "מתעדים תוך כדי טיפול", "שמירת פרטי הלקוח והתקלה ללא מעבר בין יישומים.", 7000, "notes"),
    ("SHORTCUTS", "הגישה למידע מתחילה בלחיצה", "ריכוז קישורים, מערכות ונהלים מקצועיים.", 6000, "links"),
    ("COMMANDS", "הידע המקצועי תמיד בהישג יד", "פחות חיפוש פקודות, יותר זמן לאבחון התקלה.", 9000, "commands"),
    ("SUBNET", "מחישוב ידני לתוצאה מיידית", "חישובי רשת מדויקים ללא שימוש בכלים חיצוניים.", 8000, "subnet"),
    ("PORTS", "אבחון ממוקד ומהיר", "תוצאות TCP מדומות בלבד · ללא תעבורה לרשת.", 9000, "ports"),
    ("MAC", "מזהים את הציוד בשניות", "זיהוי יצרנים מקומי וסיכום ציוד לפי יצרן.", 8000, "mac"),
    ("CLIPBOARD", "לא מקלידים את אותו מידע פעמיים", "שימוש חוזר במידע שכבר נאסף במהלך הטיפול.", 7000, "clipboard"),
    ("REMINDERS", "הטיפול לא מסתיים בשיחה", "מעקב אחר משימות פתוחות והתחייבויות ללקוח.", 7000, "reminders"),
    ("EXTRA", "המידע הנכון, ברגע הנכון", "איתור פרטי השירות ללא מעבר בין קבצים ומערכות.", 10000, "extra"),
    ("WORKFLOW", "רצף עבודה ללא הפרעות", "מעבר לבדיקת פורטים בלי לאבד את המידע שכבר נמצא.", 5000, "switch_extra"),
    ("EXTRA", "ממשיכים בדיוק מהמקום שעצרנו", "תוצאות החיפוש נשארות זמינות לאורך הטיפול.", 6000, "return_extra"),
    ("CTRL+K", "כל פעולה במרחק קיצור אחד", "גישה ישירה וחכמה לכלי העבודה.", 8000, "palette"),
    ("BUSINESS IMPACT", "פחות חיפוש. יותר טיפול.", "קיצור פעולות תפעוליות ויצירת סביבת עבודה אחידה.", 0, "summary"),
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


def seed_profile(api, folder, scenario):
    """Create a new synthetic profile and index; never import a real library."""
    from openpyxl import Workbook
    from . import extra_excel_db, reminder_store
    customer, circuit, vrf, public_ip = (scenario[k] for k in ("customer", "circuit", "vrf", "public_ip"))
    data = api["default_data"]()
    data["settings"].update(display_mode="mini", window_profile="Mini",
                            clipboard_paused=True, clipboard_storage="ram",
                            quick_slots_enabled=False, convert_enabled=False)
    data["last_tab"] = "notes"
    note = api["new_note"](f"{customer} | ERP connectivity",
        f"DEMONSTRATION ONLY\nCustomer: {customer}\nCircuit: {circuit}\nVRF: {vrf}\n"
        f"Customer reports ERP access failure.\nCisco ISR 4331 | WAN {WAN_IP}/29\n"
        f"Public target: {public_ip}\n"
        "Next: validate interfaces, review TCP results, arrange callback.")
    data["notes"] = [note]
    data["active_note"] = note["id"]
    data["links"] = [api["new_link"](name, "https://example.invalid/" + slug)
                     for name, slug in (("Network procedures", "procedures"), ("IPVPN service portal", "ipvpn"),
                                        ("Equipment knowledge base", "kb"), ("Diagnostics center", "diagnostics"))]
    layout = api["shortcut_folders"].normalize(None, data["links"])
    for name, items in (("Operational systems", data["links"][1::2]),
                        ("Knowledge & procedures", data["links"][::2])):
        fid = api["shortcut_folders"].add_folder(layout, name)
        for link in items:
            api["shortcut_folders"].move(layout, api["shortcut_folders"].link_key(link["id"]),
                                         api["shortcut_folders"].folder_key(fid), "inside")
    data["shortcut_folders"] = layout
    data["reminders"] = [reminder_store.make_reminder(f"{customer} | Customer follow-up",
        f"Check ERP connectivity and return call. Circuit: {circuit} (demo only).",
        (datetime.now().astimezone() + timedelta(minutes=30)).isoformat())]
    data["tools"].update(target=public_ip, source="local", mac_source="local",
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
        "vendors":VENDORS}), encoding="utf-8")
    book = Workbook()
    sheet = book.active
    sheet.title = "Demo services"
    sheet.append(["Circuit ID", "Customer", "Group ID", "VRF", "Site", "Device", "WAN IP", "Public IP", "VLAN FG"])
    sheet.append([circuit, customer, "DEMO-G01", vrf, "South region (demo)", "Cisco ISR 4331", WAN_IP, public_ip, "120"])
    sheet.append(["90021401", "Training customer", "DEMO-G02", "Training", "Lab B", "Juniper", "192.0.2.20", "192.0.2.53", "121"])
    path = folder / "demo-services.xlsx"
    book.save(path)
    book.close()
    extra_excel_db.sync_database(path, db_path=folder / extra_excel_db.FILE_NAME)
    return path


class Presentation:
    """Desktop-centered speech bubble and independent left-side presenter bar."""
    BG = "#101b30"
    CARD = "#172943"
    ACCENT = "#79e4cf"
    TEXT = "#f5f8ff"
    MUTED = "#b0c1d9"
    KEY = "#010203"

    def __init__(self, app, api, workbook, scenario, *, auto_start=True):
        self.app, self.api, self.workbook, self.scenario = app, api, workbook, scenario
        self.index = -1
        self.job = None
        self.events = []
        self.elapsed = 0.
        self.last = time.monotonic()
        self.speed = 1.
        self.manual = False
        self.paused = False
        self.closed = False
        self.smoke = not auto_start
        self.error = ""
        self.action_pending = False
        self.action = None
        self.root = app.root
        self.root.title("Pocket | FORMGT — DEMO ONLY")
        self.root.attributes("-topmost", True)
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.side = tk.Toplevel(self.root)
        self.side.overrideredirect(True)
        self.side.attributes("-topmost", True)
        self.side.configure(bg=self.BG, highlightthickness=1, highlightbackground="#334761")
        self.side.protocol("WM_DELETE_WINDOW", self.close)
        self.bubble = tk.Toplevel(self.root)
        self.bubble.withdraw()
        self.bubble.overrideredirect(True)
        self.bubble.attributes("-topmost", True)
        self.bubble.configure(bg=self.KEY)
        if sys.platform == "win32":
            self.bubble.attributes("-transparentcolor", self.KEY)
        self.canvas = tk.Canvas(self.bubble, bg=self.KEY, highlightthickness=0, bd=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Button-1>", lambda e: self.hide_card())
        self.card_visible = False
        self.fade_job = None
        self.reveal_until = None
        self.build_side()
        for seq, handler in (("<F5>", self.restart), ("<F6>", self.toggle),
                             ("<F7>", self.previous), ("<F8>", self.next),
                             ("<F9>", self.repeat_card), ("<F10>", self.toggle_mode),
                             ("<Control-Up>", lambda: self.change_speed(1)),
                             ("<Control-Down>", lambda: self.change_speed(-1)),
                             ("<Escape>", self.close)):
            def key(event, callback=handler):
                callback()
                return "break"
            self.root.bind_all(seq, key, add="+")
        # Remove the original app Escape handler, otherwise it precedes bind_all.
        self.root.unbind("<Escape>")
        if sys.platform == "win32":
            # Native EDIT/RichEdit controls may consume Tk key events. Poll only
            # presenter keys, only while a window of THIS process has focus.
            self.win_keys = {}
            self.root.after(40, self.poll_presenter_keys)
            for seq in ("<F5>", "<F6>", "<F7>", "<F8>", "<F9>", "<F10>", "<Control-Up>", "<Control-Down>"):
                self.root.unbind_all(seq)
        self.position()
        if auto_start:
            self.root.after(700, self.restart)
            self.job = self.root.after(50, self.tick)

    def poll_presenter_keys(self):
        if self.closed:
            return
        import ctypes
        from ctypes import wintypes
        import os
        user = ctypes.windll.user32
        user.GetForegroundWindow.restype = wintypes.HWND
        pid = wintypes.DWORD()
        user.GetWindowThreadProcessId(user.GetForegroundWindow(), ctypes.byref(pid))
        ctrl = bool(user.GetAsyncKeyState(0x11) & 0x8000)
        actions = {0x74: self.restart, 0x75: self.toggle, 0x76: self.previous,
                   0x77: self.next, 0x78: self.repeat_card, 0x79: self.toggle_mode,
                   0x26: lambda: self.change_speed(1), 0x28: lambda: self.change_speed(-1)}
        for vk, callback in actions.items():
            down = bool(user.GetAsyncKeyState(vk) & 0x8000)
            pressed = down and not self.win_keys.get(vk, False)
            self.win_keys[vk] = down
            if pid.value == os.getpid() and pressed and (vk not in (0x26,0x28) or ctrl):
                callback()
        if not self.closed:
            self.root.after(40, self.poll_presenter_keys)

    def widget_alive(self, widget):
        return widget is not None and widget.winfo_exists()

    def build_side(self):
        def label(text, size=9, fg=None):
            w = tk.Label(self.side, text=text, bg=self.BG, fg=fg or self.MUTED,
                         font=("Segoe UI", size, "bold"))
            w.pack(fill="x", padx=5, pady=3)
            return w
        label("FORMGT", 9, self.ACCENT)
        self.step_label = label("00 / 14", 10, self.TEXT)
        self.track = tk.Canvas(self.side, height=4, bg="#293a50", highlightthickness=0)
        self.track.pack(fill="x", padx=8, pady=(0, 6))
        self.pause_button = self.button("Pause", self.toggle)
        for text, cb in (("Next ›", self.next), ("‹ Back", self.previous),
                         ("Replay", self.restart), ("Explain", self.repeat_card)):
            self.button(text, cb)
        self.mode_button = self.button("AUTO", self.toggle_mode)
        self.button("+ Faster", lambda: self.change_speed(1))
        self.speed_label = label("1×", 15, self.ACCENT)
        self.button("− Slower", lambda: self.change_speed(-1))
        self.button("Exit", self.close)
        label("F5–F10", 8)

    def button(self, text, callback):
        w = tk.Button(self.side, text=text, command=callback, bg="#243852", fg=self.TEXT,
                      activebackground="#385778", activeforeground=self.TEXT,
                      relief="flat", bd=0, padx=6, pady=5, cursor="hand2",
                      font=("Segoe UI", 9, "bold"))
        w.pack(fill="x", padx=7, pady=2)
        return w

    def area(self):
        r = self.root
        r.update_idletasks()
        return self.app._screen_work_area(r.winfo_rootx()+r.winfo_width()//2,
                                          r.winfo_rooty()+r.winfo_height()//2)

    def position(self):
        left, top, right, bottom = self.area()
        self.side.update_idletasks()
        h = self.side.winfo_reqheight()
        self.side.geometry(f"108x{h}{left+12:+d}{top+max(5,(bottom-top-h)//2):+d}")
        self.side.lift()

    def draw_progress(self):
        width = max(1, self.track.winfo_width())
        self.track.delete("all")
        self.track.create_rectangle(0, 0, width*(self.index+1)/len(STEPS), 4,
                                    fill=self.ACCENT, outline="")

    def refresh(self):
        status = "SIM" if self.action == "ports" else ("MAN" if self.manual else "DEMO")
        self.step_label.configure(text=f"{self.index+1:02d}/{len(STEPS):02d} {status}")
        self.pause_button.configure(text="Play" if self.paused else "Pause")
        self.mode_button.configure(text="MANUAL" if self.manual else "AUTO")
        self.speed_label.configure(text=f"{self.speed:g}×")
        self.draw_progress()

    def change_speed(self, amount):
        self.speed = SPEEDS[max(0, min(len(SPEEDS)-1, SPEEDS.index(self.speed)+amount))]
        self.refresh()

    def toggle_mode(self):
        self.manual = not self.manual
        self.refresh()

    def toggle(self):
        if self.error:
            self.paused = False
            self.go(self.index)
            return
        self.paused = not self.paused
        self.last = time.monotonic()
        self.refresh()

    def later(self, ms, callback):
        self.events.append((self.elapsed + ms, callback))

    def cancel(self):
        self.events.clear()

    def tick(self):
        if self.closed:
            return
        now = time.monotonic()
        delta = min(250., (now-self.last)*1000)
        self.last = now
        if not self.paused:
            self.elapsed += delta*self.speed
            try:
                while self.events:
                    due, cb = min(self.events, key=lambda item: item[0])
                    if due > self.elapsed:
                        break
                    self.events.remove((due, cb))
                    cb()
                duration = STEPS[self.index][3] if self.index >= 0 else 0
                if duration and self.elapsed >= duration and not self.manual and not self.events:
                    state = self.api["extra_excel_ui"].session(self.app)
                    if not (self.app.scanning or state["busy"]):
                        self.next()
            except Exception as exc:
                self.fail(exc)
        if self.reveal_until is not None and now >= self.reveal_until:
            self.reveal_until = None
            if self.action != "summary" and not self.error:
                self.hide_card()
        self.job = self.root.after(50, self.tick)

    def fade(self, value=0.35):
        if not self.card_visible:
            return
        try:
            self.bubble.attributes("-alpha", value)
        except tk.TclError:
            return
        if value < 0.96:
            self.fade_job = self.root.after(30, lambda: self.fade(min(0.96,value+0.17)))
        else:
            self.fade_job = None

    def hide_card(self):
        if self.fade_job is not None:
            self.root.after_cancel(self.fade_job)
            self.fade_job = None
        self.card_visible = False
        self.bubble.withdraw()

    def explain(self):
        if self.index < 0:
            return
        from PIL import Image, ImageDraw, ImageTk
        name, headline, detail, _, key = STEPS[self.index]
        if self.error:
            detail = self.error
        left, top, right, bottom = self.area()
        width = min(580, right-left-40)
        height = 268 if key == "summary" else 166
        self.canvas.configure(width=width, height=height)
        # Render a truly rounded, transparent-key silhouette on Windows.
        image = Image.new("RGB", (width, height), self.KEY)
        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle((8, 7, width-8, height-8), radius=30,
                               fill=self.CARD, outline="#628c9c", width=1)
        self.bubble_photo = ImageTk.PhotoImage(image, master=self.bubble)
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, image=self.bubble_photo, anchor="nw")
        self.canvas.create_text(width/2, 29, text=f"{name}  •  {self.index+1:02d}/{len(STEPS):02d}",
                                fill=self.ACCENT, font=("Segoe UI", 10, "bold"))
        self.canvas.create_text(width/2, 64, text=headline, width=width-60,
                                fill=self.TEXT, font=("Segoe UI", 18, "bold"), justify="center")
        self.canvas.create_text(width/2, 108, text=detail, width=width-60,
                                fill=self.MUTED, font=("Segoe UI", 12), justify="center")
        if key == "summary":
            self.canvas.create_text(width/2, 154, text="183 שעות בחודש", fill=self.ACCENT,
                                    font=("Segoe UI", 26, "bold"))
            self.canvas.create_text(width/2, 192, text="30 sec × 20 calls × 50 agents × 22 days",
                                    fill=self.TEXT, font=("Segoe UI", 11))
            self.canvas.create_text(width/2, 222, text="תרחיש להמחשה בלבד · לא תוצאות מדידה",
                                    fill=self.MUTED, font=("Segoe UI", 11))
        else:
            self.canvas.create_line(width/2-35, 143, width/2+35, 143,
                                    fill=self.ACCENT, width=3, capstyle="round")
        self.bubble.geometry(f"{width}x{height}{left+(right-left-width)//2:+d}{top+(bottom-top-height)//2:+d}")
        if self.fade_job is not None:
            self.root.after_cancel(self.fade_job)
            self.fade_job = None
        self.card_visible = True
        self.bubble.deiconify()
        self.bubble.lift()
        self.side.lift()
        if not self.smoke:
            self.fade()

    def repeat_card(self):
        self.explain()
        self.reveal_until = time.monotonic()+3.0/self.speed

    def next(self):
        if self.index < len(STEPS)-1:
            self.go(self.index+1)

    def previous(self):
        self.go(max(0,self.index-1))

    def restart(self):
        self.paused = False
        self.go(0)

    def close_palette(self):
        dialog = getattr(self.app, "_quick_search_dialog", None)
        if self.widget_alive(dialog):
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
            tab = {"intro":"notes", "palette":"notes", "switch_extra":"ports",
                   "return_extra":"extra"}.get(key, key)
            a.show_tab(tab)
        self.position()

    def go(self, index):
        self.cancel()
        self.close_palette()
        self.hide_card()
        self.reveal_until = None
        self.index = index
        self.elapsed = 0.
        self.last = time.monotonic()
        self.error = ""
        self.action_pending = True
        self.action = STEPS[index][4]
        try:
            self.show_tool(self.action)
            self.refresh()
            self.explain()
            if self.action == "summary":
                self.action_pending = False
            elif self.smoke or self.paused:
                self.hide_card()
                self.perform_action()
            else:
                self.later(2300, self.hide_card)
                self.later(2500, self.perform_action)
        except Exception as exc:
            self.fail(exc)

    def fail(self, exc):
        self.cancel()
        self.paused = True
        self.error = f"Demo paused: {type(exc).__name__}: {exc}"
        self.refresh()
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

    def type_text(self, setter, value, done=None):
        if self.smoke or self.paused:
            setter(value)
            if done:
                done()
            return
        setter("")
        for i in range(1, len(value)+1, 2):
            self.later(65*i, lambda n=i: setter(value[:n]))
        self.later(65*(len(value)+1), lambda: setter(value))
        if done:
            self.later(65*(len(value)+2), done)

    def apply(self, key):
        a = self.app
        if key == "commands":
            a._command_focus_in()
            a.machine_var.set("Cisco")
            a._change_machine()
            self.type_text(a.command_query.set, "show ip interface brief", a._refresh_command_results)
        elif key == "subnet":
            a.subnet_ip_var.set(WAN_IP)
            a.subnet_prefix_var.set("29")
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
            a.host_var.set(self.scenario["public_ip"])
            a.ports_var.set("22,443,8080")
            a._start_scan()
            if not self.smoke:
                self.later(1400, lambda: self.scroll_to(a.port_tree))
        elif key == "mac":
            a.mac_source.set("local")
            a.mac_input.delete("1.0", "end")
            a.mac_input.insert("1.0", "\n".join(MACS))
            a._run_mac_lookup()
            if not a.mac_vendor_expanded:
                a._toggle_mac_summary()
            if not self.smoke:
                self.later(900, lambda: self.scroll_to(a.mac_summary_panel))
        elif key == "extra":
            a._extra_excel_path = str(self.workbook)
            a._extra_palette_search(self.scenario["circuit"])
            if not self.smoke:
                self.later(1500, lambda: self.scroll_to(fraction=0.48))
        elif key == "return_extra":
            # Manual jumps may reach this chapter before the first search.
            state = self.api["extra_excel_ui"].session(a)
            if not state["hits"] and not state["busy"]:
                a._extra_palette_search(self.scenario["circuit"])
            if not self.smoke:
                self.later(1000, lambda: self.scroll_to(fraction=0.48))
        elif key == "palette":
            a._open_global_search()
            def set_palette(value):
                a._palette_entry.delete(0, "end")
                a._palette_entry.insert(0, value)
            self.type_text(set_palette, "< extra " + self.scenario["circuit"])
            if not self.smoke:
                self.later(2300, self.execute_palette_demo)
        elif key == "summary":
            self.explain()

    def execute_palette_demo(self):
        a = self.app
        dialog = getattr(a, "_quick_search_dialog", None)
        if not self.widget_alive(dialog):
            return
        hit = self.api["command_palette"].command("extra " + self.scenario["circuit"], a.settings)
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
        if self.job is not None:
            self.root.after_cancel(self.job)
        self.hide_card()
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
        network_tools.check_tcp_port = lambda ip, port, *a, **kw: next(simulated_ports(ip, [port]))
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
        scenario = dict(DEFAULT_SCENARIO) if smoke else load_scenario()
        workbook = seed_profile(api, folder, scenario)
        class DemoApp(api["PocketDesk"]):
            def _build_shell_refresh(self):
                # Preserve independent presenter windows across layout rebuilds.
                self._flush_current_note()
                api["extra_excel_ui"].detach(self)
                for child in self.root.winfo_children():
                    if not isinstance(child, tk.Toplevel):
                        child.destroy()
                self._header_context_menu = None
                self._build_shell()
                self.show_tab(self.current_tab)
                self._install_resize_handles()
                self._place_popup(self._last_tray_xy)
            def _choose_theme(self, name):
                pass  # Keep the presentation styling stable.
            def _poll_events(self):
                super()._poll_events()
                if self.current_tab == "ports" and not self.scanning and self.port_results:
                    self.scan_info.config(text="SIMULATED TCP results · no network traffic")
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
        for snippet in (scenario["circuit"], scenario["public_ip"], WAN_IP, "show ip interface brief"):
            api["clipboard_add"](app.clipboard_items, snippet)
        presentation = Presentation(app, api, workbook, scenario, auto_start=not smoke)
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
                    assert presentation.side.winfo_ismapped(), "Missing integrated controller"
                    if step[4] in ("extra", "return_extra"):
                        state = api["extra_excel_ui"].session(app)
                        assert state["hits"] and state["query"] == scenario["circuit"], "EXTRA demo record missing"
                        assert state["selected"] == 0, "EXTRA selection missing"
                    if step[4] == "palette":
                        assert app._quick_search_dialog is not None, "Palette did not open"
                        presentation.execute_palette_demo()
                        assert app.current_tab == "extra", "Palette action did not navigate"
                    if step[4] == "commands":
                        assert app.command_filtered, "CLI results missing"
                    if step[4] == "subnet":
                        assert app.subnet_details, "Subnet calculation missing"
                    if step[4] == "ports":
                        assert len(app.port_results) == 3, "Simulated TCP results missing"
                    if step[4] == "mac":
                        assert len(app.mac_results) == 4, "Expected four MAC results"
                        names = [row["vendor"] for row in app.mac_results]
                        assert sum("Cisco" in name for name in names) == 2
                        assert sum("Alcatel" in name for name in names) == 1
                        assert sum("FortiGate" in name for name in names) == 1
                    if step[4] == "summary":
                        assert presentation.bubble.winfo_ismapped(), "Missing final impact card"
                presentation.change_speed(1)
                assert presentation.speed == 1.25
                presentation.toggle_mode()
                assert presentation.manual
                presentation.toggle_mode()
                presentation.restart()
                app.root.update()
                assert app.display_mode == "mini", "Replay did not restore Mini"
                assert presentation.side.winfo_ismapped(), "Replay controller missing"
                print("FORMGT smoke: all presentation steps completed")
            finally:
                presentation.close()
        else:
            app.run()
    return 0
