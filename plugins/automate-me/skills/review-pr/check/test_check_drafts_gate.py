"""Run: python3 check/test_check_drafts_gate.py"""
import contextlib
import io
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_drafts import check_drafts, read  # noqa: E402

FAILS = []
URL = "https://github.com/o/r/pull/1/files#diff-aR"
FIX = "The upload skips the size guard. Can it call the guard first?"
FOLLOW_UP = "Gate: follow-up | Add a size test."
BLOCKS = "Gate: blocks | Done requires the size guard."
STEPS = ["Step: measured | Post a 90 MB file", "Step: inferred | The guard never runs"]


def drafts(gate=FOLLOW_UP, tag="question", round_number=1, second_copy=False):
    verdict = "hold: drops the guard" if tag == "blocking" else "approve after the guard"
    lines = ["# PR review: t", "", "Risk.", "", f"## o/r#1 | {verdict}", "About: Adds uploads.", ""]
    steps = STEPS if tag in ("blocking", "should fix") else []
    lines += [f"### {tag} | a.py:3 | {URL}3", FIX, *steps]
    if gate:
        lines.append(gate)
    if second_copy:
        lines += ["", f"### {tag} | a.py:9 | {URL}9", FIX]
    lines += ["", "Body: See the inline comments.", "", "## Totals", "Refuter: checked 1, reworded 0, dropped 0."]
    if round_number is not None:
        lines.append(f"Round: {round_number}")
    return "\n".join(lines) + "\n"


def write(text):
    path = os.path.join(tempfile.mkdtemp(), "drafts.md")
    open(path, "w").write(text)
    return path


def expect(name, text, ok, needle=""):
    with contextlib.redirect_stdout(io.StringIO()):
        got = check_drafts(write(text))
    if ok and got:
        FAILS.append(f"{name}: wanted pass, got {got}")
    if not ok and not any(needle.lower() in f.lower() for f in got):
        FAILS.append(f"{name}: wanted a failure naming '{needle}', got {got}")


expect("follow-up question in round 1", drafts(), True)
expect("blocks on a blocking finding", drafts(BLOCKS, "blocking"), True)
expect("missing gate", drafts(""), False, "Gate")
expect("unknown gate", drafts("Gate: maybe | x"), False, "Gate")
expect("gate without separator", drafts("Gate: blocks", "blocking"), False, "Gate")
expect("gate without text", drafts("Gate: blocks |", "blocking"), False, "Gate")
expect("second copy needs no gate", drafts(second_copy=True), True)
expect("follow-up on a blocking finding", drafts(FOLLOW_UP, "blocking"), False, "follow-up")
expect("blocks on a should fix finding", drafts(BLOCKS, "should fix"), False, "blocks")
expect("round 2", drafts(round_number=2), True)
expect("round 3", drafts(round_number=3), False, "round")
expect("missing round", drafts(round_number=None), False, "Round")

doc = read(write(drafts()))
f = doc["prs"][0]["findings"][0]
if any(line.startswith("Gate:") for line in f["comment"]):
    FAILS.append(f"Gate line leaked into the comment: {f['comment']}")
if f.get("gate") != ("follow-up", "Add a size test."):
    FAILS.append(f"gate parsed wrong: {f.get('gate')}")
if doc.get("round") != 1:
    FAILS.append(f"round parsed wrong: {doc.get('round')}")

skill = Path(__file__).resolve().parent.parent / "SKILL.md"
if "Does this meet the brief's Done, and does it break a stop rule?" not in skill.read_text():
    FAILS.append("SKILL.md is missing the reviewer question")

if __name__ == "__main__":
    for line in FAILS:
        print(f"FAIL {line}")
    print("done" if not FAILS else f"{len(FAILS)} failed")
    sys.exit(1 if FAILS else 0)
