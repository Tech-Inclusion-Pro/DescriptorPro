"""Keyframe OCR via RapidOCR (ONNX runtime, pip-installed, Apache-2.0,
models bundled with the wheel — no download, no network). Text with
positions, per spec §7.4.3.
"""

from __future__ import annotations

from functools import lru_cache


@lru_cache(maxsize=1)
def _engine():
    from rapidocr_onnxruntime import RapidOCR

    return RapidOCR()


def ocr_image(image_path: str) -> list[dict]:
    """Returns [{text, box: [[x,y]x4], confidence}, ...] reading order."""
    result, _elapsed = _engine()(image_path)
    lines = []
    for box, text, confidence in result or []:
        text = str(text).strip()
        if text:
            lines.append(
                {
                    "text": text,
                    "box": [[round(float(x), 1), round(float(y), 1)] for x, y in box],
                    "confidence": round(float(confidence), 3),
                }
            )
    return lines


def ocr_text_lines(image_path: str) -> list[str]:
    return [line["text"] for line in ocr_image(image_path)]
