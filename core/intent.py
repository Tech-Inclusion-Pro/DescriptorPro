"""Intent conversation → IntentProfile (spec §7.2).

The conversation itself lives in the UI (the six questions, one at a time,
each skippable). This module owns the fixed question list, the defaults for
a skipped conversation, and the conversion of answers into an editable
IntentProfile via the local text model. The profile — not the raw
conversation — drives later stages, and the user can edit every field.
"""

from __future__ import annotations

import json

from core.prompts import render_prompt

# Order and wording per spec §7.2. Keys are stable ids the UI posts back.
QUESTIONS: list[dict] = [
    {"id": "audience", "text": "Who is this for, and what do they need to get from it?"},
    {
        "id": "content_type",
        "text": "What kind of video is it?",
        "options": [
            "lecture_slides",
            "screen_recording",
            "demonstration",
            "narrative",
            "interview",
            "other",
        ],
    },
    {
        "id": "people",
        "text": "Are there people on screen I should name? I will not guess who anyone is.",
    },
    {"id": "detail_level", "text": "How much detail: short, or fuller?"},
    {"id": "languages", "text": "Which languages?"},
    {"id": "key_terms", "text": "Any terms or names I should spell a particular way?"},
]


def default_profile() -> dict:
    """Spec §7.2: the whole step can be skipped — concise, auto content
    type, no named people."""
    return {
        "audience": "",
        "purpose": "",
        "content_type": "other",
        "people": [],
        "detail_level": "concise",
        "languages": ["en"],
        "key_terms": [],
        "notes": "",
    }


_ALLOWED_CONTENT_TYPES = {
    "lecture_slides", "screen_recording", "demonstration",
    "narrative", "interview", "other",
}
_ALLOWED_DETAIL = {"concise", "standard", "detailed"}


def sanitize_profile(raw: dict) -> dict:
    """Clamp whatever the model (or a user edit) produced to the schema.
    People get source='user' — this path only ever carries user-supplied
    names (spec §7.5)."""
    profile = default_profile()
    profile["audience"] = str(raw.get("audience") or "")[:500]
    profile["purpose"] = str(raw.get("purpose") or "")[:500]
    if raw.get("content_type") in _ALLOWED_CONTENT_TYPES:
        profile["content_type"] = raw["content_type"]
    if raw.get("detail_level") in _ALLOWED_DETAIL:
        profile["detail_level"] = raw["detail_level"]
    people = []
    for person in raw.get("people") or []:
        label = str(person.get("label") or "").strip()
        if label:
            people.append(
                {
                    "label": label[:100],
                    "role": str(person.get("role") or "")[:100],
                    "self_description": person.get("self_description") or None,
                    "source": "user",
                }
            )
    profile["people"] = people
    profile["languages"] = [
        str(lang).strip().lower()[:8] for lang in (raw.get("languages") or ["en"]) if str(lang).strip()
    ] or ["en"]
    profile["key_terms"] = [str(t).strip()[:100] for t in (raw.get("key_terms") or []) if str(t).strip()]
    profile["notes"] = str(raw.get("notes") or "")[:2000]
    return profile


def profile_from_answers(answers: dict[str, str], generate_json) -> dict:
    """answers: question id → what the person said (skipped ids absent).
    generate_json(prompt) -> str is the text-model call, injected so tests
    run without Ollama."""
    if not any(str(v).strip() for v in answers.values()):
        return default_profile()

    conversation = "\n".join(
        f"Q: {q['text']}\nA: {answers[q['id']].strip()}"
        for q in QUESTIONS
        if str(answers.get(q["id"], "")).strip()
    )
    raw = json.loads(generate_json(render_prompt("intent_profile", conversation=conversation)))
    return sanitize_profile(raw)
