"""Described MP4 rendering (spec §8.2): narration mixed into the program,
program audio ducked under narration, loudness normalized, and the frame
frozen for the length of every extended cue.

Timeline model: extended cues insert a freeze — a held frame with the
program audio silent while the narration plays — which shifts everything
after them. Inline cues keep the original timeline and play over ducked
program audio. All placement math is pure (`plan_render`), so it is
testable without FFmpeg; `render_described_video` turns the plan into one
FFmpeg filter graph.

Audio per the ACB text-to-speech guidance: 48 kHz, ducking via
sidechaincompress keyed by the narration, single loudnorm pass on the
final mix.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from core.engine.extract_audio import _find_ffmpeg


def plan_render(description_cues: list[dict], duration: float) -> dict:
    """Pure placement math.

    Returns {segments, narration}:
    - segments: ordered video pieces, {kind: "program", src_start, src_end}
      or {kind: "freeze", at (source time), length}.
    - narration: [{wav_index, out_start}] — where each cue's clip starts on
      the OUTPUT timeline (freezes included).
    """
    cues = sorted(
        enumerate(description_cues),
        key=lambda pair: (pair[1]["start"], 0 if pair[1].get("mode") == "extended" else 1),
    )
    segments: list[dict] = []
    narration: list[dict] = []
    cursor = 0.0  # source time consumed
    offset = 0.0  # output time added by freezes

    for index, cue in cues:
        clip_len = float(cue.get("clip_duration") or cue.get("est_duration") or 2.0)
        start = min(max(float(cue["start"]), 0.0), duration)
        if cue.get("mode") == "extended":
            if start > cursor:
                segments.append({"kind": "program", "src_start": cursor, "src_end": start})
                cursor = start
            segments.append({"kind": "freeze", "at": start, "length": clip_len})
            narration.append({"wav_index": index, "out_start": round(start + offset, 3)})
            offset += clip_len
        else:
            narration.append({"wav_index": index, "out_start": round(start + offset, 3)})

    if cursor < duration:
        segments.append({"kind": "program", "src_start": cursor, "src_end": duration})
    return {"segments": segments, "narration": narration}


def render_described_video(
    source: str | Path,
    description_cues: list[dict],
    narration_wavs: list[str | Path],
    duration: float,
    output_path: str | Path,
) -> Path:
    """One FFmpeg invocation from the plan. narration_wavs[i] belongs to
    description_cues[i] (cue['clip_duration'] should hold its measured
    length)."""
    plan = plan_render(description_cues, duration)
    segments, narration = plan["segments"], plan["narration"]
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    inputs: list[str] = ["-i", str(source)]
    for wav in narration_wavs:
        inputs += ["-i", str(wav)]

    lines: list[str] = []
    video_parts: list[str] = []
    audio_parts: list[str] = []
    for i, seg in enumerate(segments):
        if seg["kind"] == "program":
            lines.append(
                f"[0:v]trim=start={seg['src_start']}:end={seg['src_end']},setpts=PTS-STARTPTS[v{i}];"
            )
            lines.append(
                f"[0:a]atrim=start={seg['src_start']}:end={seg['src_end']},asetpts=PTS-STARTPTS,"
                f"aresample=48000,aformat=channel_layouts=stereo[a{i}];"
            )
        else:  # freeze: hold the frame, program audio silent
            lines.append(
                f"[0:v]trim=start={seg['at']}:end={seg['at'] + 0.1},setpts=PTS-STARTPTS,"
                f"tpad=stop_mode=clone:stop_duration={max(seg['length'] - 0.1, 0.1)}[v{i}];"
            )
            lines.append(
                f"aevalsrc=0:d={seg['length']}:s=48000,aformat=channel_layouts=stereo[a{i}];"
            )
        video_parts.append(f"[v{i}]")
        audio_parts.append(f"[a{i}]")

    n = len(segments)
    lines.append(f"{''.join(video_parts)}concat=n={n}:v=1:a=0[vprog];")
    lines.append(f"{''.join(audio_parts)}concat=n={n}:v=0:a=1[aprog];")

    # Narration track: each clip delayed to its output start, then mixed.
    narr_parts = []
    for j, item in enumerate(narration):
        delay_ms = int(item["out_start"] * 1000)
        lines.append(
            f"[{item['wav_index'] + 1}:a]aresample=48000,aformat=channel_layouts=stereo,"
            f"adelay={delay_ms}|{delay_ms}[n{j}];"
        )
        narr_parts.append(f"[n{j}]")
    if narr_parts:
        lines.append(
            f"{''.join(narr_parts)}amix=inputs={len(narr_parts)}:normalize=0,"
            f"apad=whole_dur=0,asplit=2[narr][key];"
        )
        # Duck the program under the narration, then mix narration on top,
        # then one loudness-normalization pass over the result.
        lines.append(
            "[aprog][key]sidechaincompress=threshold=0.03:ratio=8:attack=20:release=300[ducked];"
        )
        lines.append("[ducked][narr]amix=inputs=2:normalize=0,loudnorm=I=-19:TP=-2:LRA=11[aout]")
    else:
        lines.append("[aprog]loudnorm=I=-19:TP=-2:LRA=11[aout]")

    ffmpeg_bin = _find_ffmpeg()
    if not ffmpeg_bin:
        raise FileNotFoundError(
            "FFmpeg is not installed. Please install FFmpeg and add it to your PATH.\n"
            "Visit ffmpeg.org for instructions, or run: brew install ffmpeg"
        )

    filtergraph = "".join(lines)
    cmd = [
        ffmpeg_bin, "-y", "-loglevel", "error",
        *inputs,
        "-filter_complex", filtergraph,
        "-map", "[vprog]", "-map", "[aout]",
        "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
        str(out),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg failed rendering the described video: {result.stderr[-800:]}")
    return out
