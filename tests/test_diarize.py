"""Speaker assignment logic (core/diarize.py), model-free parts."""

from __future__ import annotations

from core.diarize import assign_speakers


def cue(start: float, end: float, speaker=None):
    return {"id": "c", "start": start, "end": end, "speaker": speaker, "text": "x"}


class TestAssignSpeakers:
    def test_two_speakers_assigned_by_overlap(self):
        cues = [cue(0.0, 2.0), cue(2.5, 4.0)]
        turns = [
            {"start": 0.0, "end": 2.2, "speaker": "Speaker 1"},
            {"start": 2.2, "end": 5.0, "speaker": "Speaker 2"},
        ]
        count = assign_speakers(cues, turns)
        assert count == 2
        assert cues[0]["speaker"] == "Speaker 1"
        assert cues[1]["speaker"] == "Speaker 2"

    def test_single_speaker_clears_labels(self):
        cues = [cue(0.0, 2.0, speaker="Speaker 1")]
        turns = [{"start": 0.0, "end": 5.0, "speaker": "Speaker 1"}]
        assert assign_speakers(cues, turns) == 1
        assert cues[0]["speaker"] is None

    def test_no_turns_clears_labels(self):
        cues = [cue(0.0, 2.0, speaker="Old")]
        assert assign_speakers(cues, []) == 0
        assert cues[0]["speaker"] is None

    def test_cue_overlapping_both_takes_larger_share(self):
        cues = [cue(1.0, 4.0)]
        turns = [
            {"start": 0.0, "end": 2.0, "speaker": "Speaker 1"},  # 1 s overlap
            {"start": 2.0, "end": 6.0, "speaker": "Speaker 2"},  # 2 s overlap
        ]
        assign_speakers(cues, turns)
        assert cues[0]["speaker"] == "Speaker 2"

    def test_cue_in_silence_gets_no_label(self):
        cues = [cue(10.0, 11.0)]
        turns = [
            {"start": 0.0, "end": 2.0, "speaker": "Speaker 1"},
            {"start": 2.0, "end": 4.0, "speaker": "Speaker 2"},
        ]
        assign_speakers(cues, turns)
        assert cues[0]["speaker"] is None
