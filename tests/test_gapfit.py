"""Gap fitting (core/gapfit.py)."""

from __future__ import annotations

from core.gapfit import (
    added_running_time,
    build_gap_list,
    estimate_duration,
    place_description,
    word_budget,
)


def cue_with_words(text: str, start: float, per_word: float = 0.3):
    words = []
    t = start
    for w in text.split():
        words.append({"w": w, "s": round(t, 3), "e": round(t + per_word, 3), "p": 0.9})
        t += per_word
    return {"start": start, "end": t, "text": text, "kind": "speech", "words": words}


SEGMENT = {"id": "seg-0001", "start": 0.0, "end": 30.0}


class TestGapList:
    def test_finds_silence_between_speech(self):
        cues = [cue_with_words("hello there", 0.0), cue_with_words("back again", 10.0)]
        gaps = build_gap_list(cues, duration=12.0)
        assert len(gaps) == 1
        gap = gaps[0]
        assert 0.6 <= gap["start"] <= 0.8  # after speech ends + guard
        assert 9.8 <= gap["end"] <= 9.9  # before next word - guard

    def test_leading_and_trailing_silence_counted(self):
        cues = [cue_with_words("mid words here", 10.0)]
        gaps = build_gap_list(cues, duration=20.0)
        assert len(gaps) == 2
        assert gaps[0]["start"] == 0.0  # leading gap starts at true zero

    def test_short_pauses_ignored(self):
        cues = [cue_with_words("a b", 0.0), cue_with_words("c d", 1.5)]  # 0.9 s pause
        assert build_gap_list(cues, duration=3.0) == []


class TestEstimates:
    def test_estimate_at_160_wpm(self):
        assert estimate_duration("one two three four") == 1.5

    def test_word_budget_inverse(self):
        assert word_budget(6.0) == 16


class TestPlacement:
    def test_fits_in_gap_after_visual(self):
        gaps = [{"start": 5.0, "end": 15.0, "length": 10.0}]
        placed = place_description(SEGMENT, "A diagram shows six roles.", None, gaps, "standard")
        assert placed["placement"] == "in_gap"
        assert placed["mode"] == "inline"
        assert placed["start"] == 5.0
        assert placed["flags"] == []

    def test_never_uses_gap_before_segment(self):
        gaps = [{"start": 0.0, "end": 20.0, "length": 20.0}]
        segment = {"id": "s", "start": 8.0, "end": 30.0}
        placed = place_description(segment, "Words here.", None, gaps, "standard")
        assert placed["flags"][0]["type"] == "too_long_for_gap" or placed["start"] >= 8.0

    def test_short_version_used_when_full_does_not_fit(self):
        gaps = [{"start": 5.0, "end": 7.0, "length": 2.0}]
        long_text = " ".join(["word"] * 40)  # 15 s at 160 wpm
        placed = place_description(SEGMENT, long_text, "Six roles shown.", gaps, "standard")
        assert placed["text"] == "Six roles shown."
        assert placed["flags"][0]["type"] == "shortened_for_gap"

    def test_standard_style_flags_too_long(self):
        gaps = [{"start": 5.0, "end": 6.6, "length": 1.6}]
        long_text = " ".join(["word"] * 40)
        placed = place_description(SEGMENT, long_text, " ".join(["word"] * 30), gaps, "standard")
        assert placed["flags"][0]["type"] == "too_long_for_gap"
        assert placed["mode"] == "inline"

    def test_extended_when_needed_pauses_instead(self):
        gaps = [{"start": 5.0, "end": 6.6, "length": 1.6}]
        long_text = " ".join(["word"] * 40)
        placed = place_description(SEGMENT, long_text, None, gaps, "extended_when_needed")
        assert placed["mode"] == "extended"
        assert placed["flags"] == []

    def test_extended_before_content_at_segment_start(self):
        segment = {"id": "s", "start": 48.0, "end": 80.0}
        placed = place_description(segment, "A diagram shows six roles.", None, [], "extended_before_content")
        assert placed["start"] == 48.0
        assert placed["placement"] == "before_content"
        assert placed["mode"] == "extended"


class TestAddedRunningTime:
    def test_sums_extended_only(self):
        cues = [
            {"mode": "extended", "est_duration": 8.0},
            {"mode": "inline", "est_duration": 3.0},
            {"mode": "extended", "est_duration": 2.5},
        ]
        assert added_running_time(cues) == 10.5
