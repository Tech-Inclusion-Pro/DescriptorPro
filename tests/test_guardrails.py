"""Identity/objectivity guardrails (core/guardrails.py)."""

from __future__ import annotations

from core.guardrails import check_text, known_names_from_intent


def flag_types(flags):
    return [f["type"] for f in flags]


class TestCheckText:
    def test_clean_text_no_flags(self):
        assert check_text("A diagram shows six role labels around the word Student.") == []

    def test_identity_inference_flagged(self):
        flags = check_text("An elderly white man sits at a desk.")
        types = flag_types(flags)
        assert "identity_inference" in types
        details = {f["detail"] for f in flags}
        assert "elderly" in details
        assert "white man" in details

    def test_interpretation_flagged_not_rewritten(self):
        flags = check_text("She looks furious at the screen.")
        assert flag_types(flags) == ["interpretation"]
        assert flags[0]["detail"] == "furious"

    def test_spanish_terms_matched_with_accents(self):
        flags = check_text("El presentador está enojado.")
        assert "interpretation" in flag_types(flags)

    def test_camera_language_flagged(self):
        flags = check_text("The camera pans to a whiteboard.")
        assert "camera_language" in flag_types(flags)

    def test_camera_language_allowed_for_filmmaking(self):
        flags = check_text("The camera pans to a whiteboard.", content_is_filmmaking=True)
        assert "camera_language" not in flag_types(flags)

    def test_word_boundaries_no_false_positive(self):
        # "sad" inside "crusade" must not match
        assert check_text("A crusade-themed poster hangs on the wall.") == []

    def test_name_source_flags(self):
        flags = check_text(
            "Dr. Catrone points at the slide.",
            known_names={"Dr. Catrone": "user"},
        )
        assert flag_types(flags) == ["name_from_user"]

    def test_screen_name_flag(self):
        flags = check_text(
            "A name card reads Maria Lopez.",
            known_names={"Maria Lopez": "screen"},
        )
        assert flag_types(flags) == ["name_from_screen"]


class TestKnownNames:
    def test_intent_people_are_user_source(self):
        intent = {"people": [{"label": "Dr. Catrone", "role": "instructor"}]}
        assert known_names_from_intent(intent) == {"Dr. Catrone": "user"}

    def test_short_capitalized_ocr_line_is_screen_name(self):
        names = known_names_from_intent(None, ["Maria Lopez", "who is on the team?"])
        assert names == {"Maria Lopez": "screen"}

    def test_title_case_headings_are_not_names(self):
        names = known_names_from_intent(
            None, ["Accessible Documents", "Review Checklist", "Special Educator"]
        )
        assert names == {}

    def test_intent_wins_over_screen(self):
        intent = {"people": [{"label": "Maria Lopez"}]}
        names = known_names_from_intent(intent, ["Maria Lopez"])
        assert names["Maria Lopez"] == "user"
