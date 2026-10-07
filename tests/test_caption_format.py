"""DCMP/FCC caption formatting (core/engine/caption_format.py)."""

from __future__ import annotations

from core.engine.caption_format import format_cues, wrap_lines
from core.engine.config import CaptionLimits

LIMITS = CaptionLimits()


def make_words(text: str, start: float = 0.0, per_word: float = 0.3, gap: float = 0.0):
    words = []
    t = start
    for w in text.split():
        words.append({"w": w, "s": round(t, 3), "e": round(t + per_word, 3), "p": 0.95})
        t += per_word + gap
    return words


def make_cue(text: str, words=None, **over):
    cue = {
        "id": "cap-0001",
        "start": words[0]["s"] if words else 0.0,
        "end": words[-1]["e"] if words else 2.0,
        "speaker": None,
        "text": text,
        "kind": "speech",
        "words": words or [],
        "flags": [],
        "status": "draft",
        "approved_by": None,
        "approved_at": None,
    }
    cue.update(over)
    return cue


class TestWrapLines:
    def test_short_text_single_line(self):
        assert wrap_lines("Hello there.", 32) == ["Hello there."]

    def test_wraps_at_limit_without_breaking_words(self):
        lines = wrap_lines("The quick brown fox jumps over the lazy sleeping dog", 32)
        assert all(len(line) <= 32 for line in lines)
        assert " ".join(lines) == "The quick brown fox jumps over the lazy sleeping dog"

    def test_overlong_word_gets_own_line_unbroken(self):
        lines = wrap_lines("see supercalifragilisticexpialidocious now", 32)
        assert "supercalifragilisticexpialidocious" in lines


class TestFormatCues:
    def test_short_cue_untouched_except_renumber(self):
        text = "Welcome to class."
        cues = format_cues([make_cue(text, make_words(text))], LIMITS)
        assert len(cues) == 1
        assert cues[0]["text"] == text
        assert cues[0]["id"] == "cap-0001"

    def test_two_line_cue_gets_newline(self):
        text = "Today we are going to talk about accessible documents"
        cues = format_cues([make_cue(text, make_words(text))], LIMITS)
        assert len(cues) == 1
        lines = cues[0]["text"].split("\n")
        assert len(lines) == 2
        assert all(len(line) <= 32 for line in lines)

    def test_long_cue_splits_into_multiple(self):
        text = (
            "This is a very long sentence that keeps going and going, "
            "and then it continues with a second thought that also runs long, "
            "and finally it ends after far too many words for one caption."
        )
        cues = format_cues([make_cue(text, make_words(text))], LIMITS)
        assert len(cues) >= 2
        for cue in cues:
            lines = cue["text"].split("\n")
            assert len(lines) <= 2
            assert all(len(line) <= 32 for line in lines)
        # IDs renumbered consecutively
        assert [c["id"] for c in cues] == [f"cap-{i:04d}" for i in range(1, len(cues) + 1)]

    def test_split_timing_comes_from_words(self):
        text = (
            "One two three four five six seven eight nine ten eleven twelve "
            "thirteen fourteen fifteen sixteen seventeen eighteen nineteen twenty"
        )
        words = make_words(text)
        cues = format_cues([make_cue(text, words)], LIMITS)
        assert len(cues) >= 2
        for a, b in zip(cues, cues[1:]):
            assert a["end"] <= b["start"] + 1e-9  # no overlap after split
        assert cues[0]["start"] == words[0]["s"]
        assert cues[-1]["end"] >= words[-1]["e"]  # may be extended for min time

    def test_prefers_sentence_break(self):
        text = "The lecture has ended. Now we will move on to the questions people sent in"
        cues = format_cues([make_cue(text, make_words(text))], LIMITS)
        assert cues[0]["text"].rstrip().endswith("ended.")

    def test_low_confidence_flag_recomputed_with_span(self):
        text = "Hello mumbled word"
        words = make_words(text)
        words[1]["p"] = 0.3
        cues = format_cues([make_cue(text, words)], LIMITS)
        flags = [f for f in cues[0]["flags"] if f["type"] == "low_confidence"]
        assert len(flags) == 1
        span = flags[0]["span"]
        assert cues[0]["text"][span[0] : span[1]] == "mumbled"

    def test_reading_rate_flag(self):
        # 12 words crammed into ~1.2 seconds -> about 600 wpm
        text = "a b c d e f g h i j k l"
        cues = format_cues([make_cue(text, make_words(text, per_word=0.1))], LIMITS)
        assert any(f["type"] == "reading_rate" for c in cues for f in c["flags"])

    def test_min_duration_extended_into_silence(self):
        first = make_cue("Hi.", make_words("Hi.", start=0.0, per_word=0.2))
        second = make_cue("Later words arrive.", make_words("Later words arrive.", start=10.0))
        cues = format_cues([first, second], LIMITS)
        assert cues[0]["end"] - cues[0]["start"] >= LIMITS.min_cue_seconds

    def test_min_duration_never_overlaps_next_cue(self):
        first = make_cue("Hi.", make_words("Hi.", start=0.0, per_word=0.2))
        second = make_cue("Quick follow.", make_words("Quick follow.", start=0.5))
        cues = format_cues([first, second], LIMITS)
        assert cues[0]["end"] < cues[1]["start"]

    def test_no_words_wrapped_not_split(self):
        text = (
            "This text came from a backend with no word timestamps so the "
            "formatter must not invent timing for pieces of it at all"
        )
        cues = format_cues([make_cue(text, None)], LIMITS)
        assert len(cues) == 1
        assert any(f["type"] == "needs_split" for f in cues[0]["flags"])

    def test_draft_status_and_cue_fields_preserved(self):
        text = "Keep the cue shape intact."
        cues = format_cues([make_cue(text, make_words(text))], LIMITS)
        cue = cues[0]
        for key in ("speaker", "kind", "status", "approved_by", "approved_at"):
            assert key in cue
        assert cue["status"] == "draft"
