"""faster-whisper transcription wrapper with QThread worker.

The transcription logic lives in core.engine.transcribe (Qt-free, shared with
the Describe Studio service). This worker is a thin Qt adapter around it.
"""

from PyQt6.QtCore import pyqtSignal

from utils.thread_workers import BaseWorker
from core.engine.progress import Cancelled
from core.engine.transcribe import transcribe_file
from core.models import TranscriptModel


class TranscriptionWorker(BaseWorker):
    """QThread worker that runs faster-whisper transcription."""

    segment_ready = pyqtSignal(dict)
    finished = pyqtSignal(TranscriptModel)

    def __init__(
        self,
        audio_path: str,
        model_size: str = "medium",
        language: str | None = None,
        device: str = "auto",
        compute_type: str = "int8",
        parent=None,
    ):
        super().__init__(parent)
        self.audio_path = audio_path
        self.model_size = model_size
        self.language = language
        self.device = device
        self.compute_type = compute_type

    def run(self):
        from app.qt_adapters import QtProgressAdapter, WorkerCancelToken

        try:
            transcript = transcribe_file(
                self.audio_path,
                model_size=self.model_size,
                language=self.language,
                device=self.device,
                compute_type=self.compute_type,
                word_timestamps=False,
                progress=QtProgressAdapter(
                    self.progress_update, self.status_update, self.segment_ready
                ),
                cancel=WorkerCancelToken(self),
            )
            self.finished.emit(transcript)
        except Cancelled:
            self.status_update.emit("Transcription cancelled.")
        except Exception as e:
            self.error.emit(str(e))
