"""Speech-recognition backends behind one interface (spec §4, plan P1).

Every backend turns an audio file into the same raw-cue shape:

    {language, duration, model, cues: [CaptionCue dict, ...]}

with word timestamps (`words: [{w, s, e, p}]`) whenever the engine can
produce them. `core/engine/captions.py` picks the backend, then formats the
raw cues to DCMP form — backends never format.

Qt-free, like everything under core/ that the service imports.
"""

from __future__ import annotations

from typing import Protocol

from core.engine.progress import CancelToken, ProgressReporter


class AsrBackend(Protocol):
    def transcribe(
        self,
        audio_path: str,
        model_name: str,
        language: str | None,
        *,
        progress: ProgressReporter,
        cancel: CancelToken,
    ) -> dict: ...


def get_backend(engine: str) -> AsrBackend:
    """Engines are imported lazily so an uninstalled optional runtime (for
    example parakeet-mlx on a machine that never uses it) costs nothing."""
    if engine == "whisper":
        from core.asr.whisper_backend import WhisperBackend

        return WhisperBackend()
    if engine == "parakeet":
        from core.asr.parakeet_backend import ParakeetBackend

        return ParakeetBackend()
    raise ValueError(f"Unknown speech engine: {engine}")
