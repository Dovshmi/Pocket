"""Interactive Tk smoke test and screenshot capture (run under xvfb on Linux)."""
import os
from pathlib import Path
import socket
import sys
import tempfile
import time
from PIL import ImageGrab

sys.path.insert(0, str(Path(__file__).parent))
import runpy
PocketDesk = runpy.run_path(str(Path(__file__).parent / "app.pyw"), run_name="import_test")["PocketDesk"]

with tempfile.TemporaryDirectory() as directory:
    os.environ["APPDATA"] = directory
    app = PocketDesk(preview=True)
    def render():
        for i in range(4):
            app.root.update()
            time.sleep(0.04)
    def screenshot(name):
        render()
        x, y = app.root.winfo_rootx(), app.root.winfo_rooty()
        w, h = app.root.winfo_width(), app.root.winfo_height()
        print(name, w, h)
        ImageGrab.grab(bbox=(x, y, x+w, y+h)).save(str(Path(__file__).parent / name))
    render()
    screenshot("preview-notes.png")
    app.show_tab("links")
    screenshot("preview-shortcuts.png")
    app.show_tab("ports")
    render()
    app.host_var.set("127.0.0.1")
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        app.single_port_var.set(str(listener.getsockname()[1]))
        app._start_scan()
        for i in range(100):
            render()
            if not app.scanning: break
        assert not app.scanning, "Scan did not finish"
        assert app.port_results and app.port_results[0]["status"] == "OPEN", app.port_results
        print("TCP UI scan result", app.port_results)
    app.port_mode.set("selected")
    app._port_mode_changed()
    render()
    screenshot("preview-ports.png")
    app.show_tab("mac")
    render()
    app.mac_input.delete("1.0", "end")
    app.mac_input.insert("1.0", "02:11:22:33:44:55\n01:00:5E:00:00:01\n00:00:0C:12:34:56")
    app._run_mac_lookup()
    assert len(app.mac_results) == 3
    screenshot("preview-mac.png")
    # Check old notes data remains functional after switching.
    app.show_tab("notes")
    app.add_note()
    assert len(app.data["notes"]) == 2
    app.root.destroy()
    print("UI smoke test completed")
