"""Desktop smoke test: Subnet tab, clipboard, note row popup/pinning, and screenshots."""
import os
from pathlib import Path
import runpy
import tempfile
from unittest.mock import patch
from PIL import ImageGrab

ROOT = Path(__file__).resolve().parent
PocketDesk = runpy.run_path(str(ROOT / 'app.pyw'), run_name='preview_gui')['PocketDesk']
with tempfile.TemporaryDirectory() as home:
    os.environ['APPDATA'] = home
    app = PocketDesk(preview=True)
    app.root.update()
    app.add_note()
    app.title_var.set('Switch routing notes')
    app.note_body.insert('end-1c', '\nIP / gateway: 192.168.10.20')
    # No Tk event-loop update before switching: pending edits must still persist.
    app.add_note()
    app.title_var.set('Pinned reference')
    app._toggle_note_pin(app.data['active_note'])
    app.root.update()
    assert app.note_list.get(0).strip().startswith('★'), app.note_list.get(0)
    assert app._note_rows[0]['id'] == app.data['active_note']
    row_bounds = app.note_list.bbox(1)
    assert row_bounds
    app.note_list.event_generate('<Button-3>', x=20, y=row_bounds[1] + row_bounds[3]//2)
    app.root.update()
    menu = app._note_picker_context_menu
    assert menu is not None and menu.winfo_exists()
    assert int(menu.winfo_ismapped()), 'Note picker menu failed to post'
    assert app.active_note()['id'] == app._note_rows[1]['id']
    menu.unpost()
    app.root.update()
    selected_id = app.data['active_note']
    app._duplicate_note(selected_id)
    assert len(app.data['notes']) == 4
    assert app.active_note()['title'].endswith('(copy)')
    assert 'IP / gateway: 192.168.10.20' in app.active_note()['body']
    with patch('tkinter.messagebox.askyesno', return_value=False):
        app._delete_note_by_id(selected_id)
    assert len(app.data['notes']) == 4
    with patch('tkinter.messagebox.askyesno', return_value=True):
        app._delete_note_by_id(selected_id)
    assert len(app.data['notes']) == 3
    app.root.update()
    x, y = app.root.winfo_rootx(), app.root.winfo_rooty()
    ImageGrab.grab(bbox=(x, y, x + app.root.winfo_width(), y + app.root.winfo_height())).save(ROOT/'preview-notes-pinned-v117.png')

    app.show_tab('subnet')
    app.subnet_ip_var.set('192.168.1.76')
    app.subnet_prefix_var.set('26')
    app._calculate_subnet()
    app.root.update()
    assert app.subnet_details['cidr'] == '192.168.1.64/26'
    assert app.subnet_fact_labels['mask'].cget('text') == '255.255.255.192'
    app._copy_subnet_network()
    assert app.root.clipboard_get() == '192.168.1.64/26'
    app.subnet_split_var.set('/28')
    app._split_subnet()
    assert len(app.subnet_tree.get_children()) == 4
    item = app.subnet_tree.get_children()[1]
    app.subnet_tree.selection_set(item)
    app._copy_selected_subnet()
    assert app.root.clipboard_get() == '192.168.1.80/28'
    app._copy_subnet_summary()
    assert 'First usable: 192.168.1.65' in app.root.clipboard_get()
    app.root.update()
    x, y = app.root.winfo_rootx(), app.root.winfo_rooty()
    ImageGrab.grab(bbox=(x, y, x + app.root.winfo_width(), y + app.root.winfo_height())).save(ROOT/'preview-subnet-v117.png')
    for tab in ('notes', 'links', 'ports', 'mac', 'commands', 'subnet'):
        app.show_tab(tab)
        app.root.update()
        assert app.root.winfo_width() == 480
    app.root.destroy()
print('PASS: note menu and pin/duplicate/delete, subnet copy/split, all six tabs')
