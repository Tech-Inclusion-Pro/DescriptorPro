"""Caption exports from CaptionCue dicts (spec §4), WebVTT and SRT, each
carrying the plain-language provenance block (spec §11).

WebVTT carries provenance as a NOTE block. SRT has no comment syntax, so the
provenance travels as a sidecar text file next to the .srt. Nothing may hide
or remove the status line.
"""

from __future__ import annotations

from pathlib import Path

from utils.time_utils import seconds_to_srt_time, seconds_to_vtt_time


def provenance_lines(project: dict) -> list[str]:
    prov = project.get("provenance", {})
    cap = prov.get("captions", {})
    total = cap.get("cues", len(project.get("caption_cues", [])))
    approved = cap.get("approved", 0)
    reviewed = total > 0 and approved == total
    reviewer = ""
    if reviewed:
        names = {
            c.get("approved_by")
            for c in project.get("caption_cues", [])
            if c.get("approved_by")
        }
        reviewer = ", ".join(sorted(names))
    lines = [
        f"Captions: drafted by a speech model on this computer; "
        + (f"reviewed by {reviewer}." if reviewed else "NOT yet reviewed by a person."),
        "Cloud services used: none.",
        f"Status: {'reviewed' if reviewed else 'DRAFT. Not yet reviewed by a person.'}",
    ]
    return lines


def _cue_text(cue: dict) -> str:
    speaker = cue.get("speaker")
    return f"{speaker}: {cue['text']}" if speaker else cue["text"]


def export_cues_vtt(project: dict, output_path: str | Path) -> Path:
    path = Path(output_path)
    lines = ["WEBVTT", ""]
    lines.append("NOTE")
    lines.extend(provenance_lines(project))
    lines.append("")
    for cue in project.get("caption_cues", []):
        lines.append(cue["id"])
        lines.append(
            f"{seconds_to_vtt_time(cue['start'])} --> {seconds_to_vtt_time(cue['end'])}"
        )
        lines.append(_cue_text(cue))
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def export_cues_srt(project: dict, output_path: str | Path) -> Path:
    path = Path(output_path)
    lines: list[str] = []
    for index, cue in enumerate(project.get("caption_cues", []), start=1):
        lines.append(str(index))
        lines.append(
            f"{seconds_to_srt_time(cue['start'])} --> {seconds_to_srt_time(cue['end'])}"
        )
        lines.append(_cue_text(cue))
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")

    sidecar = path.with_suffix(".provenance.txt")
    sidecar.write_text("\n".join(provenance_lines(project)) + "\n", encoding="utf-8")
    return path
