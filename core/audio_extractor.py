"""FFmpeg audio extraction — converts media files to 16kHz mono WAV."""

import tempfile
import os
import shutil

from PyQt6.QtCore import pyqtSignal
from utils.thread_workers import BaseWorker

# Common FFmpeg install locations on macOS
_FFMPEG_SEARCH_PATHS = [
    "/opt/homebrew/bin/ffmpeg",
    "/usr/local/bin/ffmpeg",
    "/opt/homebrew/opt/ffmpeg/bin/ffmpeg",
    "/usr/bin/ffmpeg",
]


def _find_ffmpeg() -> str | None:
    """Return the path to ffmpeg, checking PATH and common install locations."""
    found = shutil.which("ffmpeg")
    if found:
        return found
    for path in _FFMPEG_SEARCH_PATHS:
        if os.path.isfile(path) and os.access(path, os.X_OK):
            return path
    return None


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


def extract_audio(input_path: str) -> str:
    """Extract audio to a 16kHz mono WAV temp file. Returns temp file path.

    Raises FileNotFoundError if ffmpeg is not installed.
    Raises RuntimeError if extraction fails.
    """
    # Check ffmpeg availability
    ffmpeg_bin = _find_ffmpeg()
    if not ffmpeg_bin:
        raise FileNotFoundError(
            "FFmpeg is not installed. Please install FFmpeg and add it to your PATH.\n"
            "Visit ffmpeg.org for instructions, or run: brew install ffmpeg"
        )

    # Ensure the directory containing ffmpeg is on PATH so ffmpeg-python finds it
    ffmpeg_dir = os.path.dirname(ffmpeg_bin)
    if ffmpeg_dir not in os.environ.get("PATH", ""):
        os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")

    # If already a WAV at 16kHz, we could skip, but for consistency always convert
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp.close()

    try:
        import ffmpeg
        (
            ffmpeg
            .input(input_path)
            .output(tmp.name, ar=16000, ac=1, acodec='pcm_s16le')
            .overwrite_output()
            .run(cmd=ffmpeg_bin, quiet=True)
        )
    except Exception as e:
        # Clean up temp file on error
        if os.path.exists(tmp.name):
            os.unlink(tmp.name)
        raise RuntimeError(f"Audio extraction failed: {e}") from e

    # Verify output has content
    if not os.path.exists(tmp.name) or os.path.getsize(tmp.name) < 100:
        if os.path.exists(tmp.name):
            os.unlink(tmp.name)
        raise RuntimeError("No audio track found in this file.")

    return tmp.name
