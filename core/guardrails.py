"""Identity and objectivity guardrails (spec §7.5), rule-based layer.

Two enforcement points share these rules: the prompts (core/vision, later
core/describe) *instruct* the model, and this checker *verifies* every piece
of model text anyway — prompt compliance is hoped for, checker compliance is
guaranteed. A match raises a flag for the reviewer; nothing is silently
rewritten and nothing is censored (spec: flag the uncomfortable, never omit
it).

Name policy: names appear only when supplied by the user (intent profile /
review) or read from on-screen text. `name_flags` records the source of
every known name so the reviewer can see where each came from.
"""

from __future__ import annotations

import re
import unicodedata

from core.engine.config import DEFAULT_CONFIG, GuardrailsConfig


def _fold(text: str) -> str:
    """Lowercase + strip accents so 'Enojado' matches 'enojado'."""
    text = unicodedata.normalize("NFD", text.lower())
    return "".join(ch for ch in text if unicodedata.category(ch) != "Mn")


def _find_terms(text: str, terms: tuple[str, ...]) -> list[str]:
    folded = _fold(text)
    hits = []
    for term in terms:
        if re.search(rf"(?<!\w){re.escape(_fold(term))}(?!\w)", folded):
            hits.append(term)
    return hits


def check_text(
    text: str,
    *,
    known_names: dict[str, str] | None = None,
    content_is_filmmaking: bool = False,
    config: GuardrailsConfig | None = None,
) -> list[dict]:
    """Returns flag dicts for one piece of model-produced text.

    known_names maps a name to its source: "user" | "screen". Names found in
    the text produce a name_from_user / name_from_screen flag (information
    for the reviewer, not a violation). Everything else is a violation flag.
    """
    config = config or DEFAULT_CONFIG.guardrails
    flags: list[dict] = []

    for term in _find_terms(text, config.identity_terms):
        flags.append(
            {
                "type": "identity_inference",
                "detail": term,
                "span": None,
            }
        )
    for term in _find_terms(text, config.interpretation_terms):
        flags.append({"type": "interpretation", "detail": term, "span": None})
    if not content_is_filmmaking:
        for term in _find_terms(text, config.camera_terms):
            flags.append({"type": "camera_language", "detail": term, "span": None})

    for name, source in (known_names or {}).items():
        if name and re.search(rf"(?<!\w){re.escape(_fold(name))}(?!\w)", _fold(text)):
            flags.append(
                {
                    "type": "name_from_user" if source == "user" else "name_from_screen",
                    "detail": name,
                    "span": None,
                }
            )
    return flags


# Capitalized words that appear in slide headings, not in people's names.
# A candidate OCR line containing any of these is a title, not a name card
# (measured 2026-10-07: without this, every Title Case heading on a slide
# deck raised a name_from_screen flag).
_HEADING_WORDS = frozenset(
    """document documents accessible accessibility review checklist overview
    introduction summary agenda objectives outcomes checklist lesson module
    chapter unit week team roles goals plan notes questions resources
    references thank thanks welcome title slide special general educator
    educators teacher teachers student students parent parents guide
    guidelines key points steps part reading order text captions caption
    description descriptions""".split()
)


def known_names_from_intent(intent: dict | None, ocr_text: list[str] | None = None) -> dict[str, str]:
    """The only two legitimate name sources: the intent profile ("user") and
    on-screen text ("screen"). OCR lines are treated as potential name cards
    when they are short (a name card is not a paragraph)."""
    names: dict[str, str] = {}
    for line in ocr_text or []:
        line = line.strip()
        if not (0 < len(line) <= 40) or any(ch.isdigit() for ch in line):
            continue
        # A name card is two to five capitalized words — count only the
        # alphabetic words, so "- Headings" (one word plus a dash) is not
        # mistaken for a name.
        words = [w for w in re.split(r"[^\w']+", line) if w and w[:1].isalpha()]
        if (
            2 <= len(words) <= 5
            and all(w[:1].isupper() for w in words)
            and not any(w.lower() in _HEADING_WORDS for w in words)
        ):
            names[" ".join(words)] = "screen"
    for person in (intent or {}).get("people", []):
        label = (person.get("label") or "").strip()
        if label:
            names[label] = "user"  # intent wins over screen for the same name
    return names
