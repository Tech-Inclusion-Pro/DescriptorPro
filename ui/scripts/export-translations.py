#!/usr/bin/env python3
"""Export core/translations.py into JSON files the UI can import.

Writes ui/src/i18n/generated/<lang>.core.json for every language the engine
supports (23 today). The UI ships en and es as first-class (hand-written keys
in ui/src/i18n/{en,es}.json); the generated files carry the shared engine
strings and, in Phase 7, the remaining 21 interface languages.

Run from the repo root:  .venv/bin/python ui/scripts/export-translations.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO))

from core.translations import TRANSLATIONS  # noqa: E402

OUT = REPO / "ui" / "src" / "i18n" / "generated"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for lang, entries in TRANSLATIONS.items():
        path = OUT / f"{lang}.core.json"
        path.write_text(json.dumps(entries, ensure_ascii=False, indent=2, sort_keys=True))
    print(f"Wrote {len(TRANSLATIONS)} language files to {OUT}")


if __name__ == "__main__":
    main()
