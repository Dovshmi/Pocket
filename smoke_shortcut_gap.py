"""Regression check for the stale blank gap after Save / Cancel.

Run with a desktop display (Linux: xvfb-run -a python smoke_shortcut_gap.py).
Uses a disposable APPDATA directory; never reads or overwrites user notes.
"""
from __future__ import annotations

import os
from pathlib import Path
import tempfile
import runpy

PocketDesk = runpy.run_path(str(Path(__file__).with_name('app.pyw')), run_name='import_test')['PocketDesk']

with tempfile.TemporaryDirectory() as home:
    os.environ['APPDATA'] = home
    app = PocketDesk(preview=True)
    app.show_tab('links')

    def refresh():
        app.root.update_idletasks()
        app.root.update()

    def assert_no_gap():
        refresh()
        # In the no-form state, cards should begin immediately below the drop area.
        assert not app.form_holder.winfo_manager(), 'Shortcut form holder remained packed'
        frame_y = app._scroll_canvas.master.winfo_y()
        expected_y = app.drop_panel.winfo_y() + app.drop_panel.winfo_height() + 12
        assert abs(frame_y - expected_y) <= 2, (frame_y, expected_y)
        assert app._scroll_canvas.winfo_height() > 400, 'Shortcut list should use the available height'

    assert_no_gap()
    initial_links = len(app.data['links'])
    # Saving via the New Shortcut form.
    app._toggle_link_form(None)
    refresh()
    assert app.form_holder.winfo_manager() == 'pack'
    app._save_link('Example', 'https://example.com', 'url')
    assert len(app.data['links']) == initial_links + 1
    assert_no_gap()

    # Canceling via the same form.
    app._toggle_link_form(None)
    refresh()
    app._close_form()
    assert len(app.data['links']) == initial_links + 1
    assert_no_gap()

    # Updating an existing shortcut should not leave a gap.
    link = app.data['links'][0]
    app._toggle_link_form(link)
    refresh()
    app._save_link('Example updated', 'https://example.org', 'url')
    assert len(app.data['links']) == initial_links + 1
    assert app.data['links'][0]['title'] == 'Example updated'
    assert_no_gap()

    # Native drag event equivalent: draft → Save → drop zone resets.
    from types import SimpleNamespace
    app._shortcut_dropped(SimpleNamespace(data='https://github.com/Dovshmi/Pocket'))
    refresh()
    assert app.form_holder.winfo_manager() == 'pack'
    assert 'READY TO SAVE' in app.drop_title['text']
    app._save_link('Pocket · GitHub', 'https://github.com/Dovshmi/Pocket', 'url')
    assert_no_gap()
    assert 'DROP WEBSITE' in app.drop_title['text']
    assert app._scroll_canvas.yview()[0] == 0.0
    app.root.destroy()
    print('PASS: Add / Save / Edit / Cancel / Drop all release form space and cards start under drop zone')
