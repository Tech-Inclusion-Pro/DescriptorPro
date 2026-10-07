# Model and runtime licenses

Every model DescriptorPro can download or run, what it is licensed under,
where it comes from, and what we owe in return. Updated whenever a model
enters the pipeline; sign-off is a Phase 7 ship gate. App code is MIT;
nothing below conflicts with that. No model weights ship inside the
installer — everything downloads on first use from the sources listed here
(all on the spec §13 network allowlist).

Verified 2026-10-07 unless noted.

## Speech recognition (Phase 1)

| Component | License | Source | Obligations |
|---|---|---|---|
| faster-whisper (runtime) | MIT | PyPI | license notice |
| Whisper weights (tiny…large-v3) | MIT (OpenAI) | Hugging Face via faster-whisper | license notice |
| Silero VAD (bundled inside faster-whisper) | MIT (Silero Team) | ships with faster-whisper | license notice |
| parakeet-mlx (runtime, Apple Silicon) | Apache-2.0 | PyPI | license notice |
| parakeet-tdt-0.6b-v3 / -v2 weights | **CC-BY-4.0** (NVIDIA) | Hugging Face `mlx-community/…` | **attribution**: credit NVIDIA + CC-BY-4.0 link in About/credits |

Windows later (plan P1 note): onnx-asr (MIT) runs the same Parakeet weights
on CPU; no license change.

## Speaker labels (Phase 1)

Decision 2026-10-07 (plan P1 VERIFY, pyannote): pyannote's own Hugging Face
repos are **gated per user** (account + access request + token). That flow
is wrong for non-technical reviewers, so we use k2-fsa's ungated
redistributions of the same weights — permitted because the weights
themselves are MIT / CC-BY-4.0. No Hugging Face account involved.

| Component | License | Source | Obligations |
|---|---|---|---|
| sherpa-onnx (runtime) | Apache-2.0 | PyPI | license notice |
| pyannote segmentation-3.0 (ONNX) | MIT (CNRS / pyannote) | k2-fsa GitHub releases | license notice crediting CNRS/pyannote |
| NeMo TitaNet-small speaker embedding | CC-BY-4.0 (NVIDIA) | k2-fsa GitHub releases | attribution, as above |

## Vision, OCR, and text reasoning (Phase 2)

| Component | License | Source | Obligations |
|---|---|---|---|
| Qwen3-VL 8B (`qwen3-vl:8b`, vision facts) | Apache-2.0 (Alibaba/Qwen) | Ollama library | license notice |
| Qwen3 8B (`qwen3:8b`, need check / coach / intent) | Apache-2.0 (Alibaba/Qwen) | Ollama library | license notice |
| RapidOCR (runtime + bundled PaddleOCR models) | Apache-2.0 | PyPI (models ship in the wheel — no download) | license notice |
| PySceneDetect | BSD-3-Clause | PyPI | license notice |
| OpenCV (headless) | Apache-2.0 | PyPI | license notice |

Decision 2026-10-07 (plan P2 VERIFY, Qwen3-VL tag): `qwen3-vl:8b` exists in
the official Ollama library (requires Ollama ≥ 0.12.7; this machine runs
newer). 8B q4_K_M ≈ 8–10 GB resident — fine alone under the §5.3
one-model-at-a-time rule on the 18 GB M3. Fallback if it misbehaves:
`qwen2.5vl:7b`.

## Narration and player (Phase 4)

| Component | License | Source | Obligations |
|---|---|---|---|
| kokoro-onnx (runtime) | MIT | PyPI | license notice |
| Kokoro-82M voice model + voices file | Apache-2.0 (hexgrad) | kokoro-onnx GitHub releases (first use) | license notice |
| espeakng_loader (bundled espeak-ng) | GPL-3.0 (espeak-ng) — loaded as a separate library at runtime, not linked into app code | PyPI dependency of kokoro-onnx | keep as runtime dependency, do not vendor into MIT code |
| **Able Player v5.0.0** (bundled in `player/vendor/`, **redistributed in every player export**) | MIT | github.com/ableplayer/ableplayer | **its LICENSE ships in each exported folder** (`assets/ABLEPLAYER-LICENSE.txt`) — handled by the exporter |
| **jQuery 3.7.1 slim** (same) | MIT | jquery.com | same — `assets/JQUERY-LICENSE.txt` |
| DOMPurify (inside ableplayer.min.js) | Apache-2.0 / MPL-2.0 dual | bundled upstream | covered by shipping Able Player's license file |

Decision 2026-10-07 (plan P4 VERIFY, Able Player §9.2): **all four checks
pass** — MIT license; reads description tracks aloud via the Web Speech
API with an ARIA-live fallback; `data-desc-pause-default` pauses the video
during a description and auto-resumes (confirmed in source); zero external
requests (no CDN, no fonts, translations bundled since v5.0.0). Known
limit, stated in each export's README: VTT tracks do not load from
file:// double-click (browser fetch restriction) — any static hosting
works. Panopto A/B variants both ship until one is confirmed on UIC's
Panopto (needs Rocco's access).

## Fonts (Phase 0)

| Component | License | Source | Obligations |
|---|---|---|---|
| OpenDyslexic Regular/Bold (© Abbie Gonzalez) | SIL OFL 1.1 | bundled in `ui/public/fonts/` | OFL text ships next to the font files (`ui/public/fonts/OFL.txt`, added 2026-10-07) — this is the only third-party work the app redistributes itself |

## Coming later (recorded when they land)

- Ollama LLMs for description drafting (Phase 3) — per-model entries.
- Qwen3-VL vision (Phase 2) — license + Ollama tag at VERIFY.
- Kokoro TTS (Phase 4) — Apache-2.0 expected; confirm at entry.
- Able Player (Phase 4) — MIT expected; confirm at VERIFY.

## Network allowlist impact (spec §13)

Model downloads require exactly these hosts, only during an explicit
first-use download: `huggingface.co` + its CDN (Whisper, Parakeet),
`github.com` + `release-assets.githubusercontent.com` (sherpa-onnx
diarization models). Nothing else; nothing at caption/draft time.
