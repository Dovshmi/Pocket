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
    ("01 / OVERVIEW", "One workspace instead of scattered tools.",
     "Open Pocket Dashboard.", 6500, "home"),
    ("02 / CTRL+K", "One shortcut to find the right tool.",
     "The real command palette prepares a search for DEMO-1042.", 6500, "palette"),
    ("04 / EXTRA", "Find the service without opening multiple workbooks.",
     "Search a synthetic service record in the real offline SQLite index.", 9500, "extra"),
    ("04 / COMMANDS", "Find the right command, not the right spreadsheet.",
     "Search read-only Cisco reference commands.", 8500, "commands"),
    ("05 / SUBNET", "Calculate the network and host range immediately.",
     "Actual local IPv4 calculation: 192.0.2.10/26.", 7500, "subnet"),
    ("06 / PORTS", "See several TCP results in one place.",
     "SIMULATED results for documentation address 192.0.2.10; no connections.", 9500, "ports"),
    ("07 / MAC", "Identify equipment from the local vendor reference.",
     "Offline lookup using a small demonstration vendor table.", 7500, "mac"),
    ("08 / EXTRA", "Resume the same search after switching tools.",
     "The previous EXTRA result is still present.", 7000, "return_extra"),
    ("09 / NOTES", "Keep findings together while handling the call.",
     "Synthetic incident summary in the real Notes editor.", 8000, "notes"),
    ("10 / CLIPBOARD", "Reuse snippets rather than repeatedly typing them.",
     "Synthetic clipboard history only; no desktop clipboard capture.", 7500, "clipboard"),
    ("11 / REMINDERS", "Follow up without relying on memory.",
     "Example callback task, no external notification.", 7500, "reminders"),
    ("12 / SHORTCUTS", "Put frequently used resources within reach.",
     "Demonstration shortcuts; external launching disabled.", 6500, "links"),
    ("13 / SUMMARY", "Less searching. More time for the customer.",
     "Measure AHT, ACW and quality in an approved pilot.", 0, "summary"),
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
    data["settings"].update(display_mode="dashboard", window_profile="Dashboard",
                            clipboard_paused=True, clipboard_storage="ram",
                            quick_slots_enabled=False, convert_enabled=False)
    data["last_tab"] = "home"
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
    sheet.append(["Service ID", "Customer", "Site", "Device", "IP address"])
    sheet.append(["DEMO-1042", "Example Business", "Training site A", "Cisco", "192.0.2.10"])
    sheet.append(["DEMO-1043", "Example Business", "Training site B", "Juniper", "192.0.2.20"])
    # Blank rows prevent incidental header detection from favoring a data row.
    path = folder / "demo-services.xlsx"
    book.save(path)
    book.close()
    extra_excel_db.sync_database(path, db_path=folder / extra_excel_db.FILE_NAME)
    return path


