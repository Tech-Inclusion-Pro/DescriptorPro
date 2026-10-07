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


async def visual_track_job(ctx, model_manager) -> dict:
    """Phase 2 visual track (spec §7.4): segment the video (no model),
    OCR keyframes (tiny ONNX), then structured visual facts (vision model,
    unloaded at stage end per §5.3). Stage outputs persist for resume."""
    from service.projects import ProjectStore
    from service.settings_store import library_dir, load_settings

    store = ProjectStore(library_dir())
    try:
        project = store.load(ctx.job.project_id)
        if project is None:
            raise ValueError("Project not found.")
        source = project["source"]["path"]
        intent = project.get("intent") or {}
        settings = load_settings()

        # Stage 1: scenes + keyframes (model-free)
        ctx.stage("segments")
        segments_path = ctx.project_folder / "segments.json"
        if segments_path.exists():
            ctx.status("Video already segmented. Loading saved result.")
            segments = json.loads(segments_path.read_text())
        else:
            from core.scenes import segment_video

            segments = await asyncio.to_thread(
                segment_video,
                source,
                ctx.project_folder / "frames",
                intent.get("content_type") or "other",
                progress=ctx,
                cancel=ctx.cancel,
            )
            segments_path.write_text(json.dumps(segments, ensure_ascii=False))
        ctx.percent(100)

        # Stage 2: OCR (RapidOCR, in-process, no download)
        ctx.stage("ocr")
        ocr_path = ctx.project_folder / "ocr.json"
        if ocr_path.exists():
            ctx.status("Keyframes already read. Loading saved result.")
            ocr_map = json.loads(ocr_path.read_text())
        else:
            from core.vision.ocr import ocr_text_lines

            ocr_map: dict[str, list[str]] = {}
            for i, seg in enumerate(segments):
                ctx.cancel.raise_if_cancelled()
                lines: list[str] = []
                for frame in seg["keyframes"]:
                    lines += await asyncio.to_thread(
                        ocr_text_lines, str(ctx.project_folder / frame)
                    )
                ocr_map[seg["id"]] = lines
                ctx.percent(min(int((i + 1) / max(len(segments), 1) * 100), 99))
                ctx.status(f"Reading text on screen: part {i + 1} of {len(segments)}")
            ocr_path.write_text(json.dumps(ocr_map, ensure_ascii=False))
        for seg in segments:
            seg["ocr_text"] = ocr_map.get(seg["id"], [])
        ctx.percent(100)

        # Stage 3: visual facts (vision model via Ollama)
        ctx.stage("visual-facts")
        facts_path = ctx.project_folder / "visual_facts.json"
        if facts_path.exists():
            ctx.status("Visual facts already drafted. Loading saved result.")
            facts_map = json.loads(facts_path.read_text())
            for seg in segments:
                seg["visual_facts"] = facts_map.get(seg["id"], [])
        else:
            from core.engine.llm import LlmClient
            from core.vision.facts import extract_segment_facts

            model = settings["vision_model"]
            client = LlmClient()
            facts_map = {}
            async with model_manager.use("ollama", model):
                for i, seg in enumerate(segments):
                    ctx.cancel.raise_if_cancelled()
                    last = i == len(segments) - 1

                    def generate(prompt: str, image_rel: str, _last=last) -> str:
                        return client.generate_json(
                            model,
                            prompt,
                            images=[str(ctx.project_folder / image_rel)],
                            keep_alive=0 if _last else None,
                        )

                    await asyncio.to_thread(
                        extract_segment_facts, seg, intent, generate
                    )
                    facts_map[seg["id"]] = seg["visual_facts"]
                    ctx.percent(min(int((i + 1) / max(len(segments), 1) * 100), 99))
                    ctx.status(f"Listing what is on screen: part {i + 1} of {len(segments)}")
            facts_path.write_text(json.dumps(facts_map, ensure_ascii=False))
        ctx.percent(100)

        # Stage 4: save
        ctx.stage("save")
        project["segments"] = segments
        prov = project.setdefault("provenance", {})
        prov.setdefault("models", []).append(
            {"role": "vision", "name": settings["vision_model"], "location": "local"}
        )
        store.save(project)
        flagged = sum(1 for s in segments for f in s["visual_facts"] if f.get("flags"))
        ctx.status(f"Done: {len(segments)} parts, {flagged} facts flagged for review.")
        return {"segments": len(segments), "flagged_facts": flagged}
    finally:
        store.close()


