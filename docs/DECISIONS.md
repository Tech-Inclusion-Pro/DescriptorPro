# Describe Studio — Decision Log

Decisions confirmed with Rocco. Open decisions live in the spec, section 17 — they are
asked one at a time when reached, never resolved silently.

## 2026-10-06

1. **Architecture (spec §3.1).** The engine stays in Python, extending this repo's
   `core/` and `exporters/` packages, exposed as a local FastAPI service bound to
   127.0.0.1. The UI is React + TypeScript + Vite in `ui/`. Confirmed by Rocco.
2. **Standalone shell.** A thin Electron wrapper (`shell/`) starts the Python service
   and loads the UI. Later the same UI mounts inside Atrium as a module.
3. **Theme.** Light base using the mockup's CSS custom-property token system
   (`docs/mockup/describe-studio-mockup.html`), Tech Inclusion Pro brand colors
   (#3a2b95, #6f2fa6, #a23b84), Arial. A dark palette is NOT added yet — spec open
   decision 6 stays open until Rocco asks.
4. **Mockup.** Rocco supplied `describe-studio-mockup.html`; it is copied to
   `docs/mockup/` and treated as the source of truth for layout, wording, and the
   display settings widget.
5. **Repo.** All Describe Studio code lives in this repository. The existing PyQt6 app
   (`app/`, `main.py`, `LaMiaScribe.spec`) is untouched and must keep working.

6. **Dark theme (spec §17 open decision 6 — RESOLVED 2026-10-06).** Rocco asked for
   Atrium's Mycelium Filament dark look. The token system keeps the mockup's
   variable names and the display-settings widget's behavior, but all four palettes
   (brand, color-vision friendly, monochrome, high contrast) are now built on the
   dark Filament base: ground #05040f, tiles at rgba(10,7,24,.82), ink scale
   #f4f0fb/#cbc2dd, brand hues as fills only with lifted tints for text
   (#a3abf8/#c6a4f5/#ef9ad2), 3px magenta-lift focus ring, filament weave texture
   (decorative, never behind body text, removed in forced-colors). The mockup file
   stays light — it is the layout/wording reference, no longer the color reference.

7. **Product name (spec §17 open decision 2 — RESOLVED 2026-10-06).** The product is
   **DescriptorPro**. Renamed via the branding constants; GitHub repo is
   Tech-Inclusion-Pro/DescriptorPro (public, MIT). Logo supplied by Rocco
   (assets/descriptorpro/logo.png), app icon generated from it.

## Still open (spec §17)

Need-check default report audience · strictly blind-led standards
quotes (DS-3/4/5/7) · caption standards list · player base (Able Player
pending the §9.2 checks) · Kokoro clips in the player · sound-event tagging model ·
live-mode phase timing (currently Phase 6).

8. **Parakeet runtime (plan P1 VERIFY — RESOLVED 2026-10-07).** Apple-Silicon
   backend is **parakeet-mlx** (Apache-2.0, actively maintained, native
   word-level timestamps, default model mlx-community/parakeet-tdt-0.6b-v3,
   CC-BY-4.0 weights). The future Windows path is onnx-asr (MIT) behind the
   same `core/asr/` interface. NeMo rejected as a dependency (too heavy).

9. **Speaker-label models (plan P1 VERIFY, pyannote — RESOLVED 2026-10-07).**
   pyannote's own Hugging Face repos are gated per user (account + token) —
   the wrong flow for non-technical reviewers. The weights themselves are
   MIT/CC-BY-4.0, so we use k2-fsa's **ungated sherpa-onnx redistributions**
   (pyannote segmentation-3.0 ONNX + NeMo TitaNet-small embedding) downloaded
   from GitHub releases on first use. No Hugging Face account involved.
   github.com release downloads added to the §13 allowlist for model fetches.
