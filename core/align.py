"""Forced-alignment fallback (plan P1): give word timestamps to cues whose
speech backend produced text without them, so DCMP formatting can split cues
honestly instead of guessing.

How: transcribe the audio once with a small faster-whisper model (word
timestamps on), then anchor each cue's known words to the hypothesis words by
normalized-text matching (difflib). Anchored words take the model's timing
and confidence; words between anchors get timing interpolated proportionally
by character length. No new runtime dependencies.

Qt-free; mutates the cue dicts it is given (fills `words`), returns nothing.
"""

from __future__ import annotations

import re
from difflib import SequenceMatcher

from core.engine.progress import CancelToken, NullProgress, ProgressReporter

_WINDOW_PAD_SECONDS = 1.0
_INTERPOLATED_CONFIDENCE = 0.7  # under 1.0, above the low-confidence flag line


def _normalize(word: str) -> str:
    return re.sub(r"[^\w']", "", word.lower())


def _match_words(ref: list[str], hyp: list[dict]) -> list[dict | None]:
    """For each reference word, the matching hypothesis word dict or None.
    Matching is on normalized text via longest-common-subsequence blocks, so
    small recognition errors only lose their own word, not the whole cue."""
    ref_norm = [_normalize(w) for w in ref]
    hyp_norm = [_normalize(h["w"]) for h in hyp]
    out: list[dict | None] = [None] * len(ref)
    matcher = SequenceMatcher(a=ref_norm, b=hyp_norm, autojunk=False)
    for block in matcher.get_matching_blocks():
        for offset in range(block.size):
            out[block.a + offset] = hyp[block.b + offset]
    return out


def _interpolate(words: list[dict], start: float, end: float) -> None:
    """Fill s/e on words lacking them, spreading each unanchored run between
    its anchored neighbours proportionally by word length."""
    i = 0
    n = len(words)
    while i < n:
        if words[i].get("s") is not None:
            i += 1
            continue
        run_start = i
        while i < n and words[i].get("s") is None:
            i += 1
        left = words[run_start - 1]["e"] if run_start > 0 else start
        right = words[i]["s"] if i < n else end
        run = words[run_start:i]
        total_chars = sum(len(w["w"]) for w in run) or 1
        t = left
        span = max(right - left, 0.0)
        for w in run:
            share = span * len(w["w"]) / total_chars
            w["s"] = round(t, 3)
            w["e"] = round(t + share, 3)
            t += share


def align_words(
    audio_path: str,
    cues: list[dict],
    language: str | None = None,
    model_size: str = "base",
    *,
    progress: ProgressReporter | None = None,
    cancel: CancelToken | None = None,
) -> None:
    progress = progress or NullProgress()
    cancel = cancel or CancelToken()
    if not cues:
        return

    hypothesis = _transcribe_hypothesis(audio_path, language, model_size, cancel)
    fill_words_from_hypothesis(cues, hypothesis)
    progress.status(f"Aligned word timing for {len(cues)} cues.")


def _transcribe_hypothesis(
    audio_path: str, language: str | None, model_size: str, cancel: CancelToken
) -> list[dict]:
    from faster_whisper import WhisperModel

    model = WhisperModel(model_size, device="auto", compute_type="int8")
    cancel.raise_if_cancelled()
    segments, _info = model.transcribe(
        audio_path, language=language, word_timestamps=True, vad_filter=True
    )
    hypothesis: list[dict] = []
    for seg in segments:
        cancel.raise_if_cancelled()
        for word in seg.words or []:
            hypothesis.append(
                {
                    "w": word.word.strip(),
                    "s": round(word.start, 3),
                    "e": round(word.end, 3),
                    "p": round(word.probability, 3),
                }
            )
    return hypothesis


def fill_words_from_hypothesis(cues: list[dict], hypothesis: list[dict]) -> None:
    """Pure core of align_words, separated so tests need no model."""
    for cue in cues:
        ref_words = cue["text"].split()
        if not ref_words:
            continue
        window = [
            h
            for h in hypothesis
            if h["e"] > cue["start"] - _WINDOW_PAD_SECONDS
            and h["s"] < cue["end"] + _WINDOW_PAD_SECONDS
        ]
        matches = _match_words(ref_words, window)
        words = []
        for ref, match in zip(ref_words, matches):
            if match is not None:
                words.append({"w": ref, "s": match["s"], "e": match["e"], "p": match["p"]})
            else:
                words.append({"w": ref, "s": None, "e": None, "p": _INTERPOLATED_CONFIDENCE})
        _interpolate(words, cue["start"], cue["end"])
        cue["words"] = words