async def need_check_job(ctx, model_manager) -> dict:
    """Phase 2 need check (spec §7.6) + coach (§7.7). Text model only."""
    from core.engine.config import DEFAULT_CONFIG
    from service.projects import ProjectStore
    from service.settings_store import library_dir, load_settings

    store = ProjectStore(library_dir())
    try:
        project = store.load(ctx.job.project_id)
        if project is None:
            raise ValueError("Project not found.")
        segments = project.get("segments", [])
        if not segments:
            raise ValueError("Run the visual track first — there are no segments yet.")
        cues = project.get("caption_cues", [])

        from core.engine.llm import LlmClient
        from core.need_check import add_coach_suggestion, check_segment, tally

        settings = load_settings()
        model = settings["text_model"]
        client = LlmClient()
        pad = DEFAULT_CONFIG.need_check.transcript_pad_seconds

        ctx.stage("need-check")
        async with model_manager.use("ollama", model):
            for i, seg in enumerate(segments):
                ctx.cancel.raise_if_cancelled()
                last = i == len(segments) - 1

                def generate(prompt: str, _last=last) -> str:
                    return client.generate_json(model, prompt, keep_alive=0 if _last else None)

                # Low-confidence captions inside the window make the
                # transcript unreliable for this segment (spec §7.6.4).
                reliable = not any(
                    f["type"] == "low_confidence"
                    for c in cues
                    if c["end"] > seg["start"] - pad and c["start"] < seg["end"] + pad
                    for f in c.get("flags", [])
                )
                await asyncio.to_thread(
                    check_segment, seg, cues, generate, transcript_reliable=reliable
                )
                await asyncio.to_thread(add_coach_suggestion, seg, generate)
                ctx.percent(min(int((i + 1) / len(segments) * 100), 99))
                ctx.status(f"Checking part {i + 1} of {len(segments)}...")

        ctx.stage("save")
        project["segments"] = segments
        prov = project.setdefault("provenance", {})
        prov.setdefault("models", []).append(
            {"role": "text", "name": model, "location": "local"}
        )
        counts = tally(segments)
        prov["need_check"] = counts
        store.save(project)
        ctx.percent(100)
        ctx.status(
            f"Need check done: {counts['needed']} parts need description, "
            f"{counts['uncertain']} uncertain, {counts['not_needed']} covered by the audio."
        )
        return counts
    finally:
        store.close()


