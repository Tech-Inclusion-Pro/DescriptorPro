"""Regression canary: the existing PyQt app must keep importing cleanly.

This does not open windows. It imports the app modules the same way main.py
does, so a Describe Studio refactor that breaks the PyQt app fails here first.
Skipped automatically where PyQt6 is not installed (CI without Qt).
"""

import importlib

import pytest

pytest.importorskip("PyQt6")


APP_MODULES = [
    "core.models",
    "core.audio_extractor",
    "core.transcriber",
    "core.ollama_processor",
    "core.project_store",
    "core.i18n",
    "exporters.srt_exporter",
    "exporters.vtt_exporter",
    "exporters.txt_exporter",
    "app.main_window",
    "app.login_window",
    "app.left_panel",
    "app.export_panel",
]


@pytest.mark.parametrize("module_name", APP_MODULES)
def test_module_imports(module_name: str) -> None:
    importlib.import_module(module_name)
