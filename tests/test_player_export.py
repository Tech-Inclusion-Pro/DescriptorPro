"""Embeddable player export (exporters/player_exporter.py)."""

from __future__ import annotations

import json
import re
from pathlib import Path

from exporters.player_exporter import export_player
from tests.test_description_exports import project


def make_media(tmp_path) -> Path:
    media = tmp_path / "source.mp4"
    media.write_bytes(b"fake video bytes")
    return media


def test_folder_contains_spec_layout(tmp_path):
    result = export_player(project(), make_media(tmp_path), tmp_path / "week7-player")
    names = set(result["files"])
    for required in (
        "index.html", "media.mp4", "captions.en.vtt", "descriptions.en.vtt",
        "transcript.html", "player.json", "README.txt",
        "assets/ableplayer.min.js", "assets/ableplayer.min.css",
        "assets/jquery.slim.min.js", "assets/ABLEPLAYER-LICENSE.txt",
        "assets/JQUERY-LICENSE.txt",
    ):
        assert required in names, f"missing {required}"
    for name in names:
        assert (tmp_path / "week7-player" / name).exists()


def test_index_html_behavior_attributes(tmp_path):
    export_player(project(), make_media(tmp_path), tmp_path / "p")
    index = (tmp_path / "p" / "index.html").read_text()
    assert 'data-able-player' in index
    assert 'data-state-descriptions="on"' in index
    assert 'data-desc-pause-default="on"' in index
    assert 'kind="descriptions"' in index
    assert "synthetic voice" in index
    assert 'href="transcript.html"' in index
    assert "NOT yet reviewed by a person." in index  # provenance on the page


def test_page_references_no_external_resources(tmp_path):
    """Spec §9.3: no network requests of any kind from the player page.
    Every src/href/url() in the page and CSS must be relative."""
    export_player(project(), make_media(tmp_path), tmp_path / "p")
    index = (tmp_path / "p" / "index.html").read_text()
    refs = re.findall(r'(?:src|href)="([^"]+)"', index)
    assert refs, "expected resource references"
    for ref in refs:
        assert not ref.startswith(("http:", "https:", "//")), f"external reference: {ref}"
    css = (tmp_path / "p" / "assets" / "ableplayer.min.css").read_text()
    assert "url(" not in css  # verified upstream; guard against vendor bumps


def test_player_json_carries_extended_metadata(tmp_path):
    export_player(project(), make_media(tmp_path), tmp_path / "p")
    meta = json.loads((tmp_path / "p" / "player.json").read_text())
    by_id = {c["id"]: c for c in meta["cues"]}
    assert by_id["ad-0002"]["mode"] == "extended"
    assert by_id["ad-0002"]["placement"] == "before_content"
    assert "synthetic voice" in meta["voice_statement"]


def test_embed_code_iframe(tmp_path):
    result = export_player(project(), make_media(tmp_path), tmp_path / "week7-player")
    assert 'src="week7-player/index.html"' in result["embed_code"]
    assert "captions and audio description" in result["embed_code"]


def test_works_without_descriptions(tmp_path):
    proj = project(description_cues=[])
    result = export_player(proj, make_media(tmp_path), tmp_path / "p")
    assert "descriptions.en.vtt" not in result["files"]
    index = (tmp_path / "p" / "index.html").read_text()
    assert 'kind="descriptions"' not in index
