"""Run: python3 shared/test_check_writing.py"""
import contextlib
import io
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_writing import check_writing  # noqa: E402

FAILS = []


def fails_for(text):
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as f:
        f.write(text)
    with contextlib.redirect_stdout(io.StringIO()):
        return check_writing(f.name)


def expect(name, text, rule):
    found = fails_for(text)
    hit = any(rule in f for f in found) if rule else not found
    if not hit:
        FAILS.append(f"{name}: wanted {rule or 'no failure'}, got {found}")


expect("fancy is", "The script serves as the guard.\n", "W20")
expect("not just", "This is not just a rename but a behavior change.\n", "W21")
expect("not only", "It not only moves the file but rewrites it.\n", "W21")
expect("abstract noun", "That is the bedrock of the review.\n", "W22")
expect("abstract noun plural", "Both paradigms fail here.\n", "W22")
expect("new plain word", "Additionally, the path is wrong.\n", "W5")
expect("plain sentence passes", "The path is wrong at line 99.\n", None)
expect("but without not just", "It is not cached, but it is fast.\n", None)
expect("code span is skipped", "Call `ensureLoaded()` before the save.\n", None)
expect("code span ignored for sentence length",
       "Run `python3 check/size.py origin/master pr-123 --exclude '.claude/**' --exclude 'docs/**' --plan plan.tsv` first.\n",
       None)
expect("bad example is skipped", '- Bad: "This serves as the bedrock."\n', None)
expect("long dash still caught", "The pull runs on a schedule — not instantly.\n", "W1")
expect("arrow outside code still caught", "Save -> retry.\n", "W11")

if __name__ == "__main__":
    for f in FAILS:
        print(f"FAIL {f}")
    total = 13
    print(f"{total - len(FAILS)}/{total} passed")
    sys.exit(1 if FAILS else 0)
