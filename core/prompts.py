"""Versioned prompt loader (spec: prompts live in prompts/, versioned in the
file header, never inline in code).

Rendering replaces {name} tokens by explicit replacement — not str.format —
because prompts legitimately contain literal JSON braces.
"""

from __future__ import annotations

from pathlib import Path

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"


def load_prompt(name: str) -> str:
    """Prompt text with the `# `-comment header stripped."""
    text = (PROMPTS_DIR / f"{name}.txt").read_text(encoding="utf-8")
    lines = text.splitlines()
    body_start = 0
    for i, line in enumerate(lines):
        if not line.startswith("#"):
            body_start = i
            break
    return "\n".join(lines[body_start:]).strip()


def render_prompt(name: str, **values: str) -> str:
    text = load_prompt(name)
    for key, value in values.items():
        text = text.replace("{" + key + "}", str(value))
    return text
