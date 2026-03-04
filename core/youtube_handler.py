"""yt-dlp YouTube download handler."""

import os
import tempfile

from PyQt6.QtCore import pyqtSignal

from utils.thread_workers import BaseWorker


def download_youtube_audio(url: str) -> str:
    """Download YouTube audio to temp WAV. Returns path.

    Raises RuntimeError on failure.
    """
    import yt_dlp

    tmpdir = tempfile.mkdtemp()
    output_template = os.path.join(tmpdir, "%(title)s.%(ext)s")
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": output_template,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "wav",
            }
        ],
        "quiet": True,
        "no_warnings": True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info).rsplit(".", 1)[0] + ".wav"
    except Exception as e:
        raise RuntimeError(
            f"Could not download YouTube audio: {e}"
        ) from e

    if not os.path.exists(filename):
        # Try to find any WAV in the temp directory
        for f in os.listdir(tmpdir):
            if f.endswith(".wav"):
                filename = os.path.join(tmpdir, f)
                break
        else:
            raise RuntimeError("YouTube download completed but no audio file was produced.")

    return filename


class YouTubeWorker(BaseWorker):
    """QThread worker for YouTube audio download."""

    finished = pyqtSignal(str)  # emits downloaded file path

    def __init__(self, url: str, parent=None):
        super().__init__(parent)
        self.url = url

    def run(self):
        try:
            self.status_update.emit(f"Downloading: {self.url}")
            path = download_youtube_audio(self.url)
            self.status_update.emit(f"Download complete: {os.path.basename(path)}")
            self.finished.emit(path)
        except Exception as e:
            self.error.emit(str(e))
