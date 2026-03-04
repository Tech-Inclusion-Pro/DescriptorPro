"""QThread worker base classes for non-blocking operations."""

from PyQt6.QtCore import QThread, pyqtSignal


class BaseWorker(QThread):
    """Base worker thread with common signals."""

    progress_update = pyqtSignal(int)       # 0-100 percent
    status_update = pyqtSignal(str)         # status message
    error = pyqtSignal(str)                 # error message

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cancelled = False

    def cancel(self):
        """Request cancellation of the worker."""
        self._cancelled = True

    @property
    def is_cancelled(self) -> bool:
        return self._cancelled
