"""Phase 1 memory spike test (plan risk #2, 18 GB ceiling on the M3).

Loads and releases each Phase 1 model in sequence inside one process —
the worst realistic day: whisper medium, parakeet-tdt-0.6b-v3, speaker
diarization — printing RSS before/after each load and after release, plus
the process peak at the end. Run on the M3 with Activity Monitor open if
you want a second opinion:

    .venv/bin/python scripts/memory_spike.py [audio-file]

Without an audio file it synthesizes 30 s of tone-plus-silence so every
model genuinely runs inference (loading alone understates the spike).
"""

from __future__ import annotations

import gc
import math
import os
import resource
import struct
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def rss_mb() -> float:
    out = subprocess.run(
        ["ps", "-o", "rss=", "-p", str(os.getpid())], capture_output=True, text=True
    )
    return int(out.stdout.strip()) / 1024


def peak_mb() -> float:
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (1024 * 1024)


def synth_audio() -> str:
    path = tempfile.mktemp(suffix=".wav")
    rate = 16000
    with wave.open(path, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        frames = bytearray()
        for i in range(rate * 30):
            t = i / rate
            on = (t % 4.0) < 2.0  # 2 s tone, 2 s silence
            sample = int(8000 * math.sin(2 * math.pi * 220 * t)) if on else 0
            frames += struct.pack("<h", sample)
        wav.writeframes(bytes(frames))
    return path


def step(label: str, fn) -> None:
    before = rss_mb()
    fn()
    gc.collect()
    print(f"  {label:<46} RSS {before:8.0f} -> {rss_mb():8.0f} MB")


def main() -> None:
    audio = sys.argv[1] if len(sys.argv) > 1 else synth_audio()
    print(f"Audio: {audio}")
    print(f"Start RSS {rss_mb():.0f} MB\n")

    from core.engine.progress import CancelToken, NullProgress

    progress, cancel = NullProgress(), CancelToken()

    def whisper_run():
        from core.asr import get_backend

        get_backend("whisper").transcribe(
            audio, "medium", None, progress=progress, cancel=cancel
        )

    def parakeet_run():
        from core.asr import get_backend

        get_backend("parakeet").transcribe(
            audio, "mlx-community/parakeet-tdt-0.6b-v3", None,
            progress=progress, cancel=cancel,
        )

    def parakeet_release():
        import mlx.core as mx

        gc.collect()
        mx.clear_cache()

    def diarize_run():
        from core.diarize import diarize
        from service.paths import app_support_dir

        diarize(audio, app_support_dir() / "models" / "diarization",
                progress=progress, cancel=cancel)

    print("whisper medium (faster-whisper, int8)")
    step("load + transcribe", whisper_run)
    step("release (gc)", lambda: None)

    print("parakeet-tdt-0.6b-v3 (parakeet-mlx)")
    step("load + transcribe", parakeet_run)
    step("release (gc + mlx cache clear)", parakeet_release)

    print("speaker diarization (sherpa-onnx)")
    step("load + process", diarize_run)
    step("release (gc)", lambda: None)

    print(f"\nProcess peak RSS: {peak_mb():.0f} MB")
    print("Pass criterion: peak comfortably under the 18 GB ceiling with")
    print("room for Ollama description models later (plan risk #2).")


if __name__ == "__main__":
    main()
