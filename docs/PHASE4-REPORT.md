# Phase 4 report — Exports and player (code-complete 2026-10-07)

Every §8.2 export plus the embeddable player is built: 162 pytest + 5
vitest green, and the heavy paths ran live — a described MP4 rendered with
real Kokoro narration, ducking, and frozen frames; a complete player
folder built from the real pipeline data with every reference resolving
locally.

## VERIFY results

**Able Player (§9.2) — all four checks PASS, no stop-and-ask needed:**
- License: MIT (plus MIT jQuery, dual-licensed DOMPurify inside the
  bundle). v5.0.0 vendored into `player/vendor/` with license files;
  every export ships them (`assets/*-LICENSE.txt`).
- Browser-voice readout: yes — Web Speech API with an ARIA-live fallback
  when synthesis is unavailable. Web Speech is the flakiest layer of any
  browser stack; the fallback covers total failure.
- Pause for description: yes — `data-desc-pause-default="on"` pauses at
  each description and auto-resumes when speech ends (confirmed in the
  player's source, not just its docs). WCAG 1.2.7 behavior.
- Offline: yes — no CDN, no font fetches, translations bundled. One known
  limit, stated in every export's README: browsers refuse to load VTT
  tracks from a double-clicked file:// page. Any static hosting (course
  site, campus server) works.

**Panopto (§8.3) — still unverified on a real site.** Both variants ship
(`.panopto-a.vtt` with `<v Audio Descriptions>` markup, `.panopto-b.vtt`
plain), filenames and NOTE blocks stamped "DRAFT. Not reviewed by a
person." Needs a test upload on UIC's Panopto when Rocco has access.

## What was built

**Exports** (`exporters/description_exporter.py`): descriptions WebVTT
(for `<track kind="descriptions">`, provenance NOTE, end times from
measured narration); Panopto A/B; described transcript in HTML (standalone,
script-free, dark-mode aware, speech + descriptions interleaved in time
order — WCAG 1.2.8) and DOCX; description script DOCX (times, modes,
flags — for a human narrator or reviewer); provenance JSON. All reachable
from the Export pane, each description format gated on descriptions
existing.

**Described MP4** (`core/engine/speak.py` + `core/engine/render_video.py`
+ `render_described` job): each cue synthesized with Kokoro
(kokoro-onnx — MIT runtime, Apache-2.0 weights, espeak bundled, one-time
~340 MB download), **measured** clip durations replacing the 160 wpm
estimates (measured ran ~60 % longer on real synthesis — the spec's
"measure, don't estimate" rule earns its keep), then one FFmpeg pass:
program audio ducked under narration (sidechaincompress), 48 kHz, single
loudnorm pass, frame frozen for each extended cue. Placement math is pure
and unit-tested; the live render came out frame-accurate (46.54 s output
vs 46.51 s expected = source + freezes).

**Panopto quick mode** (`quick_panopto` job): the whole pipeline in one
pass — transcribe → visual track → need check → auto-decisions
(needed→describe, not_needed→skip, uncertain→describe and reported) →
draft+verify → A/B export. Decision records say "quick mode (no person)";
provenance and filenames carry the permanent draft stamp.

**Player** (`exporters/player_exporter.py` + export route): one folder per
spec §9.1 — index.html (descriptions on by default, pause-for-description
on by default, visible synthetic-voice statement, provenance block, link
to the described transcript), media, caption + description VTTs,
transcript.html, player.json (the extended/placement/voice metadata VTT
cannot carry), assets with licenses, and a plain-language README.txt with
the embed code and the file:// caveat. The Export pane shows the folder
path and a copyable iframe embed.

## Verified vs not

Verified live: Kokoro synthesis; described MP4 render (duration math
exact, narration audible during freezes); player folder from real
pipeline data (12 files, zero external references — asserted by test and
re-checked on the real export); Panopto A/B output; 162 pytest + 5 vitest;
UI rebuilt for the installed app.

Not verified (needs Rocco or a browser session):
- **Panopto on the real UIC site** — which variant it accepts, and
  whether it pauses for long descriptions.
- A listening pass on the described MP4 (ducking depth and narration
  loudness are set to sane broadcast-ish values; ears should confirm).
- The player in a real browser with VoiceOver: readout, pause/resume,
  zero requests in the network inspector (static analysis says zero;
  the spec's acceptance wants it observed).
- Phase 0 acceptance items and the gold set, still open.

## Next

Phase 5 (image/slide description with batch review) or the outstanding
human checks above — Rocco's call at this gate.
