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


SPEEDS = (0.1, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 3.0)
CHANNELS = ("step", "hold", "appear", "disappear", "typing")
CHANNEL_LABELS = {"step": "STEP", "hold": "BUBBLE HOLD", "appear": "FADE IN",
                  "disappear": "FADE OUT", "typing": "TYPING"}
DEFAULT_SCENARIO = {"customer": "CLALIT", "circuit": "90021400",
                    "vrf": "clalit", "public_ip": "192.0.2.52",
                    "vpn_users": "ALEX, JORDAN", "phone": "", "port": "10443",
                    "vdom": "TRAINING", "forti_ip": "10.238.2.25", "group": "DEMO-G01"}
WAN_IP = "10.178.24.14"
MACS = ("00:00:0C:24:71:11", "00:01:42:24:71:12",
        "00:80:9F:24:71:13", "00:09:0F:24:71:14")
VENDORS = {"00000C": ["Cisco", "MA-L"],
           "000142": ["Cisco", "MA-L"],
           "00809F": ["Alcatel-Lucent", "MA-L"],
           "00090F": ["Fortinet (FortiGate)", "MA-L"]}


def load_scenario():
    """Read presentation-only overrides beside the EXE/source, never commit them."""
    base = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parents[1]
    path = base / "formgt-scenario.local.json"
    if "--formgt-scenario" in sys.argv:
        arg = sys.argv.index("--formgt-scenario")+1
        if arg >= len(sys.argv):
            raise ValueError("--formgt-scenario requires a JSON file path")
        path = Path(sys.argv[arg]).expanduser().resolve()
        if not path.is_file():
            raise FileNotFoundError(path)
    elif not path.is_file():
        # Support the extracted onedir package with the configuration in its parent.
        parent_config = base.parent / "formgt-scenario.local.json"
        if parent_config.is_file():
            path = parent_config
        else:
            return {**DEFAULT_SCENARIO, "_local": False}
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict) or not {"customer", "circuit", "vrf", "public_ip"} <= set(data) <= set(DEFAULT_SCENARIO):
        raise ValueError("Invalid FORMGT scenario fields")
    data = {**DEFAULT_SCENARIO, **data}
    if any(not isinstance(v, str) or (k != "phone" and not v.strip()) or len(v) > 80 or (v and not v.isprintable()) for k, v in data.items()):
        raise ValueError("Invalid FORMGT scenario values")
    if not data["circuit"].isascii() or not data["circuit"].isdigit():
        raise ValueError("Circuit must contain digits only")
    data["public_ip"] = str(ipaddress.IPv4Address(data["public_ip"]))
    data["forti_ip"] = str(ipaddress.IPv4Address(data["forti_ip"]))
    if not data["forti_ip"].startswith("10.238.2.") or not 1 <= int(data["forti_ip"].split(".")[-1]) <= 254:
        raise ValueError("Demo FortiGate must use the 10.238.2.x sheet convention")
    if not data["port"].isascii() or not data["port"].isdigit() or not 1 <= int(data["port"]) <= 65535:
        raise ValueError("Invalid demo port")
    if data["customer"].strip().casefold() in ("orion logistics", "clalit", "כללית", "clalit / כללית", "כללית / clalit", "כללית clalit", "clalit כללית"):
        data["customer"] = "CLALIT"
        data["vrf"] = "clalit"
    data["_local"] = True
    return data


def note_title(scenario):
    """Use the Hebrew customer title consistently at startup and during replay."""
    return "כללית" if scenario["customer"].casefold() == "clalit" else scenario["customer"]


def note_text(scenario):
    users = "\n".join(name.strip() for name in scenario["vpn_users"].split(",") if name.strip())
    return f"לקוח ביקש להוסיף יוזר VPN\n{users}\n\nIP: {scenario['public_ip']}\nPORT: {scenario['port']}\n\nDEMO בלבד"


TASKS_TEXT = "משימות\n\n1. לחמם את הבאכש\n2. להוסיף יוזר VPN\n3. לחזור ללקוח\n4. לאמת גישה"
NOTE_ADDITION = "\n5. לעדכן את הלקוח לאחר סיום הבדיקות"


def demo_notes(api, scenario):
    first = api["new_note"](note_title(scenario), note_text(scenario), scenario["phone"])
    first.update(reminder_enabled=True,
                 reminder_at=(datetime.now().astimezone()+timedelta(minutes=30)).isoformat())
    line = api["new_note"]("פרטי קו",
        f"לקוח: {note_title(scenario)}\n\nקוד קו / קוד קישור:\n{scenario['circuit']}\n\n"
        f"VRF: {scenario['vrf']}\nVDOM: {scenario['vdom']}\nFORTI: {scenario['forti_ip']}\nקוד קבוצה: {scenario['group']}")
    checks = api["new_note"]("בדיקות",
        f"בדיקות מתוכננות — דוגמה בלבד\n\nIP: {scenario['public_ip']}\nPORT: {scenario['port']}\n\n"
        "show ip interface brief\n\nCisco / Alcatel / Fortinet")
    tasks = api["new_note"]("משימות", TASKS_TEXT)
    for n in (first,line,checks,tasks):
        n["direction"] = "rtl"
    return [first,line,checks,tasks]


