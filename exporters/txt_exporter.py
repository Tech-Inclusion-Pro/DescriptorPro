"""Plain text transcript exporter."""

import os
from datetime import date

from core.models import TranscriptModel
from utils.time_utils import seconds_to_display_time


def export_txt(model: TranscriptModel, output_path: str, spanish: bool = False):
    """Export transcript as plain text file.

    Args:
        model: The transcript model with segments.
        output_path: Path to write the TXT file.
        spanish: If True, use Spanish text (text_es) where available.
    """
    source_name = os.path.basename(model.source_file) if model.source_file else "Unknown"
    today = date.today().strftime("%Y-%m-%d")

    lines = [
        "La Mia Scribe Transcript",
        f"File: {source_name} | Date: {today} | Model: {model.whisper_model_used}",
        "",
    ]

    # Summary section if available
    if model.summary:
        lines.append("SUMMARY:")
        lines.append(model.summary)
        lines.append("")

    if model.key_points:
        lines.append("KEY POINTS:")
        for point in model.key_points:
            lines.append(f"  - {point}")
        lines.append("")

    lines.append("TRANSCRIPT:")
    lines.append("")

    for seg in model.segments:
        start = seconds_to_display_time(seg.start_time)
        end = seconds_to_display_time(seg.end_time)
        text = (seg.text_es if spanish and seg.text_es else seg.text)

        if seg.speaker:
            lines.append(f"[{start} \u2192 {end}]  {seg.speaker}:  {text}")
        else:
            lines.append(f"[{start} \u2192 {end}]  {text}")

        lines.append("")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
