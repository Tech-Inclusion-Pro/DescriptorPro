"""Intent profile conversion (core/intent.py) and visual fact parsing
(core/vision/facts.py), model stubbed."""

from __future__ import annotations

import json

from core.intent import QUESTIONS, default_profile, profile_from_answers, sanitize_profile
from core.vision.facts import extract_segment_facts, parse_facts


class TestIntent:
    def test_six_questions_in_spec_order(self):
        assert [q["id"] for q in QUESTIONS] == [
            "audience", "content_type", "people", "detail_level", "languages", "key_terms",
        ]

    def test_skipped_conversation_gives_defaults(self):
        profile = profile_from_answers({}, lambda p: (_ for _ in ()).throw(AssertionError))
        assert profile == default_profile()
        assert profile["detail_level"] == "concise"
        assert profile["people"] == []

    def test_profile_from_answers_sanitized(self):
        raw = {
            "audience": "Undergrads",
            "purpose": "Learn IEP roles",
            "content_type": "lecture_slides",
            "people": [{"label": "Dr. Catrone", "role": "instructor"}],
            "detail_level": "standard",
            "languages": ["EN", "es"],
            "key_terms": ["IEP"],
            "notes": "",
        }
        profile = profile_from_answers(
            {"audience": "undergrads learning IEP roles"}, lambda p: json.dumps(raw)
        )
        assert profile["content_type"] == "lecture_slides"
        assert profile["people"][0]["source"] == "user"
        assert profile["languages"] == ["en", "es"]

    def test_sanitize_rejects_bad_enum_values(self):
        profile = sanitize_profile({"content_type": "propaganda", "detail_level": "extreme"})
        assert profile["content_type"] == "other"
        assert profile["detail_level"] == "concise"

    def test_sanitize_drops_unlabelled_people(self):
        profile = sanitize_profile({"people": [{"role": "ghost"}, {"label": "Real Person"}]})
        assert [p["label"] for p in profile["people"]] == ["Real Person"]


class TestParseFacts:
    def test_valid_facts_parsed_with_ids(self):
        raw = json.dumps(
            {"facts": [
                {"text": "Six role labels surround the word Student", "kind": "diagram", "essential": True},
                {"text": "A slide title reads Who is on the team?", "kind": "text", "essential": True},
            ]}
        )
        facts = parse_facts(raw, "seg-0002")
        assert [f["id"] for f in facts] == ["vf-seg-0002-1", "vf-seg-0002-2"]
        assert facts[0]["essential"] is True

    def test_bad_kind_coerced_and_garbage_skipped(self):
        raw = json.dumps({"facts": [{"text": "Something", "kind": "vibe"}, {"kind": "text"}]})
        facts = parse_facts(raw, "s")
        assert len(facts) == 1
        assert facts[0]["kind"] == "setting"

    def test_non_json_gives_empty(self):
        assert parse_facts("the model rambled", "s") == []

    def test_fact_cap(self):
        raw = json.dumps({"facts": [{"text": f"fact {i}", "kind": "text"} for i in range(20)]})
        assert len(parse_facts(raw, "s")) == 8


class TestExtractWithGuardrails:
    def test_identity_violation_flagged_on_fact(self):
        segment = {
            "id": "seg-0001",
            "keyframes": ["frames/000001.jpg"],
            "ocr_text": [],
            "visual_facts": [],
        }
        raw = json.dumps(
            {"facts": [{"text": "An elderly woman reads a book", "kind": "person", "essential": True}]}
        )
        facts = extract_segment_facts(segment, {}, lambda prompt, image: raw)
        assert facts[0]["flags"][0]["type"] == "identity_inference"

    def test_user_name_flagged_with_source(self):
        segment = {"id": "s", "keyframes": ["k.jpg"], "ocr_text": [], "visual_facts": []}
        raw = json.dumps({"facts": [{"text": "Dr. Catrone gestures at a slide", "kind": "action"}]})
        intent = {"people": [{"label": "Dr. Catrone", "role": "instructor"}]}
        facts = extract_segment_facts(segment, intent, lambda prompt, image: raw)
        assert facts[0]["flags"][0]["type"] == "name_from_user"

    def test_no_keyframes_no_model_call(self):
        segment = {"id": "s", "keyframes": [], "ocr_text": [], "visual_facts": []}
        facts = extract_segment_facts(
            segment, {}, lambda p, i: (_ for _ in ()).throw(AssertionError)
        )
        assert facts == []