async def describe_job(ctx, model_manager) -> dict:
    """Phase 3 (spec §7.8–7.10): draft descriptions for segments a person
    marked `describe`, then verify each draft against its keyframe. Text
    stage runs fully before the vision stage so the models never co-reside
    (§5.3)."""
    from service.projects import ProjectStore
    from service.settings_store import library_dir, load_settings

    store = ProjectStore(library_dir())
    try:
        project = store.load(ctx.job.project_id)
        if project is None:
            raise ValueError("Project not found.")
        segments = project.get("segments", [])
        to_describe = [s for s in segments if (s.get("decision") or {}).get("value") == "describe"]
        if not to_describe:
            raise ValueError(
                "No parts are marked \"Describe it\" yet. Decide on the need-check step first."
            )

        from core.describe import draft_description
        from core.engine.llm import LlmClient
        from core.gapfit import added_running_time, build_gap_list
        from core.verify import verify_description

        settings = load_settings()
        client = LlmClient()
        intent = project.get("intent") or {}
        ad_style = project.get("ad_style") or "standard"
        language = (intent.get("languages") or ["en"])[0]
        cues = project.get("caption_cues", [])
        duration = float(project.get("source", {}).get("duration") or 0.0)
        gaps = build_gap_list(cues, duration)

        # Stage 1: draft (text model)
        ctx.stage("draft")
        drafts_path = ctx.project_folder / "description_drafts.json"
        if drafts_path.exists():
            ctx.status("Descriptions already drafted. Loading saved result.")
            description_cues = json.loads(drafts_path.read_text())
        else:
            text_model = settings["text_model"]
            description_cues = []
            async with model_manager.use("ollama", text_model):
                for i, seg in enumerate(to_describe):
                    ctx.cancel.raise_if_cancelled()
                    last = i == len(to_describe) - 1

                    def generate(prompt: str, _last=last) -> str:
                        return client.generate_json(text_model, prompt, keep_alive=0 if _last else None)

                    cue = await asyncio.to_thread(
                        draft_description,
                        seg, intent, gaps, ad_style, len(description_cues) + 1,
                        generate, language,
                    )
                    if cue is not None:
                        description_cues.append(cue)
                    ctx.percent(min(int((i + 1) / len(to_describe) * 100), 99))
                    ctx.status(f"Drafting description {i + 1} of {len(to_describe)}...")
            drafts_path.write_text(json.dumps(description_cues, ensure_ascii=False))
        ctx.percent(100)

        # Stage 2: verify (vision model)
        ctx.stage("verify")
        verified_path = ctx.project_folder / "description_verified.json"
        if verified_path.exists():
            ctx.status("Drafts already verified. Loading saved result.")
            description_cues = json.loads(verified_path.read_text())
        else:
            vision_model = settings["vision_model"]
            by_id = {s["id"]: s for s in segments}
            async with model_manager.use("ollama", vision_model):
                for i, cue in enumerate(description_cues):
                    ctx.cancel.raise_if_cancelled()
                    last = i == len(description_cues) - 1
                    seg = by_id.get(cue["segment"])

                    def generate(prompt: str, image_rel: str, _last=last) -> str:
                        return client.generate_json(
                            vision_model, prompt,
                            images=[str(ctx.project_folder / image_rel)],
                            keep_alive=0 if _last else None,
                        )

                    if seg is not None:
                        await asyncio.to_thread(verify_description, cue, seg, generate)
                    ctx.percent(min(int((i + 1) / max(len(description_cues), 1) * 100), 99))
                    ctx.status(f"Checking draft {i + 1} of {len(description_cues)} against the video...")
            verified_path.write_text(json.dumps(description_cues, ensure_ascii=False))
        ctx.percent(100)

        # Stage 3: save
        ctx.stage("save")
        project["description_cues"] = description_cues
        project["ad_style"] = ad_style
        prov = project.setdefault("provenance", {})
        prov.setdefault("models", []).append(
            {"role": "description", "name": settings["text_model"], "location": "local"}
        )
        prov["descriptions"] = {
            "drafted_by": "model",
            "cues": len(description_cues),
            "approved": 0,
            "flagged_open": sum(1 for c in description_cues if c["flags"]),
            "style": ad_style,
            "added_running_time": added_running_time(description_cues),
        }
        store.save(project)
        extended = sum(1 for c in description_cues if c["mode"] == "extended")
        ctx.status(
            f"Done: {len(description_cues)} descriptions drafted and checked"
            + (f", {extended} extended (adds {added_running_time(description_cues):.0f} s)" if extended else "")
            + "."
        )
        return {"cues": len(description_cues), "extended": extended}
    finally:
        store.close()


async def quick_panopto_job(ctx, model_manager) -> dict:
    """Panopto quick mode (spec §8.3): the whole pipeline in one pass with
    no stops. Auto-decisions: needed→describe, not_needed→skip,
    uncertain→describe (and listed in the result). Every output is stamped
    'Draft. Not reviewed by a person.' — the stamp is permanent until a
    person actually reviews."""
    from service.projects import ProjectStore
    from service.settings_store import library_dir

    # Chain the existing handlers; each stage resumes from its saved output.
    await transcribe_job(ctx, model_manager)
    await visual_track_job(ctx, model_manager)
    await need_check_job(ctx, model_manager)

    store = ProjectStore(library_dir())
    try:
        project = store.load(ctx.job.project_id)
        ctx.stage("auto-decide")
        uncertain_described = []
        for seg in project.get("segments", []):
            verdict = (seg.get("need") or {}).get("verdict")
            value = "describe" if verdict in ("needed", "uncertain") else "skip"
            seg["decision"] = {"value": value, "by": "quick mode (no person)", "at": None}
            if verdict == "uncertain" and value == "describe":
                uncertain_described.append(seg["id"])
        project["review_level"] = "quick_panopto"
        store.save(project)
    finally:
        store.close()

    await describe_job(ctx, model_manager)

    store = ProjectStore(library_dir())
    try:
        project = store.load(ctx.job.project_id)
        ctx.stage("export")
        from exporters.description_exporter import export_panopto_vtt

        exports_dir = ctx.project_folder / "exports"
        exports_dir.mkdir(parents=True, exist_ok=True)
        stem = (project.get("title") or "video") + ".DRAFT-not-reviewed"
        written = export_panopto_vtt(project, exports_dir, stem)
        prov = project.setdefault("provenance", {})
        prov["status"] = "draft_not_reviewed"
        prov["quick_mode"] = {
            "uncertain_described": uncertain_described,
            "stamp": "Draft. Not reviewed by a person.",
        }
        store.save(project)
        ctx.percent(100)
        ctx.status(
            f"Quick mode done: {len(project.get('description_cues', []))} descriptions, "
            f"{len(uncertain_described)} uncertain parts described anyway. "
            "Both Panopto files are stamped as unreviewed drafts."
        )
        return {
            "written": [str(p) for p in written],
            "uncertain_described": uncertain_described,
        }
    finally:
        store.close()


