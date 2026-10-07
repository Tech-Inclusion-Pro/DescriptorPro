"""Gap fitting for audio description (spec §7.10, DS-4).

Gaps come from the caption word timestamps: any silence between consecutive
words longer than `min_gap_seconds`, trimmed by a guard on each side so
description never clips speech. Spoken length is estimated from word count
at `speech_rate_wpm` (a measured synthesis length replaces the estimate in
Phase 4 when Kokoro arrives).

Placement rules: the nearest gap at or after the visual, never before it —
except the extended_before_content style, which puts every description at
the segment start, extended, so a blind viewer gets the information when
their classmates do (DS-7). Description is never placed over speech
automatically (DS-4).

Pure functions, no models.
"""

from __future__ import annotations

from core.engine.config import DEFAULT_CONFIG, GapLimits


def build_gap_list(caption_cues: list[dict], duration: float, config: GapLimits | None = None) -> list[dict]:
    """[{start, end, length}] of usable silences, guard already applied."""
    config = config or DEFAULT_CONFIG.gaps
    words = sorted(
        (w for c in caption_cues for w in c.get("words") or []),
        key=lambda w: w["s"],
    )
    edges: list[tuple[float, float]] = []
    cursor = 0.0
    for word in words:
        if word["s"] - cursor >= config.min_gap_seconds:
            edges.append((cursor, word["s"]))
        cursor = max(cursor, word["e"])
    if duration - cursor >= config.min_gap_seconds:
        edges.append((cursor, duration))

    gaps = []
    for start, end in edges:
        usable_start = start + (config.gap_guard_seconds if start > 0 else 0.0)
        usable_end = end - config.gap_guard_seconds
        if usable_end - usable_start >= config.min_gap_seconds - 2 * config.gap_guard_seconds:
            gaps.append(
                {
                    "start": round(usable_start, 3),
                    "end": round(usable_end, 3),
                    "length": round(usable_end - usable_start, 3),
                }
            )
    return gaps


def estimate_duration(text: str, config: GapLimits | None = None) -> float:
    config = config or DEFAULT_CONFIG.gaps
    words = len(text.split())
    return round(words * 60.0 / config.speech_rate_wpm, 2)


def word_budget(gap_length: float, config: GapLimits | None = None) -> int:
    """How many words fit a gap at the configured speaking rate."""
    config = config or DEFAULT_CONFIG.gaps
    return max(int(gap_length * config.speech_rate_wpm / 60.0), 0)


def place_description(
    segment: dict,
    text: str,
    short_text: str | None,
    gaps: list[dict],
    ad_style: str,
    config: GapLimits | None = None,
) -> dict:
    """Returns placement for one description:
    {start, gap, mode, placement, text, est_duration, flags}.

    ad_style: standard | extended_when_needed | extended_before_content.
    """
    config = config or DEFAULT_CONFIG.gaps

    if ad_style == "extended_before_content":
        return {
            "start": segment["start"],
            "gap": 0.0,
            "mode": "extended",
            "placement": "before_content",
            "text": text,
            "est_duration": estimate_duration(text, config),
            "flags": [],
        }

    candidates = [g for g in gaps if g["start"] >= segment["start"] - 1e-9]
    est = estimate_duration(text, config)
    for gap in candidates:
        if est <= gap["length"]:
            return {
                "start": gap["start"],
                "gap": gap["length"],
                "mode": "inline",
                "placement": "in_gap",
                "text": text,
                "est_duration": est,
                "flags": [],
            }

    # Full version fits nowhere. Try the short version in the same gaps.
    if short_text:
        short_est = estimate_duration(short_text, config)
        for gap in candidates:
            if short_est <= gap["length"]:
                return {
                    "start": gap["start"],
                    "gap": gap["length"],
                    "mode": "inline",
                    "placement": "in_gap",
                    "text": short_text,
                    "est_duration": short_est,
                    "flags": [
                        {
                            "type": "shortened_for_gap",
                            "detail": "The full version did not fit; the cut version is placed. Both are kept for review.",
                            "span": None,
                        }
                    ],
                }

    # Nothing fits inline.
    anchor = candidates[0] if candidates else None
    start = anchor["start"] if anchor else segment["start"]
    gap_len = anchor["length"] if anchor else 0.0
    if ad_style == "extended_when_needed":
        return {
            "start": start,
            "gap": gap_len,
            "mode": "extended",
            "placement": "in_gap",
            "text": text,
            "est_duration": est,
            "flags": [],
        }
    return {
        "start": start,
        "gap": gap_len,
        "mode": "inline",
        "placement": "in_gap",
        "text": text,
        "est_duration": est,
        "flags": [
            {
                "type": "too_long_for_gap",
                "detail": f"Needs about {est:.0f} s; the nearest pause holds {gap_len:.0f} s. "
                "Consider the extended style or the described transcript.",
                "span": None,
            }
        ],
    }


def added_running_time(cues: list[dict]) -> float:
    """Seconds of pause the extended cues add (spec §7.10.6 — the user
    sees the cost)."""
    return round(sum(c["est_duration"] for c in cues if c.get("mode") == "extended"), 2)
