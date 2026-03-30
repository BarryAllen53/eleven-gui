from __future__ import annotations

import traceback
from typing import Any, Callable

from PySide6.QtCore import QObject, QRunnable, Signal


class WorkerSignals(QObject):
    success = Signal(object)
    progress = Signal(object)
    error = Signal(str)
    finished = Signal()


class Worker(QRunnable):
    def __init__(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> None:
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()
        self._cancel_requested = False

    def cancel(self) -> None:
        self._cancel_requested = True

    @property
    def is_cancelled(self) -> bool:
        return self._cancel_requested

    def run(self) -> None:
        try:
            result = self.fn(*self.args, **self.kwargs)
        except Exception as exc:  # pragma: no cover - GUI surface
            message = f"{exc}\n\n{traceback.format_exc(limit=6)}"
            try:
                self.signals.error.emit(message)
            except RuntimeError:
                pass
        else:
            try:
                self.signals.success.emit(result)
            except RuntimeError:
                pass
        finally:
            try:
                self.signals.finished.emit()
            except RuntimeError:
                pass
