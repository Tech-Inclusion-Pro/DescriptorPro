"""Streaming live captions (spec §10.1) on parakeet-mlx's streaming API.

VERIFY resolved 2026-10-07: parakeet-mlx `transcribe_stream` runs the
already-downloaded Parakeet TDT model incrementally on Apple Silicon —
no new runtime, no new weights. WhisperKit rejected (Swift-only, wrong
fit for the Python service); Windows later rides onnx-asr chunking behind
this same class.

Delay honesty (the UI must *show* the measured delay): `lag_ms` is how
far processing trails real time (wall clock elapsed minus audio seconds
accepted), plus the chunk length itself — the floor any chunked system
carries. No target is claimed; the number is displayed.
"""

from __future__ import annotations

import time


class LiveCaptioner:
    """One live session. feed() takes mono float32 PCM at 16 kHz."""

    SAMPLE_RATE = 16000

    def __init__(self, model_name: str = "mlx-community/parakeet-tdt-0.6b-v3"):
        from parakeet_mlx import from_pretrained

        self._model = from_pretrained(model_name)
        self._stream_ctx = self._model.transcribe_stream(context_size=(256, 256))
        self._stream = self._stream_ctx.__enter__()
        self._audio_seconds = 0.0
        self._wall_start: float | None = None
        self.model_name = model_name

    def feed(self, pcm) -> dict:
        """Returns {text, sentences, lag_ms, audio_seconds}."""
        import mlx.core as mx

        if self._wall_start is None:
            self._wall_start = time.monotonic()
        chunk_seconds = len(pcm) / self.SAMPLE_RATE
        self._stream.add_audio(mx.array(pcm))
        self._audio_seconds += chunk_seconds

        elapsed = time.monotonic() - self._wall_start
        backlog = max(elapsed - self._audio_seconds, 0.0)
        lag_ms = int((backlog + chunk_seconds) * 1000)

        result = self._stream.result
        sentences = [
            {
                "text": s.text.strip(),
                "start": round(float(s.start), 2),
                "end": round(float(s.end), 2),
            }
            for s in result.sentences
            if s.text.strip()
        ]
        return {
            "text": result.text.strip(),
            "sentences": sentences,
            "lag_ms": lag_ms,
            "audio_seconds": round(self._audio_seconds, 2),
        }

    def close(self) -> dict:
        """Final transcript sentences."""
        result = self._stream.result
        sentences = [
            {
                "text": s.text.strip(),
                "start": round(float(s.start), 2),
                "end": round(float(s.end), 2),
            }
            for s in result.sentences
            if s.text.strip()
        ]
        self._stream_ctx.__exit__(None, None, None)
        return {"text": result.text.strip(), "sentences": sentences}
