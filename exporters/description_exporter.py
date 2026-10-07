"""Description exports (spec §8.2–8.3) from DescriptionCue dicts.

Every human-readable export carries the plain-language provenance block
(spec §11); nothing may hide or remove the status line. The described
transcript interleaves speech and descriptions in time order so the whole
video is readable without playing it (WCAG 1.2.8).
"""

from __future__ import annotations

import html
from pathlib import Path

from utils.time_utils import seconds_to_vtt_time


def description_provenance_lines(project: dict) -> list[str]:
    prov = project.get("provenance", {})
    desc = prov.get("descriptions", {})
    total = desc.get("cues", len(project.get("description_cues", [])))
    approved = desc.get("approved", 0)
    reviewed = total > 0 and approved == total
    reviewer = ""
    if reviewed:
        names = {
            c.get("approved_by")
            for c in project.get("description_cues", [])
            if c.get("approved_by")
        }
        reviewer = ", ".join(sorted(names))
    return [
        "Audio description: drafted by a model on this computer; "
        + (f"reviewed by {reviewer}." if reviewed else "NOT yet reviewed by a person."),
        "The description voice is synthetic unless a cue names a human recording.",
        "Cloud services used: none.",
        f"Status: {'reviewed' if reviewed else 'DRAFT. Not yet reviewed by a person.'}",
    ]


def export_descriptions_vtt(project: dict, output_path: str | Path) -> Path:
    """WebVTT for <track kind="descriptions">. Extended/placement metadata
    the VTT cannot carry goes in player.json (spec §9.1)."""
    path = Path(output_path)
    lines = ["WEBVTT", "", "NOTE"]
    lines.extend(description_provenance_lines(project))
    lines.append("")
    for cue in project.get("description_cues", []):
        end = cue["start"] + max(cue.get("est_duration", 2.0), 1.0)
        lines.append(cue["id"])
        lines.append(f"{seconds_to_vtt_time(cue['start'])} --> {seconds_to_vtt_time(end)}")
        lines.append(cue["text"].replace("\n", " "))
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def export_panopto_vtt(project: dict, output_dir: str | Path, stem: str) -> list[Path]:
    """Two variants until one is confirmed on a real Panopto site (spec
    §8.3): A with <v Audio Descriptions> voice markup, B plain. Both carry
    the draft stamp in a NOTE block and in the filename."""
    out = Path(output_dir)
    written = []
    for suffix, with_voice in (("panopto-a", True), ("panopto-b", False)):
        lines = ["WEBVTT", "", "NOTE"]
        lines.extend(description_provenance_lines(project))
        lines.append("")
        for cue in project.get("description_cues", []):
            end = cue["start"] + max(cue.get("est_duration", 2.0), 1.0)
            text = cue["text"].replace("\n", " ")
            lines.append(f"{seconds_to_vtt_time(cue['start'])} --> {seconds_to_vtt_time(end)}")
            lines.append(f"<v Audio Descriptions>{text}" if with_voice else text)
            lines.append("")
        path = out / f"{stem}.{suffix}.vtt"
        path.write_text("\n".join(lines), encoding="utf-8")
        written.append(path)
    return written


def _interleaved(project: dict) -> list[dict]:
    """Captions + descriptions in time order, each {kind, start, speaker,
    text, extended}."""
    items: list[dict] = []
    for cue in project.get("caption_cues", []):
        items.append(
            {
                "kind": "speech",
                "start": cue["start"],
                "speaker": cue.get("speaker"),
                "text": cue["text"].replace("\n", " "),
                "extended": False,
            }
        )
    for cue in project.get("description_cues", []):
        items.append(
            {
                "kind": "description",
                "start": cue["start"],
                "speaker": None,
                "text": cue["text"].replace("\n", " "),
                "extended": cue.get("mode") == "extended",
            }
        )
    # Descriptions placed before_content sort ahead of speech at the same time.
    return sorted(items, key=lambda i: (i["start"], 0 if i["kind"] == "description" else 1))


def _fmt_time(seconds: float) -> str:
    s = int(seconds)
    return f"{s // 60}:{s % 60:02d}"


