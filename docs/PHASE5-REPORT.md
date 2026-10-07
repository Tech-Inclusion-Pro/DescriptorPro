# Phase 5 report — Image and slide description (code-complete 2026-10-07)

Image description mode is built and verified live: 178 pytest + 5 vitest
green, and three real slides ran the whole chain — ingest → OCR →
Qwen3-VL description → guardrails — producing alts all under 150
characters, sensible long descriptions, correct kinds, zero identity or
interpretation violations, and no decorative false-positives.

## What was built

**Ingest** (`core/images.py`): a batch of image files or a PDF slide deck
(rendered page by page with pypdfium2 — chosen over the usual PyMuPDF
because PyMuPDF is AGPL and would contaminate the MIT app).
PowerPoint/Keynote files are rejected at upload with plain guidance:
export the deck to PDF first.

**Description** (`describe_image` + `prompts/image_description.txt`,
spec §7.11): per image — alt under ~150 characters (over-length draws an
`alt_too_long` flag), optional long description, kind
(photo/slide/chart/diagram/…), and a **decorative suggestion with a
reason**. The suggestion is only ever a suggestion: `confirmed` starts
null, only a person sets it, and **approval is blocked until the person
decides** — the route refuses with "the tool never decides it alone."

**Chart honesty**: the prompt allows numbers and labels only from OCR, and
a post-check flags any digits in the description that OCR never read
(`unsourced_numbers` — tested: "the left bar is more than twice as tall"
passes, an invented "72%" is flagged). The §7.5 identity guardrails run on
every description.

**Batch review** (ReviewPane): per-image editable alt (with live character
count), long description, the decorative question as an explicit
yes/no the reviewer must answer, plain-language flags, approve-with-name.
MediaPane gained an "Images or slides" uploader that also works with no
existing project (the first file becomes the project source; nothing
transcribes).

**Exports** (`exporters/image_exporter.py` + Export pane): CSV, JSON, and
a DOCX list. Decorative status exports exactly as decided — "suggested
decorative — NOT confirmed" until a person rules, and the provenance
block rides every format.

**Job** (`describe_images`): resumable per image (saves after each one),
vision model under the model manager, skips already-described images
unless forced.

## Fixes found by the live run

- `ingest_images` hardcoded its relative path prefix; now derived from
  the actual images directory.
- The screen-name heuristic flagged Title Case slide headings
  ("Accessible Documents") as name cards — every slide deck would have
  drowned reviewers in `name_from_screen` flags. A heading-word stoplist
  fixes it, with a regression test; real names ("Maria Lopez") still
  detect.

## Verified vs not

Verified live: full chain on three real slides (results above); PDF
page-rendering in tests; decorative-blocks-approval rule; 178 pytest + 5
vitest; UI rebuilt for the installed app.

Not verified (needs Rocco): real photographs and real charts (synthetic
slides only — the chart number-honesty check is unit-tested but hasn't
seen a real chart through the vision model); VoiceOver pass over the
batch review table; the gold set and earlier phases' human checks, still
open.

## Next

Phase 6 (live captions + slide announcer) or Phase 7 (Spanish parity,
cloud BYOK, packaging) — plus the growing list of human verification
items whenever Rocco has a session free.
