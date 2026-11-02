"""Never close Pocket when the last data write failed."""
import runpy
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

APP = runpy.run_path(str(Path(__file__).resolve().parents[1] / "app.pyw"),
                     run_name="test_shutdown")
PocketDesk = APP["PocketDesk"]


class SafeShutdownTests(unittest.TestCase):
    def test_quit_does_not_destroy_unsaved_data(self):
        desk = SimpleNamespace(
            _write_now=Mock(return_value=False),
            scan_cancel=Mock(), tasks=Mock(), tray=Mock(),
            root=SimpleNamespace(destroy=Mock()))
        PocketDesk.quit(desk)
        desk.scan_cancel.assert_not_called()
        desk.tasks.stop.assert_not_called()
        desk.tray.stop.assert_not_called()
        desk.root.destroy.assert_not_called()

    def test_quit_stops_timers_after_successful_write(self):
        desk = SimpleNamespace(
            _write_now=Mock(return_value=True),
            scan_cancel=SimpleNamespace(set=Mock()), tasks=SimpleNamespace(stop=Mock()),
            tray=SimpleNamespace(stop=Mock()), root=SimpleNamespace(destroy=Mock()))
        PocketDesk.quit(desk)
        desk.scan_cancel.set.assert_called_once()
        desk.tasks.stop.assert_called_once()
        desk.tray.stop.assert_called_once()
        desk.root.destroy.assert_called_once()

    def test_hide_keeps_window_open_if_save_failed(self):
        desk = SimpleNamespace(_write_now=Mock(return_value=False),
                               preview=True,
                               root=SimpleNamespace(iconify=Mock()))
        PocketDesk.hide(desk)
        desk.root.iconify.assert_not_called()


if __name__ == "__main__":
    unittest.main()
