"""Need check (spec §7.6): does this video need audio description, and
where? Applies the W3C rule — if all important information in the video
track is already in the audio track, no additional audio description is
necessary (Understanding SC 1.2.5) — per segment, and reports. The person
decides; there is never a whole-video "exempt" verdict.

Model calls are injected (generate_json(prompt) -> str) so the logic tests
without Ollama. OCR text first tries a direct fuzzy match against the
transcript; only unmatched facts cost a model question.
"""

from __future__ import annotations

import json
import re
import unicodedata
from difflib import SequenceMatcher

from core.engine.config import DEFAULT_CONFIG, NeedCheckConfig
from core.prompts import render_prompt

# Standards shown with every report (spec §7.6: report, not legal advice).
STANDARDS_CHECKED = [
    "WCAG 2.1/2.2: 1.2.3 (A), 1.2.5 (AA), 1.2.7 (AAA), 1.2.8 (AAA)",
    "Section 508 (incorporates WCAG 2.0 AA)",
    "ADA Title II web rule (WCAG 2.1 AA)",
    "EN 301 549 (WCAG 2.1 AA)",
    "DCMP Description Key",
]


def _fold(text: str) -> str:
    text = unicodedata.normalize("NFD", text.lower())
    return "".join(ch for ch in text if unicodedata.category(ch) != "Mn")


def transcript_window(cues: list[dict], start: float, end: float, pad: float) -> str:
    """Spoken words for [start-pad, end+pad], from caption cues."""
    parts = [
        c["text"].replace("\n", " ")
        for c in cues
        if c.get("kind", "speech") == "speech"
        and c["end"] > start - pad
        and c["start"] < end + pad
    ]
    return " ".join(parts)


def ocr_covered_by_transcript(ocr_line: str, transcript: str, ratio: float) -> bool:
    """Direct fuzzy containment: does the transcript say this OCR text?
    Slides the OCR-sized word window over the transcript and keeps the best
    difflib ratio."""
    needle = _fold(re.sub(r"\s+", " ", ocr_line)).strip()
    hay_words = _fold(transcript).split()
    if not needle or not hay_words:
        return False
    n = max(len(needle.split()), 1)
    best = 0.0
    for i in range(0, max(len(hay_words) - n + 1, 1)):
        window = " ".join(hay_words[i : i + n + 2])
        best = max(best, SequenceMatcher(a=needle, b=window, autojunk=False).ratio())
        if best >= ratio:
            return True
    return False


def find_deictic(transcript: str, config: NeedCheckConfig | None = None) -> list[str]:
    config = config or DEFAULT_CONFIG.need_check
    folded = _fold(transcript)
    hits = []
    for phrase in config.deictic_en + config.deictic_es:
        if _fold(phrase) in folded:
            hits.append(phrase)
    return hits


def _ask_fact(fact_text: str, transcript: str, generate_json) -> dict:
    prompt = render_prompt("need_check_fact", fact=fact_text, transcript=transcript or "(nothing was said)")
    for attempt in range(2):  # one retry: thinking models occasionally reply empty
        try:
            raw = json.loads(generate_json(prompt))
            answer = raw.get("answer")
            if answer not in ("covered", "not_covered", "unsure"):
                answer = "unsure"
            return {"answer": answer, "evidence": str(raw.get("evidence") or "")}
        except (json.JSONDecodeError, TypeError):
            continue
    return {"answer": "unsure", "evidence": ""}


def check_segment(
    segment: dict,
    caption_cues: list[dict],
    generate_json,
    *,
    config: NeedCheckConfig | None = None,
    transcript_reliable: bool = True,
) -> dict:
    """Fills segment['need'] (verdict, reason, uncovered_facts, criteria)
    and returns it. Coach text is added separately (needs its own prompt).

    transcript_reliable=False (caller saw low-confidence captions in the
    window) forces at best an `uncertain` verdict, per spec §7.6.4.
    """
    config = config or DEFAULT_CONFIG.need_check
    transcript = transcript_window(
        caption_cues, segment["start"], segment["end"], config.transcript_pad_seconds
    )

    facts = [f for f in segment.get("visual_facts", []) if f.get("essential")]
    uncovered: list[str] = []
    any_unsure = False

    for fact in facts:
        # OCR-derived text facts: fuzzy match first, model only on a miss.
        if fact.get("kind") == "text" and ocr_covered_by_transcript(
            fact["text"], transcript, config.ocr_match_ratio
        ):
            fact["coverage"] = {"answer": "covered", "evidence": "matched in transcript"}
            continue
        result = _ask_fact(fact["text"], transcript, generate_json)
        fact["coverage"] = result
        if result["answer"] == "not_covered":
            uncovered.append(fact["id"])
        elif result["answer"] == "unsure":
            any_unsure = True

    if uncovered:
        verdict = "needed"
        reason = _reason_needed(segment, uncovered)
    elif any_unsure or not transcript_reliable or _has_unreadable_text(segment):
        verdict = "uncertain"
        reason = (
            "The speech in this part was hard to recognize, so coverage could not be confirmed."
            if not transcript_reliable
            else "It was not possible to confirm whether everything on screen was said aloud."
        )
    else:
        verdict = "not_needed"
        reason = (
            "Everything important on screen in this part is also said out loud."
            if facts
            else "Nothing essential appears on screen in this part."
        )

    criteria = ["WCAG-1.2.5"]
    segment["need"] = {
        "verdict": verdict,
        "reason": reason,
        "uncovered_facts": uncovered,
        "criteria": criteria,
        "deictic": find_deictic(transcript, config),
        "coach": None,
    }
    segment["transcript_window"] = transcript
    segment.setdefault("decision", {"value": "undecided", "by": None, "at": None})
    return segment["need"]


def _has_unreadable_text(segment: dict) -> bool:
    return any(f.get("kind") == "text" and f.get("unreadable") for f in segment.get("visual_facts", []))


def _reason_needed(segment: dict, uncovered: list[str]) -> str:
    by_id = {f["id"]: f for f in segment.get("visual_facts", [])}
    first = by_id.get(uncovered[0], {}).get("text", "information on screen")
    extra = f" (and {len(uncovered) - 1} more)" if len(uncovered) > 1 else ""
    return f"Shown but never said aloud: {first}{extra}"


def add_coach_suggestion(segment: dict, generate_json) -> None:
    """Spec §7.7: only for `needed` segments whose transcript points at the
    screen — the speaker could have said it aloud."""
    need = segment.get("need") or {}
    if need.get("verdict") != "needed" or not need.get("deictic"):
        return
    by_id = {f["id"]: f for f in segment.get("visual_facts", [])}
    uncovered_text = "\n".join(
        f"- {by_id[fid]['text']}" for fid in need["uncovered_facts"] if fid in by_id
    )
    prompt = render_prompt(
        "coach",
        deictic_phrases=", ".join(f'"{p}"' for p in need["deictic"]),
        uncovered_facts=uncovered_text,
        transcript=segment.get("transcript_window", ""),
    )
    try:
        raw = json.loads(generate_json(prompt))
        suggestion = str(raw.get("suggestion") or "").strip()
        if suggestion:
            need["coach"] = suggestion
    except (json.JSONDecodeError, TypeError):
        pass


def tally(segments: list[dict]) -> dict:
    counts = {"needed": 0, "not_needed": 0, "uncertain": 0, "unchecked": 0}
    for seg in segments:
        verdict = (seg.get("need") or {}).get("verdict")
        counts[verdict if verdict in counts else "unchecked"] += 1
    return counts
