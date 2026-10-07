"""Image description mode (core/images.py + exporters/image_exporter.py)."""

from __future__ import annotations

import json
from pathlib import Path

from core.images import (
    ingest_images,
    parse_image_description,
    unsourced_numbers,
)
from exporters.image_exporter import export_images_csv, export_images_docx, export_images_json


def png(path: Path) -> Path:
    import cv2
    import numpy as np

    img = np.full((80, 120, 3), 240, dtype=np.uint8)
    cv2.imwrite(str(path), img)
    return path


class TestIngest:
    def test_folder_of_images(self, tmp_path):
        src = tmp_path / "pics"
        src.mkdir()
        png(src / "a.png")
        png(src / "b.png")
        (src / "notes.txt").write_text("skip me")
        items = ingest_images([src], tmp_path / "images")
        assert [i["id"] for i in items] == ["img-0001", "img-0002"]
        assert all((tmp_path / i["path"]).exists() for i in items)
        assert items[0]["decorative"]["confirmed"] is None

    def test_pdf_renders_pages(self, tmp_path):
        import pypdfium2 as pdfium

        pdf = pdfium.PdfDocument.new()
        for _ in range(2):
            pdf.new_page(200, 150)
        pdf_path = tmp_path / "deck.pdf"
        pdf.save(str(pdf_path))
        items = ingest_images([pdf_path], tmp_path / "images")
        assert len(items) == 2
        assert "page 1" in items[0]["name"]

    def test_pptx_rejected_with_guidance(self, tmp_path):
        bad = tmp_path / "deck.pptx"
        bad.write_bytes(b"zip")
        try:
            ingest_images([bad], tmp_path / "images")
            raise AssertionError("expected ValueError")
        except ValueError as exc:
            assert "export the deck to PDF" in str(exc)


class TestParse:
    def test_valid(self):
        raw = json.dumps(
            {"alt": "Six roles around a student.", "long_description": "",
             "kind": "diagram", "decorative": {"suggested": False, "reason": ""}}
        )
        parsed = parse_image_description(raw)
        assert parsed["kind"] == "diagram"
        assert parsed["decorative"]["confirmed"] is None  # model never confirms

    def test_missing_alt_is_none(self):
        assert parse_image_description(json.dumps({"alt": ""})) is None
        assert parse_image_description("garbage") is None


class TestUnsourcedNumbers:
    def test_number_from_ocr_allowed(self):
        assert unsourced_numbers("Enrollment rose to 45%", ["45%", "Enrollment"]) == []

    def test_invented_number_flagged(self):
        assert unsourced_numbers("The bar reaches 72%", ["Enrollment"]) == ["72%"]

    def test_relationship_language_clean(self):
        assert unsourced_numbers("The left bar is more than twice as tall", []) == []


def project():
    return {
        "title": "Week 7 slides",
        "images": [
            {"id": "img-0001", "name": "roles.png", "kind": "diagram",
             "alt": "Six roles around a student.", "long_description": "Parent, educators...",
             "decorative": {"suggested": False, "reason": "", "confirmed": None},
             "flags": [], "status": "approved", "approved_by": "Rocco Catrone",
             "approved_at": "2026-10-07T00:00:00Z", "lang": "en", "ocr_text": [], "path": "images/1.png"},
            {"id": "img-0002", "name": "divider.png", "kind": "other",
             "alt": "Decorative divider.", "long_description": "",
             "decorative": {"suggested": True, "reason": "No informational content.", "confirmed": None},
             "flags": [], "status": "draft", "approved_by": None,
             "approved_at": None, "lang": "en", "ocr_text": [], "path": "images/2.png"},
        ],
    }


class TestExports:
    def test_csv_shows_unconfirmed_suggestion(self, tmp_path):
        text = export_images_csv(project(), tmp_path / "images.csv").read_text()
        assert "suggested decorative — NOT confirmed" in text
        assert "Six roles around a student." in text
        assert "NOT yet reviewed by a person." in text

    def test_json_round_trips(self, tmp_path):
        data = json.loads(export_images_json(project(), tmp_path / "images.json").read_text())
        assert len(data["images"]) == 2
        assert data["provenance"]

    def test_docx_writes(self, tmp_path):
        path = export_images_docx(project(), tmp_path / "images.docx")
        assert path.stat().st_size > 0
