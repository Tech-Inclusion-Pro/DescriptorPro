"""Per-group WER scoring over the gold set (eval/README.md has the layout).

Usage:
    .venv/bin/python eval/score_wer.py [--engine whisper|parakeet] [--model NAME]

Runs the same pipeline the app uses (core/asr backend + extract_audio), so a
score here is a score for what reviewers actually see as the first draft.
"""

from __future__ import annotations

import argparse
import datetime
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.engine.extract_audio import extract_audio  # noqa: E402
from eval.wer import word_error_rate  # noqa: E402

GOLD = Path(__file__).parent / "gold"
RESULTS = Path(__file__).parent / "results"
MEDIA_SUFFIXES = {".wav", ".mp3", ".m4a", ".mp4", ".mov", ".mkv", ".webm", ".flac", ".ogg"}


def transcribe(path: Path, engine: str, model: str) -> str:
    from core.asr import get_backend
    from core.engine.progress import CancelToken, NullProgress

    wav = extract_audio(str(path))
    try:
        result = get_backend(engine).transcribe(
            wav, model, None, progress=NullProgress(), cancel=CancelToken()
        )
        return " ".join(c["text"] for c in result["cues"])
    finally:
        Path(wav).unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine", default="whisper", choices=["whisper", "parakeet"])
    parser.add_argument("--model", default=None)
    args = parser.parse_args()

    if args.model is None:
        args.model = (
            "medium" if args.engine == "whisper" else "mlx-community/parakeet-tdt-0.6b-v3"
        )

    groups = sorted(d for d in GOLD.iterdir() if d.is_dir()) if GOLD.exists() else []
    if not groups:
        print(f"No gold set yet. Add clips under {GOLD}/<group>/ (see eval/README.md).")
        return 1

    report = {"engine": args.engine, "model": args.model, "groups": {}}
    for group in groups:
        clips = []
        for media in sorted(group.iterdir()):
            if media.suffix.lower() not in MEDIA_SUFFIXES:
                continue
            reference_file = media.with_suffix(".txt")
            if not reference_file.exists():
                print(f"  SKIP {media.name}: no {reference_file.name} reference")
                continue
            print(f"  {group.name}/{media.name}...", flush=True)
            hypothesis = transcribe(media, args.engine, args.model)
            wer = word_error_rate(reference_file.read_text(), hypothesis)
            clips.append({"clip": media.name, "wer": round(wer, 4)})
        if clips:
            mean = sum(c["wer"] for c in clips) / len(clips)
            report["groups"][group.name] = {"wer": round(mean, 4), "clips": clips}

    if not report["groups"]:
        print("No scorable clips found (each clip needs a .txt reference).")
        return 1

    all_clips = [c for g in report["groups"].values() for c in g["clips"]]
    report["overall_wer"] = round(sum(c["wer"] for c in all_clips) / len(all_clips), 4)

    print(f"\nWER by group — {args.engine} ({args.model})")
    width = max(len(name) for name in report["groups"])
    for name, group in sorted(report["groups"].items(), key=lambda kv: -kv[1]["wer"]):
        print(f"  {name:<{width}}  {group['wer']:.1%}  ({len(group['clips'])} clips)")
    print(f"  {'overall':<{width}}  {report['overall_wer']:.1%}")

    RESULTS.mkdir(exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    out = RESULTS / f"{stamp}-{args.engine}.json"
    out.write_text(json.dumps(report, indent=2))
    print(f"\nSaved {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
