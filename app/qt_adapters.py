"""Bridge between the Qt-free engine and QThread workers.

QtProgressAdapter implements core.engine.progress.ProgressReporter by emitting
the signals the existing UI already listens to.
"""

from __future__ import annotations

from PyQt6.QtCore import QObject, pyqtBoundSignal

from core.engine.progress import CancelToken


class QtProgressAdapter:
    """Forwards engine progress events to Qt signals.

    partial_signal is optional: workers that stream pieces of the result
    (for example transcription segments) pass their signal; others pass None.
    """

    def __init__(
        self,
        progress_signal: pyqtBoundSignal,
        status_signal: pyqtBoundSignal,
        partial_signal: pyqtBoundSignal | None = None,
    ) -> None:
        self._progress = progress_signal
        self._status = status_signal
        self._partial = partial_signal

    def percent(self, value: int) -> None:
        self._progress.emit(value)

    def status(self, message: str) -> None:
        self._status.emit(message)

    def partial(self, payload: dict) -> None:
        if self._partial is not None:
            self._partial.emit(payload)


class WorkerCancelToken(CancelToken):
    """CancelToken that mirrors a BaseWorker's is_cancelled flag."""

    def __init__(self, worker: QObject) -> None:
        super().__init__()
        self._worker = worker

    @property
    def cancelled(self) -> bool:
        return super().cancelled or bool(getattr(self._worker, "is_cancelled", False))

    def raise_if_cancelled(self) -> None:
        if self.cancelled:
            from core.engine.progress import Cancelled

            raise Cancelled()
