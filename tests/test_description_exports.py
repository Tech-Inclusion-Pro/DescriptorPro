"""Description exports (exporters/description_exporter.py)."""

from __future__ import annotations

from exporters.description_exporter import (
    export_described_transcript_docx,
    export_described_transcript_html,
    export_description_script_docx,
    export_descriptions_vtt,
    export_panopto_vtt,
)


def project(**over):
    data = {
        "title": "Week 7 — What does the team do?",
        "intent": {"languages": ["en"]},
        "caption_cues": [
            {"id": "cap-0001", "start": 0.5, "end": 3.0, "speaker": "Dr. Catrone",
             "text": "Welcome to\nweek seven.", "kind": "speech", "status": "draft",
             "approved_by": None},
        ],
        "description_cues": [
            {"id": "ad-0001", "segment": "seg-0001", "start": 4.0, "gap": 3.0,
             "text": "A diagram shows six roles.", "est_duration": 2.5,
             "mode": "inline", "placement": "in_gap",
             "flags": [], "criteria": [], "status": "draft",
             "approved_by": None, "approved_at": None, "lang": "en"},
            {"id": "ad-0002", "segment": "seg-0002", "start": 0.5, "gap": 0.0,
             "text": "Title slide: Who is on the team?", "est_duration": 3.0,
             "mode": "extended", "placement": "before_content",
             "flags": [{"type": "too_long_for_gap", "detail": "needs 3 s"}],
             "criteria": ["DS-4"], "status": "draft",
             "approved_by": None, "approved_at": None, "lang": "en"},
        ],
        "provenance": {"descriptions": {"cues": 2, "approved": 0}},
    }
    data.update(over)
    return data


class TestDescriptionsVtt:
    def test_vtt_shape_and_provenance(self, tmp_path):
        path = export_descriptions_vtt(project(), tmp_path / "descriptions.en.vtt")
        text = path.read_text()
        assert text.startswith("WEBVTT")
        assert "NOTE" in text
        assert "DRAFT. Not yet reviewed by a person." in text
        assert "A diagram shows six roles." in text
        assert "00:00:04.000 -->" in text

    def test_end_time_from_estimate(self, tmp_path):
        text = export_descriptions_vtt(project(), tmp_path / "d.vtt").read_text()
        assert "00:00:04.000 --> 00:00:06.500" in text


class TestPanopto:
    def test_two_variants_with_draft_stamp(self, tmp_path):
        written = export_panopto_vtt(project(), tmp_path, "week7")
        names = [p.name for p in written]
        assert names == ["week7.panopto-a.vtt", "week7.panopto-b.vtt"]
        a = written[0].read_text()
        b = written[1].read_text()
        assert "<v Audio Descriptions>A diagram shows six roles." in a
        assert "<v" not in b
        assert "DRAFT. Not yet reviewed by a person." in a
        assert "DRAFT. Not yet reviewed by a person." in b


class TestDescribedTranscript:
    def test_html_interleaves_in_time_order(self, tmp_path):
        text = export_described_transcript_html(project(), tmp_path / "t.html").read_text()
        # before_content description at 0.5 sorts ahead of speech at 0.5
        before = text.index("Who is on the team?")
        speech = text.index("Welcome to week seven.")
        inline = text.index("A diagram shows six roles.")
        assert before < speech < inline
        assert "Description (extended)" in text
        assert "NOT yet reviewed by a person." in text
        assert "<script" not in text  # standalone, no scripts, no network

    def test_html_escapes_content(self, tmp_path):
        proj = project()
        proj["caption_cues"][0]["text"] = "Use <track> & enjoy"
        text = export_described_transcript_html(proj, tmp_path / "t.html").read_text()
        assert "<track>" not in text
        assert "&lt;track&gt;" in text

    def test_docx_writes(self, tmp_path):
        path = export_described_transcript_docx(project(), tmp_path / "t.docx")
        assert path.exists() and path.stat().st_size > 0


class TestScript:
    def test_script_has_flags_column(self, tmp_path):
        path = export_description_script_docx(project(), tmp_path / "script.docx")
        import docx

        table = docx.Document(str(path)).tables[0]
        cells = [c.text for row in table.rows for c in row.cells]
        assert any("too_long_for_gap" in c for c in cells)
        assert any("extended, before content" in c for c in cells)
