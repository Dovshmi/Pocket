"""Check taller Commands popup with safe synthetic (non-work) demonstration data."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from pathlib import Path
import os, runpy, tempfile
from PIL import ImageGrab
import tkinter as tk

ROOT=Path(__file__).resolve().parents[2]
PocketDesk=runpy.run_path(str(ROOT/'app.pyw'),run_name='smoke_command_layout')['PocketDesk']

with tempfile.TemporaryDirectory() as d:
    os.environ['APPDATA']=d
    app=PocketDesk(preview=True)
    app.command_library=[
        {'id':f'demo:{i}', 'machine':'Demo Router', 'category':'Monitoring',
         'description': desc, 'command': cmd, 'origin':'bundled'}
        for i,(desc,cmd) in enumerate([
          ('הצגת טבלת הניתוב', 'show ip route'),
          ('Check interface status', 'show interfaces status'),
          ('בדיקת חיבור לרשת', 'ping <IP_ADDRESS>'),
          ('Show ARP entries', 'show ip arp'),
          ('בדיקת נתיבי תקשורת', 'traceroute <DESTINATION>'),
          ('Show VLAN summary', 'show vlan brief'),
          ('הצגת מצב שכנים', 'show cdp neighbors'),
          ('Display system information', 'show version'),
          ('הצגת הגדרות המערכת', 'show running-config'),
          ('Display interface counters', 'show interfaces counters'),
          ('List connected routes', 'show ip route connected'),
          ('Show operational uptime', 'show clock'),
        ])]
    app.show_tab('commands')
    app.machine_var.set('Demo Router')
    app._change_machine()
    app.root.update()
    tree=app.command_tree
    assert tuple(tree['columns']) == ('Command', 'Purpose / Description'), tree['columns']
    first=tree.item(tree.get_children()[0])['values']
    assert first[0].startswith('show') or first[0].startswith('ping') or first[0].startswith('trace'), first
    assert tree.column('Purpose / Description')['anchor']=='e'
    assert tree.column('Command')['anchor']=='w'
    assert app.root.winfo_height() >= 800,app.root.winfo_height()
    assert int(app.command_code.cget('height'))==6
    assert tree.winfo_height() >= 180,tree.winfo_height()
    assert app.command_code.winfo_rooty() + app.command_code.winfo_height() < app.root.winfo_rooty()+app.root.winfo_height()
    x,y=app.root.winfo_rootx(),app.root.winfo_rooty()
    shot=ROOT/'preview-commands-layout.png'
    ImageGrab.grab(bbox=(x,y,x+app.root.winfo_width(),y+app.root.winfo_height())).save(shot)
    print('Full screen:',app.root.winfo_geometry(), 'table:',tree.winfo_height(),'column names:',tree['columns'])
    app.show_tab('notes'); app.root.update()
    assert app.root.winfo_height()==850,app.root.winfo_height()
    app.show_tab('commands'); app.root.update()
    assert app.root.winfo_height()>=800,app.root.winfo_height()
    for job in app.root.tk.call('after','info'):
        try: app.root.after_cancel(job)
        except tk.TclError: pass
    app.root.destroy()
print('PASS: column order, Hebrew alignment, six-line editor, unified 850px tab heights')
