"""faster-whisper backend: word timestamps, per-word confidence, Silero VAD
gating (no cues drafted from silence — stops hallucination in quiet
stretches). Runs on CPU/Metal via ctranslate2; models cached by
faster-whisper in the Hugging Face cache on first use.
"""

from __future__ import annotations

from core.engine.config import DEFAULT_CONFIG
from core.engine.progress import CancelToken, ProgressReporter


class WhisperBackend:
    def transcribe(
        self,
        audio_path: str,
        model_name: str,
        language: str | None,
        *,
        progress: ProgressReporter,
        cancel: CancelToken,
        device: str = "auto",
        compute_type: str = "int8",
    ) -> dict:
        threshold = DEFAULT_CONFIG.captions.low_confidence_threshold

        progress.status(f"Loading speech model: {model_name}...")
        progress.percent(5)

        from faster_whisper import WhisperModel

        model = WhisperModel(model_name, device=device, compute_type=compute_type)
        cancel.raise_if_cancelled()

        progress.status("Listening for speech...")
        progress.percent(10)

        vad = DEFAULT_CONFIG.vad
        segments_gen, info = model.transcribe(
            audio_path,
            language=language,
            word_timestamps=True,
            vad_filter=vad.enabled,
            vad_parameters={
                "threshold": vad.threshold,
                "min_silence_duration_ms": vad.min_silence_duration_ms,
                "speech_pad_ms": vad.speech_pad_ms,
            },
        )
        duration = float(info.duration or 0.0)
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
                # float() strips numpy scalars so cues stay json-serializable
                words.append(
                    {
                        "w": w,
                        "s": round(float(word.start), 3),
                        "e": round(float(word.end), 3),
                        "p": round(float(word.probability), 3),
                    }
                )
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
                    "start": round(float(seg.start), 3),
                    "end": round(float(seg.end), 3),
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

        return {
            "language": info.language or "",
            "duration": duration,
            "model": f"faster-whisper {model_name}",
            "cues": cues,
        }
