"""Interactive-command smoke test; run with xvfb-run or on desktop."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import os
from pathlib import Path
import runpy
import tempfile
import tkinter as tk
from tkinter import ttk, messagebox
from unittest import mock

ROOT=Path(__file__).resolve().parents[2]
PocketDesk=runpy.run_path(str(ROOT/'app.pyw'),run_name='smoke_custom')['PocketDesk']


def shutdown(app):
    for job in app.root.tk.call('after', 'info'):
        try:
            app.root.after_cancel(job)
        except tk.TclError:
            pass
    app.root.destroy()


def all_children(obj):
    for child in obj.winfo_children():
        yield child
        yield from all_children(child)


def label_click(root, title):
    options=[w for w in all_children(root) if isinstance(w,tk.Label) and w.cget('text') == title]
    assert options, f'button not found: {title}'
    options[-1].event_generate('<Button-1>')
    root.update()


with tempfile.TemporaryDirectory() as folder:
    os.environ['APPDATA']=folder
    app=PocketDesk(preview=True)
    app.show_tab('commands'); app.root.update()
    assert len(app.command_library)>400
    app.machine_var.set('Cisco');app._change_machine();app.command_query.set('טבלת ניתוב')
    app.root.update()
    assert app._selected_command()['command']=='show ip route'
    app.command_code.delete('1.0','end')
    app.command_code.insert('1.0','show ip route vrf CUSTOMER_TEST')
    app._copy_command()
    assert app.root.clipboard_get()=='show ip route vrf CUSTOMER_TEST'
    app._reset_command_draft()
    assert app.command_code.get('1.0','end-1c')=='show ip route'
    assert app._selected_command()['command']=='show ip route'
    label_click(app.root,'+ New')
    top=[w for w in app.root.winfo_children() if isinstance(w,tk.Toplevel)][-1]
    inputs=list(all_children(top))
    device, category=[w for w in inputs if isinstance(w,ttk.Combobox)]
    title=[w for w in inputs if type(w) is tk.Entry][0]
    code=[w for w in inputs if isinstance(w,tk.Text)][0]
    assert device.get()=='Cisco',device.get()
    title.insert(0,'Check uplink status')
    category.set('Interfaces')
    code.insert('1.0','show interface GigabitEthernet0/1')
    label_click(top,'Save command')
    assert len(app.data['custom_commands'])==1
    item=app._selected_command()
    assert item['description']=='Check uplink status',item
    assert item['command']=='show interface GigabitEthernet0/1'
    app._toggle_command_favorite()
    assert item['id'] in app.data['command_state']['favorites']
    app._write_now()
    shutdown(app)
    # Reload, edit the custom record, and delete it. All without modifying the packaged reference.
    app=PocketDesk(preview=True);app.show_tab('commands');app.root.update()
    app.machine_var.set('Cisco');app._change_machine();app.command_query.set('uplink')
    app.root.update()
    assert len(app.command_filtered)==1,app.command_filtered
    assert app._selected_command()['id']==item['id']
    label_click(app.root,'Edit saved')
    top=[w for w in app.root.winfo_children() if isinstance(w,tk.Toplevel)][-1]
    code=[w for w in all_children(top) if isinstance(w,tk.Text)][0]
    code.delete('1.0','end');code.insert('1.0','show interface GigabitEthernet0/2')
    label_click(top,'Save command')
    assert app._selected_command()['id']==item['id']
    assert app._selected_command()['command']=='show interface GigabitEthernet0/2'
    assert item['id'] in app.data['command_state']['favorites']
    with mock.patch.object(messagebox,'askyesno',return_value=True):
        app._delete_custom_command()
    assert not app.data['custom_commands']
    assert item['id'] not in app.data['command_state']['favorites']
    assert len(app.bundled_commands)>400
    app._write_now();shutdown(app)
print('PASS: editable clipboard, reset, add, restart, edit, favorite, delete')
