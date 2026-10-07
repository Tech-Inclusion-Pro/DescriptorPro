"""Forced-alignment fallback (core/align.py), model-free pure parts."""

from __future__ import annotations

from core.align import _interpolate, _match_words, fill_words_from_hypothesis


def hyp(text: str, start: float = 0.0, per_word: float = 0.5):
    out = []
    t = start
    for w in text.split():
        out.append({"w": w, "s": round(t, 3), "e": round(t + per_word, 3), "p": 0.9})
        t += per_word
    return out


class TestMatchWords:
    def test_exact_match(self):
        hypothesis = hyp("hello there friend")
        matches = _match_words(["Hello", "there,", "friend."], hypothesis)
        assert all(m is not None for m in matches)
        assert matches[0]["s"] == 0.0

    def test_recognition_error_loses_only_its_word(self):
        hypothesis = hyp("hello their friend")  # middle word misheard
        matches = _match_words(["hello", "there", "friend"], hypothesis)
        assert matches[0] is not None
        assert matches[1] is None
        assert matches[2] is not None


class TestInterpolate:
    def test_fills_run_between_anchors(self):
        words = [
            {"w": "one", "s": 0.0, "e": 1.0, "p": 0.9},
            {"w": "two", "s": None, "e": None, "p": 0.7},
            {"w": "three", "s": 3.0, "e": 4.0, "p": 0.9},
        ]
        _interpolate(words, 0.0, 4.0)
        assert words[1]["s"] == 1.0
        assert words[1]["e"] == 3.0

    def test_all_unanchored_spreads_across_cue(self):
        words = [{"w": w, "s": None, "e": None, "p": 0.7} for w in ["a", "bb", "ccc"]]
        _interpolate(words, 10.0, 16.0)
        assert words[0]["s"] == 10.0
        assert words[-1]["e"] == 16.0
        # proportional by length: "ccc" gets half of the 6 seconds
        assert words[2]["e"] - words[2]["s"] == 3.0


class TestFillWords:
    def test_cue_words_filled_from_window(self):
        hypothesis = hyp("way before stuff", start=0.0) + hyp(
            "the actual cue text here", start=10.0
        )
        cue = {
            "id": "cap-0001",
            "start": 10.0,
            "end": 12.5,
            "text": "the actual cue text here",
            "words": [],
        }
        fill_words_from_hypothesis([cue], hypothesis)
        assert len(cue["words"]) == 5
        assert cue["words"][0]["s"] == 10.0
        assert all(w["s"] is not None for w in cue["words"])

    def test_unmatched_words_interpolated_not_dropped(self):
        hypothesis = hyp("completely different speech", start=5.0)
        cue = {"id": "c", "start": 5.0, "end": 6.5, "text": "what was said", "words": []}
        fill_words_from_hypothesis([cue], hypothesis)
        assert [w["w"] for w in cue["words"]] == ["what", "was", "said"]
        assert cue["words"][0]["s"] >= 5.0
        assert cue["words"][-1]["e"] <= 6.5
