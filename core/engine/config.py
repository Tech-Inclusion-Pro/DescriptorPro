"""One configuration object for pipeline limits and thresholds (spec §7.3, §7.10).

Values become user-visible settings later; stages must read them from here so
there is a single place to tune and to show in the UI.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class CaptionLimits:
    """DCMP Captioning Key / FCC-derived caption formatting limits."""

    max_lines: int = 2
    max_chars_per_line: int = 32
    min_cue_seconds: float = 1.0
    max_reading_rate_wpm: int = 180
    low_confidence_threshold: float = 0.6


@dataclass(frozen=True)
class GapLimits:
    """Gap detection for audio description placement."""

    min_gap_seconds: float = 1.5
    gap_guard_seconds: float = 0.15
    speech_rate_wpm: int = 160


@dataclass(frozen=True)
class EngineConfig:
    captions: CaptionLimits = field(default_factory=CaptionLimits)
    gaps: GapLimits = field(default_factory=GapLimits)
    transcript_window_pad_seconds: float = 3.0


DEFAULT_CONFIG = EngineConfig()
