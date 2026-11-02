"""Centralized, cancellable Tk callback coordination for Pocket.

Only schedules already-existing local maintenance work. A registered task must
run on the Tk/UI thread; socket and IEEE requests stay in explicit worker flows.
"""
from __future__ import annotations


class TaskManager:
    def __init__(self, root, *, on_error=None):
        self.root = root
        self.on_error = on_error
        self._tasks = {}
        self._handles = {}
        self._stopped = False

    def every(self, name: str, interval_ms: int, callback, *, initial_ms=None):
        if self._stopped:
            raise RuntimeError("Task manager is stopped")
        if name in self._tasks:
            raise ValueError(f"Task already scheduled: {name}")
        if not name or not callable(callback) or type(interval_ms) is not int or interval_ms < 20:
            raise ValueError("Invalid periodic task")
        self._tasks[name] = (interval_ms, callback)
        self._schedule(name, interval_ms if initial_ms is None else initial_ms)

    def _schedule(self, name, delay_ms):
        self._handles[name] = self.root.after(delay_ms, lambda: self._run(name))

    def _run(self, name):
        self._handles.pop(name, None)
        if self._stopped or name not in self._tasks:
            return
        interval, callback = self._tasks[name]
        try:
            callback()
        except Exception as exc:
            if self.on_error is not None:
                self.on_error(name, exc)
        finally:
            if not self._stopped and name in self._tasks:
                self._schedule(name, interval)

    def cancel(self, name):
        self._tasks.pop(name, None)
        handle = self._handles.pop(name, None)
        if handle is not None:
            try:
                self.root.after_cancel(handle)
            except (RuntimeError, ValueError):
                pass

    def stop(self):
        self._stopped = True
        for name in list(self._tasks):
            self.cancel(name)

    @property
    def scheduled(self):
        return tuple(self._tasks)
