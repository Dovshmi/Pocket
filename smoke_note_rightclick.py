"""Actual Tk right-click event posting and popup lifetime regression."""
import os, tempfile, runpy
from pathlib import Path
ROOT=Path(__file__).resolve().parent
PocketDesk=runpy.run_path(str(ROOT/'app.pyw'),run_name='smoke_ui')['PocketDesk']
with tempfile.TemporaryDirectory() as home:
    os.environ['APPDATA']=home
    app=PocketDesk(preview=True)
    app.root.update()
    text=app.note_body
    text.insert('1.0','192.168.1.10')
    text.tag_add('sel','1.0','1.12')
    text.event_generate('<Button-3>',x=40,y=23)
    app.root.update()
    menu=getattr(app,'_note_context_menu',None)
    assert menu is not None and menu.winfo_exists(), 'Context menu destroyed too early'
    assert int(menu.winfo_ismapped()), 'Right-click did not post context menu'
    menu.unpost()
    app.root.update()
    assert not app._modal
    app.root.destroy()
print('PASS: native Tk right-click menu remains posted and unposting restores focus state')
