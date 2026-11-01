"""Capture the hotkey hint with disposable data and a virtual display."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import os
import tempfile
import runpy
from pathlib import Path
from PIL import ImageGrab
PocketDesk = runpy.run_path(str((Path(__file__).resolve().parents[2] / 'app.pyw')), run_name='hotkey_screenshot')['PocketDesk']
with tempfile.TemporaryDirectory() as home:
    os.environ['APPDATA'] = home
    app = PocketDesk(preview=True)
    app.root.update()
    app.root.update_idletasks()
    x, y = app.root.winfo_rootx(), app.root.winfo_rooty()
    width, height = app.root.winfo_width(), app.root.winfo_height()
    ImageGrab.grab(bbox=(x, y, x+width, y+height)).save(str(Path(__file__).resolve().parents[2]/'preview-hotkey.png'))
    app.root.destroy()
    print('Saved preview-hotkey.png')
