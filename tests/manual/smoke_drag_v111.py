"""GUI smoke test for swapped notes and unsaved shortcut drop draft."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from pathlib import Path
import os
import tempfile
from types import SimpleNamespace
import importlib.machinery
import importlib.util

APP_PATH = (Path(__file__).resolve().parents[2] / 'app.pyw')
loader = importlib.machinery.SourceFileLoader('pocket_ui', str(APP_PATH))
spec = importlib.util.spec_from_loader('pocket_ui', loader)
mod = importlib.util.module_from_spec(spec)
loader.exec_module(mod)

with tempfile.TemporaryDirectory() as home:
    os.environ['APPDATA'] = home
    app = mod.PocketDesk(preview=True)
    app.root.update()
    # Notes editor should be physically to the left of the note index.
    editor = app.title_entry.master
    sidebar = app.note_list.master
    assert editor.winfo_rootx() < sidebar.winfo_rootx(), (editor.winfo_rootx(), sidebar.winfo_rootx())
    print('PASS: notes editor left, all notes right')

    app.show_tab('links')
    initial_count = len(app.data['links'])
    assert app.drop_title.winfo_exists()
    app._shortcut_dropped(SimpleNamespace(data='https://github.com/Dovshmi/Pocket'))
    app.root.update()
    assert len(app.data['links']) == initial_count
    assert app.edit_link_id is None
    entries = [c for c in app.form_holder.winfo_children()]
    assert len(entries) == 1
    assert 'READY TO SAVE' in app.drop_title['text']
    print('PASS: dropped URL populated edit form without saving')
    app.root.update()
    app.root.after(50, lambda: None)
    if os.environ.get('SCREENSHOT_OUTPUT'):
        from PIL import ImageGrab
        app.root.geometry('480x850+100+100')
        app.root.update()
        shot = ImageGrab.grab(bbox=(100, 100, 580, 950))
        shot.save(os.environ['SCREENSHOT_OUTPUT'])
    app._save_link('Pocket · GitHub','https://github.com/Dovshmi/Pocket','url')
    assert len(app.data['links']) == initial_count + 1
    assert app.data['links'][0]['kind'] == 'url'
    print('PASS: saving after reviewing draft persists shortcut')
    app.show_tab('notes')
    assert app.title_entry.master.winfo_rootx() < app.note_list.master.winfo_rootx()
    app.root.destroy()
