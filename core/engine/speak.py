"""Synthetic narration via kokoro-onnx (spec §8.2 described video; DS-8:
synthetic voice is disclosed in every export).

Kokoro 82M: Apache-2.0 code and weights, downloaded once from the
kokoro-onnx GitHub releases (on the network allowlist for model fetches).
Runs on onnxruntime, which the pipeline already carries; espeak-ng comes
bundled through espeakng_loader — no system install.

Qt-free. The engine is cached per process; the model manager treats a
render stage like any other model stage.
"""

from __future__ import annotations

import urllib.request
import wave
from pathlib import Path

from core.engine.progress import NullProgress, ProgressReporter

_BASE = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0"
_MODEL = "kokoro-v1.0.onnx"
_VOICES = "voices-v1.0.bin"

DEFAULT_VOICE = "af_heart"
_ENGINE = None


def ensure_models(models_dir: Path, progress: ProgressReporter | None = None) -> tuple[Path, Path]:
    progress = progress or NullProgress()
    models_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for name in (_MODEL, _VOICES):
        target = models_dir / name
        if not target.exists():
            progress.status(f"Downloading narration voice ({name}, one time)...")
            tmp = target.with_suffix(".part")
            urllib.request.urlretrieve(f"{_BASE}/{name}", tmp)
            tmp.rename(target)
        paths.append(target)
    return paths[0], paths[1]


def _engine(models_dir: Path, progress: ProgressReporter | None = None):
    global _ENGINE
    if _ENGINE is None:
        model, voices = ensure_models(models_dir, progress)
        from kokoro_onnx import Kokoro

        _ENGINE = Kokoro(str(model), str(voices))
    return _ENGINE


def release_engine() -> None:
    global _ENGINE
    _ENGINE = None


def synthesize(
    text: str,
    out_wav: str | Path,
    models_dir: Path,
    *,
    voice: str = DEFAULT_VOICE,
    speed: float = 1.0,
    lang: str = "en-us",
    progress: ProgressReporter | None = None,
) -> float:
    """Writes 16-bit mono WAV at Kokoro's native rate; returns measured
    duration in seconds (spec §7.10.2 — measure, don't estimate, when a
    local voice is available)."""
    import numpy as np

    engine = _engine(models_dir, progress)
    samples, rate = engine.create(text, voice=voice, speed=speed, lang=lang)
    pcm = (np.clip(samples, -1.0, 1.0) * 32767).astype(np.int16)
    out = Path(out_wav)
    out.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(out), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        wav.writeframes(pcm.tobytes())
    return round(len(pcm) / rate, 3)
