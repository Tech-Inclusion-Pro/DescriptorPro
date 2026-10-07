"""DCMP Captioning Key / FCC caption formatting (spec §4, limits in
`core/engine/config.py:CaptionLimits`).

Takes the raw cues a speech backend drafts (sentence-sized, with word
timestamps) and reshapes them to broadcast form: at most `max_lines` lines of
`max_chars_per_line` characters, split at linguistically sensible points
(after sentence punctuation, then clause punctuation, then the longest pause
between words), minimum on-screen time, and a `reading_rate` flag when a cue
asks viewers to read faster than `max_reading_rate_wpm`.

Pure functions, no model access: formatting must be testable without audio.
Cues whose backend returned no word timestamps are wrapped but never split —
there is no honest way to time the pieces (forced alignment, `core/align.py`,
exists to give those cues words first).
"""

from __future__ import annotations

import re

from core.engine.config import CaptionLimits

_SENTENCE_END = re.compile(r"[.!?…]['\"”’)]*$")
_CLAUSE_END = re.compile(r"[,;:]['\"”’)]*$")


def wrap_lines(text: str, max_chars: int) -> list[str]:
    """Greedy word wrap. A single word longer than max_chars gets its own
    line unbroken — captions never hyphenate mid-word."""
    lines: list[str] = []
    current = ""
    for word in text.split():
        candidate = f"{current} {word}".strip()
        if current and len(candidate) > max_chars:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines


def _fits(words: list[dict], limits: CaptionLimits) -> bool:
    text = " ".join(w["w"] for w in words)
    lines = wrap_lines(text, limits.max_chars_per_line)
    return len(lines) <= limits.max_lines and all(
        len(line) <= limits.max_chars_per_line for line in lines
    )


def _break_score(words: list[dict], index: int) -> float:
    """Score a split AFTER words[index]. Higher is better."""
    word = words[index]["w"]
    score = 0.0
    if _SENTENCE_END.search(word):
        score += 100.0
    elif _CLAUSE_END.search(word):
        score += 50.0
    if index + 1 < len(words):
        gap = max(0.0, words[index + 1]["s"] - words[index]["e"])
        score += min(gap, 2.0) * 10.0
    return score


def _split_words(words: list[dict], limits: CaptionLimits) -> list[list[dict]]:
    """Split a word list into chunks that each fit max_lines × max_chars,
    preferring sentence ends, then clause ends, then the longest pause."""
    if _fits(words, limits):
        return [words]

    # Furthest prefix that still fits, then the best break point inside it.
    # Punctuation and pauses outrank the small keep-chunks-full bonus, so a
    # sentence end early in the prefix still wins over a mid-clause split.
    hi = 1
    while hi < len(words) and _fits(words[: hi + 1], limits):
        hi += 1
    best = hi - 1
    best_score = -1.0
    for i in range(hi):
        score = _break_score(words, i) + (i + 1) / hi * 10.0
        if score >= best_score:  # ties go to the later (more balanced) split
            best_score = score
            best = i
    head, tail = words[: best + 1], words[best + 1 :]
    return [head] + _split_words(tail, limits)


def _word_flags(words: list[dict], text: str, limits: CaptionLimits) -> list[dict]:
    flags = []
    for word in words:
        w = word["w"]
        if w and word.get("p", 1.0) < limits.low_confidence_threshold:
            start_ix = text.find(w)
            flags.append(
                {
                    "type": "low_confidence",
                    "detail": w,
                    "span": [start_ix, start_ix + len(w)] if start_ix >= 0 else None,
                }
            )
    return flags


def _reading_rate_wpm(word_count: int, duration: float) -> float:
    if duration <= 0:
        return 0.0
    return word_count * 60.0 / duration


def format_cues(cues: list[dict], limits: CaptionLimits) -> list[dict]:
    """Reshape backend cues to DCMP form. Returns new cue dicts, renumbered,
    text as newline-joined display lines. Draft-only input: callers run this
    before anyone reviews, never on approved text."""
    shaped: list[dict] = []

    for cue in cues:
        words = cue.get("words") or []
        if not words:
            # No timings: wrap for display, flag if it cannot fit the grid.
            lines = wrap_lines(cue["text"], limits.max_chars_per_line)
            flags = list(cue.get("flags", []))
            if len(lines) > limits.max_lines:
                flags.append(
                    {
                        "type": "needs_split",
                        "detail": "No word timings; text longer than the caption grid.",
                        "span": None,
                    }
                )
            shaped.append({**cue, "text": "\n".join(lines), "flags": flags})
            continue

        for chunk in _split_words(words, limits):
            text = "\n".join(
                wrap_lines(" ".join(w["w"] for w in chunk), limits.max_chars_per_line)
            )
            start = round(chunk[0]["s"], 3)
            end = round(chunk[-1]["e"], 3)
            flags = _word_flags(chunk, text, limits)
            rate = _reading_rate_wpm(len(chunk), end - start)
            if rate > limits.max_reading_rate_wpm:
                flags.append(
                    {
                        "type": "reading_rate",
                        "detail": f"{rate:.0f} words per minute",
                        "span": None,
                    }
                )
            shaped.append(
                {
                    **cue,
                    "start": start,
                    "end": end,
                    "text": text,
                    "words": chunk,
                    "flags": flags,
                }
            )

    # Minimum on-screen time: extend short cues into the following silence
    # when there is room; never overlap the next cue.
    for i, cue in enumerate(shaped):
        short_by = limits.min_cue_seconds - (cue["end"] - cue["start"])
        if short_by <= 0:
            continue
        limit = shaped[i + 1]["start"] - 0.08 if i + 1 < len(shaped) else None
        target = cue["start"] + limits.min_cue_seconds
        cue["end"] = round(min(target, limit) if limit is not None else target, 3)

    for index, cue in enumerate(shaped, start=1):
        cue["id"] = f"cap-{index:04d}"
    return shaped
