"""Check the compact phone row, note timestamp, export of the selected note, and screenshot."""
import os
from pathlib import Path
import runpy
import tempfile
from unittest.mock import patch
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
    assert app.created_label.cget('text').startswith('Created: ')
    assert 'unknown' not in app.created_label.cget('text')
    with patch('sys.platform', 'win32'), patch('subprocess.Popen') as popen:
        app.open_notepad()
        popen.assert_called_once()
        args = popen.call_args.args[0]
        assert args[0] == 'notepad.exe'
        selected_path = Path(args[1])
        assert selected_path.exists()
        assert selected_path.read_text(encoding='utf-8-sig') == 'show interfaces status\nshow ip route\nshow version'
    app.root.update()
    pane = app.note_body
    assert pane.winfo_height() > 300, pane.winfo_height()
    assert app.note_list.winfo_height() > 50
    assert app.note_body.winfo_width() > app.note_list.winfo_width() * 2
    assert app.note_body.winfo_rooty() > app.note_list.winfo_rooty()
    x, y = app.root.winfo_rootx(), app.root.winfo_rooty()
    ImageGrab.grab(bbox=(x, y, x + app.root.winfo_width(), y + app.root.winfo_height())).save(ROOT / 'preview-notes-v114.png')
    app.show_tab('links')
    app.root.update()
    assert not hasattr(app, 'footer')
    app.root.destroy()
print('PASS: compact phone field, created timestamp, real note in Notepad, and recovered editor space')
