import re


def passes(review):
    """A review passes when it names a file, a line number, and a failed input."""
    has_place = re.search(r"\w+\.\w+:\d+", review) is not None
    has_input = "input" in review.lower()
    return has_place and has_input
