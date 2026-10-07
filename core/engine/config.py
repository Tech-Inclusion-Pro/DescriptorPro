"""One configuration object for pipeline limits and thresholds (spec §7.3, §7.10).

Values become user-visible settings later; stages must read them from here so
there is a single place to tune and to show in the UI.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class CaptionLimits:
    """DCMP Captioning Key / FCC-derived caption formatting limits."""

    max_lines: int = 2
    max_chars_per_line: int = 32
    min_cue_seconds: float = 1.0
    max_reading_rate_wpm: int = 180
    low_confidence_threshold: float = 0.6


@dataclass(frozen=True)
class VadConfig:
    """Silero VAD gating for speech recognition (spec §4: no captions drafted
    from silence; stops model hallucination in quiet stretches).

    Values match faster-whisper's VadOptions defaults on purpose: tighter
    silence windows fragment speech, and with word_timestamps=True the
    fragment edges drop words (measured 2026-10-07 — final words of a clip
    lost at min_silence 700 ms, intact at 2000 ms)."""

    enabled: bool = True
    threshold: float = 0.5
    min_silence_duration_ms: int = 2000
    speech_pad_ms: int = 400


@dataclass(frozen=True)
class GapLimits:
    """Gap detection for audio description placement."""

    min_gap_seconds: float = 1.5
    gap_guard_seconds: float = 0.15
    speech_rate_wpm: int = 160


@dataclass(frozen=True)
class VisualTrack:
    """Scene/slide sampling and keyframe choice (spec §7.4)."""

    # PySceneDetect content detector threshold (their 27.0 default is tuned
    # for cuts in filmed content; slides change less of the frame).
    scene_threshold: float = 27.0
    # Slide/text change detection: frames are compared on a 64×36 grayscale
    # grid; a change is a pixel delta above diff_threshold on more than
    # changed_fraction of the grid. A 64-bit perceptual hash was measured
    # too coarse for text-only slide builds (2026-10-07) — the text
    # disappears at 8×8 while the white background dominates the hash.
    diff_threshold: int = 25
    changed_fraction: float = 0.005
    # Sample cadence for the slide scan, and minimum segment length.
    hash_sample_seconds: float = 1.0
    min_segment_seconds: float = 2.0
    # Long segments also get one mid-segment keyframe.
    long_segment_seconds: float = 30.0
    # First stable frame: this far after the detected change.
    keyframe_settle_seconds: float = 0.5


@dataclass(frozen=True)
class NeedCheckConfig:
    """Need check per spec §7.6."""

    transcript_pad_seconds: float = 3.0
    # Direct fuzzy match threshold for OCR text against the transcript
    # before asking the model (0..1, difflib ratio).
    ocr_match_ratio: float = 0.8
    # Deictic phrases that point at the screen without naming what is there.
    deictic_en: tuple[str, ...] = (
        "as you can see",
        "as you see here",
        "this one here",
        "over there",
        "right here",
        "like this",
        "like so",
        "click this",
        "click here",
        "this button",
        "this slide",
        "this diagram",
        "this chart",
        "shown here",
        "you can see",
        "see here",
    )
    deictic_es: tuple[str, ...] = (
        "como pueden ver",
        "como puedes ver",
        "como ven aquí",
        "este de aquí",
        "allí",
        "aquí mismo",
        "como esto",
        "así",
        "haz clic aquí",
        "hagan clic aquí",
        "este botón",
        "esta diapositiva",
        "este diagrama",
        "esta gráfica",
        "que se muestra aquí",
    )


@dataclass(frozen=True)
class GuardrailsConfig:
    """Identity and objectivity rules (spec §7.5)."""

    # Interpretation terms: emotional/mental states inferred from appearance.
    # A match raises an `interpretation` flag; nothing is silently rewritten.
    interpretation_terms: tuple[str, ...] = (
        "furious", "angry", "sad", "happy", "happily", "excited", "nervous",
        "anxious", "bored", "confused", "frustrated", "worried", "scared",
        "afraid", "upset", "annoyed", "delighted", "depressed", "cheerful",
        "menacing", "threatening", "suspicious", "lovingly", "angrily",
        "nervously", "sadly", "enojado", "furioso", "triste", "feliz",
        "emocionado", "nervioso", "aburrido", "confundido", "frustrado",
        "preocupado", "asustado", "molesto", "contento", "deprimido",
    )
    # Identity categories that must never be inferred from appearance.
    identity_terms: tuple[str, ...] = (
        # race / ethnicity
        "white man", "white woman", "black man", "black woman", "asian",
        "hispanic", "latino", "latina", "caucasian", "african american",
        "middle eastern", "indian man", "indian woman",
        # age guesses
        "elderly", "old man", "old woman", "middle-aged", "young man",
        "young woman", "teenager", "in his twenties", "in her twenties",
        "in his thirties", "in her thirties", "in his forties", "in her forties",
        "in his fifties", "in her fifties", "años de edad",
        # disability / health inferred
        "disabled", "wheelchair-bound", "handicapped", "autistic",
        "down syndrome", "mentally ill", "blind man", "blind woman",
        "deaf man", "deaf woman",
        # religion inferred
        "muslim", "jewish", "christian", "hindu", "sikh",
    )
    # Camera language (allowed only when intent says content is filmmaking).
    camera_terms: tuple[str, ...] = (
        "the camera", "we see", "we can see", "the shot", "the frame",
        "cuts to", "pans to", "zooms in", "zooms out", "close-up on",
        "la cámara", "vemos", "podemos ver", "el plano",
    )


@dataclass(frozen=True)
class EngineConfig:
    captions: CaptionLimits = field(default_factory=CaptionLimits)
    vad: VadConfig = field(default_factory=VadConfig)
    visual: VisualTrack = field(default_factory=VisualTrack)
    need_check: NeedCheckConfig = field(default_factory=NeedCheckConfig)
    guardrails: GuardrailsConfig = field(default_factory=GuardrailsConfig)
    gaps: GapLimits = field(default_factory=GapLimits)
    transcript_window_pad_seconds: float = 3.0


DEFAULT_CONFIG = EngineConfig()
