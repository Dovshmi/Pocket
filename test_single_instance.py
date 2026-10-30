"""Headless tests for Windows single-instance mutex and activation contract."""
import runpy
from pathlib import Path
from unittest import TestCase
from unittest.mock import Mock, patch
from types import SimpleNamespace

from single_instance import WindowsSingleInstance, MUTEX_NAME, ACTIVATE_EVENT_NAME

app = runpy.run_path(str(Path(__file__).with_name("app.pyw")), run_name="test_import")


class FakeKernel:
    def __init__(self, duplicate=False):
        self.duplicate = duplicate
        self.open_results = [None, 99]
        self.closed = []
        self.signals = []
        self.wait_results = []
        self.mutex_names = []
        self.event_names = []

    def CreateMutexW(self, _, owner, name):
        self.mutex_names.append(name)
        return 10

    def CreateEventW(self, _, manual, initial, name):
        self.event_names.append(name)
        return 20

    def OpenEventW(self, *args):
        return self.open_results.pop(0) if self.open_results else None

    def SetEvent(self, handle):
        self.signals.append(handle)
        return True

    def WaitForSingleObject(self, event, timeout):
        return 0xFFFFFFFF

    def CloseHandle(self, handle):
        self.closed.append(handle)


class InstanceTests(TestCase):
    def test_first_launch_acquires_and_closes_resources(self):
        k = FakeKernel()
        guard = WindowsSingleInstance(kernel=k, get_last_error=lambda: 0)
        self.assertTrue(guard.acquire())
        self.assertEqual(k.mutex_names, [MUTEX_NAME])
        self.assertEqual(k.event_names, [ACTIVATE_EVENT_NAME])
        guard.close()
        guard.close()
        self.assertEqual(k.closed, [20, 10])

    def test_duplicate_signals_and_exits_without_creating_event(self):
        k = FakeKernel(duplicate=True)
        sleep = Mock()
        guard = WindowsSingleInstance(kernel=k, get_last_error=lambda: 183, sleep=sleep)
        self.assertFalse(guard.acquire())
        self.assertEqual(k.event_names, [])
        self.assertEqual(k.signals, [99])
        sleep.assert_called_once_with(0.05)
        self.assertEqual(k.closed, [10, 99])

    def test_duplicate_never_creates_second_app_or_loads_files(self):
        fake = Mock()
        fake.acquire.return_value = False
        with patch.dict(app["main"].__globals__, {"single_instance": SimpleNamespace(WindowsSingleInstance=Mock(return_value=fake)),
                                                   "PocketDesk": Mock(),
                                                   "sys": SimpleNamespace(platform="win32", argv=["app.pyw"])}):
            self.assertEqual(app["main"]([]), 0)
            app["main"].__globals__["PocketDesk"].assert_not_called()

    def test_preview_skips_single_instance_guard(self):
        instance = Mock()
        with patch.dict(app["main"].__globals__, {
            "single_instance": SimpleNamespace(WindowsSingleInstance=Mock()),
            "PocketDesk": Mock(return_value=instance),
            "sys": SimpleNamespace(platform="win32", argv=["app.pyw"])}):
            self.assertEqual(app["main"](["--preview"]), 0)
            app["main"].__globals__["single_instance"].WindowsSingleInstance.assert_not_called()
            instance.run.assert_called_once()

    def test_activation_enqueues_instead_of_touching_tk_on_worker(self):
        instance = Mock()
        guard = Mock()
        guard.acquire.return_value = True
        with patch.dict(app["main"].__globals__, {
            "single_instance": SimpleNamespace(WindowsSingleInstance=Mock(return_value=guard)),
            "PocketDesk": Mock(return_value=instance),
            "sys": SimpleNamespace(platform="win32", argv=["app.pyw"])}):
            self.assertEqual(app["main"]([]), 0)
            callback = guard.start.call_args.args[0]
            callback()
            instance.events.put.assert_called_once_with(("activate_existing", None))
            instance.show.assert_not_called()
            guard.close.assert_called_once()


if __name__ == "__main__":
    import unittest
    unittest.main()
