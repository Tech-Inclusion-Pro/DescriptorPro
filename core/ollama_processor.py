"""Ollama post-processing — filler cleanup, summary, translation, speaker labeling."""

import json
import urllib.request
import urllib.error

from PyQt6.QtCore import pyqtSignal

from utils.thread_workers import BaseWorker
from core.models import TranscriptSegment, TranscriptModel


def check_ollama_status() -> tuple[bool, list[str] | None]:
    """Check if Ollama is running and return available models.

    Returns (is_running, model_names_list_or_None).
    """
    try:
        req = urllib.request.Request("http://localhost:11434/api/tags")
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode())
            models = [m["name"] for m in data.get("models", [])]
            return True, models if models else ["llama3"]
    except Exception:
        return False, None


class OllamaProcessor:
    """Ollama-based transcript post-processing."""

    def clean_fillers(self, segment: TranscriptSegment, model: str) -> TranscriptSegment:
        """Remove filler words from a transcript segment."""
        import ollama
        prompt = (
            "Remove filler words (um, uh, like, you know, kind of, sort of) "
            "from this transcript segment.\n"
            "Preserve ALL meaningful content exactly. "
            "Return ONLY the cleaned text with no commentary or explanation.\n\n"
            f"Text: {segment.text}"
        )
        response = ollama.generate(model=model, prompt=prompt)
        segment.text = response["response"].strip()
        segment.cleaned = True
        return segment

    def generate_summary(self, full_text: str, model: str) -> tuple[str, list[str]]:
        """Generate a summary and key points from the full transcript."""
        import ollama
        prompt = (
            "Summarize this transcript. Respond in this exact format:\n"
            "SUMMARY: [2-4 sentence summary]\n"
            "KEY POINTS:\n"
            "- [point 1]\n"
            "- [point 2]\n"
            "(5-7 key points total)\n\n"
            f"Transcript:\n{full_text}"
        )
        response = ollama.generate(model=model, prompt=prompt)
        text = response["response"].strip()

        # Parse SUMMARY and KEY POINTS sections
        summary = ""
        key_points = []

        if "SUMMARY:" in text:
            parts = text.split("KEY POINTS:")
            summary_part = parts[0].replace("SUMMARY:", "").strip()
            summary = summary_part

            if len(parts) > 1:
                points_text = parts[1].strip()
                for line in points_text.split("\n"):
                    line = line.strip()
                    if line.startswith("- "):
                        key_points.append(line[2:].strip())
                    elif line.startswith("* "):
                        key_points.append(line[2:].strip())
        else:
            summary = text

        return summary, key_points

    def translate_to_spanish(self, segment: TranscriptSegment, model: str) -> TranscriptSegment:
        """Translate segment text to Spanish."""
        import ollama
        prompt = (
            "Translate this English text to Spanish.\n"
            "Return ONLY the Spanish translation. No commentary, no original text.\n\n"
            f"Text: {segment.text}"
        )
        response = ollama.generate(model=model, prompt=prompt)
        segment.text_es = response["response"].strip()
        return segment

    def label_speakers(self, segments: list[TranscriptSegment], model: str) -> list[TranscriptSegment]:
        """Analyze segments and assign speaker labels."""
        import ollama
        batch_text = "\n".join([f"[{s.index}] {s.text}" for s in segments])
        prompt = (
            "Analyze these transcript segments for speaker changes based on context, "
            "topic shifts, question/answer patterns, and conversational cues.\n"
            "Label each with Speaker 1, Speaker 2, etc.\n"
            'Respond ONLY with valid JSON array: [{"index": 1, "speaker": "Speaker 1"}, ...]\n\n'
            f"Segments:\n{batch_text}"
        )
        response = ollama.generate(model=model, prompt=prompt)
        resp_text = response["response"].strip()

        try:
            # Try to extract JSON from the response
            start = resp_text.find("[")
            end = resp_text.rfind("]") + 1
            if start >= 0 and end > start:
                speaker_data = json.loads(resp_text[start:end])
                speaker_map = {item["index"]: item["speaker"] for item in speaker_data}
                for seg in segments:
                    if seg.index in speaker_map:
                        seg.speaker = speaker_map[seg.index]
        except (json.JSONDecodeError, KeyError, TypeError):
            # If parsing fails, assign Speaker 1 to all
            for seg in segments:
                seg.speaker = "Speaker 1"

        return segments


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
