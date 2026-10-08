"""QThread wrapper around the engine's FFmpeg audio extraction.

The pure extract_audio lives in core.engine.extract_audio (Qt-free, shared
with the FastAPI service); this module adds the PyQt worker for the desktop
app and re-exports extract_audio for existing imports.
"""

import os

from PyQt6.QtCore import pyqtSignal
from utils.thread_workers import BaseWorker

from core.engine.extract_audio import extract_audio

__all__ = ["AudioExtractionWorker", "extract_audio"]


class AudioExtractionWorker(BaseWorker):
    """QThread worker for non-blocking audio extraction."""

    finished = pyqtSignal(str)  # emits extracted audio path

    def __init__(self, input_path: str, parent=None):
        super().__init__(parent)
        self._input_path = input_path

    def run(self):
        try:
            self.status_update.emit("Extracting audio...")
            audio_path = extract_audio(self._input_path)
            if self.is_cancelled:
                if os.path.exists(audio_path):
                    os.unlink(audio_path)
                return
            self.finished.emit(audio_path)
        except FileNotFoundError as e:
            self.error.emit(str(e))
        except RuntimeError as e:
            self.error.emit(str(e))
        except Exception as e:
            self.error.emit(f"Audio extraction failed: {e}")
