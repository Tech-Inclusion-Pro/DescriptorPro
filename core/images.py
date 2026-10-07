"""Image, slide, and chart description (spec §7.11).

Per image: short alt (target < 150 characters), optional long description,
and a decorative *suggestion* with a reason — the person confirms
decorative status, the tool never decides it alone. Charts follow the
OCR-first rule: numbers and labels may be stated only when OCR actually
read them; the prompt enforces it and a post-check flags any digits in the
description that OCR never saw.

Batch ingest: a folder of images or a PDF slide deck (rendered page by
page with pypdfium2 — chosen over PyMuPDF because pypdfium2 is
BSD/Apache-2.0 while PyMuPDF is AGPL). PowerPoint users export to PDF
first; the UI says so.

Qt-free; vision calls injected (generate_vision_json(prompt, image_path)).
"""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

from core.guardrails import check_text, known_names_from_intent
from core.prompts import render_prompt

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".tif", ".tiff"}
ALT_TARGET_CHARS = 150
_KINDS = {"photo", "slide", "chart", "diagram", "screenshot", "artwork", "other"}


def ingest_images(sources: list[str | Path], images_dir: Path) -> list[dict]:
    """Copies images (and renders PDF pages) into the project's images/
    folder; returns ImageItem dicts with empty descriptions."""
    images_dir.mkdir(parents=True, exist_ok=True)
    items: list[dict] = []

    def add(path: Path, label: str) -> None:
        items.append(
            {
                "id": f"img-{len(items) + 1:04d}",
                "path": f"{images_dir.name}/{path.name}",
                "name": label,
                "kind": "other",
                "ocr_text": [],
                "alt": "",
                "long_description": "",
                "decorative": {"suggested": False, "reason": "", "confirmed": None},
                "flags": [],
                "status": "draft",
                "approved_by": None,
                "approved_at": None,
                "lang": "en",
            }
        )

    for source in sources:
        source = Path(source)
        if source.is_dir():
            for child in sorted(source.iterdir()):
                if child.suffix.lower() in IMAGE_SUFFIXES:
                    target = images_dir / f"{len(items) + 1:04d}-{child.name}"
                    shutil.copy2(child, target)
                    add(target, child.name)
        elif source.suffix.lower() == ".pdf":
            import pypdfium2 as pdfium

            pdf = pdfium.PdfDocument(str(source))
            try:
                for page_index in range(len(pdf)):
                    page = pdf[page_index]
                    bitmap = page.render(scale=2.0)
                    target = images_dir / f"{len(items) + 1:04d}-{source.stem}-p{page_index + 1}.png"
                    bitmap.to_pil().save(str(target))
                    add(target, f"{source.name} — page {page_index + 1}")
            finally:
                pdf.close()
        elif source.suffix.lower() in IMAGE_SUFFIXES:
            target = images_dir / f"{len(items) + 1:04d}-{source.name}"
            shutil.copy2(source, target)
            add(target, source.name)
        else:
            raise ValueError(
                f"Not an image or PDF: {source.name}. "
                "For PowerPoint or Keynote, export the deck to PDF first."
            )
    return items


def parse_image_description(raw_json: str) -> dict | None:
    try:
        raw = json.loads(raw_json)
        alt = str(raw.get("alt") or "").strip()
        if not alt:
            return None
    except (json.JSONDecodeError, AttributeError, TypeError):
        return None
    decorative = raw.get("decorative") or {}
    return {
        "alt": alt,
        "long_description": str(raw.get("long_description") or "").strip(),
        "kind": raw.get("kind") if raw.get("kind") in _KINDS else "other",
        "decorative": {
            "suggested": bool(decorative.get("suggested", False)),
            "reason": str(decorative.get("reason") or "").strip(),
            "confirmed": None,  # a person sets this, never the model
        },
    }


def unsourced_numbers(text: str, ocr_lines: list[str]) -> list[str]:
    """Numbers in the description that OCR never read (spec §7.11: state
    values only when they were read from the image)."""
    ocr_blob = " ".join(ocr_lines)
    ocr_numbers = set(re.findall(r"\d[\d,.]*%?", ocr_blob))
    hits = []
    for number in re.findall(r"\d[\d,.]*%?", text):
        if number not in ocr_numbers and number.rstrip(".,") not in ocr_numbers:
            hits.append(number)
    return hits


def describe_image(
    item: dict,
    image_path: Path,
    intent: dict,
    generate_vision_json,
) -> dict:
    """Fills alt/long_description/kind/decorative + flags on the item."""
    from core.vision.ocr import ocr_text_lines

    item["ocr_text"] = ocr_text_lines(str(image_path))

    prompt = render_prompt(
        "image_description",
        ocr_text="\n".join(f"- {line}" for line in item["ocr_text"]) or "(none found)",
        audience=intent.get("audience") or "(not stated)",
        purpose=intent.get("purpose") or "(not stated)",
        detail_level=intent.get("detail_level") or "concise",
        key_terms=", ".join(intent.get("key_terms") or []) or "(none)",
    )
    parsed = parse_image_description(generate_vision_json(prompt, str(image_path)))
    if parsed is None:
        parsed = parse_image_description(generate_vision_json(prompt, str(image_path)))
    if parsed is None:
        item["flags"] = [
            {
                "type": "unverified_claim",
                "detail": "The vision model returned nothing usable for this image. Describe it by hand.",
                "span": None,
            }
        ]
        return item

    item.update(
        alt=parsed["alt"],
        long_description=parsed["long_description"],
        kind=parsed["kind"],
        decorative=parsed["decorative"],
    )

    flags = []
    if len(item["alt"]) > ALT_TARGET_CHARS:
        flags.append(
            {
                "type": "alt_too_long",
                "detail": f"{len(item['alt'])} characters; aim under {ALT_TARGET_CHARS}.",
                "span": None,
            }
        )
    names = known_names_from_intent(intent, item["ocr_text"])
    combined = f"{item['alt']} {item['long_description']}".strip()
    flags += check_text(combined, known_names=names)
    for number in unsourced_numbers(combined, item["ocr_text"]):
        flags.append(
            {
                "type": "unverified_claim",
                "detail": f"The number {number} does not appear in the text OCR read from the image.",
                "span": None,
            }
        )
    item["flags"] = flags
    return item
