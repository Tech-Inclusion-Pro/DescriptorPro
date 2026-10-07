# Phase 1 report — Captions (code-complete 2026-10-07)

Everything the plan's P1 line lists is built and tested: 73 pytest + 5
vitest green, both speech engines verified live on real synthesized speech,
memory spike measured on the M3. Items that still need Rocco are listed at
the end — the per-group WER gold set is the big one.

## What was built

**Silero VAD gating** — `vad_filter` on in the Whisper backend, parameters
in `core/engine/config.py:VadConfig`. No cues are drafted from silence.
Finding during verification: tightening `min_silence_duration_ms` below
faster-whisper's default (2000 ms) fragments speech, and with word
timestamps on, fragment edges *drop words* — the final words of a test clip
vanished at 700 ms and returned at 2000 ms. VadConfig therefore pins the
library defaults, with the measurement recorded in the dataclass docstring.

**`core/asr/` backend interface** — `get_backend("whisper"|"parakeet")`,
both returning the same raw-cue shape with word timestamps and per-word
confidence. Engine chosen by the `asr_engine` setting (default whisper),
overridable per job. VERIFY resolved: **parakeet-mlx** on Apple Silicon
(Apache-2.0; model weights CC-BY-4.0, attribution recorded); onnx-asr (MIT)
is the Windows path later, behind this same interface. Parakeet subword
tokens are merged into words with geometric-mean confidence.

**Forced alignment** (`core/align.py`) — for backends that return text
without word timings: one pass of a small Whisper model produces hypothesis
words; cue words anchor to them by normalized-text matching (difflib); the
gaps interpolate proportionally by word length. No new dependencies, no
torch. Runs automatically only when a cue lacks words.

**DCMP/FCC formatting** (`core/engine/caption_format.py`) — pure functions,
14 dedicated tests. Max 2 lines × 32 characters; splits prefer sentence
ends, then clause punctuation, then the longest pause between words; cue
timing after a split comes from the word timestamps, never guessed. Short
cues extend into following silence up to `min_cue_seconds`, never
overlapping the next cue. Cues over 180 wpm get a `reading_rate` flag; cues
that cannot be split honestly (no word timings) get `needs_split`. Both new
flag types render in plain language in the review editor.

**Speaker labels** (`core/diarize.py`) — sherpa-onnx offline diarization.
VERIFY resolved: pyannote's HF repos are per-user gated, so we use k2-fsa's
ungated redistributions of the same MIT/CC-BY-4.0 weights (segmentation-3.0
+ TitaNet-small, ~46 MB total, one-time download from GitHub releases — no
Hugging Face account, which matters for non-technical reviewers). Speakers
are painted onto cues by largest overlap, numbered by first appearance, and
suppressed entirely when only one speaker is found (DCMP). The job treats
diarization as best-effort: captions never fail because speaker labels
could not run. Reviewers can edit or clear each cue's label in the review
editor; changing a label returns the cue to draft.

**Eval harness** (`eval/`) — `score_wer.py` runs the app's own pipeline per
clip and reports WER per speaker group plus overall, saving JSON results.
Dependency-free WER (tested). `eval/gold/` is gitignored — clips of real
people stay on this machine. **Waiting on Rocco to assemble the gold set**
(folder layout and group suggestions in `eval/README.md`).

**M3 memory spike test** (`scripts/memory_spike.py`) — measured 2026-10-07,
worst-case sequence in one process (whisper medium → parakeet-tdt-0.6b-v3 →
diarization, each with real inference): **peak RSS 2,484 MB**, far under
the 18 GB ceiling. parakeet-mlx releases cleanly (1.5 GB → 428 MB after
`mx.clear_cache()`; the model manager now does this on release).
Measured caveat: ctranslate2 keeps ~770 MB pooled after Whisper release
in-process — acceptable headroom-wise, worth rechecking when Ollama
description models join in Phase 3.

**`docs/MODEL_LICENSES.md`** — started, all Phase 1 models recorded with
licenses, sources, and obligations; network-allowlist impact noted
(huggingface.co + github.com release hosts, first-use downloads only).

## Verified vs not

Verified live on this machine:
- Both engines end-to-end on a two-voice synthesized clip: every cue within
  the 2×32 grid, correct text, tail words intact, output JSON-safe.
- Diarization found exactly 2 speakers and labeled the switch correctly on
  both engines' cues.
- Model downloads: parakeet weights (HF), diarization models (GitHub).
- Memory spike numbers above.
- A numpy-float serialization bug found and fixed during verification
  (would have crashed the job's save stage on faster-whisper 1.2.1).

Not verified (needs Rocco):
- **Per-group WER** — no gold set yet.
- Caption quality on real classroom audio (synthesized voices only so far).
- The installed app (`/Applications/DescriptorPro.app`) picks up the new UI
  on next launch (`ui/dist` rebuilt); a quick upload-to-export pass there
  is worth a minute.
- Phase 0 acceptance items still open: PyQt `make pyqt` sanity, VoiceOver/
  keyboard checklist, network observation, OpenDyslexic OFL confirm.

## Open items carried forward

- Gold set + first WER run (Rocco assembles; one command to score).
- Settings UI for engine/model choice — service setting exists
  (`asr_engine`), no pane exposes it yet; natural to fold into a settings
  pane later rather than invent one now.
- Windows Parakeet backend (onnx-asr) — when a Windows build exists.
