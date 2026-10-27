"""Private-data-safe visual regression for the five taller tabs and multiline CLI editor.

Run on Windows with Python + Pillow or with xvfb-run on Linux.
"""
from pathlib import Path
import os
import runpy
import tempfile
import time
from PIL import ImageGrab

ROOT = Path(__file__).resolve().parent
PocketDesk = runpy.run_path(str(ROOT / 'app.pyw'), run_name='layout_smoke')['PocketDesk']


def close_app(app):
    for job in app.root.tk.call('after', 'info'):
        try:
            app.root.after_cancel(job)
        except Exception:
            pass
    app.root.destroy()


with tempfile.TemporaryDirectory() as temp:
    os.environ['APPDATA'] = temp  # Prevent use of real user notes/settings.
    app = PocketDesk(preview=True)
    for tab in ('notes', 'links', 'ports', 'mac', 'commands'):
        if tab == 'commands':
            app.command_library = [
                {'id': f'demo:{i}', 'machine': 'Demo Router', 'category': 'Interfaces',
                 'description': f'Show interface status {i}', 'command': f'show interface {i}',
                 'origin': 'bundled'}
                for i in range(13)
            ]
        app.show_tab(tab)
        app.root.update()
        assert app.root.winfo_width() == 480
        if app.root.winfo_screenheight() >= 935:
            assert app.root.winfo_height() == 850, (tab, app.root.winfo_height())
        print('Tab:', tab, 'popup:', app.root.winfo_geometry())

    app.machine_var.set('Demo Router')
    app._change_machine()
    app.root.update()
    assert int(app.command_code.cget('height')) == 6
    assert app.command_tree.winfo_height() >= 160
    selected = app._selected_command()
    assert selected
    sample = '\n'.join([
        'configure terminal',
        'interface GigabitEthernet0/1',
        'description TEST_UPLINK',
        'switchport mode access',
        'switchport access vlan 100',
        'end',
    ])
    app.command_code.delete('1.0', 'end')
    app.command_code.insert('1.0', sample)
    app._copy_command()
    assert app.root.clipboard_get() == sample
    assert app._selected_command()['command'] == selected['command']
    app.root.update()
    x, y = app.root.winfo_rootx(), app.root.winfo_rooty()
    ImageGrab.grab(bbox=(x, y, x+app.root.winfo_width(), y+app.root.winfo_height())).save(ROOT / 'preview-commands-edit.png')
    close_app(app)
print('PASS: all five tab heights and editable six-line command copy (without changing reference)')
