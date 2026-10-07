"""Scene and slide segmentation + keyframe choice (spec §7.4).

Two detectors, merged:
- PySceneDetect's content detector finds cuts (filmed content).
- A grid-difference scan (64×36 grayscale, OpenCV only) finds slide builds
  and on-screen text changes that content detection misses. Measured
  2026-10-07: a 64-bit perceptual hash loses text-only slide changes
  entirely (text vanishes at 8×8), while the grid diff separates them
  cleanly (2–4% of cells change on a slide flip, 0% between).

Keyframes: first stable frame after each change (settle delay skips
transition blur), plus one mid-segment frame for long segments. Frames are
written as JPEGs into the project's frames/ folder.

Sampling density follows the intent profile's content type
(lecture_slides → hash-driven; narrative → scene-driven; screen_recording /
demonstration → both, denser hash cadence).

Qt-free; no AI models — this stage runs before any model loads (§5.3).
"""

from __future__ import annotations

from pathlib import Path

from core.engine.config import DEFAULT_CONFIG, VisualTrack
from core.engine.progress import CancelToken, NullProgress, ProgressReporter


def _scene_changes(video_path: str, threshold: float) -> list[float]:
    from scenedetect import ContentDetector, detect

    return [scene[0].get_seconds() for scene in detect(video_path, ContentDetector(threshold=threshold))]


def _slide_changes(
    video_path: str,
    config: VisualTrack,
    cadence: float,
    cancel: CancelToken,
    progress: ProgressReporter,
) -> list[float]:
    import cv2

    cap = cv2.VideoCapture(video_path)
    try:
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        total = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0
        duration = total / fps if fps else 0.0
        changes: list[float] = []
        prev = None
        t = 0.0
        while t < duration:
            cancel.raise_if_cancelled()
            cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
            ok, frame = cap.read()
            if not ok:
                break
            grid = cv2.resize(
                cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), (64, 36), interpolation=cv2.INTER_AREA
            )
            if prev is not None:
                fraction = float((cv2.absdiff(grid, prev) > config.diff_threshold).mean())
                if fraction > config.changed_fraction:
                    changes.append(round(t, 3))
            prev = grid
            t += cadence
        return changes
    finally:
        cap.release()


def _merge_changes(changes: list[float], min_gap: float) -> list[float]:
    merged: list[float] = []
    for t in sorted(changes):
        if not merged or t - merged[-1] >= min_gap:
            merged.append(t)
    return merged


def _save_frame(video_path: str, t: float, out_path: Path) -> bool:
    import cv2

    cap = cv2.VideoCapture(video_path)
    try:
        cap.set(cv2.CAP_PROP_POS_MSEC, max(t, 0.0) * 1000)
        ok, frame = cap.read()
        if not ok:
            return False
        out_path.parent.mkdir(parents=True, exist_ok=True)
        return bool(cv2.imwrite(str(out_path), frame, [cv2.IMWRITE_JPEG_QUALITY, 90]))
    finally:
        cap.release()


def _video_duration(video_path: str) -> float:
    import cv2

    cap = cv2.VideoCapture(video_path)
    try:
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        total = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0
        return total / fps if fps else 0.0
    finally:
        cap.release()


def segment_video(
    video_path: str,
    frames_dir: Path,
    content_type: str = "other",
    *,
    config: VisualTrack | None = None,
    progress: ProgressReporter | None = None,
    cancel: CancelToken | None = None,
) -> list[dict]:
    """Returns Segment dicts (spec §4) with keyframes written to frames_dir.
    visual_facts/ocr_text/need stay empty — later stages fill them."""
    config = config or DEFAULT_CONFIG.visual
    progress = progress or NullProgress()
    cancel = cancel or CancelToken()

    duration = _video_duration(video_path)
    if duration <= 0:
        raise ValueError("Could not read the video (zero duration).")

    use_scenes = content_type in ("narrative", "interview", "demonstration", "other")
    use_hash = content_type in ("lecture_slides", "screen_recording", "demonstration", "other")
    cadence = (
        config.hash_sample_seconds / 2
        if content_type in ("screen_recording", "demonstration")
        else config.hash_sample_seconds
    )

    changes: list[float] = [0.0]
    if use_scenes:
        progress.status("Finding scene changes...")
        changes += _scene_changes(video_path, config.scene_threshold)
        cancel.raise_if_cancelled()
    if use_hash:
        progress.status("Scanning for slide and text changes...")
        changes += _slide_changes(video_path, config, cadence, cancel, progress)

    boundaries = _merge_changes(changes, config.min_segment_seconds)
    if boundaries[0] != 0.0:
        boundaries.insert(0, 0.0)

    progress.status(f"Choosing keyframes for {len(boundaries)} parts...")
    segments: list[dict] = []
    for i, start in enumerate(boundaries):
        cancel.raise_if_cancelled()
        end = boundaries[i + 1] if i + 1 < len(boundaries) else duration
        if end - start < config.min_segment_seconds and i > 0:
            continue
        seg_id = f"seg-{len(segments) + 1:04d}"
        keyframes: list[str] = []

        settle = min(start + config.keyframe_settle_seconds, (start + end) / 2)
        frame_name = f"{int(settle * 1000):09d}.jpg"
        if _save_frame(video_path, settle, frames_dir / frame_name):
            keyframes.append(f"frames/{frame_name}")
        if end - start > config.long_segment_seconds:
            mid = (start + end) / 2
            mid_name = f"{int(mid * 1000):09d}.jpg"
            if _save_frame(video_path, mid, frames_dir / mid_name):
                keyframes.append(f"frames/{mid_name}")

        segments.append(
            {
                "id": seg_id,
                "start": round(start, 3),
                "end": round(end, 3),
                "keyframes": keyframes,
                "ocr_text": [],
                "visual_facts": [],
                "transcript_window": "",
                "need": None,
                "decision": {"value": "undecided", "by": None, "at": None},
            }
        )
        progress.percent(min(int((end / duration) * 100), 99))

    return segments
