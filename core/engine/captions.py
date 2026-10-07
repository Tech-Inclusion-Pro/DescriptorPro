"""Caption drafting from speech, producing CaptionCue dicts (spec §4).

Phase 1 pipeline: the configured backend in `core/asr/` drafts raw
sentence-sized cues with word timestamps (Whisper gated by Silero VAD so no
cues are drafted from silence; Parakeet TDT does not hallucinate in silence),
`core/align.py` fills in word timings when a backend cannot provide them, and
`core/engine/caption_format.py` reshapes everything to DCMP/FCC form.
"""

from __future__ import annotations

from core.asr import get_backend
from core.engine.caption_format import format_cues
from core.engine.config import DEFAULT_CONFIG
from core.engine.progress import CancelToken, NullProgress, ProgressReporter


def transcribe_to_cues(
    audio_path: str,
    model_size: str = "small",
    language: str | None = None,
    device: str = "auto",
    compute_type: str = "int8",
    *,
    engine: str = "whisper",
    progress: ProgressReporter | None = None,
    cancel: CancelToken | None = None,
) -> dict:
    """Returns {language, duration, model, cues: [CaptionCue dict, ...]}.

    `model_size` is backend-specific: a Whisper size name ("medium") or a
    Parakeet model id ("mlx-community/parakeet-tdt-0.6b-v3").
    """
    progress = progress or NullProgress()
    cancel = cancel or CancelToken()

    backend = get_backend(engine)
    result = backend.transcribe(
        audio_path,
        model_size,
        language,
        progress=progress,
        cancel=cancel,
    )

    needs_words = [c for c in result["cues"] if c["text"] and not c["words"]]
    if needs_words:
        progress.status("Timing words with forced alignment...")
        from core.align import align_words

        align_words(audio_path, needs_words, language=result["language"] or language)

    progress.status("Formatting captions to DCMP line limits...")
    result["cues"] = format_cues(result["cues"], DEFAULT_CONFIG.captions)

    progress.percent(100)
    progress.status(f"Caption drafting complete: {len(result['cues'])} cues")
    return result
