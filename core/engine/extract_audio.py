"""Audio extraction for the engine. extract_audio() in core.audio_extractor is
already a pure function (FFmpeg -> 16 kHz mono WAV); this module gives engine
callers a Qt-free import path. The QThread wrapper in core.audio_extractor is
not imported here.
"""

from core.audio_extractor import extract_audio

__all__ = ["extract_audio"]
