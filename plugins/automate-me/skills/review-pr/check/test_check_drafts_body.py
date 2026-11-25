"""Run: python3 check/test_check_drafts_body.py

The Body line here is the review summary in drafts.md, checked by check_drafts.py.
check_pr_body.py checks the author's PR description (body.md), a different artifact.
"""
import contextlib
import io
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_drafts import check_drafts  # noqa: E402

FAILS = []
URL = "https://github.com/o/r/pull/1/files#diff-aR"
APPROVAL = "Approving, since an existing refund still goes through and the comments are inline."
RATES = "The old config scored 20/40 and the new config scored 20/40, measured once."
THIRD = "The description still says the old timeout."


def drafts(body, verdict="approve"):
    lines = [
        "# PR review: t",
        "",
        "Risk.",
        "",
        f"## o/r#1 | {verdict}",
        "About: Adds a refund guard.",
        "",
        f"### question | a.py:3 | {URL}3",
        "The guard skips a prior refund. Can it count earlier refunds first?",
        "",
        f"Body: {body}",
        "",
        "## Totals",
        "Refuter: checked 1, reworded 0, dropped 0.",
    ]
    path = os.path.join(tempfile.mkdtemp(), "drafts.md")
    open(path, "w").write("\n".join(lines) + "\n")
    return path


def fails_of(body, verdict="approve"):
    with contextlib.redirect_stdout(io.StringIO()):
        return check_drafts(drafts(body, verdict))


def expect(name, body, ok, needle="", verdict="approve"):
    got = fails_of(body, verdict)
    if ok and got:
        FAILS.append(f"{name}: wanted pass, got {got}")
    if not ok and not any(needle in f for f in got):
        FAILS.append(f"{name}: wanted a failure naming '{needle}', got {got}")


expect("approval sentence only passes", APPROVAL, True)
expect("approval plus one pass-rate sentence passes", f"{APPROVAL} {RATES}", True)
expect("approval, pass rates, and a third sentence fails", f"{APPROVAL} {RATES} {THIRD}", False, "extra sentence")
expect("missing Body on approve with comments still fails", "", False, "approval stands")
expect("approve after plus one pass-rate sentence passes", f"{APPROVAL} {RATES}", True, verdict="approve after the gate runs")
expect("approve after with a third sentence fails", f"{APPROVAL} {RATES} {THIRD}", False, "extra sentence", verdict="approve after the gate runs")
expect("needs answer is not this cap", f"{APPROVAL} {RATES} {THIRD}", True, verdict="needs answer: should the timeout stay?")

if __name__ == "__main__":
    for line in FAILS:
        print(f"FAIL {line}")
    print("done" if not FAILS else f"{len(FAILS)} failed")
    sys.exit(1 if FAILS else 0)
