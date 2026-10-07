"""Structured visual facts from keyframes (spec §7.4.4) under the §7.5
guardrails. The vision model gets the keyframe image, the OCR text, and the
intent profile, and must return short checkable statements — never prose,
never identity guesses. `core/guardrails.py` re-checks every fact anyway;
violations become flags on the fact for the reviewer.

The model call is injected (generate_vision_json(prompt, image_path) ->
str) so logic tests run without Ollama.
"""

from __future__ import annotations

import json

from core.guardrails import check_text, known_names_from_intent
from core.prompts import render_prompt

_ALLOWED_KINDS = {"text", "diagram", "chart", "action", "person", "setting"}
MAX_FACTS_PER_SEGMENT = 8


def facts_prompt(segment: dict, intent: dict) -> str:
    ocr_lines = segment.get("ocr_text") or []
    return render_prompt(
        "visual_facts",
        ocr_text="\n".join(f"- {line}" for line in ocr_lines) or "(none found)",
        audience=intent.get("audience") or "(not stated)",
        purpose=intent.get("purpose") or "(not stated)",
        content_type=intent.get("content_type") or "other",
        key_terms=", ".join(intent.get("key_terms") or []) or "(none)",
    )


def parse_facts(raw_json: str, segment_id: str) -> list[dict]:
    try:
        raw = json.loads(raw_json)
        items = raw.get("facts") or []
    except (json.JSONDecodeError, AttributeError, TypeError):
        return []
    facts = []
    for i, item in enumerate(items[:MAX_FACTS_PER_SEGMENT]):
        text = str(item.get("text") or "").strip()
        if not text:
            continue
        kind = item.get("kind") if item.get("kind") in _ALLOWED_KINDS else "setting"
        facts.append(
            {
                "id": f"vf-{segment_id}-{i + 1}",
                "text": text[:300],
                "kind": kind,
                "essential": bool(item.get("essential", False)),
                "flags": [],
            }
        )
    return facts


def extract_segment_facts(
    segment: dict,
    intent: dict,
    generate_vision_json,
) -> list[dict]:
    """Fills segment['visual_facts'] from its first keyframe; guardrail
    flags attach to each fact. Returns the facts."""
    keyframes = segment.get("keyframes") or []
    if not keyframes:
        segment["visual_facts"] = []
        return []

    prompt = facts_prompt(segment, intent)
    facts = parse_facts(generate_vision_json(prompt, keyframes[0]), segment["id"])
    if not facts:
        # Thinking-model flakiness: an empty/garbled reply happens
        # occasionally (measured 2026-10-07); one retry recovers it.
        facts = parse_facts(generate_vision_json(prompt, keyframes[0]), segment["id"])

    names = known_names_from_intent(intent, segment.get("ocr_text"))
    filmmaking = "film" in (intent.get("purpose") or "").lower() or "film" in (
        intent.get("notes") or ""
    ).lower()
    for fact in facts:
        fact["flags"] = check_text(
            fact["text"], known_names=names, content_is_filmmaking=filmmaking
        )
    segment["visual_facts"] = facts
    return facts
