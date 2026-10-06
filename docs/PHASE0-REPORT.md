# Phase 0 Report — Foundation

Date: 2026-10-06. Phase 0 of the Describe Studio build (spec §15) is code-complete.
Per spec §0 rule 8, this report separates what was verified from what was not.

## What was built

- **Qt-free engine** (`core/engine/`): transcription, Ollama client (with
  `keep_alive` support and an `unload_model()` eviction call), audio extraction,
  progress/cancel primitives, pipeline config object. The PyQt app now wraps these
  through thin adapters (`app/qt_adapters.py`); its import surface is unchanged.
- **FastAPI service** (`service/`): 127.0.0.1-only, OS-assigned port, per-launch
  bearer token, 0600 handshake file + `DS_READY` stdout line, project folders
  (`project.json`, `media/ frames/ audio/ exports/ jobs/`) with a rebuildable SQLite
  index, resumable job runner (single worker = one model at a time), websocket
  progress (`state | progress | status | partial | done | error`, ≤2 progress
  messages/sec), model manager with Ollama `keep_alive=0` eviction, settings routes,
  authed shutdown. Serves the built UI at `/ui/` (same origin, no CORS in prod).
- **React UI** (`ui/`): mockup CSS token system verbatim (all four palettes, text
  size/spacing, motion, cursors), display settings widget ported 1:1 (drag grip,
  arrow-key nudge, corner memory, trail, reset, localStorage persistence, polite
  announcements), app bar + chips, mode switch, five-step tablist with the mockup's
  exact keyboard pattern, five panes (media pane full; later panes show honest
  empty states naming their phase), skip link, polite live region, en + es i18n
  with RTL support, OpenDyslexic bundled, test-job button streaming real websocket
  progress.
- **Electron shell** (`shell/`): spawns the service (or attaches in dev), waits for
  `DS_READY` + `/health`, injects `{port, token}` via preload (token never in a
  URL), blocks every non-loopback network request, clean shutdown.
- **Tooling:** `make setup / dev / dev-web / test / build-ui / pyqt`;
  `ui/scripts/export-translations.py` (23 languages exported);
  `requirements-service.txt` kept separate so the PyQt PyInstaller build is
  untouched.

## Verified (I ran these)

- `pytest`: **35 passed** — PyQt import canary (13 app modules), no-Qt-in-engine
  guard, auth (401 without/with wrong token, handshake file mode 0600), project
  CRUD + folder layout + sha256 + keep-exports delete + index rebuild, job
  lifecycle + stage-file resume + cancel + websocket message shapes + bad-token
  websocket rejection, model manager serialization + unloader + Ollama keep_alive=0
  path (mocked).
- `vitest`: **5 passed** — axe reports zero violations on the shell, all five
  panes, live + standards views, and the open display-settings panel; tablist
  arrow/Home/End behavior.
- Live service boot: `DS_READY` handshake, open `/health`, 401 on unauthenticated
  API, authed shutdown removes the handshake file, built UI served at `/ui/`.
- `npm run build`: TypeScript strict + Vite build clean.

## Not verified yet (needs you)

1. **PyQt app end-to-end:** imports pass and the transcription worker is a thin
   wrapper over unchanged logic, but I did not run a real transcription. Please run
   `make pyqt` and transcribe a short file once.
2. **Manual keyboard + VoiceOver pass** (spec §12 requires it before a phase is
   done): run `make dev`, then walk the checklist in `docs/a11y-checklist.md`.
3. **Zero-network observation in the shell:** the request blocker is in place and
   the UI makes only loopback calls by construction, but I did not observe a full
   session with a network monitor. Little Snitch or `nettop` during `make dev` will
   confirm.
4. **OpenDyslexic license:** the OTFs were already shipped with La Mia Scribe and
   OpenDyslexic is published under the SIL Open Font License 1.1, which permits
   bundling — but per spec §5.4-style care I have not re-read the license file
   itself. Flagging rather than resolving: confirm once and I will record it in
   `docs/MODEL_LICENSES.md` when that file starts in Phase 1.

## Open decisions touched (spec §17) — none resolved

Dark palette, product name, and all others remain open. The mockup's light token
system shipped as agreed on 2026-10-06 (see docs/DECISIONS.md).

## Next

Phase 1 (Captions): Silero VAD, ASR backend interface (Whisper with word
timestamps first), caption formatting to DCMP/FCC limits, caption review editor,
VTT/SRT with provenance, per-group accuracy on your gold set. First VERIFY items:
Parakeet runtime on Apple Silicon, pyannote license. **Awaiting your go-ahead.**
