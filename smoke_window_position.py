"""Visual drag, persistence, cross-tab, show/hide and reset tests (Xvfb or desktop)."""
from pathlib import Path
import os
import runpy
from types import SimpleNamespace
import tempfile

from PIL import ImageGrab

ROOT = Path(__file__).parent
m = runpy.run_path(str(ROOT / 'app.pyw'), run_name='test_ui')
PocketDesk = m['PocketDesk']

with tempfile.TemporaryDirectory() as d:
    os.environ['APPDATA'] = d
    app = PocketDesk(preview=True)
    app.root.update()
    original = (app.root.winfo_x(), app.root.winfo_y())
    event = lambda x, y: SimpleNamespace(x_root=x, y_root=y)
    start = event(original[0] + 65, original[1] + 35)
    app._begin_window_drag(start)
    app._finish_window_drag(start)
    assert app.data['window_position'] is None, 'A click must not freeze the tray position'

    app._begin_window_drag(start)
    app._continue_window_drag(event(start.x_root - 110, start.y_root - 90))
    app.root.update()
    app._finish_window_drag(event(start.x_root - 110, start.y_root - 90))
    app.root.update()
    dragged = (app.root.winfo_x(), app.root.winfo_y())
    assert dragged != original, (original, dragged)
    assert app.data['window_position'] == {'x': dragged[0], 'y': dragged[1]}

    app.show_tab('links')
    app.root.update()
    assert (app.root.winfo_x(), app.root.winfo_y()) == dragged, 'Tab switch shifted the window'
    app.show_tab('subnet')
    app.root.update()
    assert (app.root.winfo_x(), app.root.winfo_y()) == dragged
    app.show_tab('notes')
    app.root.update()
    assert (app.root.winfo_x(), app.root.winfo_y()) == dragged

    app._write_now()
    x, y = app.root.winfo_rootx(), app.root.winfo_rooty()
    ImageGrab.grab(bbox=(x, y, x + app.root.winfo_width(), y + app.root.winfo_height())).save(ROOT / 'preview-window-position.png')
    for job in app.root.tk.call('after', 'info'):
        app.root.after_cancel(job)
    app.root.destroy()

    app2 = PocketDesk(preview=True)
    app2.root.update()
    assert (app2.root.winfo_x(), app2.root.winfo_y()) == dragged, 'Saved position not restored'
    app2.hide()
    app2.root.update()
    app2.show()
    app2.root.update()
    assert (app2.root.winfo_x(), app2.root.winfo_y()) == dragged, 'Show moved the window'
    app2.reset_window_position()
    app2.root.update()
    assert app2.data['window_position'] is None
    app2._write_now()
    for job in app2.root.tk.call('after', 'info'):
        app2.root.after_cancel(job)
    app2.root.destroy()

    app3 = PocketDesk(preview=True)
    app3.root.update()
    assert app3.data['window_position'] is None
    for job in app3.root.tk.call('after', 'info'):
        app3.root.after_cancel(job)
    app3.root.destroy()

print('PASS: drag & persist, switch tabs, hide/show, reset to tray default')
