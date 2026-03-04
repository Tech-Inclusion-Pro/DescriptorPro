"""TranscriptSegment and TranscriptModel dataclasses."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class TranscriptSegment:
    index: int
    start_time: float        # seconds
    end_time: float          # seconds
    text: str                # transcribed text
    text_es: Optional[str] = None     # Spanish translation (if generated)
    speaker: Optional[str] = None     # Speaker label (if diarization run)
    cleaned: bool = False             # True if filler cleanup applied


@dataclass
class TranscriptModel:
    segments: list[TranscriptSegment] = field(default_factory=list)
    source_file: str = ""
    duration_seconds: float = 0.0
    language_detected: str = ""
    whisper_model_used: str = ""
    summary: Optional[str] = None    # Generated summary text (if requested)
    key_points: Optional[list[str]] = None