class Presentation:
    def __init__(self, app, api, workbook, *, auto_start=True):
        self.app, self.api, self.workbook = app, api, workbook
        self.index = -1
        self.job = None
        self.paused = False
        self.closed = False
        self.panel = tk.Toplevel(app.root)
        self.panel.title("FORMGT | Pocket Management Demo")
        self.panel.configure(bg="#101b30")
        self.panel.attributes("-topmost", True)
        self.panel.resizable(False, False)
        self.panel.protocol("WM_DELETE_WINDOW", self.close)
        self.panel.geometry("650x245+20+20")
        self.label("POCKET  /  MANAGEMENT DEMO  •  SYNTHETIC DATA", 11, "#75e3d2")
        self.heading = self.label("", 17, "white")
        self.detail = self.label("", 12, "#e1e9f9")
        self.sub = self.label("", 10, "#aebed5")
        self.progress = ttk.Progressbar(self.panel, maximum=len(STEPS))
        self.progress.pack(fill="x", padx=18, pady=6)
        buttons = tk.Frame(self.panel, bg="#101b30")
        buttons.pack(fill="x", padx=12, pady=5)
        for title, command in (("Previous", self.previous), ("Pause / Resume", self.toggle),
                               ("Next", self.next), ("Replay", self.restart), ("Exit demo", self.close)):
            tk.Button(buttons, text=title, command=command, padx=7).pack(side="left", padx=3)
        app.root.title("Pocket | FORMGT — DEMO ONLY")
        app.root.protocol("WM_DELETE_WINDOW", self.close)
        app.root.bind("<Escape>", lambda e: self.close())
        self.panel.bind("<Escape>", lambda e: self.close())
        app.root.after(350, self.position)
        if auto_start:
            self.job = app.root.after(900, self.next)

    def label(self, text, size, color):
        w = tk.Label(self.panel, text=text, font=("Segoe UI", size, "bold" if size != 10 else "normal"),
                     bg="#101b30", fg=color, wraplength=610, justify="left", anchor="w")
        w.pack(fill="x", padx=18, pady=(6, 1))
        return w

    def position(self):
        if self.closed:
            return
        r = self.app.root
        r.update_idletasks()
        sw, sh = r.winfo_screenwidth(), r.winfo_screenheight()
        # Prefer separate areas on wide or tall presentation screens.
        w, h = min(1160, sw-24), min(800, sh-70)
        if sw >= 1850:
            x, y = sw-w-16, max(0, (sh-h)//2)
        elif sh >= 1050:
            h = min(h, sh-325)
            x, y = max(0, (sw-w)//2), 270
        else:
            x, y = sw-w-16, max(0, (sh-h)//2)
        r.geometry(f"{w}x{h}+{x}+{y}")
        # On compact screens the presenter can drag the caption panel aside.
        self.panel.lift()

    def cancel(self):
        if self.job is not None:
            self.app.root.after_cancel(self.job)
            self.job = None

    def next(self):
        self.cancel()
        self.go(min(self.index+1, len(STEPS)-1))

    def previous(self):
        self.cancel()
        self.go(max(0, self.index-1))

    def toggle(self):
        self.paused = not self.paused
        self.cancel()
        if self.paused:
            self.sub.configure(text="PAUSED — use Next, Previous or Pause / Resume.")
        elif self.index < len(STEPS)-1:
            self.sub.configure(text=STEPS[self.index][2])
            self.job = self.app.root.after(STEPS[self.index][3], self.next)

    def restart(self):
        self.cancel()
        self.paused = False
        self.go(0)

    def go(self, index):
        self.index = index
        name, headline, detail, delay, key = STEPS[index]
        self.heading.configure(text=name + "   •   " + headline)
        self.detail.configure(text=detail)
        self.sub.configure(text=f"Step {index+1} of {len(STEPS)}  |  Demo playback, not a timed benchmark")
        self.progress["value"] = index+1
        try:
            self.apply(key)
        except Exception as exc:
            self.paused = True
            self.sub.configure(text=f"DEMO PAUSED: {type(exc).__name__}: {exc}")
            return
        if delay and not self.paused:
            self.job = self.app.root.after(delay, self.next)

    def apply(self, key):
        a = self.app
        dialog = getattr(a, "_quick_search_dialog", None)
        if dialog is not None and dialog.winfo_exists():
            dialog.event_generate("<Escape>")
        if key == "palette":
            a.show_tab("home")
            a._open_global_search()
            a._palette_entry.insert(0, "> extra DEMO-1042")
        elif key == "home":
            a.show_tab("home")
        elif key == "extra":
            a._extra_excel_path = str(self.workbook)
            a.show_tab("extra")
            a._extra_palette_search("DEMO-1042")
        elif key == "commands":
            a.show_tab("commands")
            a._command_focus_in()
            a.command_query.set("show ip interface brief")
            a._refresh_command_results()
        elif key == "subnet":
            a.show_tab("subnet")
            a.subnet_ip_var.set("192.0.2.10")
            a.subnet_prefix_var.set("26")
            a._calculate_subnet()
        elif key == "ports":
            a.show_tab("ports")
            a.port_source.set("local")
            a.host_var.set("192.0.2.10")
            a.ports_var.set("22,443,8080")
            a._start_scan()
        elif key == "mac":
            a.show_tab("mac")
            a.mac_source.set("local")
            a.mac_input.delete("1.0", "end")
            a.mac_input.insert("1.0", "00:00:0C:12:34:56")
            a._run_mac_lookup()
        elif key == "return_extra":
            a.show_tab("extra")
        elif key == "clipboard":
            a.show_tab("clipboard")
        elif key in ("notes", "reminders", "links"):
            a.show_tab(key)
        elif key == "summary":
            a.show_tab("home")
            self.detail.configure(text="Illustrative target: 30 seconds saved × 20 relevant calls × "
                "50 agents × 22 days = 183 staff-hours/month.")
            self.sub.configure(text="Hypothesis only — validate via pilot. Replay or exit when ready.")

    def close(self):
        if self.closed:
            return
        self.closed = True
        self.cancel()
        self.app._extra_excel_cancel.set()
        self.app.scan_cancel.set()
        self.app.tasks.stop()
        self.app.root.destroy()


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
                    if presentation.sub.cget("text").startswith("DEMO PAUSED:"):
                        raise AssertionError(presentation.sub.cget("text"))
                    if step[4] in ("extra", "return_extra"):
                        assert api["extra_excel_ui"].session(app)["hits"], "EXTRA demo record missing"
                    if step[4] == "commands":
                        assert app.command_filtered, "CLI results missing"
                    if step[4] == "subnet":
                        assert app.subnet_details, "Subnet calculation missing"
                    if step[4] == "ports":
                        assert len(app.port_results) == 3, "Simulated TCP results missing"
                    if step[4] == "mac":
                        assert app.mac_results, "MAC results missing"
                print("FORMGT smoke: all presentation steps completed")
            finally:
                presentation.close()
        else:
            app.run()
    return 0
