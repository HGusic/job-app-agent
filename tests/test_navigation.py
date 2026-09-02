"""Tests for multi-page navigation helpers."""

from src.navigation import is_next_label, is_submit_label


def test_next_labels():
    assert is_next_label("Next")
    assert is_next_label("Continue")
    assert is_next_label("Save and Continue")
    assert not is_next_label("Submit Application")


def test_submit_labels():
    assert is_submit_label("Submit")
    assert is_submit_label("Submit Application")
    assert is_submit_label("Apply Now")
    assert not is_submit_label("Next")
