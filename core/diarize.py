"""Speaker labels via sherpa-onnx offline diarization (plan P1).

License path verified 2026-10-07 (plan P1 VERIFY): pyannote's own Hugging
Face repos are gated per-user (account + token — wrong flow for
non-technical reviewers), but the weights are MIT/CC-BY-4.0 and k2-fsa
redistributes converted copies ungated from GitHub releases. We download
those on first use: pyannote segmentation-3.0 (MIT, CNRS) + NeMo TitaNet
small speaker embedding (CC-BY-4.0, NVIDIA). Attribution in
docs/MODEL_LICENSES.md; github.com release downloads are on the network
allowlist for model fetches only.

Output is speaker-turn segments; `assign_speakers` paints them onto caption
cues by overlap. One detected speaker means no labels at all — DCMP only
wants speaker IDs when speakers can be confused.

Qt-free. Model files are cached under the directory the caller provides
(the service passes its app-support models dir).
"""

from __future__ import annotations

import tarfile
import urllib.request
import wave
from pathlib import Path

from core.engine.progress import CancelToken, NullProgress, ProgressReporter

_SEGMENTATION_URL = (
    "https://github.com/k2-fsa/sherpa-onnx/releases/download/"
    "speaker-segmentation-models/sherpa-onnx-pyannote-segmentation-3-0.tar.bz2"
)
_EMBEDDING_URL = (
    "https://github.com/k2-fsa/sherpa-onnx/releases/download/"
    "speaker-recongition-models/nemo_en_titanet_small.onnx"  # typo is theirs
)
_SEGMENTATION_MODEL = "sherpa-onnx-pyannote-segmentation-3-0/model.onnx"
_EMBEDDING_MODEL = "nemo_en_titanet_small.onnx"


def ensure_models(models_dir: Path, progress: ProgressReporter) -> tuple[Path, Path]:
    """Download-once. Returns (segmentation_model, embedding_model) paths."""
    models_dir.mkdir(parents=True, exist_ok=True)
    segmentation = models_dir / _SEGMENTATION_MODEL
    embedding = models_dir / _EMBEDDING_MODEL

    if not segmentation.exists():
        progress.status("Downloading speaker segmentation model (one time)...")
        archive = models_dir / "segmentation.tar.bz2"
        urllib.request.urlretrieve(_SEGMENTATION_URL, archive)
        with tarfile.open(archive, "r:bz2") as tar:
            tar.extractall(models_dir, filter="data")
        archive.unlink()
    if not embedding.exists():
        progress.status("Downloading speaker voice model (one time)...")
        tmp = embedding.with_suffix(".part")
        urllib.request.urlretrieve(_EMBEDDING_URL, tmp)
        tmp.rename(embedding)
    return segmentation, embedding


def _read_mono_wav(audio_path: str) -> tuple[list[float], int]:
    import numpy as np

    with wave.open(audio_path, "rb") as wav:
        if wav.getnchannels() != 1 or wav.getsampwidth() != 2:
            raise ValueError("Diarization expects the pipeline's 16-bit mono WAV.")
        rate = wav.getframerate()
        raw = wav.readframes(wav.getnframes())
    samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    return samples, rate


def diarize(
    audio_path: str,
    models_dir: Path,
    *,
    progress: ProgressReporter | None = None,
    cancel: CancelToken | None = None,
) -> list[dict]:
    """Returns speaker turns: [{start, end, speaker: "Speaker N"}, ...],
    speakers numbered by first appearance."""
    progress = progress or NullProgress()
    cancel = cancel or CancelToken()

    segmentation, embedding = ensure_models(models_dir, progress)
    cancel.raise_if_cancelled()

    import sherpa_onnx

    config = sherpa_onnx.OfflineSpeakerDiarizationConfig(
        segmentation=sherpa_onnx.OfflineSpeakerSegmentationModelConfig(
            pyannote=sherpa_onnx.OfflineSpeakerSegmentationPyannoteModelConfig(
                model=str(segmentation)
            ),
        ),
        embedding=sherpa_onnx.SpeakerEmbeddingExtractorConfig(model=str(embedding)),
        clustering=sherpa_onnx.FastClusteringConfig(num_clusters=-1, threshold=0.5),
    )
    diarizer = sherpa_onnx.OfflineSpeakerDiarization(config)

    progress.status("Listening for different speakers...")
    samples, rate = _read_mono_wav(audio_path)
    if rate != diarizer.sample_rate:
        raise ValueError(f"Diarizer wants {diarizer.sample_rate} Hz audio, got {rate} Hz.")

    def on_progress(processed: int, total: int) -> int:
        cancel.raise_if_cancelled()
        return 0

    result = diarizer.process(samples, callback=on_progress).sort_by_start_time()

    order: dict[int, int] = {}
    turns = []
    for seg in result:
        if seg.speaker not in order:
            order[seg.speaker] = len(order) + 1
        turns.append(
            {
                "start": round(seg.start, 3),
                "end": round(seg.end, 3),
                "speaker": f"Speaker {order[seg.speaker]}",
            }
        )
    progress.status(f"Found {len(order)} speaker{'s' if len(order) != 1 else ''}.")
    return turns


def assign_speakers(cues: list[dict], turns: list[dict]) -> int:
    """Set cue['speaker'] to the turn with the largest time overlap. Returns
    the number of distinct speakers; with fewer than two, labels are cleared
    (DCMP: identify speakers only when they could be confused)."""
    distinct = {t["speaker"] for t in turns}
    if len(distinct) < 2:
        for cue in cues:
            cue["speaker"] = None
        return len(distinct)

    for cue in cues:
        best = None
        best_overlap = 0.0
        for turn in turns:
            overlap = min(cue["end"], turn["end"]) - max(cue["start"], turn["start"])
            if overlap > best_overlap:
                best_overlap = overlap
                best = turn["speaker"]
        cue["speaker"] = best
    return len(distinct)
