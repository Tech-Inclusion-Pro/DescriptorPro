"""Ollama post-processing — filler cleanup, summary, translation, speaker labeling.

The processing logic lives in core.engine.llm (Qt-free, shared with the
Describe Studio service). This module keeps the original import surface for
the PyQt app: OllamaProcessor, OllamaWorker, check_ollama_status.
"""

from PyQt6.QtCore import pyqtSignal

from utils.thread_workers import BaseWorker
from core.engine.llm import LlmClient as OllamaProcessor
from core.engine.llm import check_ollama_status
from core.models import TranscriptModel

__all__ = ["OllamaProcessor", "OllamaWorker", "check_ollama_status"]


class OllamaWorker(BaseWorker):
    """QThread worker for Ollama post-processing tasks."""

    finished = pyqtSignal(TranscriptModel)

    def __init__(
        self,
        transcript_model: TranscriptModel,
        ollama_model: str,
        clean_fillers: bool = False,
        generate_summary: bool = False,
        translate_spanish: bool = False,
        label_speakers: bool = False,
        parent=None,
    ):
        super().__init__(parent)
        self.transcript_model = transcript_model
        self.ollama_model = ollama_model
        self.do_clean = clean_fillers
        self.do_summary = generate_summary
        self.do_translate = translate_spanish
        self.do_speakers = label_speakers

    def run(self):
        try:
            processor = OllamaProcessor()
            model = self.transcript_model
            total_steps = sum([self.do_clean, self.do_summary, self.do_translate, self.do_speakers])
            step = 0

            # 1. Filler word cleanup
            if self.do_clean:
                self.status_update.emit("Cleaning filler words...")
                n = len(model.segments)
                for i, seg in enumerate(model.segments):
                    if self.is_cancelled:
                        return
                    processor.clean_fillers(seg, self.ollama_model)
                    self.progress_update.emit(int((i + 1) / n * 25))
                    if (i + 1) % 5 == 0:
                        self.status_update.emit(f"Cleaning filler words... {i + 1}/{n}")
                step += 1
                self.status_update.emit("Filler word cleanup complete.")

            # 2. Speaker labeling
            if self.do_speakers:
                if self.is_cancelled:
                    return
                self.status_update.emit("Labeling speakers...")
                self.progress_update.emit(25 + int(step / total_steps * 25))
                processor.label_speakers(model.segments, self.ollama_model)
                step += 1
                self.status_update.emit("Speaker labeling complete.")

            # 3. Summary
            if self.do_summary:
                if self.is_cancelled:
                    return
                self.status_update.emit("Generating summary and key points...")
                self.progress_update.emit(50 + int(step / total_steps * 25))
                full_text = "\n".join(seg.text for seg in model.segments)
                summary, key_points = processor.generate_summary(full_text, self.ollama_model)
                model.summary = summary
                model.key_points = key_points
                step += 1
                self.status_update.emit("Summary generation complete.")

            # 4. Spanish translation
            if self.do_translate:
                self.status_update.emit("Translating to Spanish...")
                n = len(model.segments)
                for i, seg in enumerate(model.segments):
                    if self.is_cancelled:
                        return
                    processor.translate_to_spanish(seg, self.ollama_model)
                    base = 75 if step > 0 else 50
                    self.progress_update.emit(base + int((i + 1) / n * 25))
                    if (i + 1) % 5 == 0:
                        self.status_update.emit(f"Translating to Spanish... {i + 1}/{n}")
                step += 1
                self.status_update.emit("Spanish translation complete.")

            self.progress_update.emit(100)
            self.finished.emit(model)

        except Exception as e:
            self.error.emit(str(e))
