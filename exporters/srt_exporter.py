"""SRT subtitle file exporter."""

from core.models import TranscriptModel
from utils.time_utils import seconds_to_srt_time


def export_srt(model: TranscriptModel, output_path: str, spanish: bool = False):
    """Export transcript as SRT subtitle file.

    Args:
        model: The transcript model with segments.
        output_path: Path to write the SRT file.
        spanish: If True, use Spanish text (text_es) where available.
    """
    lines = []
    for seg in model.segments:
        lines.append(str(seg.index))
        start = seconds_to_srt_time(seg.start_time)
        end = seconds_to_srt_time(seg.end_time)
        lines.append(f"{start} --> {end}")

        text = (seg.text_es if spanish and seg.text_es else seg.text)
        if seg.speaker:
            lines.append(f"[{seg.speaker}:]  {text}")
        else:
            lines.append(text)

        lines.append("")  # blank line between entries

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
