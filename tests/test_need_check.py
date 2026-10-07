"""Need check logic (core/need_check.py), model stubbed."""

from __future__ import annotations

import json

from core.need_check import (
    check_segment,
    find_deictic,
    ocr_covered_by_transcript,
    tally,
    transcript_window,
)


def cue(start, end, text):
    return {"start": start, "end": end, "text": text, "kind": "speech"}


def segment(facts, start=0.0, end=10.0):
    return {
        "id": "seg-0001",
        "start": start,
        "end": end,
        "keyframes": [],
        "ocr_text": [],
        "visual_facts": facts,
        "transcript_window": "",
        "need": None,
        "decision": {"value": "undecided", "by": None, "at": None},
    }


def fact(fid, text, kind="text", essential=True):
    return {"id": fid, "text": text, "kind": kind, "essential": essential}


def stub_model(answer, evidence=""):
    return lambda prompt: json.dumps({"answer": answer, "evidence": evidence})


class TestTranscriptWindow:
    def test_includes_padded_cues(self):
        cues = [cue(0, 2, "early"), cue(9, 11, "late"), cue(50, 52, "far away")]
        text = transcript_window(cues, 3.0, 8.0, pad=3.0)
        assert "early" in text and "late" in text and "far away" not in text


class TestOcrMatch:
    def test_direct_quote_matches(self):
        assert ocr_covered_by_transcript(
            "Who is on the team?", "so let's ask who is on the team here", 0.8
        )

    def test_unrelated_text_does_not_match(self):
        assert not ocr_covered_by_transcript(
            "LEA representative", "today we talk about weather patterns", 0.8
        )


class TestDeictic:
    def test_english_phrase(self):
        assert find_deictic("As you can see, this works.") == ["as you can see", "you can see"]

    def test_spanish_phrase_accent_folded(self):
        assert "como pueden ver" in find_deictic("Como pueden ver, cada persona tiene un rol.")

    def test_clean_speech_none(self):
        assert find_deictic("The team has six roles, including the parent.") == []


class TestVerdicts:
    def test_all_covered_not_needed(self):
        seg = segment([fact("vf-1", "Six roles listed", kind="diagram")])
        need = check_segment(seg, [cue(0, 5, "the six roles are parent, teacher...")], stub_model("covered"))
        assert need["verdict"] == "not_needed"
        assert need["reason"]
        assert need["criteria"] == ["WCAG-1.2.5"]

    def test_uncovered_fact_needed_with_reason(self):
        seg = segment([fact("vf-1", "Six role labels surround the word Student", kind="diagram")])
        need = check_segment(seg, [cue(0, 5, "as you can see each has a job")], stub_model("not_covered"))
        assert need["verdict"] == "needed"
        assert need["uncovered_facts"] == ["vf-1"]
        assert "Six role labels" in need["reason"]
        assert "as you can see" in need["deictic"]

    def test_unsure_gives_uncertain(self):
        seg = segment([fact("vf-1", "A chart trends upward", kind="chart")])
        need = check_segment(seg, [cue(0, 5, "numbers are improving")], stub_model("unsure"))
        assert need["verdict"] == "uncertain"

    def test_unreliable_transcript_forces_uncertain(self):
        seg = segment([fact("vf-1", "Title slide", kind="text")])
        need = check_segment(
            seg,
            [cue(0, 5, "title slide")],
            stub_model("covered"),
            transcript_reliable=False,
        )
        assert need["verdict"] == "uncertain"

    def test_ocr_fact_fuzzy_match_skips_model(self):
        calls = []

        def model(prompt):
            calls.append(prompt)
            return json.dumps({"answer": "not_covered", "evidence": ""})

        seg = segment([fact("vf-1", "Who is on the team?", kind="text")])
        need = check_segment(seg, [cue(0, 5, "who is on the team")], model)
        assert need["verdict"] == "not_needed"
        assert calls == []  # fuzzy match answered without the model

    def test_no_essential_facts_not_needed(self):
        seg = segment([fact("vf-1", "Decorative background", kind="setting", essential=False)])
        need = check_segment(seg, [], stub_model("covered"))
        assert need["verdict"] == "not_needed"

    def test_model_garbage_becomes_unsure(self):
        seg = segment([fact("vf-1", "A diagram", kind="diagram")])
        need = check_segment(seg, [cue(0, 5, "words")], lambda p: "not json at all")
        assert need["verdict"] == "uncertain"


class TestTally:
    def test_counts(self):
        segs = [segment([]) for _ in range(3)]
        segs[0]["need"] = {"verdict": "needed"}
        segs[1]["need"] = {"verdict": "not_needed"}
        counts = tally(segs)
        assert counts == {"needed": 1, "not_needed": 1, "uncertain": 0, "unchecked": 1}
