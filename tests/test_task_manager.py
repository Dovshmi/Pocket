"""Periodic UI timers are single-owner, cancellable and never run after stop."""
import unittest
from pocket.task_manager import TaskManager


class FakeRoot:
    def __init__(self):
        self.calls = {}
        self.next_id = 0

    def after(self, delay, callback):
        self.next_id += 1
        self.calls[self.next_id] = (delay, callback)
        return self.next_id

    def after_cancel(self, handle):
        self.calls.pop(handle, None)

    def tick(self):
        handle = min(self.calls)
        delay, callback = self.calls.pop(handle)
        callback()
        return delay


class TaskManagerTests(unittest.TestCase):
    def test_periodic_task_has_one_handle_and_reschedules(self):
        root = FakeRoot()
        seen = []
        scheduler = TaskManager(root)
        scheduler.every("clipboard", 600, lambda: seen.append("tick"), initial_ms=650)
        self.assertEqual(root.tick(), 650)
        self.assertEqual(seen, ["tick"])
        self.assertEqual(len(root.calls), 1)
        self.assertEqual(root.tick(), 600)
        self.assertEqual(len(seen), 2)
        scheduler.stop()
        self.assertEqual(root.calls, {})
        with self.assertRaises(RuntimeError):
            scheduler.every("unused", 120, lambda: None)

    def test_exception_reported_and_does_not_kill_future_ticks(self):
        root = FakeRoot()
        failures = []
        manager = TaskManager(root, on_error=lambda name, exc: failures.append((name, str(exc))))
        def broken():
            raise RuntimeError("test issue")
        manager.every("notepad", 1200, broken)
        root.tick()
        self.assertEqual(failures, [("notepad", "test issue")])
        self.assertEqual(len(root.calls), 1)
        manager.stop()

    def test_duplicate_tasks_rejected_and_stop_inside_callback_is_safe(self):
        root = FakeRoot()
        manager = TaskManager(root)
        manager.every("events", 100, manager.stop)
        with self.assertRaises(ValueError):
            manager.every("events", 100, lambda: None)
        root.tick()
        self.assertFalse(root.calls)
        self.assertEqual(manager.scheduled, ())

    def test_cancel_removes_pending_event(self):
        root = FakeRoot()
        manager = TaskManager(root)
        manager.every("reminders", 1500, lambda: None)
        manager.cancel("reminders")
        self.assertEqual(root.calls, {})


if __name__ == "__main__":
    unittest.main()