STEPS = (
    ("WELCOME", "כל הכלים. מקום אחד.", "סביבת עבודה אחת לצד מערכות העבודה הקיימות.", 5500, "intro"),
    ("NOTES", "כל התיעוד בהישג יד", "דפדוף בין ארבע הערות, הוספת משימה ושמירה אוטומטית.", 13000, "notes"),
    ("SHORTCUTS", "גישה מהירה למשאבי עבודה", "קבצים ואתרים מסודרים בתיקיות עבודה, לימודים וקישורים נוספים.", 9000, "links"),
    ("COMMANDS", "הידע המקצועי בהישג יד", "חיפוש ממשקים אחד — פקודות שונות למגוון סוגי ציוד.", 14000, "commands"),
    ("SUBNET", "מחישוב ידני לתוצאה מיידית", "חישוב רשת וטווח כתובות, כולל חלוקה לתת־רשתות.", 12000, "subnet"),
    ("PORTS", "אבחון ממוקד ומהיר", "בדיקת יעד ופורטים · תוצאות מדומות בלבד.", 11500, "ports"),
    ("MAC VENDOR", "מזהים ארבעה התקנים בפעולה אחת", "שני Cisco, אחד Alcatel ואחד Fortinet · סיכום וסינון לפי יצרן.", 16000, "mac"),
    ("CLIPBOARD", "מידע נשאר זמין לשימוש חוזר", "כתובות, פקודות, מספרי קו ותמונות שנאספו במהלך הטיפול.", 14000, "clipboard"),
    ("REMINDERS", "התחייבויות ללקוח בשליטה", "מעקב אחר תזכורת מקושרת להערה ומשימת המשך.", 7500, "reminders"),
    ("EXTRA NET", "המידע הנכון, ברגע הנכון", "שליפת פרטי קו ושירות מתוך מאגר מקומי.", 11000, "extra"),
    ("CTRL+K", "כל פעולה במרחק קיצור אחד", "חיפוש חכם לפי כתובת, פקודה או כלי — בלי לעבור בתפריטים.", 10000, "palette"),
    ("DISPLAY MODES", "שלושה מצבי תצוגה. אותם כלים.", "מחלון Mini קומפקטי, דרך Normal ועד סביבת Dashboard מלאה.", 6400, "modes"),
    ("BUSINESS IMPACT", "פחות חיפוש. יותר טיפול.", "סביבת עבודה אחידה שמחברת את שלבי הטיפול.", 0, "summary"),
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
    data["notes"] = demo_notes(api, scenario)
    data["active_note"] = data["notes"][0]["id"]
    # Actual file-type shortcuts, but only harmless temporary demonstration files.
    demo_files = folder / "demo-files"
    demo_files.mkdir(exist_ok=True)
    password_book = Workbook()
    password_book.active.append(["Demo file", "No credentials are stored here"])
    password_book.save(demo_files / "סיסמאות.xlsx")
    password_book.close()
    for filename in ("BWIFI.txt", "BCAM.txt"):
        (demo_files / filename).write_text("FORMGT — קובץ לימוד לדוגמה בלבד", encoding="utf-8")
    groups = [
        ("עבודה", [
            ("קובץ סיסמאות", str(demo_files / "סיסמאות.xlsx"), "file"),
            ("EXTRANET.XL", str(folder / "EXTRANET.xlsx"), "file"),
            ("אתר בזק", "https://www.bezeq.co.il/", "url")]),
        ("לימודים", [
            ("קובץ BWIFI", str(demo_files / "BWIFI.txt"), "file"),
            ("קובץ BCAM", str(demo_files / "BCAM.txt"), "file"),
            ("אתר הלימודים של סיסקו", "https://www.netacad.com/", "url")]),
        ("קישורים נוספים", [
            ("מחשבון מקוון", "https://example.invalid/calculator", "url"),
            ("חדשות טכנולוגיה", "https://example.invalid/technology", "url"),
            ("קובץ דוגמה", str(demo_files / "BWIFI.txt"), "file")]),
    ]
    data["links"] = []
    sf = api["shortcut_folders"]
    layout = sf.normalize(None, [])
    for index,(name,items) in enumerate(groups):
        fid = sf.add_folder(layout,name)
        for title,target,kind in items:
            link = api["new_link"](title,target,kind)
            data["links"].append(link)
            sf.add_link(layout,link["id"],group=fid)
        # add_link inserts at front; restore the authored order.
        layout["children"][fid].reverse()
        sf.set_expanded(layout,fid,index < 2)
    data["shortcut_folders"] = layout
    data["reminders"] = [reminder_store.make_reminder("REBAR – חזרה ללקוח",
        "לבדוק את סטטוס התקלה, לעדכן את הלקוח ולתאם המשך טיפול.",
        (datetime.now().astimezone() + timedelta(minutes=20)).isoformat())]
    data["tools"].update(target=public_ip, source="local", mac_source="local",
                         ports_input=f"22,443,{scenario['port']}")
    api["save_data"](folder / "data.json", data)
    commands = [
        ("Alcatel-Lucent SR", "Interfaces", "Display router interface status", "show router interface"),
        ("Cisco IOS", "Interfaces", "Display interface addresses and status", "show ip interface brief"),
        ("FortiGate", "Interfaces", "Display interface configuration", "show system interface"),
        ("Huawei VRP", "Interfaces", "Display IP interface summary", "display ip interface brief"),
        ("Juniper SRX", "Interfaces", "Display interface addresses and status", "show interfaces terse"),
        ("Nokia SR OS", "Interfaces", "Display port and interface details", "show router interface detail"),
        ("Cisco IOS", "Routing", "Display routing table", "show ip route"),
        ("Cisco IOS", "Diagnostics", "Display system logs", "show logging"),
    ]
    (folder / "commands.json").write_text(json.dumps({"schema": 1, "commands": [
        dict(id="demo-"+str(i), machine=m, category=c, description=d, command=cmd)
        for i, (m,c,d,cmd) in enumerate(commands)]}, ensure_ascii=False), encoding="utf-8")
    (folder / "vendors.json").write_text(json.dumps({"updated":"DEMO",
        "vendors":VENDORS}), encoding="utf-8")
    book = Workbook()
    sheet = book.active
    # EXTRA derives the FortiGate IP from the real worksheet naming convention.
    sheet.title = "FG" + scenario["forti_ip"].split(".")[-1]
    sheet.append(["קוד קישור", "Customer", "Group ID", "VDOM", "VRF", "Site", "Device", "WAN IP", "Public IP", "VLAN FG", "Service port", "Service"])
    sheet.append([circuit, customer, scenario["group"], scenario["vdom"], vrf, "South region (demo)", "Cisco ISR 4331", WAN_IP, public_ip, "120", scenario["port"], "Business IPVPN / VPN"])
    sheet.append(["90021401", "Training customer", "DEMO-G02", "training", "Training", "Lab B", "Juniper", "192.0.2.20", "192.0.2.53", "121", "443", "Training"])
    path = folder / "EXTRANET.xlsx"
    book.save(path)
    book.close()
    extra_excel_db.sync_database(path, db_path=folder / extra_excel_db.FILE_NAME)
    return path


def sample_images(scenario):
    """Original mock screenshots, not captures of the host desktop."""
    from PIL import Image, ImageDraw, ImageFont
    try:
        font = ImageFont.truetype("segoeui.ttf", 23)
        large = ImageFont.truetype("segoeuib.ttf", 30)
    except OSError:
        font, large = ImageFont.load_default(), ImageFont.load_default()
    layouts = [
        ("VPN ACCESS REQUEST", [("REQUEST", "Add VPN users"), ("USERS", scenario["vpn_users"]),
                                ("DESTINATION", scenario["public_ip"]), ("TCP PORT", scenario["port"])]),
        ("SERVICE DETAILS", [("CIRCUIT", scenario["circuit"]), ("VRF", scenario["vrf"]),
                             ("SERVICE", "Business IPVPN"), ("DEVICE", "Cisco ISR 4331")]),
        ("CONNECTIVITY REVIEW", [("TARGET", scenario["public_ip"]), ("TCP PORT", scenario["port"]),
                                 ("RESULT", "CLOSED / simulated"), ("NEXT", "Validate access policy")]),
    ]
    for title, rows in layouts:
        image = Image.new("RGB", (850, 480), "#101b30")
        d = ImageDraw.Draw(image)
        d.rounded_rectangle((24,24,826,456), radius=20, fill="#1b2b42", outline="#435b75", width=2)
        d.text((48,45), title, font=large, fill="#ffffff")
        d.text((48,93), "POCKET  /  DEMONSTRATION IMAGE", font=font, fill="#79e4cf")
        for i,(label,value) in enumerate(rows):
            y=149+i*65
            d.rounded_rectangle((45,y-8,805,y+46),radius=8,fill="#101b30")
            d.text((63,y), label, font=font, fill="#a9bed7")
            d.text((340,y), value, font=font, fill="#ffffff")
        d.text((48,421), "Synthetic screenshot - not a live system", font=font, fill="#a9bed7")
        yield image
    image = Image.new("RGB",(850,480),"#101b30")
    d = ImageDraw.Draw(image)
    d.text((45,38),"NETWORK TOPOLOGY / DEMO",font=large,fill="#79e4cf")
    nodes = [(45,185,235,275,"Customer LAN"),(330,185,520,275,"IPVPN / VRF"),(615,185,805,275,"FortiGate")]
    for x1,y1,x2,y2,title in nodes:
        d.rounded_rectangle((x1,y1,x2,y2),radius=14,fill="#253952",outline="#79e4cf",width=2)
        d.text((x1+12,y1+30),title,font=font,fill="white")
    d.line((235,230,330,230),fill="#79e4cf",width=4)
    d.line((520,230,615,230),fill="#79e4cf",width=4)
    d.text((45,330),"Illustrative connection path - no live network data",font=font,fill="#a9bed7")
    yield image
    image = Image.new("RGB",(850,480),"#0b1220")
    d = ImageDraw.Draw(image)
    d.rectangle((0,0,850,50),fill="#263952")
    d.text((20,10),"TERMINAL / DEMO OUTPUT",font=font,fill="white")
    lines=["Router# show ip interface brief","Interface       IP-Address     Status","Gi0/0           "+WAN_IP+"    up","Gi0/1           unassigned     down","","Synthetic CLI output - not executed"]
    for i,line in enumerate(lines):
        d.text((30,85+i*53),line,font=font,fill="#79e4cf" if i==0 else "#d7e5f4")
    yield image


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
        self.rates = dict.fromkeys(CHANNELS, 1.)
        self.selected_channel = "step"
        self.clocks = dict.fromkeys(CHANNELS, 0.)
        self.bubble_phase = "hidden"
        self.phase_elapsed = 0.
        self.phase_start_alpha = 0.
        self.alpha = 0.
        self.action_finished_at = None
        self.dim_enabled = False
        self.dim = None
        self.highlight = None
        self.highlight_until = None
        self.manual = False
        self.paused = False
        self.closed = False
        self.smoke = not auto_start
        self.error = ""
        self.native_wait = None
        self.palette_demo_active = False
        self.action_pending = False
        self.highlight_channel = "step"
        self.action = None
        self.root = app.root
        self.root.withdraw()
        self.root.overrideredirect(True)
        self.root.title("Pocket | FORMGT — DEMO ONLY")
        self.root.deiconify()
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
        self.canvas.bind("<Button-1>", lambda e: self.dismiss_card())
        self.card_visible = False
        self.build_side()
        for seq, handler in (("<F5>", self.restart), ("<F6>", self.toggle),
                             ("<F7>", self.previous), ("<F8>", self.next),
                             ("<F9>", self.repeat_card), ("<F10>", self.toggle_mode),
                             ("<F11>", self.cycle_channel),
                             ("<F12>", self.reset_rates),
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
            for seq in ("<F5>", "<F6>", "<F7>", "<F8>", "<F9>", "<F10>", "<F11>", "<F12>", "<Control-Up>", "<Control-Down>"):
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
                   0x7A: self.cycle_channel, 0x7B: self.reset_rates,
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

    @property
    def speed(self):
        return self.rates["step"]

    def build_side(self):
        def label(text, size=9, fg=None):
            w = tk.Label(self.side, text=text, bg=self.BG, fg=fg or self.MUTED,
                         font=("Segoe UI", size, "bold"))
            w.pack(fill="x", padx=6, pady=2)
            return w
        label("P O C K E T   /   FORMGT", 9, self.ACCENT)
        label("LOCAL SCENARIO" if self.scenario.get("_local") else "SAMPLE DATA", 8,
              self.ACCENT if self.scenario.get("_local") else "#FFD47A")
        self.step_label = label(f"00 / {len(STEPS)}", 11, self.TEXT)
        self.chapter = label("PRESENTER", 9)
        self.track = tk.Canvas(self.side, height=4, bg="#293a50", highlightthickness=0)
        self.track.pack(fill="x", padx=8, pady=(0, 6))
        self.pause_button = self.button("Pause  ·  F6", self.toggle)
        nav = tk.Frame(self.side, bg=self.BG)
        nav.pack(fill="x", padx=5)
        self.button("‹ Back", self.previous, nav).pack(side="left", fill="x", expand=True, padx=1)
        self.button("Next ›", self.next, nav).pack(side="left", fill="x", expand=True, padx=1)
        nav2 = tk.Frame(self.side, bg=self.BG)
        nav2.pack(fill="x", padx=5, pady=2)
        self.button("Replay", self.restart, nav2).pack(side="left", fill="x", expand=True, padx=1)
        self.button("Explain", self.repeat_card, nav2).pack(side="left", fill="x", expand=True, padx=1)
        self.mode_button = self.button("AUTO  ·  F10", self.toggle_mode)
        label("INDEPENDENT TIMING", 8, self.ACCENT)
        self.rate_labels, self.rate_rows = {}, {}
        for channel in CHANNELS:
            row = tk.Frame(self.side, bg=self.BG)
            row.pack(fill="x", padx=6, pady=2)
            self.rate_rows[channel] = row
            caption = tk.Label(row, text=CHANNEL_LABELS[channel], font=("Segoe UI", 8, "bold"),
                               bg=self.BG, fg=self.MUTED, anchor="w", cursor="hand2")
            caption.pack(side="left", fill="x", expand=True)
            caption.bind("<Button-1>", lambda e, ch=channel: self.select_channel(ch))
            controls = tk.Frame(row, bg=self.BG)
            controls.pack(side="right")
            self.button("−", lambda ch=channel: self.adjust(ch,-1), controls).pack(side="left")
            value = tk.Label(controls, bg=self.BG, fg=self.ACCENT, font=("Segoe UI", 11, "bold"),
                             cursor="hand2")
            value.configure(width=6)
            value.pack(side="left")
            value.bind("<Button-1>", lambda e, ch=channel: self.select_channel(ch))
            self.rate_labels[channel] = value
            self.button("+", lambda ch=channel: self.adjust(ch,1), controls).pack(side="right")
        self.dim_button = self.button("Dim: OFF", self.toggle_dim)
        self.native_button = self.button("Windows Notepad", self.native_notepad)
        self.button("Reset timing · F12", self.reset_rates)
        self.button("Exit", self.close)
        label("F11: select rate", 8)
        label("Ctrl ↑ / ↓: adjust", 8)
        self.refresh()

    def button(self, text, callback, parent=None):
        w = tk.Button(parent or self.side, text=text, command=callback, bg="#243852", fg=self.TEXT,
                      activebackground="#385778", activeforeground=self.TEXT,
                      relief="flat", bd=0, padx=6, pady=3, cursor="hand2",
                      font=("Segoe UI", 9, "bold"))
        if parent is None:
            w.pack(fill="x", padx=7, pady=2)
        return w

    def select_channel(self, channel):
        self.selected_channel = channel
        self.refresh()

    def cycle_channel(self):
        self.select_channel(CHANNELS[(CHANNELS.index(self.selected_channel)+1)%len(CHANNELS)])

    def adjust(self, channel, amount):
        self.selected_channel = channel
        i = SPEEDS.index(self.rates[channel])
        self.rates[channel] = SPEEDS[max(0, min(len(SPEEDS)-1, i+amount))]
        self.refresh()

    def reset_rates(self):
        self.rates.update(dict.fromkeys(CHANNELS, 1.))
        self.selected_channel = "step"
        self.refresh()

    def area(self):
        r = self.root
        r.update_idletasks()
        return self.app._screen_work_area(r.winfo_rootx()+r.winfo_width()//2,
                                          r.winfo_rooty()+r.winfo_height()//2)

    def position(self):
        left, top, right, bottom = self.area()
        self.side.update_idletasks()
        h = self.side.winfo_reqheight()
        self.side.geometry(f"236x{min(h,bottom-top-10)}{left+12:+d}{top+max(5,(bottom-top-h)//2):+d}")
        self.side.lift()

    def draw_progress(self):
        width = max(1, self.track.winfo_width())
        self.track.delete("all")
        self.track.create_rectangle(0, 0, width*(self.index+1)/len(STEPS), 4,
                                    fill=self.ACCENT, outline="")

    def refresh(self):
        status = "SAVE" if self.native_wait else ("SIM" if self.action in ("ports", "switch_extra") else ("MAN" if self.manual else "DEMO"))
        self.step_label.configure(text=f"{self.index+1:02d}/{len(STEPS):02d}  {status}")
        self.chapter.configure(text=STEPS[self.index][0] if self.index >= 0 else "PRESENTER")
        if hasattr(self, "native_button"):
            self.native_button.configure(state="normal" if self.action == "notes" and not self.native_wait else "disabled")
        self.pause_button.configure(text="Play  ·  F6" if self.paused else "Pause  ·  F6")
        self.mode_button.configure(text=("MANUAL" if self.manual else "AUTO")+"  ·  F10")
        for channel, label in self.rate_labels.items():
            rate = self.rates[channel]
            selected = channel == self.selected_channel
            label.configure(text=("› " if selected else "")+f"{rate:.2f}×",
                            fg=self.ACCENT if selected else self.TEXT)
        self.draw_progress()

    def change_speed(self, amount):
        self.adjust(self.selected_channel, amount)

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

    def later(self, ms, callback, channel="step"):
        self.events.append((channel, self.clocks[channel]+ms, callback))

    def cancel(self):
        self.events.clear()

    def tick(self):
        if self.closed:
            return
        now = time.monotonic()
        delta = min(250., (now-self.last)*1000)
        self.last = now
        if not self.paused:
            try:
                self.advance(delta)
            except Exception as exc:
                self.fail(exc)
        self.job = self.root.after(40, self.tick)

    def advance(self, delta):
        for channel in CHANNELS:
            self.clocks[channel] += delta*self.rates[channel]
        # Bubble has its own timeline, independent of time on the tool.
        if self.bubble_phase in ("appear", "hold", "disappear"):
            channel = self.bubble_phase
            self.phase_elapsed += delta*self.rates[channel]
            if channel == "appear":
                self.set_alpha(min(.98, .98*self.phase_elapsed/240))
                if self.phase_elapsed >= 240:
                    self.bubble_phase = "hold"
                    self.phase_elapsed = 0.
            elif channel == "hold":
                if self.action == "palette" and self.phase_elapsed >= 2300 and self.action_pending:
                    self.perform_action()
                if self.phase_elapsed >= 2300 and self.action != "summary" and not self.error and not self.palette_demo_active:
                    self.bubble_phase = "disappear"
                    self.phase_start_alpha = self.alpha
                    self.phase_elapsed = 0.
            elif channel == "disappear":
                self.set_alpha(max(0., self.phase_start_alpha*(1-self.phase_elapsed/280)))
                if self.phase_elapsed >= 280:
                    self.hide_card()
                    if self.action_pending:
                        self.perform_action()
        while True:
            due = next((e for e in self.events if e[1] <= self.clocks[e[0]]), None)
            if due is None:
                break
            self.events.remove(due)
            due[2]()
        if self.highlight_until is not None and self.clocks[self.highlight_channel] >= self.highlight_until:
            self.clear_highlight()
        if self.native_wait is not None:
            note_id, baseline = self.native_wait
            note = next((n for n in self.app.data["notes"] if n["id"] == note_id), None)
            if note and note["body"] != baseline:
                self.native_wait = None
                self.app._write_now()
                self.root.lift()
                self.focus_result(self.app.bidi_editor if self.app._bidi_active() else self.app.note_body, "SYNCED TO POCKET")
                self.refresh()
            else:
                return
        if self.index < 0 or self.action == "summary" or self.action_pending or self.events:
            return
        state = self.api["extra_excel_ui"].session(self.app)
        if self.app.scanning or state["busy"] or getattr(self.app,"mac_lookup_running",False):
            return
        if self.action_finished_at is None:
            self.action_finished_at = self.clocks["step"]
        # Readable result dwell is separate from typing, fade and worker completion.
        duration = max(1800, STEPS[self.index][3]-4200)
        if (not self.manual and self.bubble_phase == "hidden" and
                self.clocks["step"]-self.action_finished_at >= duration):
            self.next()

    def set_alpha(self, value):
        self.alpha = value
        try:
            self.bubble.attributes("-alpha", value)
            if self.dim_enabled and self.widget_alive(self.dim):
                self.dim.attributes("-alpha", value*.18)
        except tk.TclError:
            pass

    def passive_window(self, w):
        if sys.platform != "win32":
            return
        # No focus activation; pointer passes through the visual overlay.
        import ctypes
        from ctypes import wintypes
        u = ctypes.windll.user32
        u.GetParent.argtypes = [wintypes.HWND]
        u.GetParent.restype = wintypes.HWND
        hwnd = u.GetParent(w.winfo_id()) or w.winfo_id()
        get = u.GetWindowLongW
        put = u.SetWindowLongW
        get.argtypes = [wintypes.HWND, ctypes.c_int]
        put.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_long]
        put(hwnd, -20, get(hwnd,-20) | 0x08000000 | 0x00080000 | 0x20)

    def toggle_dim(self):
        self.dim_enabled = not self.dim_enabled
        self.dim_button.configure(text="Dim: ON" if self.dim_enabled else "Dim: OFF")
        if self.dim_enabled and self.card_visible:
            self.show_dim()
            self.bubble.lift()
            self.side.lift()
        elif self.widget_alive(self.dim):
            self.dim.withdraw()

    def show_dim(self):
        if not self.dim_enabled:
            return
        if not self.widget_alive(self.dim):
            self.dim = tk.Toplevel(self.root)
            self.dim.withdraw()
            self.dim.overrideredirect(True)
            self.dim.configure(bg="black")
            self.dim.attributes("-topmost", True)
        left, top, right, bottom = self.area()
        self.dim.geometry(f"{right-left}x{bottom-top}{left:+d}{top:+d}")
        self.dim.attributes("-alpha", self.alpha*.18)
        self.dim.deiconify()
        self.passive_window(self.dim)
        self.dim.lift()

    def clear_highlight(self):
        self.highlight_until = None
        if self.widget_alive(self.highlight):
            self.highlight.withdraw()

    def focus_result(self, widget, caption="RESULT", kind="result"):
        if self.smoke or not self.widget_alive(widget) or not widget.winfo_ismapped():
            return
        self.root.update_idletasks()
        r = widget.winfo_toplevel()
        x = max(widget.winfo_rootx(), r.winfo_rootx()+2)
        y = max(widget.winfo_rooty(), r.winfo_rooty()+2)
        right = min(widget.winfo_rootx()+widget.winfo_width(), r.winfo_rootx()+r.winfo_width()-2)
        bottom = min(widget.winfo_rooty()+widget.winfo_height(), r.winfo_rooty()+r.winfo_height()-2)
        canvas = getattr(self.app, "_tool_scroll_canvas", None)
        if r == self.root and self.widget_alive(canvas):
            x = max(x, canvas.winfo_rootx())
            y = max(y, canvas.winfo_rooty())
            right = min(right, canvas.winfo_rootx()+canvas.winfo_width())
            bottom = min(bottom, canvas.winfo_rooty()+canvas.winfo_height())
        if right-x < 20 or bottom-y < 16 or sys.platform != "win32":
            return
        if not self.widget_alive(self.highlight):
            self.highlight = tk.Toplevel(self.root)
            self.highlight.withdraw()
            self.highlight.overrideredirect(True)
            self.highlight.attributes("-topmost", True)
            self.highlight.attributes("-transparentcolor", self.KEY)
            self.outline = tk.Canvas(self.highlight, bg=self.KEY, highlightthickness=0, bd=0)
            self.outline.pack(fill="both", expand=True)
        w,h = right-x,bottom-y
        # Draw outside the control where possible, with a pointer and label.
        left,top,screen_right,screen_bottom = self.area()
        margin = min(10,max(0,x-left),max(0,screen_right-right))
        above = min(24,max(0,y-top))
        total_w, total_h = w+2*margin,h+above+4
        self.highlight.geometry(f"{total_w}x{total_h}{x-margin:+d}{y-above:+d}")
        self.outline.delete("all")
        color = "#FFD47A" if kind == "input" else self.ACCENT
        self.outline.create_rectangle(margin+2,above+2,margin+w-2,above+h-2,outline=color,width=3)
        # Keep the highlighted control entirely unobstructed; label and pointer stay outside.
        if above >= 20 and total_w >= 92:
            label_w=min(total_w-6,max(85,len(caption)*8+12))
            self.outline.create_rectangle(3,1,label_w,above-5,fill="#101b30",outline=color)
            self.outline.create_text(8, (above-4)/2,text=caption,anchor="w",fill=color,font=("Segoe UI",8,"bold"))
            self.outline.create_polygon(13,above-5,23,above-5,18,above+3,fill=color)
        self.highlight.deiconify()
        self.passive_window(self.highlight)
        self.highlight.lift()
        self.highlight_until = self.clocks["typing"]+2200 if kind == "input" else self.clocks["step"]+2200
        self.highlight_channel = "typing" if kind == "input" else "step"

    def dismiss_card(self):
        self.hide_card()
        if self.action_pending:
            self.perform_action()

    def hide_card(self):
        self.card_visible = False
        self.bubble_phase = "hidden"
        self.bubble.withdraw()
        if self.widget_alive(self.dim):
            self.dim.withdraw()

    def explain(self):
        if self.index < 0:
            return
        from PIL import Image, ImageDraw, ImageTk
        name, headline, detail, _, key = STEPS[self.index]
        if self.error:
            detail = self.error
        if key == "intro" and not self.error:
            detail = "Pocket | Management Demo\n" + detail
        left, top, right, bottom = self.area()
        width = min(760, right-left-40)
        height = 374 if key == "summary" else 250
        self.canvas.configure(width=width, height=height)
        # Render a truly rounded, transparent-key silhouette on Windows.
        image = Image.new("RGB", (width, height), self.KEY)
        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle((8, 7, width-8, height-8), radius=40,
                               fill=self.CARD, outline="#628c9c", width=1)
        self.bubble_photo = ImageTk.PhotoImage(image, master=self.bubble)
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, image=self.bubble_photo, anchor="nw")
        self.canvas.create_text(width/2, 37, text=f"{name}  •  {self.index+1:02d}/{len(STEPS):02d}",
                                fill=self.ACCENT, font=("Segoe UI", 14, "bold"))
        self.canvas.create_text(width/2, 89, text=headline, width=width-60,
                                fill=self.TEXT, font=("Segoe UI", 25, "bold"), justify="center")
        self.canvas.create_text(width/2, 158, text=detail, width=width-60,
                                fill=self.MUTED, font=("Segoe UI", 17), justify="center")
        if key == "summary":
            self.canvas.create_text(width/2, 220, text="183 שעות בחודש", fill=self.ACCENT,
                                    font=("Segoe UI", 34, "bold"))
            self.canvas.create_text(width/2, 267, text="30 sec × 20 calls × 50 agents × 22 days",
                                    fill=self.TEXT, font=("Segoe UI", 15))
            self.canvas.create_text(width/2, 335, text="תרחיש להמחשה בלבד · לא תוצאות מדידה",
                                    fill=self.MUTED, font=("Segoe UI", 14))
            self.canvas.create_text(width/2, 302, text="AHT  •  ACW  •  QUALITY",
                                    fill=self.ACCENT, font=("Segoe UI", 13, "bold"))
        else:
            self.canvas.create_line(width/2-45, 207, width/2+45, 207,
                                    fill=self.ACCENT, width=3, capstyle="round")
        y = top+8 if key == "palette" else top+(bottom-top-height)//2
        self.bubble.geometry(f"{width}x{height}{left+(right-left-width)//2:+d}{y:+d}")
        self.card_visible = True
        self.bubble_phase = "appear"
        self.phase_elapsed = 0.
        self.set_alpha(.98 if self.smoke else .03)
        self.show_dim()
        self.bubble.deiconify()
        self.bubble.lift()
        self.side.lift()

    def repeat_card(self):
        self.explain()
        # Repeat is useful even while paused: make the message immediately legible.
        if self.paused:
            self.set_alpha(.98)
            self.bubble_phase = "hold"

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
            if a.display_mode != "dashboard":
                a._set_display_mode("dashboard")
            a.show_tab("home" if a.display_mode == "dashboard" else "notes")
        else:
            tab = {"intro":"notes", "modes":"notes", "notepad":"notes", "palette":"extra", "switch_extra":"ports",
                   "return_extra":"extra"}.get(key, key)
            a.show_tab(tab)
            if key in ("intro", "notes", "notepad"):
                self.select_note(3 if key == "notepad" else 0)
        self.position()

    def go(self, index):
        self.cancel()
        self.native_wait = None
        self.palette_demo_active = False
        self.close_palette()
        self.hide_card()
        self.clear_highlight()
        self.index = index
        self.clocks = dict.fromkeys(CHANNELS, 0.)
        self.action_finished_at = None
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
            # Otherwise the independent bubble timeline starts the action.
        except Exception as exc:
            self.fail(exc)

    def fail(self, exc):
        self.cancel()
        self.paused = True
        self.error = f"Demo paused: {type(exc).__name__}: {exc}"
        self.refresh()
        self.explain()
        self.set_alpha(.98)

    def scroll_to(self, widget=None, fraction=None, caption="RESULT", kind="result"):
        a = self.app
        canvas = getattr(a, "_tool_scroll_canvas", None)
        if not self.widget_alive(canvas):
            self.focus_result(widget, caption, kind)
            return
        self.root.update_idletasks()
        if fraction is not None:
            canvas.yview_moveto(fraction)
        elif self.widget_alive(widget):
            region = canvas.bbox("all")
            if region and region[3] > region[1]:
                y = widget.winfo_rooty()-canvas.winfo_rooty()+canvas.canvasy(0)
                canvas.yview_moveto(max(0, (y-16)/(region[3]-region[1])))
            self.focus_result(widget, caption, kind)

    def perform_action(self):
        if not self.action_pending:
            return
        self.action_pending = False
        try:
            self.apply(self.action)
        except Exception as exc:
            self.fail(exc)

    def type_text(self, setter, value, done=None, widget=None):
        if self.widget_alive(widget):
            self.scroll_to(widget, caption="INPUT", kind="input")
            if self.highlight_until is not None:
                self.highlight_until = self.clocks["typing"] + max(2200,42*(len(value)+2)+300)
        if self.smoke or self.paused:
            setter(value)
            if done:
                done()
            return
        setter("")
        for i in range(1, len(value)+1):
            self.later(42*i, lambda n=i: setter(value[:n]), "typing")
        self.later(42*(len(value)+1), lambda: setter(value), "typing")
        if done:
            self.later(42*(len(value)+2), done, "typing")

    def find_entry(self, variable, parent=None):
        """Find the actual input bound to a Tk variable, including native wrappers."""
        parent = parent or self.app.body
        for w in parent.winfo_children():
            try:
                if str(w.cget("textvariable")) == str(variable):
                    return w
            except tk.TclError:
                pass
            found = self.find_entry(variable, w)
            if found is not None:
                return found
        return None

    def after_result(self, delay, callback):
        if self.smoke or self.paused:
            callback()
        else:
            self.later(delay, callback)

    def write_note(self, text):
        a = self.app
        note = a.active_note()
        note["direction"] = "rtl"
        # WM_SETTEXT recreates RichEdit paragraphs with default alignment.
        # Reapply native paragraph direction after EVERY animation frame.
        if a._bidi_active():
            a.bidi_editor.set_text(text)
            a.bidi_editor.set_direction("rtl")
        else:
            a.note_body.delete("1.0","end")
            a.note_body.tag_configure("note_alignment",justify="right")
            a.note_body.insert("1.0",text,"note_alignment")
            a.note_body.tag_add("note_alignment","1.0","end")
        note["body"] = text
        a._edit_dirty()

    def verify_note_rtl(self):
        """Check actual paragraph style rather than only the saved note flag."""
        a = self.app
        if a._bidi_active():
            import ctypes
            from .native_bidi import PARAFORMAT2
            editor = a.bidi_editor
            start,end = editor.selection_range()
            editor.select_all()
            try:
                para = PARAFORMAT2()
                para.cbSize = ctypes.sizeof(para)
                editor._send(editor.WM_USER+61,0,ctypes.addressof(para))
                assert para.dwMask & editor.PFM_ALIGNMENT and para.wAlignment == 2, "RichEdit lost right alignment"
                assert para.dwMask & editor.PFM_RTLPARA and para.wEffects & 1, "RichEdit lost RTL paragraph direction"
            finally:
                editor._send(editor.EM_SETSEL,start,end)
        else:
            assert a.note_body.tag_cget("note_alignment","justify") == "right"
            assert "note_alignment" in a.note_body.tag_names("1.0")


    def select_note(self, index):
        a = self.app
        if a.current_tab != "notes":
            a.show_tab("notes")
        a._flush_current_note()
        a.data["active_note"] = a.data["notes"][index]["id"]
        a.refresh_note_list()
        a._load_selected_note()
        a.title_entry.configure(justify="right")
        a.mini_note_picker.configure(justify="right")
        a.root.update_idletasks()

    def prepare_text_session(self):
        """Use Pocket's real note-sync working file and session, without launching a process."""
        a = self.app
        a._flush_current_note()
        note = a.active_note()
        sync = self.api["note_sync"]
        session = a._notepad_sessions.get(note["id"])
        if session is None:
            path = a._unique_note_path(note,note["title"])
            if path.exists():
                sync.write_text(path,note["body"])
            else:
                sync.create_text(path,note["body"])
            session = {"path":path,"baseline":note["body"]}
            a._notepad_sessions[note["id"]] = session
            note["notepad_filename"] = path.name
        return note, session

    def native_notepad(self):
        """Optional real Windows Notepad; never imitate or inject keys into it."""
        if self.action != "notes" or self.native_wait is not None or sys.platform != "win32":
            return
        self.cancel()
        self.hide_card()
        self.action_pending = False
        self.select_note(3)
        a = self.app
        note, session = self.prepare_text_session()
        self.native_wait = (note["id"],note["body"])
        self.action_finished_at = None
        self.paused = False
        self.refresh()
        a.open_notepad()

    def palette_position(self):
        dialog = getattr(self.app,"_quick_search_dialog",None)
        if not self.widget_alive(dialog):
            return
        from . import palette_preferences as prefs
        left,top,right,bottom = self.area()
        dialog.update_idletasks()
        width,height = dialog.winfo_width(),dialog.winfo_height()
        x = left + (right-left-width)//2
        y = top + 265
        x,y = prefs.clamp(x,y,width,height,(left,top,right,bottom))
        prefs.move(dialog,x,y)
        dialog.lift()

    def clipboard_text(self):
        a = self.app
        snippets = [self.scenario["customer"], self.scenario["vrf"], self.scenario["vdom"],
                    self.scenario["group"], self.scenario["forti_ip"], self.scenario["circuit"],
                    "show ip interface brief", WAN_IP+"/29", "22,443,"+self.scenario["port"],
                    "\n".join(MACS), *MACS, self.scenario["public_ip"], self.scenario["port"],
                    self.scenario["public_ip"]+":"+self.scenario["port"]]
        for item in snippets:
            self.api["clipboard_add"](a.clipboard_items,item)

    def apply(self, key):
        a = self.app
        if key == "intro":
            self.select_note(0)
        elif key == "notes":
            self.select_note(0)
            self.focus_result(a.mini_note_picker,"NOTE 1 / 4")
            def page(index):
                a._move_mini_note(1)
                a.title_entry.configure(justify="right")
                a.mini_note_picker.configure(justify="right")
                self.focus_result(a.mini_note_picker,f"NOTE {index+1} / 4")
                if index < 3:
                    self.after_result(2000,lambda: page(index+1))
                else:
                    def add_sentence():
                        target = a.bidi_editor if a._bidi_active() else a.note_body
                        original = a._editor_text()
                        base = original.removesuffix(NOTE_ADDITION)
                        def saved():
                            a._apply_note_direction(a.active_note())
                            a._flush_current_note()
                            a._write_now()
                            self.focus_result(a.save_status.master,"AUTOSAVED")
                        if self.smoke:
                            self.write_note(base+NOTE_ADDITION[:9])
                            self.verify_note_rtl()
                        self.type_text(lambda suffix: self.write_note(base+suffix), NOTE_ADDITION,saved,target)
                        if self.smoke:
                            self.verify_note_rtl()
                    self.after_result(1000,add_sentence)
            self.after_result(1800,lambda: page(1))
        elif key == "links":
            a.root.update_idletasks()
            layout = a.data["shortcut_folders"]
            for i,folder in enumerate(layout["folders"]):
                self.api["shortcut_folders"].set_expanded(layout,folder["id"],i < 2)
            a.refresh_links()
            a.root.update_idletasks()
            canvas = a.links_stack.master
            def show_folder(index):
                fid = layout["folders"][index]["id"]
                bar = getattr(a,"shortcut_folder_headers",{}).get(fid)
                if self.widget_alive(bar):
                    region = canvas.bbox("all")
                    if region and region[3] > region[1]:
                        canvas.yview_moveto(max(0,(bar.winfo_y()-5)/(region[3]-region[1])))
                    a.root.update_idletasks()
                    self.focus_result(bar,("WORK","STUDY","MORE / CLOSED")[index])
                if index < 2:
                    self.after_result(2000,lambda: show_folder(index+1))
            canvas.yview_moveto(0)
            show_folder(0)
        elif key == "commands":
            a._command_focus_in()
            a.machine_var.set(self.api["ch"].ALL_MACHINES)
            a._change_machine()
            a._set_command_mode("all")
            def cli_done():
                a._refresh_command_results()
                if len(a.command_filtered) < 5:
                    raise AssertionError("Expected at least five interface matches")
                def show_page(index):
                    if index:
                        a._move_mini_command(1)
                    item = a._selected_command()
                    self.focus_result(a.command_code,f"{item['machine']}  {index+1}/{len(a.command_filtered)}")
                    if index < min(5,len(a.command_filtered)-1):
                        self.after_result(2000,lambda: show_page(index+1))
                show_page(0)
            self.type_text(a.command_query.set,"interface",cli_done,a.command_search_entry)
        elif key == "subnet":
            def prefix_done():
                a._calculate_subnet()
                def calculated():
                    self.scroll_to(a.subnet_fact_labels["cidr"].master,caption="NETWORK RANGE")
                    def split():
                        a.subnet_split_var.set("/30")
                        a._split_subnet()
                        self.scroll_to(a.subnet_tree,caption="2 SUBNETS")
                        def back_to_top():
                            self.clear_highlight()
                            self.scroll_to(fraction=0.)
                            a.root.update_idletasks()
                            self.focus_result(a.subnet_fact_labels["cidr"].master,"NETWORK OVERVIEW")
                        self.after_result(2100,back_to_top)
                    self.after_result(1600,split)
                self.after_result(500,calculated)
            def ip_done():
                self.type_text(a.subnet_prefix_var.set,"29",prefix_done,self.find_entry(a.subnet_prefix_var))
            self.type_text(a.subnet_ip_var.set,WAN_IP,ip_done,self.find_entry(a.subnet_ip_var))
        elif key == "ports":
            if a.scanning:
                a.scan_cancel.set()
                a.scan_token += 1
                a.scanning = False
            a.port_source.set("local")
            def ports_done():
                a._start_scan()
                if not self.smoke:
                    self.later(1500,lambda: self.scroll_to(a.port_tree,caption="SIMULATED TCP"))
            def host_done():
                self.type_text(a.ports_var.set,"22,443,"+self.scenario["port"],ports_done,a.ports_entry)
            self.type_text(a.host_var.set,self.scenario["public_ip"],host_done,self.find_entry(a.host_var))
        elif key == "mac":
            a.mac_source.set("local")
            a.mac_vendor_filter = None
            a.mac_vendor_exclude = False
            if a.mac_vendor_expanded:
                a._toggle_mac_summary()
            def mac_text(value):
                a.mac_input.delete("1.0","end")
                a.mac_input.insert("1.0",value)
                a.mac_input.see("end")
            def mac_done():
                a._run_mac_lookup()
                def show_table():
                    # Compact vendor labels preserve all four rows in Mini.
                    tree = a.mac_tree
                    tree.configure(height=4)
                    tree.configure(displaycolumns=("MAC address","Vendor / result"))
                    tree.column("#1",width=135,minwidth=110,stretch=False)
                    tree.column("#2",width=151,minwidth=100,stretch=True)
                    self.scroll_to(tree,caption="4 MAC RESULTS")
                    def summary():
                        if not a.mac_vendor_expanded:
                            a._toggle_mac_summary()
                        self.scroll_to(a.mac_summary_list,caption="3 VENDOR GROUPS")
                        def filter_cisco():
                            cisco = next((name for name,count in a.mac_summary_groups if "Cisco" in name),None)
                            if cisco:
                                a._set_mac_vendor_filter(cisco)
                                self.scroll_to(a.mac_tree,caption="2 CISCO DEVICES")
                            def all_results():
                                a._set_mac_vendor_filter(None)
                                if a.mac_vendor_expanded:
                                    a._toggle_mac_summary()
                                self.scroll_to(a.mac_tree,caption="ALL 4 MACS")
                            self.after_result(1600,all_results)
                        self.after_result(1800,filter_cisco)
                    self.after_result(2300,summary)
                self.after_result(600,show_table)
            self.type_text(mac_text,"\n".join(MACS),mac_done,a.mac_input)
        elif key == "clipboard":
            gallery = self.api["clipboard_gallery"]
            self.clipboard_text()
            gallery.show_page(a,"text")
            a.clipboard_query.set("")
            a._refresh_clipboard()
            if a.clipboard_list.size():
                a.clipboard_list.selection_set(0)
                a._update_clipboard_text_status()
            self.focus_result(a.clipboard_list,"TEXT HISTORY")
            def show_more():
                if a.clipboard_list.size():
                    row=min(7,a.clipboard_list.size()-1)
                    a.clipboard_list.selection_clear(0,"end")
                    a.clipboard_list.selection_set(row)
                    a.clipboard_list.see(row)
                    a._update_clipboard_text_status()
                self.focus_result(a.clipboard_list,"IP / MAC / CLI")
                self.after_result(2200,show_images)
            def show_images():
                gallery.show_page(a,"images")
                self.root.update_idletasks()
                gallery.refresh_images(a,force=True)
                if a.clipboard_images:
                    gallery.select_image(a,a.clipboard_images[0]["id"])
                self.focus_result(a.clipboard_images_canvas,"SAVED IMAGES")
                def next_image(i):
                    gallery.move_selection(a,1)
                    self.focus_result(a.clipboard_images_canvas,f"IMAGE {i+1}/{len(a.clipboard_images)}")
                    if i < len(a.clipboard_images)-1:
                        self.after_result(1800,lambda: next_image(i+1))
                self.after_result(1800,lambda: next_image(1))
            self.after_result(2600,show_more)
        elif key == "reminders":
            fields = getattr(a,"_reminders_inline_fields",{})
            if fields:
                title, details = next(iter(fields.values()))
                title.configure(justify="right")
                details.tag_configure("formgt_rtl",justify="right")
                details.tag_add("formgt_rtl","1.0","end")
                self.scroll_to(title,caption="FOLLOW-UP TASK")
            else:
                self.focus_result(a.body,caption="REMINDERS")
        elif key == "extra":
            term = self.scenario["customer"].lower()
            def search_done():
                a._extra_palette_search(term)
                def hits():
                    self.scroll_to(getattr(a,"_formgt_extra_results",None),caption="MATCH FOUND")
                    self.after_result(1500,lambda: self.scroll_to(getattr(a,"_formgt_extra_details",None),caption="SERVICE DETAILS"))
                self.after_result(1200,hits)
            field = getattr(a,"_formgt_extra_input",None)
            if field and self.widget_alive(field[0]):
                self.type_text(field[1].set,term,search_done,field[0])
            else:
                search_done()
        elif key == "modes":
            self.preview_modes()
        elif key == "palette":
            self.palette_demo_active = True
            a._open_global_search()
            self.palette_position()
            queries = [self.scenario["public_ip"], "< cli interface",
                       "< subnet "+WAN_IP+"/29", "< extra "+self.scenario["customer"].lower(),
                       "> open notes"]
            def set_palette(value):
                if self.widget_alive(a._palette_entry):
                    a._palette_entry.delete(0,"end")
                    a._palette_entry.insert(0,value)
            def example(index):
                if not self.widget_alive(a._palette_entry):
                    self.palette_demo_active = False
                    self.hide_card()
                    return
                def typed():
                    self.palette_position()
                    if self.smoke:
                        if index < len(queries)-1:
                            example(index+1)
                        return
                    if index < len(queries)-1:
                        self.after_result(1700,lambda: example(index+1))
                    else:
                        self.after_result(1800,self.execute_palette_demo)
                self.type_text(set_palette,queries[index],typed,a._palette_entry)
            example(0)

    def preview_modes(self):
        """Fast real-tool tour across the three factory layouts, with no scans."""
        a = self.app
        modes = ("mini","normal","dashboard")
        tools = ("notes","links","commands","subnet","ports","mac","clipboard","reminders","extra")
        self.mode_trace = []
        def show_mode(i):
            mode = modes[i]
            self.clear_highlight()
            if a.display_mode != mode:
                a._set_display_mode(mode)
            a.root.update_idletasks()
            self.position()
            # Never relabel a responsive Normal window as a Dashboard.
            actual = a.display_mode
            self.chapter.configure(text=actual.upper()+"  ·  "+str(i+1)+"/3")
            self.focus_result(a.header_icon,actual.upper()+" MODE")
            def visit(j):
                self.clear_highlight()
                tab = tools[j]
                a.show_tab(tab)
                a.root.update_idletasks()
                self.mode_trace.append((a.display_mode,tab))
                self.chapter.configure(text=f"{a.display_mode.upper()}  ·  {tab.upper()}")
                if j+1 < len(tools):
                    self.after_result(620,lambda: visit(j+1))
                elif i+1 < len(modes):
                    self.after_result(850,lambda: show_mode(i+1))
                else:
                    def finish():
                        a.show_tab("home" if a.display_mode == "dashboard" else "notes")
                        a.root.update_idletasks()
                        self.chapter.configure(text=a.display_mode.upper()+"  ·  OVERVIEW")
                    self.after_result(800,finish)
            self.after_result(1100,lambda: visit(0))
        show_mode(0)

    def execute_palette_demo(self):
        a = self.app
        dialog = getattr(a,"_quick_search_dialog",None)
        if not self.widget_alive(dialog):
            return
        hit = self.api["command_palette"].command("open notes",a.settings)
        if hit is None:
            self.fail(ValueError("Demo palette action not recognized"))
            return
        self.close_palette()
        self.palette_demo_active = False
        if self.card_visible:
            self.bubble_phase = "disappear"
            self.phase_start_alpha = self.alpha
            self.phase_elapsed = 0.
        a._run_palette_action(hit)
        self.select_note(0)
        self.focus_result(a.title_entry,"BACK TO NOTES")

    def close(self):
        if self.closed:
            return
        self.closed = True
        self.cancel()
        if self.job is not None:
            self.root.after_cancel(self.job)
        self.hide_card()
        self.clear_highlight()
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
            def refresh_links(self):
                super().refresh_links()
                if self.current_tab != "links" or not hasattr(self,"links_stack"):
                    return
                translations = {"Quick shortcuts":"קיצורים מהירים", "Websites, files and folders":"אתרים, קבצים ותיקיות",
                                "+ Add ▾":"+ הוספה ▾", "Search":"חיפוש", "Unfiled  ·  drop here":"ללא תיקייה · גרירה לכאן"}
                def translate(widget):
                    for child in widget.winfo_children():
                        if isinstance(child,(tk.Label,tk.Button)):
                            value = str(child.cget("text"))
                            if value in translations:
                                child.configure(text=translations[value])
                            elif value in ("עבודה","לימודים","קישורים נוספים","קובץ סיסמאות","EXTRANET.XL","אתר בזק","קובץ BWIFI","קובץ BCAM","אתר הלימודים של סיסקו","מחשבון מקוון","חדשות טכנולוגיה","קובץ דוגמה"):
                                child.configure(anchor="e",justify="right")
                            elif value.startswith(("FILE  ·", "URL  ·")):
                                prefix = "קובץ" if value.startswith("FILE") else "אתר"
                                child.configure(text=prefix+"  ·  "+value.split("·",1)[1].strip())
                        translate(child)
                translate(self.body)
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
                # Only open the isolated demo working file on explicit user action.
                super().open_notepad()
            def _update_vendors(self):
                pass
        app = DemoApp(preview=True)
        for image in sample_images(scenario):
            app._clipboard_on_new_image(image)
        presentation = Presentation(app, api, workbook, scenario, auto_start=not smoke)
        app._formgt = presentation
        presentation.clipboard_text()
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
                    if step[4] not in ("summary","modes"):
                        assert app.display_mode == "mini", "Expected Mini mode"
                    if step[4] == "modes":
                        assert len(presentation.mode_trace) == 27, "Mode tour missed tools"
                        assert {mode for mode,tab in presentation.mode_trace} == {"mini","normal","dashboard"}, "Expected three factory layouts"
                        assert app.current_tab == "home", "Dashboard overview missing"
                    assert presentation.side.winfo_ismapped(), "Missing integrated controller"
                    if step[4] in ("extra", "return_extra"):
                        state = api["extra_excel_ui"].session(app)
                        assert state["hits"] and state["query"] == scenario["customer"].lower(), "EXTRA demo record missing"
                        assert state["selected"] == 0, "EXTRA selection missing"
                        from .extra_excel_presentation import row_overview
                        overview = row_overview(state["hits"][0])
                        pairs = {cell.label:cell.value for pair in overview.pairs for cell in pair}
                        assert pairs["קוד קישור"] == scenario["circuit"]
                        assert pairs["VDOM"] == scenario["vdom"] and pairs["FortiGate IP"] == scenario["forti_ip"]
                        assert pairs["קוד קבוצה"] == scenario["group"]
                    if step[4] == "palette":
                        assert app._quick_search_dialog is not None, "Palette did not open"
                        presentation.execute_palette_demo()
                        assert app.current_tab == "notes", "Palette action did not navigate"
                    if step[4] == "clipboard":
                        assert app.clipboard_page == "images" and len(app.clipboard_images) >= 4
                        assert all(mac in [item["text"] for item in app.clipboard_items] for mac in MACS)
                    if step[4] == "intro":
                        assert app.active_note()["title"] == note_title(scenario), "Hebrew demo title missing"
                    if step[4] == "notes":
                        assert len(app.data["notes"]) == 4 and app.active_note()["title"] == "משימות"
                        assert app.mini_note_page.cget("text").strip() == "4 / 4"
                        assert all(n["direction"] == "rtl" for n in app.data["notes"])
                        assert app.active_note()["body"].endswith(NOTE_ADDITION), "Note addition missing"
                    if step[4] == "links":
                        folders = app.data["shortcut_folders"]["folders"]
                        assert [f["title"] for f in folders] == ["עבודה","לימודים","קישורים נוספים"]
                        assert [f["expanded"] for f in folders] == [True,True,False]
                        assert all(len(app.data["shortcut_folders"]["children"][f["id"]]) == 3 for f in folders)
                    if step[4] == "reminders":
                        assert app.data["reminders"][0]["title"].startswith("REBAR")
                    if step[4] == "commands":
                        assert len(app.command_filtered) >= 5, "CLI results missing"
                        assert len({row["machine"] for row in app.command_filtered}) >= 5
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
                presentation.select_channel("hold")
                presentation.change_speed(-4)
                assert presentation.rates["hold"] == .1 and presentation.speed == 1.25
                presentation.reset_rates()
                assert all(rate == 1. for rate in presentation.rates.values())
                # Deterministic independent-clock check, without real waiting.
                presentation.go(0)
                presentation.action_pending = True
                presentation.explain()
                presentation.bubble_phase = "appear"
                presentation.phase_elapsed = 0.
                presentation.rates["appear"] = .25
                presentation.manual = True
                presentation.advance(480)
                assert presentation.bubble_phase == "appear" and presentation.phase_elapsed == 120
                presentation.advance(480)
                assert presentation.bubble_phase == "hold"
                presentation.rates["hold"] = .1
                presentation.advance(1000)
                assert presentation.bubble_phase == "hold" and presentation.phase_elapsed == 100
                presentation.rates["hold"] = 1.
                presentation.advance(2200)
                assert presentation.bubble_phase == "disappear"
                presentation.rates["disappear"] = .25
                presentation.advance(560)
                assert presentation.bubble_phase == "disappear" and presentation.card_visible
                presentation.advance(560)
                assert presentation.bubble_phase == "hidden" and not presentation.action_pending
                presentation.manual = False
                presentation.reset_rates()
                assert app.root.overrideredirect(), "Pocket must be borderless"
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
