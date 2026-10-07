"""NVIDIA Parakeet TDT backend via parakeet-mlx (Apple Silicon / Metal).

Verified 2026-10-07 (plan P1 VERIFY): parakeet-mlx is the maintained
Apple-Silicon runtime (Apache-2.0, word timestamps via AlignedToken); the
ONNX route (onnx-asr) is the future Windows path behind this same interface.
Model weights (parakeet-tdt-0.6b-v2/v3) are CC-BY-4.0 — attribution lives in
docs/MODEL_LICENSES.md. Downloaded from Hugging Face on first use, then
cached locally.

Parakeet emits subword tokens; this backend merges them into words (a token
starting with a space starts a new word) so cues carry the same
`words: [{w, s, e, p}]` shape as the Whisper backend. Confidence is the
geometric-mean token confidence per word.
"""

from __future__ import annotations

from core.engine.config import DEFAULT_CONFIG
from core.engine.progress import CancelToken, ProgressReporter

# Long files are transcribed in chunks so memory stays flat (parakeet-mlx
# merges the overlap); 120 s matches the library's own CLI default.
_CHUNK_SECONDS = 120.0
_OVERLAP_SECONDS = 15.0


def _tokens_to_words(tokens) -> list[dict]:
    words: list[dict] = []
    for token in tokens:
        text = token.text
        starts_word = text.startswith(" ") or not words
        clean = text.strip()
        if starts_word:
            if clean:
                words.append(
                    {
                        "w": clean,
                        "s": round(float(token.start), 3),
                        "e": round(float(token.end), 3),
                        "p": round(float(token.confidence), 3),
                        "_n": 1,
                    }
                )
        elif words:
            prev = words[-1]
            prev["w"] += clean
            prev["e"] = round(float(token.end), 3)
            # running geometric mean of token confidences
            n = prev.pop("_n")
            prev["p"] = round((prev["p"] ** n * float(token.confidence)) ** (1 / (n + 1)), 3)
            prev["_n"] = n + 1
    for word in words:
        word.pop("_n", None)
    return words


class ParakeetBackend:
    def transcribe(
        self,
        audio_path: str,
        model_name: str,
        language: str | None,
        *,
        progress: ProgressReporter,
        cancel: CancelToken,
    ) -> dict:
        threshold = DEFAULT_CONFIG.captions.low_confidence_threshold

        progress.status(f"Loading speech model: {model_name}...")
        progress.percent(5)

        from parakeet_mlx import from_pretrained

        model = from_pretrained(model_name)
        cancel.raise_if_cancelled()

        progress.status("Listening for speech...")
        progress.percent(10)

        def on_chunk(current: float, total: float) -> None:
            cancel.raise_if_cancelled()
            if total > 0:
                progress.percent(min(10 + int(current / total * 85), 95))

        result = model.transcribe(
            audio_path,
            chunk_duration=_CHUNK_SECONDS,
            overlap_duration=_OVERLAP_SECONDS,
            chunk_callback=on_chunk,
        )
        cancel.raise_if_cancelled()

        cues: list[dict] = []
        duration = 0.0
        for sentence in result.sentences:
            index = len(cues) + 1
            text = sentence.text.strip()
            words = _tokens_to_words(sentence.tokens)
            duration = max(duration, float(sentence.end))
            flags = []
            for word in words:
                if word["w"] and word["p"] < threshold:
                    start_ix = text.find(word["w"])
                    flags.append(
                        {
                            "type": "low_confidence",
                            "detail": word["w"],
                            "span": [start_ix, start_ix + len(word["w"])] if start_ix >= 0 else None,
                        }
                    )
            cues.append(
                {
                    "id": f"cap-{index:04d}",
                    "start": round(float(sentence.start), 3),
                    "end": round(float(sentence.end), 3),
                    "speaker": None,
                    "text": text,
                    "kind": "speech",
                    "words": words,
                    "flags": flags,
                    "status": "draft",
                    "approved_by": None,
                    "approved_at": None,
                }
            )
            progress.partial(
                {"index": index, "start": sentence.start, "end": sentence.end, "text": text}
            )

        # Parakeet v3 detects language itself but does not report it; leave
        # blank rather than guess (the UI treats "" as "not stated").
        return {
            "language": language or "",
            "duration": duration,
            "model": f"parakeet-mlx {model_name}",
            "cues": cues,
        }
