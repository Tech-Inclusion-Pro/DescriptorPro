"""Verification pass (spec §7.9, DS-3): a second, separate model call per
draft. A blind viewer cannot check a description against the screen, so
the tool does — claim by claim, against the keyframe and the OCR text.

Rules enforced here:
- Quoted on-screen text in a draft must match the OCR text (fuzzy); a
  mismatch is an `unverified_claim` flag.
- `contradicted` claims are removed from the *suggested* text and recorded
  so the reviewer sees them struck out; the original draft is kept.
- `cannot_confirm` claims stay in the text and are flagged.
- A draft never loses a flag because a later pass disagreed; flags clear
  only when a person approves the cue.

Model call injected (generate_vision_json(prompt, image_path) -> str).
"""

from __future__ import annotations

import json
import re
from difflib import SequenceMatcher

from core.describe import criteria_for_flag
from core.prompts import render_prompt

_QUOTE_RE = re.compile(r"[\"“”'‘’]([^\"“”'‘’]{3,80})[\"“”'‘’]")
_QUOTE_MATCH_RATIO = 0.85


def parse_verdicts(raw_json: str) -> list[dict] | None:
    try:
        raw = json.loads(raw_json)
        claims = raw.get("claims")
        if not isinstance(claims, list):
            return None
    except (json.JSONDecodeError, AttributeError, TypeError):
        return None
    out = []
    for claim in claims:
        text = str(claim.get("text") or "").strip()
        verdict = claim.get("verdict")
        if text and verdict in ("supported", "contradicted", "cannot_confirm"):
            out.append({"text": text, "verdict": verdict})
    return out or None


def check_quotes(draft: str, ocr_lines: list[str]) -> list[dict]:
    """Quoted text in the draft must appear in the OCR text (DS-3)."""
    flags = []
    haystack = " ".join(ocr_lines).lower()
    for quoted in _QUOTE_RE.findall(draft):
        needle = quoted.lower().strip()
        if not needle:
            continue
        matched = needle in haystack or any(
            SequenceMatcher(a=needle, b=line.lower(), autojunk=False).ratio() >= _QUOTE_MATCH_RATIO
            for line in ocr_lines
        )
        if not matched:
            flags.append(
                {
                    "type": "unverified_claim",
                    "detail": quoted,
                    "span": None,
                }
            )
    return flags


def _strike_claims(text: str, contradicted: list[str]) -> str:
    """Remove contradicted claims from the suggested text, sentence-wise."""
    sentences = re.split(r"(?<=[.!?])\s+", text)
    kept = []
    for sentence in sentences:
        if any(
            SequenceMatcher(a=sentence.lower(), b=claim.lower(), autojunk=False).ratio() > 0.6
            or claim.lower() in sentence.lower()
            for claim in contradicted
        ):
            continue
        kept.append(sentence)
    return " ".join(kept).strip()


def verify_description(
    cue: dict,
    segment: dict,
    generate_vision_json,
) -> None:
    """Mutates the cue: adds verification flags, `verification` record, and
    `suggested_text` with contradicted claims removed. Existing flags are
    never removed (spec: only a person clears flags)."""
    keyframes = segment.get("keyframes") or []
    ocr_lines = segment.get("ocr_text") or []

    flags = list(cue.get("flags", []))
    flags += check_quotes(cue["text"], ocr_lines)

    verdicts: list[dict] | None = None
    if keyframes:
        prompt = render_prompt(
            "verify_claims",
            draft=cue["text"],
            ocr_text="\n".join(f"- {line}" for line in ocr_lines) or "(none)",
        )
        verdicts = parse_verdicts(generate_vision_json(prompt, keyframes[0]))
        if verdicts is None:
            verdicts = parse_verdicts(generate_vision_json(prompt, keyframes[0]))

    if verdicts is None:
        # Could not verify at all: the whole draft is unconfirmed.
        flags.append(
            {
                "type": "unverified_claim",
                "detail": "The verification pass could not check this draft. Review it against the video.",
                "span": None,
            }
        )
        cue["flags"] = flags
        _refresh_criteria(cue)
        cue["verification"] = {"checked": False, "claims": []}
        cue["suggested_text"] = cue["text"]
        return

    contradicted = [v["text"] for v in verdicts if v["verdict"] == "contradicted"]
    for verdict in verdicts:
        if verdict["verdict"] == "contradicted":
            flags.append({"type": "contradicted", "detail": verdict["text"], "span": None})
        elif verdict["verdict"] == "cannot_confirm":
            flags.append({"type": "unverified_claim", "detail": verdict["text"], "span": None})

    cue["flags"] = flags
    _refresh_criteria(cue)
    cue["verification"] = {"checked": True, "claims": verdicts}
    cue["suggested_text"] = (
        _strike_claims(cue["text"], contradicted) if contradicted else cue["text"]
    )


def _refresh_criteria(cue: dict) -> None:
    """Flags gained in verification carry their standard ids too (every
    flag links to its standard — Phase 3 acceptance)."""
    cue["criteria"] = sorted(
        set(cue.get("criteria", []))
        | {ds for flag in cue["flags"] for ds in criteria_for_flag(flag["type"])}
    )
