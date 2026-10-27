import os
from pathlib import Path
import runpy
import tempfile
from PIL import ImageGrab

ROOT = Path(__file__).resolve().parent
PocketDesk = runpy.run_path(str(ROOT / 'app.pyw'), run_name='test_ui')['PocketDesk']
with tempfile.TemporaryDirectory() as home:
    os.environ['APPDATA'] = home
    app = PocketDesk(preview=True)
    app.root.update()
    app.add_note()
    app.title_var.set('Switch configuration')
    app.phone_var.set('+972 50 123 4567')
    app.note_body.insert('1.0', 'show interfaces status\nshow ip route\nshow version')
    app.root.update()
    # Layout assertions for new arrangement
    assert app.note_body.winfo_width() > app.note_list.winfo_width() * 2
    assert app.note_body.winfo_rooty() > app.note_list.winfo_rooty()
    x, y = app.root.winfo_rootx(), app.root.winfo_rooty()
    ImageGrab.grab(bbox=(x, y, x + app.root.winfo_width(), y + app.root.winfo_height())).save(ROOT / 'preview-notes-v115.png')
    app.root.destroy()
print('PASS: notes top-left details, top-right picker, bottom full-width editor')
