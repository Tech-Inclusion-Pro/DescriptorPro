"""Described-video placement math (core/engine/render_video.plan_render)."""

from __future__ import annotations

from core.engine.render_video import plan_render


def cue(start, mode="inline", clip=3.0):
    return {"start": start, "mode": mode, "clip_duration": clip, "est_duration": clip}


class TestPlanRender:
    def test_inline_only_single_program_segment(self):
        plan = plan_render([cue(4.0), cue(9.0)], duration=20.0)
        assert plan["segments"] == [{"kind": "program", "src_start": 0.0, "src_end": 20.0}]
        assert [n["out_start"] for n in plan["narration"]] == [4.0, 9.0]

    def test_extended_cue_inserts_freeze_and_shifts_later_cues(self):
        plan = plan_render([cue(8.0, mode="extended", clip=5.0), cue(12.0)], duration=20.0)
        kinds = [s["kind"] for s in plan["segments"]]
        assert kinds == ["program", "freeze", "program"]
        freeze = plan["segments"][1]
        assert freeze["at"] == 8.0 and freeze["length"] == 5.0
        # inline cue after the freeze is shifted by the freeze length
        starts = {n["wav_index"]: n["out_start"] for n in plan["narration"]}
        assert starts[0] == 8.0
        assert starts[1] == 17.0

    def test_two_freezes_accumulate_offset(self):
        plan = plan_render(
            [cue(5.0, "extended", 2.0), cue(10.0, "extended", 3.0), cue(15.0)],
            duration=20.0,
        )
        starts = {n["wav_index"]: n["out_start"] for n in plan["narration"]}
        assert starts[0] == 5.0
        assert starts[1] == 12.0  # 10 + first freeze (2)
        assert starts[2] == 20.0  # 15 + 2 + 3

    def test_extended_at_zero_before_content(self):
        plan = plan_render([cue(0.0, "extended", 4.0)], duration=10.0)
        assert plan["segments"][0] == {"kind": "freeze", "at": 0.0, "length": 4.0}
        assert plan["segments"][1]["src_start"] == 0.0
        assert plan["segments"][1]["src_end"] == 10.0

    def test_program_segments_cover_source_exactly_once(self):
        plan = plan_render(
            [cue(3.0, "extended", 2.0), cue(7.5, "extended", 1.0)], duration=12.0
        )
        program = [s for s in plan["segments"] if s["kind"] == "program"]
        assert program[0]["src_start"] == 0.0
        for a, b in zip(program, program[1:]):
            assert a["src_end"] <= b["src_start"]
        assert program[-1]["src_end"] == 12.0
