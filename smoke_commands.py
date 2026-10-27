"""Graphical smoke test (Linux Xvfb or Windows with a desktop)."""
import os
from pathlib import Path
import runpy
import tempfile
import time
from PIL import ImageGrab

p=Path(__file__).resolve().parent
PocketDesk=runpy.run_path(str(p/'app.pyw'),run_name='smoke_import')['PocketDesk']
with tempfile.TemporaryDirectory() as d:
    os.environ['APPDATA']=d
    app=PocketDesk(preview=True)
    app.show_tab('commands')
    for _ in range(8):app.root.update();time.sleep(.06)
    print('Command count:',len(app.command_library))
    assert len(app.command_library)>=400
    app.machine_var.set('Cisco')
    app._change_machine()
    app.command_query.set('טבלת ניתוב')
    for _ in range(8):app.root.update();time.sleep(.06)
    assert 0 < len(app.command_filtered) < 6, len(app.command_filtered)
    assert all(x['machine']=='Cisco' for x in app.command_filtered)
    item=app._selected_command()
    assert item is not None
    app._toggle_command_favorite()
    assert item['id'] in app.data['command_state']['favorites']
    app._copy_command()
    assert app.root.clipboard_get()==item['command']
    assert app.data['command_state']['recent'][0]==item['id']
    for _ in range(8):app.root.update();time.sleep(.06)
    x,y=app.root.winfo_rootx(),app.root.winfo_rooty()
    w,h=app.root.winfo_width(),app.root.winfo_height()
    ImageGrab.grab(bbox=(x,y,x+w,y+h)).save(p/'preview-commands.png')
    print('Preview:',w,h)
    app._write_now()
    saved=app.path.read_text(encoding='utf-8')
    assert item['id'] in saved and 'command_state' in saved
    app.root.destroy()