def export_described_transcript_html(project: dict, output_path: str | Path) -> Path:
    """Standalone HTML, no scripts or network: readable without the video
    (WCAG 1.2.8). The player export links this same file."""
    path = Path(output_path)
    title = html.escape(project.get("title") or "Described transcript")
    prov = "<br>".join(html.escape(l) for l in description_provenance_lines(project))

    rows = []
    for item in _interleaved(project):
        time_attr = f"{item['start']:.3f}"
        stamp = _fmt_time(item["start"])
        if item["kind"] == "description":
            label = "Description (extended)" if item["extended"] else "Description"
            rows.append(
                f'<p class="description" data-start="{time_attr}">'
                f'<span class="time">{stamp}</span> '
                f'<strong class="label">{label}:</strong> {html.escape(item["text"])}</p>'
            )
        else:
            speaker = f'<strong class="speaker">{html.escape(item["speaker"])}:</strong> ' if item["speaker"] else ""
            rows.append(
                f'<p class="speech" data-start="{time_attr}">'
                f'<span class="time">{stamp}</span> {speaker}{html.escape(item["text"])}</p>'
            )

    body = "\n".join(rows)
    doc = f"""<!DOCTYPE html>
<html lang="{html.escape((project.get('intent') or {}).get('languages', ['en'])[0])}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
  body {{ font-family: Arial, sans-serif; max-inline-size: 46rem; margin: 2rem auto; padding: 0 1rem; line-height: 1.6; }}
  .time {{ font-variant-numeric: tabular-nums; color: #555; margin-inline-end: .5rem; }}
  .description {{ border-inline-start: 4px solid #6f2fa6; padding-inline-start: .75rem; background: #f7f2fb; }}
  .provenance {{ border: 1px solid #999; padding: 1rem; margin-block-end: 2rem; }}
  @media (prefers-color-scheme: dark) {{
    body {{ background: #111; color: #eee; }}
    .time {{ color: #aaa; }}
    .description {{ background: #221a2e; }}
  }}
</style>
</head>
<body>
<h1>{title}</h1>
<section class="provenance" aria-label="About this transcript">
<p>{prov}</p>
</section>
<main>
{body}
</main>
</body>
</html>
"""
    path.write_text(doc, encoding="utf-8")
    return path


def export_described_transcript_docx(project: dict, output_path: str | Path) -> Path:
    import docx
    from docx.shared import Pt

    path = Path(output_path)
    document = docx.Document()
    document.add_heading(project.get("title") or "Described transcript", level=1)
    for line in description_provenance_lines(project):
        p = document.add_paragraph(line)
        p.runs[0].font.size = Pt(9)
    document.add_paragraph()

    for item in _interleaved(project):
        stamp = _fmt_time(item["start"])
        if item["kind"] == "description":
            label = "Description (extended)" if item["extended"] else "Description"
            p = document.add_paragraph()
            p.add_run(f"[{stamp}] {label}: ").bold = True
            p.add_run(item["text"]).italic = True
        else:
            p = document.add_paragraph()
            prefix = f"[{stamp}] " + (f"{item['speaker']}: " if item["speaker"] else "")
            p.add_run(prefix).bold = True
            p.add_run(item["text"])
    document.save(str(path))
    return path


def export_description_script_docx(project: dict, output_path: str | Path) -> Path:
    """The narrator's script: every description cue with its time, mode,
    duration, and open flags (spec §8.2)."""
    import docx
    from docx.shared import Pt

    path = Path(output_path)
    document = docx.Document()
    document.add_heading(f"Description script — {project.get('title') or 'Untitled'}", level=1)
    for line in description_provenance_lines(project):
        p = document.add_paragraph(line)
        p.runs[0].font.size = Pt(9)

    table = document.add_table(rows=1, cols=4)
    table.style = "Light Grid Accent 1"
    header = table.rows[0].cells
    for i, text in enumerate(["Time", "Mode", "Description", "Flags"]):
        header[i].text = text
    for cue in project.get("description_cues", []):
        row = table.add_row().cells
        row[0].text = f"{_fmt_time(cue['start'])} ({cue.get('est_duration', 0):.0f}s)"
        row[1].text = ("extended" if cue.get("mode") == "extended" else "inline") + (
            ", before content" if cue.get("placement") == "before_content" else ""
        )
        row[2].text = cue["text"]
        row[3].text = "; ".join(
            f"{f['type']}" + (f" ({f['detail']})" if f.get("detail") else "")
            for f in cue.get("flags", [])
        ) or "—"
    document.save(str(path))
    return path
