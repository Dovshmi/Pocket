"""Headless-compatible UI dispatch test; native Windows registration requires Windows."""
import os
from pathlib import Path
import runpy
import tempfile
from types import SimpleNamespace

PocketDesk = runpy.run_path(str(Path(__file__).with_name('app.pyw')), run_name='test_import')['PocketDesk']
with tempfile.TemporaryDirectory() as home:
    os.environ['APPDATA'] = home
    app = PocketDesk(preview=True)
    app.root.update()
    # Simulate Windows tray mode: preview iconify() is not supported by Xvfb.
    app.preview = False
    app.tray = SimpleNamespace(error=None, stop=lambda: None)
    assert 'Ctrl+Shift+*' in app.shortcut_hint['text']
    assert app.root.state() == 'normal', app.root.state()
    # The actual WM_HOTKEY handler emits the same event as clicking the tray icon.
    app.events.put(('toggle', None))
    app._poll_events()
    app.root.update()
    assert app.root.state() == 'withdrawn', app.root.state()
    app.events.put(('toggle', None))
    app._poll_events()
    app.root.update()
    assert app.root.state() == 'normal', app.root.state()
    # Repeat with a pinned popup: the hotkey must hide it anyway.
    app.toggle_pin()
    app.events.put(('toggle', None))
    app._poll_events()
    app.root.update()
    assert app.root.state() == 'withdrawn', app.root.state()
    app.root.destroy()
    print('PASS: hotkey event toggles hidden / visible / pinned popup')
