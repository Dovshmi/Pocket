"""Desktop smoke: contextual menu labels, clipboard, timestamp and integrated searches."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import os
from pathlib import Path
import runpy
import tempfile
from PIL import ImageGrab

ROOT = Path(__file__).resolve().parents[2]
PocketDesk = runpy.run_path(str(ROOT / 'app.pyw'), run_name='test_ui')['PocketDesk']
with tempfile.TemporaryDirectory() as home:
    os.environ['APPDATA'] = home
    app = PocketDesk(preview=True)
    app.root.update()
    app.add_note()
    app.title_var.set('Network notes')
    app.note_body.insert('1.0','192.168.1.50\nshow ip route\nTest text')
    app.root.update()
    text = app.note_body

    def selected(a,b):
        text.tag_remove('sel','1.0','end')
        text.tag_add('sel',a,b)
        app.root.update()

    def find(menu,name):
        for i in range(menu.index('end')+1):
            if menu.type(i) == 'command' and name in menu.entrycget(i,'label'):
                return i
        raise AssertionError(f'Missing {name}')

    selected('1.0','1.12')
    menu=app._build_note_context_menu()
    assert 'Check selected IP' in menu.entrycget(find(menu,'Check selected IP'),'label')
    assert menu.entrycget(find(menu,'Copy     Ctrl+C'),'state')=='normal'
    # Menu screenshot, no personal note contents.
    menu.post(text.winfo_rootx()+70,text.winfo_rooty()+40)
    app.root.update()
    x,y = app.root.winfo_rootx(),app.root.winfo_rooty()
    ImageGrab.grab(bbox=(x,y,x+app.root.winfo_width(),y+app.root.winfo_height())).save(ROOT/'preview-note-context-menu.png')
    menu.unpost()
    menu.invoke(find(menu,'Check selected IP'))
    app.root.update()
    assert app.current_tab=='ports'
    assert app.host_var.get()=='192.168.1.50'
    assert not app.scanning
    menu.destroy()

    app.show_tab('notes')
    app.root.update()
    text=app.note_body
    selected('2.0','2.13')
    menu=app._build_note_context_menu()
    menu.invoke(find(menu,'Find selection in Commands'))
    app.root.update()
    assert app.current_tab=='commands'
    assert app.machine_var.get()=='All machines'
    assert app.command_query.get()=='show ip route'
    menu.destroy()

    app.show_tab('notes')
    app.root.update()
    text=app.note_body
    text.mark_set('insert', 'end-1c')
    app._insert_note_timestamp()
    app.root.update()
    assert '20' in text.get('1.0','end-1c')
    app._copy_entire_note()
    assert app.root.clipboard_get()==text.get('1.0','end-1c')
    text.tag_remove('sel','1.0','end')
    menu=app._build_note_context_menu()
    assert menu.entrycget(find(menu,'Copy     Ctrl+C'),'state')=='disabled'
    assert not any('Check selected IP' in menu.entrycget(i,'label') for i in range(menu.index('end')+1) if menu.type(i)=='command')
    menu.destroy()
    app.root.destroy()
print('PASS: context menu, targeted IP, command search, selection conditions and clipboard')
