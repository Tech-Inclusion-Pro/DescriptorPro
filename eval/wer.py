"""Word error rate, dependency-free (Levenshtein over normalized words).

WER = (substitutions + deletions + insertions) / reference word count.
Normalization lowercases and strips punctuation so "Hello," matches "hello" —
caption accuracy here means the right words, not the right commas (DCMP
punctuation quality is reviewed by a person, not scored by this script).
"""

from __future__ import annotations

import re


def normalize_words(text: str) -> list[str]:
    return [w for w in re.sub(r"[^\w'\s]", " ", text.lower()).split() if w]


def word_error_rate(reference: str, hypothesis: str) -> float:
    ref = normalize_words(reference)
    hyp = normalize_words(hypothesis)
    if not ref:
        return 0.0 if not hyp else 1.0

    previous = list(range(len(hyp) + 1))
    for i, ref_word in enumerate(ref, start=1):
        current = [i] + [0] * len(hyp)
        for j, hyp_word in enumerate(hyp, start=1):
            cost = 0 if ref_word == hyp_word else 1
            current[j] = min(
                previous[j] + 1,        # deletion
                current[j - 1] + 1,     # insertion
                previous[j - 1] + cost, # substitution / match
            )
        previous = current
    return previous[-1] / len(ref)
