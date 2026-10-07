# Phase 7 report — Parity and packaging (code-complete 2026-10-07)

The final build phase. 187 pytest + 5 vitest green; the installed app is
self-contained; DescriptorPro is an Atrium module.

## What was built

**23-language UI** — the engine's full language set loads from generated
JSON (core/translations.py is the single source); en + es carry the
hand-written UI keys and the other 21 fall back to en for UI-only
strings. RTL (ar/arz/ur) preserved. Known gap, deliberate: the newest
pane strings (Phases 1–6 additions) are hardcoded English pending key
extraction — pipeline *outputs* honor the project language, app chrome
beyond the original keyset does not yet.

**Spanish output parity** — describe and image prompts carry a language
directive from the intent profile's first language; on-screen quotes stay
untranslated so they match the slide. (Captions were always multilingual
via Whisper.)

**Cloud BYOK (spec §13)** — keys in the macOS Keychain (python-keyring),
never in files, never returned by any route; per-project, per-stage,
off by default; the cloud-preview endpoint shows exactly what a stage
would send, what never leaves the machine, and sends nothing itself.
Provider calls themselves are not wired yet — the first real cloud
provider needs Rocco's key and an allowlist decision.

**Self-contained packaging** — PyInstaller onedir of the entire service
(859 MB: ctranslate2/whisper, parakeet-mlx, sherpa-onnx, RapidOCR,
PySceneDetect, kokoro-onnx, pypdfium2, prompts/standards/player
vendor/UI). Smoke-tested frozen: handshake, health, /ui/, authenticated
API reading bundled data, clean shutdown. electron-builder ships it as
extraResources; the shell already preferred the bundled binary.
**Verified: the service boots and serves from inside
/Applications/DescriptorPro.app — the repo checkout is no longer
needed.** Still unsigned (macOS will warn on first launch); FFmpeg and
Ollama remain documented external requirements.

**Atrium mount** — `descriptor` module in ~/Projects/atrium (commit
abc0c70): main-process ensure/status reads DescriptorPro's handshake,
probes health, spawns the bundled app service (repo venv fallback),
never kills a service it didn't spawn; the view hosts the full UI in a
webview and injects {port, token} on dom-ready so it authenticates.
Tile sits above RALPH. Typecheck + build + tests clean.

## Remaining before any public release (human gates)

- MODEL_LICENSES.md sign-off (Rocco — the file is complete and current).
- §6.3 line-by-line quote verification; DS-3/4/5/7 source-leadership call.
- Gold set → per-group WER + need-check recall numbers.
- Panopto A/B on UIC; described-MP4 listening pass; player VoiceOver +
  network observation; live mic session; Phase 0 acceptance items.
- Paid blind and low-vision reviewer evaluation (spec gate).
- Code signing / notarization when distribution goes beyond this Mac.
