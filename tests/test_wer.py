"""WER scoring (eval/wer.py)."""

from __future__ import annotations

from eval.wer import normalize_words, word_error_rate


def test_identical_is_zero():
    assert word_error_rate("Hello there, friend.", "hello there friend") == 0.0


def test_punctuation_and_case_ignored():
    assert normalize_words("Well — YES, I do!") == ["well", "yes", "i", "do"]


def test_substitution():
    assert word_error_rate("the cat sat", "the hat sat") == 1 / 3


def test_deletion_and_insertion():
    assert word_error_rate("one two three", "one three") == 1 / 3
    assert word_error_rate("one three", "one two three") == 1 / 2


def test_empty_reference():
    assert word_error_rate("", "") == 0.0
    assert word_error_rate("", "anything") == 1.0


def test_wer_can_exceed_one():
    assert word_error_rate("hi", "a b c d") > 1.0
