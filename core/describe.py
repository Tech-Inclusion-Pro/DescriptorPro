"""Description drafting (spec §7.8) for segments a person marked
`describe`. The text model drafts from the uncovered facts under the DS
rules; guardrails flag every draft; gap fitting (core/gapfit.py) places it.

Model calls injected (generate_json(prompt) -> str). Qt-free.
"""

from __future__ import annotations

import json

from core.engine.config import DEFAULT_CONFIG
from core.gapfit import place_description, word_budget
from core.guardrails import check_text, known_names_from_intent
from core.prompts import render_prompt


def _uncovered_facts(segment: dict) -> list[dict]:
    need = segment.get("need") or {}
    by_id = {f["id"]: f for f in segment.get("visual_facts", [])}
    facts = [by_id[fid] for fid in need.get("uncovered_facts", []) if fid in by_id]
    # Essential-but-unchecked facts still matter when a person said
    # "describe" on an uncertain segment.
    if not facts:
        facts = [f for f in segment.get("visual_facts", []) if f.get("essential")]
    return facts


def draft_prompt(segment: dict, intent: dict, budget: int) -> str:
    facts = _uncovered_facts(segment)
    budget_line = (
        f"- The spoken description must fit about {budget} words. The \"short\" "
        "version MUST be within that budget; the \"full\" version may run longer."
        if budget > 0
        else "- There is no length limit for this description (extended style)."
    )
    return render_prompt(
        "describe",
        facts="\n".join(f"- {f['text']}" for f in facts) or "(none listed)",
        ocr_text="\n".join(f"- {line}" for line in segment.get("ocr_text") or []) or "(none)",
        transcript=segment.get("transcript_window") or "(nothing is said here)",
        audience=intent.get("audience") or "(not stated)",
        detail_level=intent.get("detail_level") or "concise",
        key_terms=", ".join(intent.get("key_terms") or []) or "(none)",
        word_budget=str(budget),
        budget_line=budget_line,
    )


def parse_draft(raw_json: str) -> tuple[str, str] | None:
    try:
        raw = json.loads(raw_json)
        full = str(raw.get("full") or "").strip()
        short = str(raw.get("short") or "").strip() or full
        return (full, short) if full else None
    except (json.JSONDecodeError, AttributeError, TypeError):
        return None


def draft_description(
    segment: dict,
    intent: dict,
    gaps: list[dict],
    ad_style: str,
    index: int,
    generate_json,
    language: str = "en",
) -> dict | None:
    """Returns a DescriptionCue dict (spec §4), or None when the segment
    has nothing to describe. Flags: guardrails + gap-fit, DS criteria ids
    attached per flag type."""
    facts = _uncovered_facts(segment)
    if not facts:
        return None

    candidates = [g for g in gaps if g["start"] >= segment["start"] - 1e-9]
    budget = word_budget(candidates[0]["length"]) if candidates and ad_style != "extended_before_content" else 0

    prompt = draft_prompt(segment, intent, budget)
    parsed = parse_draft(generate_json(prompt))
    if parsed is None:
        parsed = parse_draft(generate_json(prompt))  # one retry on garble
    if parsed is None:
        return None
    full, short = parsed

    placed = place_description(segment, full, short, gaps, ad_style)

    names = known_names_from_intent(intent, segment.get("ocr_text"))
    flags = placed["flags"] + check_text(placed["text"], known_names=names)

    criteria = sorted({ds for flag in flags for ds in _FLAG_CRITERIA.get(flag["type"], [])})
    cue = {
        "id": f"ad-{index:04d}",
        "segment": segment["id"],
        "start": placed["start"],
        "gap": placed["gap"],
        "text": placed["text"],
        "full_text": full,
        "short_text": short,
        "est_duration": placed["est_duration"],
        "mode": placed["mode"],
        "placement": placed["placement"],
        "voice": {"kind": "synthetic", "clip": None},
        "flags": flags,
        "criteria": criteria,
        "status": "draft",
        "approved_by": None,
        "approved_at": None,
        "lang": language,
    }
    return cue


# Flag type -> description standard ids (standards/description_criteria.json
# carries the same mapping in each criterion's flag_types; keep in sync).
_FLAG_CRITERIA: dict[str, list[str]] = {
    "nonessential_detail": ["DS-1"],
    "interpretation": ["DS-2"],
    "unverified_claim": ["DS-3"],
    "contradicted": ["DS-3"],
    "too_long_for_gap": ["DS-4"],
    "shortened_for_gap": ["DS-4"],
    "identity_inference": ["DS-6"],
    "name_from_user": ["DS-6"],
    "name_from_screen": ["DS-6"],
    "camera_language": ["DS-2"],
}


def criteria_for_flag(flag_type: str) -> list[str]:
    return _FLAG_CRITERIA.get(flag_type, [])
