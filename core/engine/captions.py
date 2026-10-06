"""Caption drafting from speech: faster-whisper with word timestamps and
per-word confidence, producing CaptionCue dicts (spec §4).

This is the first working slice of the Phase 1 captions pipeline. Deliberately
not here yet (full Phase 1): Silero VAD gating, the Parakeet backend, forced
alignment, DCMP line-length formatting, speaker labels. The cue shape already
matches the spec so those arrive without breaking the UI or exports.
"""

from __future__ import annotations

from core.engine.config import DEFAULT_CONFIG
from core.engine.progress import CancelToken, NullProgress, ProgressReporter


def transcribe_to_cues(
    audio_path: str,
    model_size: str = "small",
    language: str | None = None,
    device: str = "auto",
    compute_type: str = "int8",
    *,
    progress: ProgressReporter | None = None,
    cancel: CancelToken | None = None,
) -> dict:
    """Returns {language, duration, model, cues: [CaptionCue dict, ...]}."""
    progress = progress or NullProgress()
    cancel = cancel or CancelToken()
    threshold = DEFAULT_CONFIG.captions.low_confidence_threshold

    progress.status(f"Loading speech model: {model_size}...")
    progress.percent(5)

    from faster_whisper import WhisperModel

    model = WhisperModel(model_size, device=device, compute_type=compute_type)
    cancel.raise_if_cancelled()

    progress.status("Listening for speech...")
    progress.percent(10)

    segments_gen, info = model.transcribe(
        audio_path,
        language=language,
        word_timestamps=True,
    )
    duration = info.duration or 0.0
    progress.status(f"Language detected: {info.language} | Duration: {duration:.1f}s")

    cues: list[dict] = []
    for seg in segments_gen:
        cancel.raise_if_cancelled()
        index = len(cues) + 1
        text = seg.text.strip()
        words = []
        flags = []
        for word in seg.words or []:
            w = word.word.strip()
            words.append({"w": w, "s": round(word.start, 3), "e": round(word.end, 3), "p": round(word.probability, 3)})
            if word.probability < threshold and w:
                start_ix = text.find(w)
                flags.append(
                    {
                        "type": "low_confidence",
                        "detail": w,
                        "span": [start_ix, start_ix + len(w)] if start_ix >= 0 else None,
                    }
                )

        cues.append(
            {
                "id": f"cap-{index:04d}",
                "start": round(seg.start, 3),
                "end": round(seg.end, 3),
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

        progress.partial({"index": index, "start": seg.start, "end": seg.end, "text": text})
        if duration > 0:
            progress.percent(min(10 + int((seg.end / duration) * 85), 95))
        if index % 10 == 0:
            progress.status(f"Drafting caption {index}...")

    progress.percent(100)
    progress.status(f"Caption drafting complete: {len(cues)} cues")
    return {
        "language": info.language or "",
        "duration": duration,
        "model": f"faster-whisper {model_size}",
        "cues": cues,
    }
