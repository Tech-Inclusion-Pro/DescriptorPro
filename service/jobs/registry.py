"""Job-type registry. Phase 0 ships only `noop`, which exercises the whole
pipeline contract: stages, progress, resume-from-saved-output, cancellation.
Phase 1 adds `ingest` and `captions` here.
"""

from __future__ import annotations

import asyncio
import json
from typing import Awaitable, Callable

JobHandler = Callable[..., Awaitable[dict]]


async def noop_job(ctx, model_manager) -> dict:
    """Test job: three stages, each writes a stage file and resume-skips it."""
    params = ctx.job.params
    steps = int(params.get("steps", 3))
    delay = float(params.get("delay", 0.4))
    stage_dir = ctx.project_folder / "jobs"
    stage_dir.mkdir(parents=True, exist_ok=True)

    completed = 0
    for step in range(1, steps + 1):
        ctx.cancel.raise_if_cancelled()
        stage_name = f"noop-{step}"
        ctx.stage(stage_name)
        stage_file = stage_dir / f"{ctx.job.type}-stage-{step}.json"

        if stage_file.exists():
            ctx.status(f"Stage {step} already complete. Skipping.")
        else:
            ctx.status(f"Working on stage {step} of {steps}...")
            await asyncio.sleep(delay)
            ctx.cancel.raise_if_cancelled()
            stage_file.write_text(json.dumps({"stage": step, "done": True}))
            completed += 1

        ctx.percent(min(int(step / steps * 100), 100))

    ctx.status("Test job complete.")
    return {"steps": steps, "ran": completed, "skipped": steps - completed}


async def transcribe_job(ctx, model_manager) -> dict:
    """Captions pipeline, first slice: extract audio -> whisper with word
    timestamps -> CaptionCue list saved into project.json. Each stage writes
    its output to the project folder and is skipped when it already exists.
    """
    import json
    from service.projects import ProjectStore
    from service.settings_store import library_dir, load_settings

    store = ProjectStore(library_dir())
    try:
        project = store.load(ctx.job.project_id)
        if project is None:
            raise ValueError("Project not found.")

        source = project["source"]["path"]
        settings = load_settings()
        engine = str(ctx.job.params.get("engine") or settings["asr_engine"])
        default_model = settings["whisper_model"] if engine == "whisper" else settings["parakeet_model"]
        model_size = str(ctx.job.params.get("model") or default_model)
        language = ctx.job.params.get("language") or None

        # Stage 1: extract 16 kHz mono WAV
        ctx.stage("extract-audio")
        wav_path = ctx.project_folder / "audio" / "extracted.wav"
        if wav_path.exists():
            ctx.status("Audio already extracted. Skipping.")
        else:
            ctx.status("Extracting audio with FFmpeg...")
            import asyncio
            import shutil

            from core.engine.extract_audio import extract_audio

            tmp = await asyncio.to_thread(extract_audio, source)
            ctx.cancel.raise_if_cancelled()
            shutil.move(tmp, wav_path)
        ctx.percent(100)

        # Stage 2: speech to caption cues
        ctx.stage("transcribe")
        transcript_path = ctx.project_folder / "audio" / "captions.json"
        if transcript_path.exists():
            ctx.status("Captions already drafted. Loading saved result.")
            result = json.loads(transcript_path.read_text())
        else:
            import asyncio

            from core.engine.captions import transcribe_to_cues

            async with model_manager.use(engine, model_size):
                result = await asyncio.to_thread(
                    transcribe_to_cues,
                    str(wav_path),
                    model_size,
                    language,
                    engine=engine,
                    progress=ctx,
                    cancel=ctx.cancel,
                )
            transcript_path.write_text(json.dumps(result, ensure_ascii=False, indent=2))

        # Stage 3: speaker labels. Best effort — captions never fail because
        # diarization could not run (missing download, odd audio, and so on).
        ctx.stage("speakers")
        speakers_path = ctx.project_folder / "audio" / "speakers.json"
        turns: list | None = None
        if speakers_path.exists():
            ctx.status("Speaker turns already found. Loading saved result.")
            turns = json.loads(speakers_path.read_text())
        else:
            import asyncio

            from core.diarize import diarize
            from core.engine.progress import Cancelled
            from service.paths import app_support_dir

            try:
                turns = await asyncio.to_thread(
                    diarize,
                    str(wav_path),
                    app_support_dir() / "models" / "diarization",
                    progress=ctx,
                    cancel=ctx.cancel,
                )
                speakers_path.write_text(json.dumps(turns))
            except Cancelled:
                raise
            except Exception as exc:
                ctx.status(f"Speaker labels unavailable ({exc}). Captions continue without them.")
        if turns:
            from core.diarize import assign_speakers

            assign_speakers(result["cues"], turns)
        ctx.percent(100)

        # Stage 4: save cues + provenance into the project
        ctx.stage("save")
        project["caption_cues"] = result["cues"]
        project["source"]["duration"] = result["duration"]
        project["status"] = "captions_drafted"
        prov = project.setdefault("provenance", {})
        prov.setdefault("models", []).append(
            {"role": "asr", "name": result["model"], "location": "local"}
        )
        prov["captions"] = {
            "drafted_by": "model",
            "cues": len(result["cues"]),
            "approved": 0,
            "flagged_open": sum(1 for c in result["cues"] if c["flags"]),
            "style": "verbatim",
        }
        prov["cloud_services_used"] = []
        prov["status"] = "draft_not_reviewed"
        store.save(project)
        ctx.percent(100)
        ctx.status(f"Done: {len(result['cues'])} caption cues drafted.")
        return {"cues": len(result["cues"]), "language": result["language"]}
    finally:
        store.close()


_HANDLERS: dict[str, JobHandler] = {
    "noop": noop_job,
    "transcribe": transcribe_job,
}


def get_job_handler(job_type: str) -> JobHandler:
    try:
        return _HANDLERS[job_type]
    except KeyError:
        raise ValueError(f"Unknown job type: {job_type}") from None


def register_job(job_type: str, handler: JobHandler) -> None:
    _HANDLERS[job_type] = handler
