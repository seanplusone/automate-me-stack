import re


def passes(review):
    """A review passes when it names a bug and a line."""
    words = set(re.findall(r"[a-z0-9]+", review.lower()))
    return "bug" in words and "line" in words
