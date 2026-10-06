"""Progress reporting and cancellation primitives shared by all engine stages."""

from __future__ import annotations

import threading
from typing import Protocol


class Cancelled(Exception):
    """Raised inside an engine stage when its CancelToken is triggered."""


class ProgressReporter(Protocol):
    """Sink for progress events. Implementations: Qt signal adapter, job runner."""

    def percent(self, value: int) -> None: ...

    def status(self, message: str) -> None: ...

    def partial(self, payload: dict) -> None:
        """A piece of the result available early (for example one segment)."""
        ...


class NullProgress:
    """ProgressReporter that discards everything. Default for tests."""

    def percent(self, value: int) -> None:
        pass

    def status(self, message: str) -> None:
        pass

    def partial(self, payload: dict) -> None:
        pass


class CancelToken:
    """Thread-safe cancellation flag checked inside engine stages."""

    def __init__(self) -> None:
        self._event = threading.Event()

    def cancel(self) -> None:
        self._event.set()

    @property
    def cancelled(self) -> bool:
        return self._event.is_set()

    def raise_if_cancelled(self) -> None:
        if self._event.is_set():
            raise Cancelled()
