"""Slide-change announcer (spec §10.2). It reads text; it does NOT
describe images, charts, or people live — when a slide looks graphical,
it says so and logs it for the recorded pass.

Pure logic: the caller sends frames (as image bytes); the watcher detects
changes with the same 64×36 grid diff the recorded pipeline uses, OCRs
changed slides, and returns what to speak. Speech itself happens in the
UI (the viewer picks the output device there — headphones for a private
channel, or room speakers).
"""

from __future__ import annotations

import numpy as np

from core.engine.config import DEFAULT_CONFIG

# Below this fraction of the frame covered by recognized text, the slide
# likely carries pictures or charts the announcer must not improvise on.
_TEXT_COVERAGE_FLOOR = 0.02
GRAPHICS_NOTE = "This slide may contain images or charts. Not described live."


class SlideWatcher:
    def __init__(self) -> None:
        self._prev_grid: np.ndarray | None = None
        self._slide_number = 0
        self.log: list[dict] = []  # for the recorded pass

    def feed(self, image_bytes: bytes) -> dict | None:
        """Returns None when the slide has not changed; otherwise
        {slide_number, title, lines, graphics_note}."""
        import cv2

        frame = cv2.imdecode(np.frombuffer(image_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)
        if frame is None:
            return None
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        grid = cv2.resize(gray, (64, 36), interpolation=cv2.INTER_AREA)

        config = DEFAULT_CONFIG.visual
        if self._prev_grid is not None:
            fraction = float((cv2.absdiff(grid, self._prev_grid) > config.diff_threshold).mean())
            if fraction <= config.changed_fraction:
                return None
        self._prev_grid = grid
        self._slide_number += 1

        from core.vision.ocr import ocr_image

        boxes = ocr_image_bytes_cached(frame)
        lines = [b["text"] for b in boxes]
        title = lines[0] if lines else ""

        height, width = gray.shape
        text_area = sum(_box_area(b["box"]) for b in boxes)
        coverage = text_area / float(width * height) if width and height else 0.0
        graphics_note = GRAPHICS_NOTE if coverage < _TEXT_COVERAGE_FLOOR or not lines else None

        change = {
            "slide_number": self._slide_number,
            "title": title,
            "lines": lines,
            "graphics_note": graphics_note,
        }
        self.log.append(change)
        return change


def _box_area(box: list[list[float]]) -> float:
    xs = [p[0] for p in box]
    ys = [p[1] for p in box]
    return max(max(xs) - min(xs), 0.0) * max(max(ys) - min(ys), 0.0)


def ocr_image_bytes_cached(frame) -> list[dict]:
    """OCR an in-memory frame with the shared RapidOCR engine."""
    from core.vision.ocr import _engine

    result, _elapsed = _engine()(frame)
    lines = []
    for box, text, confidence in result or []:
        text = str(text).strip()
        if text:
            lines.append(
                {
                    "text": text,
                    "box": [[float(x), float(y)] for x, y in box],
                    "confidence": round(float(confidence), 3),
                }
            )
    return lines
