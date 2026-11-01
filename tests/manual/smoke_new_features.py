"""UI preview tests for v1.2 (requires Tk desktop and Pillow to create images)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import os
from pathlib import Path
import runpy
import sys
import tempfile
from PIL import ImageGrab

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
PocketDesk = runpy.run_path(str((Path(__file__).resolve().parents[2] / "app.pyw")), run_name="import_test")["PocketDesk"]

with tempfile.TemporaryDirectory() as directory:
    os.environ["APPDATA"] = directory
    app = PocketDesk(preview=True)
    app.pinned = True  # keep dashboard visible during UI tests

    def render():
        for _ in range(4): app.root.update()

    def screenshot(name):
        render()
        x, y = app.root.winfo_rootx(), app.root.winfo_rooty()
        ImageGrab.grab(bbox=(x, y, x+app.root.winfo_width(), y+app.root.winfo_height())).save(str(Path(__file__).with_name(name)))

    # Every note keeps its own phone, without leaking to another note.
    app.phone_var.set("+972 50 111 2222")
    render()
    assert app.active_note()["phone"] == "+972 50 111 2222"
    app.add_note()
    render()
    assert app.phone_var.get() == ""
    app.phone_var.set("050-333-4444")
    assert app.active_note()["phone"] == "050-333-4444"
    app.note_list.selection_clear(0, "end")
    app.note_list.selection_set(1)
    app._select_from_list(None)
    assert app.phone_var.get() == "+972 50 111 2222"
    app._copy_phone()
    assert app.root.clipboard_get() == "+972501112222"
    screenshot("preview-notes.png")

    app.show_tab("links")
    app._toggle_link_form(None)
    render()
    screenshot("preview-add-shortcut.png")
    app._close_form()
    app._save_link("Example folder", directory, "folder")
    example = Path(directory) / "example.txt"
    example.write_text("hello", encoding="utf-8")
    app._save_link("Example file", str(example), "file")
    assert app.data["links"][0]["kind"] == "file"
    assert app.data["links"][1]["kind"] == "folder"
    app._toggle_link_form(app.data["links"][0])
    render()
    screenshot("preview-edit-file.png")
    app._close_form()
    screenshot("preview-shortcuts.png")
    app._write_now()
    saved = app.path.read_text(encoding="utf-8")
    assert '"phone"' in saved and '"kind": "folder"' in saved
    app.root.destroy()
    print("new-feature smoke tests passed")
