"""Embeddable accessible player export (spec §9): one folder the user can
host anywhere and embed with one line.

Built on Able Player v5.0.0 (VERIFY passed 2026-10-07, docs/DECISIONS.md):
MIT; reads description tracks aloud with the browser's speech synthesis
(ARIA-live fallback); `data-desc-pause-default` pauses the video during a
description and auto-resumes; ships with zero external requests (no CDN,
no fonts, translations bundled). Vendored under player/vendor/ with its
license — the export copies, never downloads.

Known limit, stated in the exported README: browsers block VTT loading
when index.html is opened by double-click (file://). Any static hosting —
a course site, campus server, or local preview server — works.
"""

from __future__ import annotations

import html
import json
import shutil
from pathlib import Path

from exporters.caption_cue_exporter import export_cues_vtt
from exporters.description_exporter import (
    description_provenance_lines,
    export_described_transcript_html,
    export_descriptions_vtt,
)

VENDOR_DIR = Path(__file__).resolve().parent.parent / "player" / "vendor"
_VENDOR_FILES = [
    "ableplayer.min.js",
    "ableplayer.min.css",
    "jquery.slim.min.js",
    "ABLEPLAYER-LICENSE.txt",
    "JQUERY-LICENSE.txt",
]


def embed_code(folder_name: str, title: str) -> str:
    safe_title = html.escape(f"{title} — video with captions and audio description")
    return (
        f'<iframe src="{folder_name}/index.html"\n'
        f'  title="{safe_title}"\n'
        f'  width="800" height="620" allowfullscreen></iframe>'
    )


def export_player(project: dict, media_path: str | Path, output_dir: str | Path) -> dict:
    """Builds the player folder. Returns {folder, files, embed_code}."""
    media_path = Path(media_path)
    folder = Path(output_dir)
    assets = folder / "assets"
    assets.mkdir(parents=True, exist_ok=True)

    title = project.get("title") or "Video"
    lang = (project.get("intent") or {}).get("languages", ["en"])[0]

    files: list[str] = []

    media_name = f"media{media_path.suffix.lower()}"
    shutil.copy2(media_path, folder / media_name)
    files.append(media_name)

    export_cues_vtt(project, folder / f"captions.{lang}.vtt")
    files.append(f"captions.{lang}.vtt")
    has_descriptions = bool(project.get("description_cues"))
    if has_descriptions:
        export_descriptions_vtt(project, folder / f"descriptions.{lang}.vtt")
        files.append(f"descriptions.{lang}.vtt")
    export_described_transcript_html(project, folder / "transcript.html")
    files.append("transcript.html")

    # Cue metadata the VTT cannot carry (spec §9.1).
    player_meta = {
        "title": title,
        "ad_style": project.get("ad_style") or "standard",
        "voice_statement": "Descriptions are read by a synthetic voice, not a person.",
        "provenance": description_provenance_lines(project),
        "cues": [
            {
                "id": c["id"],
                "start": c["start"],
                "mode": c.get("mode"),
                "placement": c.get("placement"),
                "voice": c.get("voice"),
                "duration": c.get("clip_duration") or c.get("est_duration"),
            }
            for c in project.get("description_cues", [])
        ],
    }
    (folder / "player.json").write_text(json.dumps(player_meta, indent=2))
    files.append("player.json")

    for name in _VENDOR_FILES:
        shutil.copy2(VENDOR_DIR / name, assets / name)
        files.append(f"assets/{name}")

    description_track = (
        f'    <track kind="descriptions" src="descriptions.{lang}.vtt" srclang="{lang}">\n'
        if has_descriptions
        else ""
    )
    prov_block = "<br>".join(html.escape(l) for l in description_provenance_lines(project))
    index = f"""<!DOCTYPE html>
<html lang="{html.escape(lang)}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<link rel="stylesheet" href="assets/ableplayer.min.css">
<style>
  body {{ font-family: Arial, sans-serif; margin: 1rem; }}
  .voice-note {{ border: 1px solid #6f2fa6; border-radius: 6px; padding: .6rem .9rem; margin-block: 1rem; }}
  .provenance {{ font-size: .85rem; color: #444; margin-block-start: 1rem; }}
  a {{ color: #3a2b95; }}
</style>
</head>
<body>
<h1>{html.escape(title)}</h1>

<video id="player" data-able-player preload="auto" playsinline
  data-state-descriptions="on"
  data-desc-pause-default="on"
  data-heading-level="2"
  data-speed-icons="animals">
  <source type="video/mp4" src="{media_name}">
  <track kind="captions" src="captions.{lang}.vtt" srclang="{lang}" label="{html.escape(lang)}" default>
{description_track}</video>

<p class="voice-note">Descriptions on this page are read by a <strong>synthetic voice</strong>,
not a person. Use the player's Description preferences to change the voice, speed,
or whether the video pauses while a description is read.</p>

<p><a href="transcript.html">Read the described transcript</a> — every spoken line and
every description, in order, readable without playing the video.</p>

<p class="provenance">{prov_block}</p>

<script src="assets/jquery.slim.min.js"></script>
<script src="assets/ableplayer.min.js"></script>
</body>
</html>
"""
    (folder / "index.html").write_text(index, encoding="utf-8")
    files.append("index.html")

    readme = f"""{title} — accessible player folder
Made with DescriptorPro (Tech Inclusion Pro).

HOW TO USE
1. Upload this whole folder to your course site or any web server.
2. Embed it with:

{embed_code(folder.name, title)}

NOTES
- Everything is local: the page makes no network requests beyond its own folder.
- Opening index.html by double-click may not load captions — browsers block
  caption files on file:// pages. Upload the folder, or preview it through
  DescriptorPro.
- Descriptions are read by a synthetic voice (stated on the page). Viewers
  control voice, speed, visibility, and whether the video pauses for
  descriptions, in the player preferences.
- Credits: Able Player (MIT) and jQuery (MIT) are included under assets/
  with their license files.

{chr(10).join(description_provenance_lines(project))}
"""
    (folder / "README.txt").write_text(readme, encoding="utf-8")
    files.append("README.txt")

    return {"folder": str(folder), "files": files, "embed_code": embed_code(folder.name, title)}
