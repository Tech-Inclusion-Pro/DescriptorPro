# Phase 6 report — Live session mode (code-complete 2026-10-07)

Live captions and the slide announcer are built: 184 pytest + 5 vitest
green, streaming verified end to end through the real websocket.

## VERIFY result

Streaming backend = parakeet-mlx `transcribe_stream` (the same Parakeet
TDT model the recorded pipeline uses — nothing new to download).
Measured on the M3: faster than realtime (23.8 s of audio in 15.2 s),
median lag 500 ms with 0.5 s chunks, 832 ms with 1 s chunks over the
websocket — inside the spec's under-one-second target, and the UI shows
the measured number instead of claiming one. WhisperKit rejected
(Swift-only). Windows later: onnx-asr chunking behind the same class.

## What was built

**Live captions** (core/live/captions.py + /ws/live + LivePane): the
browser captures the microphone, streams mono 16 kHz PCM over the
authenticated websocket, the service runs streaming Parakeet and returns
text + honest lag (wall-clock behind realtime + chunk length). Display:
adjustable text size, line count, high contrast; a detachable caption
window to place over slides. Recording is OFF unless turned on, and the
toggle says so in words.

**Save + full pipeline** (spec §10.1): stopping offers "save as a
project" — transcript sentences become draft caption cues (provenance:
"model (live session)", status draft_not_reviewed), the recording (when
on) becomes the project media, so the full recorded pipeline can redo
the captions properly. Verified live: recorded session → project with
4 cues and the wav.

**Slide announcer** (core/live/announcer.py + /api/live/{id}/frame):
screen capture of the slides window → grid-diff change detection (same
detector as the recorded pipeline) → OCR → spoken "Slide N. Title." with
optional read-all-text. It reads text only: a slide with low text
coverage gets "This slide may contain images or charts. Not described
live." — spoken, shown, and logged for the recorded pass (the log rides
the saved project's provenance). Output device = the system sound
output the user picks (headphones = private channel).

**Required notices** (§10.3): all three are permanently visible in the
pane — not a CART replacement; error rates differ across accents and
speech patterns; recording may need consent and is off by default.

## Verified vs not

Verified: streaming + lag + record/stop/save through the real websocket
with real speech audio; slide watcher change detection, graphics note,
and log in tests; 184 pytest + 5 vitest; UI rebuilt.

Not verified (needs Rocco at the machine): a real microphone session
(permissions prompt, echo cancellation, room acoustics), the announcer
against a real slideshow with VoiceOver listening, and the detached
window over a presentation. ~20–30 minutes.

## Next

Phase 7: Spanish parity + 21 UI languages, cloud BYOK, MODEL_LICENSES
sign-off, installers (PyInstaller service), Atrium mount.
