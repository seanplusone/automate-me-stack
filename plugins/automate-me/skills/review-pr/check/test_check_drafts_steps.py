"""Run: python3 check/test_check_drafts_steps.py"""
import contextlib
import html
import io
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_drafts import check_drafts, read  # noqa: E402
from render_page import render  # noqa: E402

FAILS = []
URL = "https://github.com/o/r/pull/1/files#diff-aR"
FIX = "The upload skips the size guard. Can it call the guard first?"


def drafts(*findings):
    """Each finding is (tag, line, steps) where steps are raw 'Step:' lines; the comment text is shared per tag."""
    verdict = "hold: drops the guard" if any(t == "blocking" for t, _, _ in findings) else "approve after the guard"
    lines = ["# PR review: t", "", "Risk.", "", f"## o/r#1 | {verdict}", "About: Adds uploads.", ""]
    for tag, line, steps in findings:
        lines += [f"### {tag} | a.py:{line} | {URL}{line}", FIX if tag != "nit" else "Rename this variable.", *steps, ""]
    lines += ["Body: Approving; the comments are inline.", "", "## Totals", "Refuter: checked 1, reworded 0, dropped 0."]
    return "\n".join(lines) + "\n"


def write(text):
    path = os.path.join(tempfile.mkdtemp(), "drafts.md")
    open(path, "w").write(text)
    return path


def fails_of(text):
    with contextlib.redirect_stdout(io.StringIO()):
        return check_drafts(write(text))


def expect(name, text, ok, needle=""):
    got = fails_of(text)
    if ok and got:
        FAILS.append(f"{name}: wanted pass, got {got}")
    if not ok and not any(needle in f for f in got):
        FAILS.append(f"{name}: wanted a failure naming '{needle}', got {got}")


def step(label, text="The caller posts a file"):
    return f"Step: {label} | {text}"


two = [step("measured", "Post a 90 MB file"), step("inferred", "The guard never runs")]

expect("should fix with 0 steps", drafts(("should fix", 3, [])), False, "needs 2 to 6")
expect("should fix with 2 steps", drafts(("should fix", 3, two)), True)
expect("blocking with 2 steps", drafts(("blocking", 3, two)), True)
expect("7 steps", drafts(("should fix", 3, [step("inferred", f"step {i}") for i in range(7)])), False, "needs 2 to 6")
expect("bad label", drafts(("should fix", 3, two + ["Step: guessed | The guard never runs"])), False, "Step line must be")
expect("missing separator", drafts(("should fix", 3, two + ["Step: measured The guard never runs"])), False, "Step line must be")
expect("21-word step", drafts(("should fix", 3, [step("measured", " ".join(["word"] * 21)), two[1]])), False, "21 words")
expect("20-word step", drafts(("should fix", 3, [step("measured", " ".join(["word"] * 20)), two[1]])), True)
expect("nit with a step", drafts(("nit", 3, [step("inferred")])), False, "nits take none")
expect("question without steps", drafts(("question", 3, [])), True)
expect("question with 1 step", drafts(("question", 3, [step("inferred")])), False, "question takes")
expect("question with 2 steps", drafts(("question", 3, two)), True)
expect("second copy needs no steps", drafts(("should fix", 3, two), ("should fix", 9, [])), True)
expect("first copy still needs steps", drafts(("should fix", 3, []), ("should fix", 9, two)), False, "needs 2 to 6")

doc = read(write(drafts(("should fix", 3, two))))
f = doc["prs"][0]["findings"][0]
if f["steps"] != [("measured", "Post a 90 MB file"), ("inferred", "The guard never runs")]:
    FAILS.append(f"steps parsed wrong: {f['steps']}")
if any("Step" in c for c in f["comment"]):
    FAILS.append(f"Step line leaked into the comment: {f['comment']}")

tricky = 'Call `f("x")` (done) -> [a|b]: $5 <tag> & more'
page = render(write(drafts(("should fix", 3, [step("measured", tricky), two[1]]))))
source = html.unescape(page.split('<pre class="mermaid">')[1].split("</pre>")[0])
for name, needle in [("explain panel", 'class="explain"'), ("mermaid block", 'class="mermaid"'), ("flowchart", "flowchart TD"),
                     ("quote entity", "#quot;"), ("quoted label", 's1["1. Call f(#quot;x#quot;) (done) -#gt; [a|b]: $5 #lt;tag#gt; & more"]:::measured'),
                     ("measured chip", 'class="chip measured"'), ("legend", "Solid: measured. Dashed: inferred."),
                     ("dashed class", ":::inferred")]:
    if needle not in page and needle not in source:
        FAILS.append(f"render missing {name}: {needle}")
if "`" in source:
    FAILS.append("backtick left in the mermaid source")
if "Explain</summary>" in render(write(drafts(("should fix", 3, [])))):
    FAILS.append("explain panel rendered with no steps")

if __name__ == "__main__":
    for line in FAILS:
        print(f"FAIL {line}")
    print("done" if not FAILS else f"{len(FAILS)} failed")
    sys.exit(1 if FAILS else 0)
