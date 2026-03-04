"""faster-whisper transcription wrapper with QThread worker."""

from PyQt6.QtCore import pyqtSignal

from utils.thread_workers import BaseWorker
from core.models import TranscriptSegment, TranscriptModel


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
        try:
            self.status_update.emit(f"Loading Whisper model: {self.model_size}...")
            self.progress_update.emit(5)

            from faster_whisper import WhisperModel

            model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type,
            )

            if self.is_cancelled:
                return

            self.status_update.emit("Transcribing audio...")
            self.progress_update.emit(10)

            segments_gen, info = model.transcribe(
                self.audio_path,
                language=self.language,
                word_timestamps=False,
            )

            duration = info.duration
            detected_lang = info.language

            self.status_update.emit(
                f"Language detected: {detected_lang} | Duration: {duration:.1f}s"
            )

            transcript = TranscriptModel(
                source_file=self.audio_path,
                duration_seconds=duration,
                language_detected=detected_lang or "",
                whisper_model_used=self.model_size,
            )

            segment_list = []
            idx = 0
            for seg in segments_gen:
                if self.is_cancelled:
                    self.status_update.emit("Transcription cancelled.")
                    return

                idx += 1
                ts = TranscriptSegment(
                    index=idx,
                    start_time=seg.start,
                    end_time=seg.end,
                    text=seg.text.strip(),
                )
                segment_list.append(ts)

                seg_dict = {
                    "index": idx,
                    "start": seg.start,
                    "end": seg.end,
                    "text": seg.text.strip(),
                }
                self.segment_ready.emit(seg_dict)

                # Estimate progress: 10-95% range based on time position
                if duration > 0:
                    progress = 10 + int((seg.end / duration) * 85)
                    progress = min(progress, 95)
                    self.progress_update.emit(progress)

                if idx % 10 == 0:
                    self.status_update.emit(
                        f"Transcribing segment {idx}..."
                    )

            transcript.segments = segment_list
            self.progress_update.emit(100)
            self.status_update.emit(
                f"Transcription complete: {len(segment_list)} segments"
            )
            self.finished.emit(transcript)

        except Exception as e:
            self.error.emit(str(e))
