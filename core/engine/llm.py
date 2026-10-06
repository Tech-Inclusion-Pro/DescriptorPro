"""Qt-free Ollama client for transcript post-processing and, later, the
Describe Studio pipeline (need check, drafting, verification).

keep_alive: pass 0 on the last call of a pipeline stage so Ollama unloads the
model before the next stage loads a different one (spec, section 5.3). None
leaves Ollama's default behavior for the interactive PyQt app.
"""

from __future__ import annotations

import json
import urllib.request

from core.models import TranscriptSegment


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


def unload_model(model: str) -> None:
    """Ask Ollama to evict a model now (keep_alive=0 with an empty prompt)."""
    import ollama

    ollama.generate(model=model, prompt="", keep_alive=0)


class LlmClient:
    """Ollama-based text processing. All methods are synchronous and Qt-free."""

    def _generate(self, model: str, prompt: str, keep_alive: int | None = None) -> str:
        import ollama

        kwargs: dict = {"model": model, "prompt": prompt}
        if keep_alive is not None:
            kwargs["keep_alive"] = keep_alive
        response = ollama.generate(**kwargs)
        return response["response"].strip()

    def clean_fillers(
        self, segment: TranscriptSegment, model: str, keep_alive: int | None = None
    ) -> TranscriptSegment:
        """Remove filler words from a transcript segment."""
        prompt = (
            "Remove filler words (um, uh, like, you know, kind of, sort of) "
            "from this transcript segment.\n"
            "Preserve ALL meaningful content exactly. "
            "Return ONLY the cleaned text with no commentary or explanation.\n\n"
            f"Text: {segment.text}"
        )
        segment.text = self._generate(model, prompt, keep_alive)
        segment.cleaned = True
        return segment

    def generate_summary(
        self, full_text: str, model: str, keep_alive: int | None = None
    ) -> tuple[str, list[str]]:
        """Generate a summary and key points from the full transcript."""
        prompt = (
            "Summarize this transcript. Respond in this exact format:\n"
            "SUMMARY: [2-4 sentence summary]\n"
            "KEY POINTS:\n"
            "- [point 1]\n"
            "- [point 2]\n"
            "(5-7 key points total)\n\n"
            f"Transcript:\n{full_text}"
        )
        text = self._generate(model, prompt, keep_alive)

        # Parse SUMMARY and KEY POINTS sections
        summary = ""
        key_points: list[str] = []

        if "SUMMARY:" in text:
            parts = text.split("KEY POINTS:")
            summary = parts[0].replace("SUMMARY:", "").strip()

            if len(parts) > 1:
                for line in parts[1].strip().split("\n"):
                    line = line.strip()
                    if line.startswith("- ") or line.startswith("* "):
                        key_points.append(line[2:].strip())
        else:
            summary = text

        return summary, key_points

    def translate_to_spanish(
        self, segment: TranscriptSegment, model: str, keep_alive: int | None = None
    ) -> TranscriptSegment:
        """Translate segment text to Spanish."""
        prompt = (
            "Translate this English text to Spanish.\n"
            "Return ONLY the Spanish translation. No commentary, no original text.\n\n"
            f"Text: {segment.text}"
        )
        segment.text_es = self._generate(model, prompt, keep_alive)
        return segment

    def label_speakers(
        self,
        segments: list[TranscriptSegment],
        model: str,
        keep_alive: int | None = None,
    ) -> list[TranscriptSegment]:
        """Analyze segments and assign speaker labels."""
        batch_text = "\n".join(f"[{s.index}] {s.text}" for s in segments)
        prompt = (
            "Analyze these transcript segments for speaker changes based on context, "
            "topic shifts, question/answer patterns, and conversational cues.\n"
            "Label each with Speaker 1, Speaker 2, etc.\n"
            'Respond ONLY with valid JSON array: [{"index": 1, "speaker": "Speaker 1"}, ...]\n\n'
            f"Segments:\n{batch_text}"
        )
        resp_text = self._generate(model, prompt, keep_alive)

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
