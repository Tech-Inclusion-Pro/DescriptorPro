# Phase 3 report — Description (code-complete 2026-10-07)

Drafting, the verification pass, gap fitting, the three AD styles, the full
flag taxonomy, and the standards view are built and tested: 144 pytest + 5
vitest green, and the whole chain ran live — three descriptions drafted by
`qwen3:8b`, each verified claim-by-claim by `qwen3-vl:8b` against its
keyframe. **The Phase 3 acceptance held: zero guardrail violations in the
drafted text**, every verdict-bearing flag cites its DS standard, and
extended cues carry correct placement metadata plus the added-running-time
total the spec requires.

## What was built

**Standards view** (`standards/description_criteria.json` + StandardsPane,
spec §6) — all ten criteria with plain-language rules, the quoted source,
what the app does about each, and the flag types that cite it. The
`quotes_verified: false` notice shows in-app until Rocco confirms the
line-by-line check (§6.3). The source-leadership table says plainly which
sources are blind-led, Deaf-led, or unconfirmed. The UI and the code read
the same file.

**Gap fitting** (`core/gapfit.py`, §7.10, DS-4) — gaps from caption word
timestamps (min 1.5 s, guard trimmed); spoken length estimated at 160 wpm
(a measured synthesis length replaces this in Phase 4); placement in the
nearest gap at or after the visual, never before it; never over speech.
Styles: `standard` (short version, then `too_long_for_gap`),
`extended_when_needed` (video pauses — WCAG 1.2.7), and
`extended_before_content` (every description first, at segment start —
DS-7). Extended cues report the pause time they add.

**Drafting** (`core/describe.py` + `prompts/describe.txt`, §7.8) — inputs
are the uncovered facts, OCR text, transcript window, intent profile, gap
budget, and style; the model returns a full and a gap-budgeted short
version, and the reviewer can switch between them (plus the verified
suggestion) at any time. Guardrails run on every draft; each flag type maps
to its DS criterion ids.

**Verification pass** (`core/verify.py` + `prompts/verify_claims.txt`,
§7.9, DS-3) — a second, separate vision-model call per draft judges each
claim `supported` / `contradicted` / `cannot_confirm` against the keyframe
and OCR. Quoted text is checked against OCR in code before any model runs.
Contradicted claims are struck from the *suggested* text only — the
original draft is never altered, and flags never clear except by a
person's approval. An unverifiable draft gets a whole-draft
`unverified_claim` flag rather than silently passing.

**Review + routes** — description cues appear in the Review step under the
captions: mode/placement chips ("extended (video pauses)", "before the
content"), editable text, the verified suggestion with a one-click "Use the
checked version", full/short switches, flags in plain language with their
DS citation pointing at the Standards view, and the same approve-with-name
rules as captions. `GET /api/standards` serves the criteria file;
provenance records cue counts, open flags, style, and added running time.

## Live verification

On the three-slide test lecture (segments and decisions from the Phase 2
run, `extended_when_needed` style):

- 3/3 drafted, 3/3 verified (4 claims each).
- **Zero identity, interpretation, or camera-language flags in the drafts.**
- The audio is dense (one usable 1.34 s pause), so cues correctly went
  extended, with the added running time reported (16 s).
- The strike-out path fired live: the verifier ruled one claim
  contradicted and the suggested text dropped that sentence while the
  original stayed intact for the reviewer. Honest caveat: that particular
  verdict was *over-strict* — the claim said "Review Checklist" and the
  OCR string is the squeezed "ReviewChecklist", so the checker sided with
  OCR. This is the designed failure direction (a wrong description is
  worse than none; the person sees both versions and decides), but it
  means suggested text on text-heavy slides will sometimes be more
  conservative than needed.
- Bug found by the live run and fixed with a regression test: flags gained
  during verification now carry their DS criteria ids too (the draft-time
  mapping had already closed over).

## Timing note

`qwen3:8b` and `qwen3-vl:8b` are thinking models: a draft takes roughly
45–90 s and a verification 60–170 s per cue on the M3. The job is
resumable with live progress, so this is tolerable, but if it drags on
real projects the non-thinking instruct variants (or `qwen2.5vl:7b` for
verification) are the first dial to turn.

## Verified vs not

Verified: everything above, live, on this machine; 144 pytest + 5 vitest +
tsc clean; production UI rebuilt (installed app picks it up on relaunch).

Not verified (needs Rocco):
- The §6.3 quote check (every quotation against its original document) —
  the in-app notice stays until then. Also ask: DS-3/4/5/7 rest on
  Deaf-led or unconfirmed sources; keep, or seek blind-led replacements?
- Extended-cue *playback* (the player that actually pauses arrives in
  Phase 4; the metadata it needs is in place and tested).
- Real lecture content, VoiceOver pass over the new panes, gold set.

## Next

Phase 4: exports (descriptions VTT, Panopto quick mode, described
transcript/MP4) and the embeddable player — where extended cues actually
pause and the provenance record rides every artifact.