async def render_described_job(ctx, model_manager) -> dict:
    """Described MP4 (spec §8.2): synthesize each description with Kokoro
    (measured durations replace estimates), then one FFmpeg pass — ducked
    program audio, loudness-normalized, frames frozen for extended cues."""
    from service.paths import app_support_dir
    from service.projects import ProjectStore
    from service.settings_store import library_dir

    store = ProjectStore(library_dir())
    try:
        project = store.load(ctx.job.project_id)
        if project is None:
            raise ValueError("Project not found.")
        cues = project.get("description_cues", [])
        if not cues:
            raise ValueError("There are no descriptions yet. Draft them on the Review step first.")
        source = project["source"]["path"]
        duration = float(project.get("source", {}).get("duration") or 0.0)

        # Stage 1: narration clips (Kokoro, one at a time like any model)
        ctx.stage("narration")
        narr_dir = ctx.project_folder / "narration"
        narr_dir.mkdir(parents=True, exist_ok=True)
        from core.engine.speak import release_engine, synthesize

        models_dir = app_support_dir() / "models" / "kokoro"
        wavs = []
        async with model_manager.use("kokoro", "kokoro-v1.0"):
            for i, cue in enumerate(cues):
                ctx.cancel.raise_if_cancelled()
                wav = narr_dir / f"{cue['id']}.wav"
                if not wav.exists():
                    measured = await asyncio.to_thread(
                        synthesize, cue["text"], wav, models_dir, progress=ctx
                    )
                    cue["clip_duration"] = measured
                elif not cue.get("clip_duration"):
                    import wave as _wave

                    with _wave.open(str(wav), "rb") as f:
                        cue["clip_duration"] = round(f.getnframes() / f.getframerate(), 3)
                wavs.append(wav)
                ctx.percent(min(int((i + 1) / len(cues) * 100), 99))
                ctx.status(f"Recording narration {i + 1} of {len(cues)}...")
        release_engine()
        ctx.percent(100)

        # Stage 2: render
        ctx.stage("render")
        from core.engine.render_video import render_described_video

        exports_dir = ctx.project_folder / "exports"
        exports_dir.mkdir(parents=True, exist_ok=True)
        stem = project.get("title") or "video"
        out = exports_dir / f"{stem}.described.mp4"
        ctx.status("Mixing the described video (this can take a while)...")
        await asyncio.to_thread(
            render_described_video, source, cues, wavs, duration, out
        )

        ctx.stage("save")
        project["description_cues"] = cues  # clip_duration now measured
        prov = project.setdefault("provenance", {})
        prov.setdefault("descriptions", {})["voice"] = "synthetic (Kokoro, local)"
        store.save(project)
        ctx.percent(100)
        ctx.status(f"Described video written: {out.name}")
        return {"written": str(out)}
    finally:
        store.close()


_HANDLERS: dict[str, JobHandler] = {
    "noop": noop_job,
    "transcribe": transcribe_job,
    "visual_track": visual_track_job,
    "need_check": need_check_job,
    "describe": describe_job,
    "quick_panopto": quick_panopto_job,
    "render_described": render_described_job,
}


def get_job_handler(job_type: str) -> JobHandler:
    try:
        return _HANDLERS[job_type]
    except KeyError:
        raise ValueError(f"Unknown job type: {job_type}") from None


def register_job(job_type: str, handler: JobHandler) -> None:
    _HANDLERS[job_type] = handler
