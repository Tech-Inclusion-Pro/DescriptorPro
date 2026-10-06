"""Whisper transcription as a plain function, shared by PyQt and the service."""

from __future__ import annotations

from core.engine.progress import CancelToken, NullProgress, ProgressReporter
from core.models import TranscriptModel, TranscriptSegment


def transcribe_file(
    audio_path: str,
    model_size: str = "medium",
    language: str | None = None,
    device: str = "auto",
    compute_type: str = "int8",
    *,
    word_timestamps: bool = False,
    progress: ProgressReporter | None = None,
    cancel: CancelToken | None = None,
) -> TranscriptModel:
    """Transcribe an audio file with faster-whisper.

    Raises Cancelled if the token is triggered. word_timestamps stays off for
    the PyQt app; the Describe Studio caption pipeline turns it on (Phase 1).
    """
    progress = progress or NullProgress()
    cancel = cancel or CancelToken()

    progress.status(f"Loading Whisper model: {model_size}...")
    progress.percent(5)

    from faster_whisper import WhisperModel

    model = WhisperModel(model_size, device=device, compute_type=compute_type)
    cancel.raise_if_cancelled()

    progress.status("Transcribing audio...")
    progress.percent(10)

    segments_gen, info = model.transcribe(
        audio_path,
        language=language,
        word_timestamps=word_timestamps,
    )

    duration = info.duration
    detected_lang = info.language
    progress.status(f"Language detected: {detected_lang} | Duration: {duration:.1f}s")

    transcript = TranscriptModel(
        source_file=audio_path,
        duration_seconds=duration,
        language_detected=detected_lang or "",
        whisper_model_used=model_size,
    )

    segment_list: list[TranscriptSegment] = []
    idx = 0
    for seg in segments_gen:
        cancel.raise_if_cancelled()

        idx += 1
        ts = TranscriptSegment(
            index=idx,
            start_time=seg.start,
            end_time=seg.end,
            text=seg.text.strip(),
        )
        segment_list.append(ts)

        progress.partial(
            {
                "index": idx,
                "start": seg.start,
                "end": seg.end,
                "text": seg.text.strip(),
            }
        )

        # Estimate progress: 10-95% range based on time position
        if duration > 0:
            progress.percent(min(10 + int((seg.end / duration) * 85), 95))
        if idx % 10 == 0:
            progress.status(f"Transcribing segment {idx}...")

    transcript.segments = segment_list
    progress.percent(100)
    progress.status(f"Transcription complete: {len(segment_list)} segments")
    return transcript
