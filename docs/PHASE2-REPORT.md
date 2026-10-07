# Phase 2 report — Intent and need check (code-complete 2026-10-07)

Everything in the plan's P2 line is built, tested, and verified live
against the real local models: 115 pytest + 5 vitest green, and a
synthesized three-slide lecture ran the whole chain — segmentation → OCR →
Qwen3-VL visual facts → Qwen3 need check → coach — with correct verdicts,
reasons, and citations on every segment.

## What was built

**Intent conversation** (spec §7.2) — the six questions, one at a time,
every one skippable, in the Intent pane. Answers go to the local text model
(`qwen3:8b`) which returns an IntentProfile; the profile is shown beside
the conversation and **every field is editable** (content type and detail
level as selects, people/languages/terms as text). A fully skipped
conversation yields the spec defaults (concise, auto content type, no named
people). All profile content is sanitized server-side — bad enum values
clamp, people always carry `source: "user"`. Verified live: a five-answer
conversation produced a correct profile (people, both languages, key terms)
on the first try. Spoken answers are typed-only for now — mic capture notes
below.

**Scene and slide detection** (`core/scenes.py`, §7.4) — PySceneDetect
content detector for filmed content plus a slide/text-change scan, sampling
density by content type from the intent profile. Keyframes: first stable
frame after each change + a mid-segment frame for long segments. Finding
during verification: the planned 64-bit perceptual hash **completely missed
text-only slide changes** (slide text vanishes at 8×8 downscale under a
dominant white background), so the detector uses a 64×36 grayscale grid
diff instead — measured 2–4 % of cells change on a slide flip, 0 % between.
The synthesized lecture segmented at exactly its two slide boundaries.

**OCR** (`core/vision/ocr.py`) — RapidOCR: Apache-2.0, pip wheel, models
bundled — zero network, nothing to download. Text with positions.

**Structured visual facts** (`core/vision/facts.py` + `prompts/
visual_facts.txt`) — Qwen3-VL per keyframe, OCR text and intent in the
prompt, JSON-constrained, at most 8 short checkable statements with
kind/essential. The §7.5 guardrails apply twice: the prompt instructs, and
`core/guardrails.py` re-checks every fact regardless — identity inference,
interpretation terms (English + Spanish, accent-folded), camera language
(allowed only for filmmaking content), and name-source flags
(`name_from_user` / `name_from_screen`; names only ever come from the
intent profile or on-screen text). Nothing is rewritten or censored — a
match flags for the reviewer. Live run: facts quoted slide text correctly;
zero identity/interpretation violations.

**Need check** (`core/need_check.py` + prompt, §7.6) — the W3C 1.2.5 rule
per segment: OCR-text facts first try a direct fuzzy match against the
transcript (no model cost); remaining essential facts get the narrow
covered/not_covered/unsure question. Verdict logic per spec, including:
low-confidence captions in the window force `uncertain`, and there is no
whole-video verdict — the API returns the tally, the per-segment table, the
standards list, and the required "not legal advice" sentence. Deictic
phrases detected from the config lists (English + Spanish). Decisions
(describe/skip) require a name and record who/when; `undecided` clears.
Live run on real speech + slides: all three segments correctly `needed`
(the audio genuinely never says the slide contents), each with a plain
reason and WCAG-1.2.5 citation.

**Coach** (§7.7) — for `needed` segments with deictic speech: a short
fix-it-at-the-source suggestion naming the actual on-screen content.
Live output: *"Instead of 'as you can see,' say, 'These roles include
Parent, Special Educator, General Educator, LEA Representative, Evaluator,
and Student.'"* Suggestions appear in the pane's "Fix it at the source"
box; the one-page handout export can ride along with Phase 4's exporters.

**Jobs and memory rule** — `visual_track` (segments → OCR → vision facts)
and `need_check` (text model) as resumable jobs with per-stage skip files;
the vision and text models run under the model manager with `keep_alive: 0`
on each stage's last call (§5.3). Models never co-reside.

**UI** — IntentPane: live conversation + editable profile. NeedCheckPane:
run button (two-phase progress wording), tally line, per-segment findings
table (time / on screen with flag chips / said aloud / finding with reason
+ citation / decision buttons), standards + notice, coach box.

## Engineering findings worth knowing

- Qwen3-VL and Qwen3 are *thinking* models: `ollama.generate(format=json)`
  returns an **empty response** (thinking consumes the output), while
  `ollama.chat(format=json)` answers correctly. `LlmClient.generate_json`
  therefore uses the chat endpoint. Occasional empty replies still happen;
  fact extraction and need-check questions retry once (a garbled need-check
  reply degrades safely to `unsure`).
- `qwen3-vl:8b` and `qwen3:8b` pulled and recorded in MODEL_LICENSES.md
  (both Apache-2.0). VERIFY resolved: official Ollama tags, no GGUF
  workarounds needed.

## Verified vs not

Verified live: full chain on a synthesized 3-slide lecture with real
two-voice speech; correct segment boundaries; OCR accurate; facts clean of
identity violations; verdicts/reasons/citations correct; coach and intent
conversion correct; 115 pytest + 5 vitest + tsc + axe green; UI rebuilt so
the installed app serves the new panes on next launch.

Not verified (needs Rocco):
- **Need-check recall on `needed`** (the Phase 2 acceptance metric) needs
  the gold set — same blocker as the Phase 1 WER numbers.
- Real lecture recordings (synthetic slides/voices only so far).
- Spoken intent answers (mic capture + local Whisper) — typed works; voice
  is natural to add alongside Phase 6's live capture plumbing.
- A keyboard/VoiceOver pass over the two new panes.

## Open items carried forward

- Gold set: one folder of clips unlocks both the WER table and need-check
  recall reporting.
- Phase 0 acceptance items still owed (PyQt sanity, VoiceOver checklist,
  network observation, OpenDyslexic OFL confirm).
- Phase 3 (description drafting/verification/gap fitting) builds directly
  on these segments, facts, and decisions.
