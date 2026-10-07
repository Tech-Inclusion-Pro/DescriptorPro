"""Description drafting (core/describe.py) + verification (core/verify.py),
models stubbed."""

from __future__ import annotations

import json

from core.describe import criteria_for_flag, draft_description
from core.verify import check_quotes, parse_verdicts, verify_description


def segment(**over):
    seg = {
        "id": "seg-0002",
        "start": 48.0,
        "end": 80.0,
        "keyframes": ["frames/000048000.jpg"],
        "ocr_text": ["Who is on the team?", "Parent", "Special Educator"],
        "visual_facts": [
            {"id": "vf-1", "text": "Six role labels surround the word Student", "kind": "diagram", "essential": True},
        ],
        "transcript_window": "As you can see here, each of these people has a job.",
        "need": {"verdict": "needed", "uncovered_facts": ["vf-1"], "criteria": ["WCAG-1.2.5"], "deictic": ["as you can see"], "coach": None},
        "decision": {"value": "describe", "by": "Rocco", "at": "2026-10-07T00:00:00Z"},
    }
    seg.update(over)
    return seg


GAPS = [{"start": 52.0, "end": 60.0, "length": 8.0}]
INTENT = {"audience": "Undergraduates", "detail_level": "concise", "key_terms": [], "people": []}


def drafter(full, short=None):
    return lambda prompt: json.dumps({"full": full, "short": short or full})


class TestDrafting:
    def test_produces_description_cue_shape(self):
        cue = draft_description(
            segment(), INTENT, GAPS, "standard", 1,
            drafter("A diagram shows six role labels around the word Student."),
        )
        assert cue["id"] == "ad-0001"
        assert cue["segment"] == "seg-0002"
        assert cue["placement"] == "in_gap"
        assert cue["voice"] == {"kind": "synthetic", "clip": None}
        assert cue["status"] == "draft"
        assert cue["flags"] == []

    def test_guardrail_violation_flagged_with_criteria(self):
        cue = draft_description(
            segment(), INTENT, GAPS, "standard", 1,
            drafter("An elderly woman looks furious at the diagram."),
        )
        types = {f["type"] for f in cue["flags"]}
        assert "identity_inference" in types
        assert "interpretation" in types
        assert "DS-2" in cue["criteria"]
        assert "DS-6" in cue["criteria"]

    def test_nothing_to_describe_returns_none(self):
        seg = segment(visual_facts=[], need={"verdict": "not_needed", "uncovered_facts": []})
        called = []
        result = draft_description(seg, INTENT, GAPS, "standard", 1, lambda p: called.append(p))
        assert result is None
        assert called == []

    def test_garbled_model_retried_once_then_none(self):
        calls = []

        def bad(prompt):
            calls.append(prompt)
            return "not json"

        assert draft_description(segment(), INTENT, GAPS, "standard", 1, bad) is None
        assert len(calls) == 2

    def test_flag_criteria_mapping(self):
        assert criteria_for_flag("too_long_for_gap") == ["DS-4"]
        assert criteria_for_flag("contradicted") == ["DS-3"]


class TestQuoteCheck:
    def test_exact_quote_passes(self):
        assert check_quotes('The title reads "Who is on the team?"', ["Who is on the team?"]) == []

    def test_mismatched_quote_flagged(self):
        flags = check_quotes('A button reads "Submit"', ["Who is on the team?"])
        assert flags[0]["type"] == "unverified_claim"
        assert flags[0]["detail"] == "Submit"


class TestVerification:
    def make_cue(self, text):
        return {
            "id": "ad-0001", "text": text, "flags": [],
            "status": "draft",
        }

    def test_contradicted_claim_struck_from_suggestion_only(self):
        cue = self.make_cue("A diagram shows six roles. The roles are printed in red.")
        verdicts = json.dumps({"claims": [
            {"text": "A diagram shows six roles", "verdict": "supported"},
            {"text": "The roles are printed in red", "verdict": "contradicted"},
        ]})
        verify_description(cue, segment(), lambda p, img: verdicts)
        assert cue["text"].endswith("printed in red.")  # original untouched
        assert "red" not in cue["suggested_text"]
        assert any(f["type"] == "contradicted" for f in cue["flags"])
        # a flag gained in verification carries its standard id (DS-3)
        assert "DS-3" in cue["criteria"]

    def test_cannot_confirm_stays_and_flags(self):
        cue = self.make_cue("A presenter gestures toward the diagram.")
        verdicts = json.dumps({"claims": [
            {"text": "A presenter gestures toward the diagram", "verdict": "cannot_confirm"},
        ]})
        verify_description(cue, segment(), lambda p, img: verdicts)
        assert cue["suggested_text"] == cue["text"]
        assert any(f["type"] == "unverified_claim" for f in cue["flags"])

    def test_existing_flags_never_removed(self):
        cue = self.make_cue("A diagram shows six roles.")
        cue["flags"] = [{"type": "interpretation", "detail": "furious", "span": None}]
        verdicts = json.dumps({"claims": [{"text": "A diagram shows six roles", "verdict": "supported"}]})
        verify_description(cue, segment(), lambda p, img: verdicts)
        assert any(f["type"] == "interpretation" for f in cue["flags"])

    def test_unverifiable_pass_flags_whole_draft(self):
        cue = self.make_cue("A diagram shows six roles.")
        verify_description(cue, segment(), lambda p, img: "garbage")
        assert cue["verification"]["checked"] is False
        assert any(f["type"] == "unverified_claim" for f in cue["flags"])

    def test_parse_verdicts_rejects_bad_verdict_values(self):
        raw = json.dumps({"claims": [{"text": "x", "verdict": "probably"}]})
        assert parse_verdicts(raw) is None
