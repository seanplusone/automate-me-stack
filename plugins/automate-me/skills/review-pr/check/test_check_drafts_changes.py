"""Run: python3 check/test_check_drafts_changes.py"""
import contextlib
import html
import io
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_drafts import check_drafts, read  # noqa: E402
from live_state import problems  # noqa: E402
from render_page import render  # noqa: E402

FAILS = []
URL = "https://github.com/o/r/pull/1/files#diff-aR"
CHANGES = "2 files: 1 source, 1 generated"
CLASSES = {"o/r#1": {"head": "a" * 40, "files": {"app/a.php": "source", "public/index.js": "generated"}}}


def drafts(path, changes=CHANGES):
    lines = ["# PR review: t", "", "Risk.", "", "## o/r#1 | approve after the guard", "About: Adds uploads."]
    if changes:
        lines.append(f"Changes: {changes}")
    lines += ["", f"### question | {path}:3 | {URL}3", "The upload skips the size guard. Can it call the guard first?", "",
              "Body: Approving; the comments are inline.", "", "## Totals", "Refuter: checked 1, reworded 0, dropped 0."]
    return "\n".join(lines) + "\n"


def run(text, classes=CLASSES):
    d = tempfile.mkdtemp()
    path = os.path.join(d, "drafts.md")
    open(path, "w").write(text)
    if classes is not None:
        json.dump(classes, open(os.path.join(d, "classes.json"), "w"))
    with contextlib.redirect_stdout(io.StringIO()):
        return check_drafts(path), path


def expect(name, text, ok, needle="", classes=CLASSES):
    got, _ = run(text, classes)
    if ok and got:
        FAILS.append(f"{name}: wanted pass, got {got}")
    if not ok and not any(needle in f for f in got):
        FAILS.append(f"{name}: wanted a failure naming '{needle}', got {got}")


expect("source path passes", drafts("app/a.php"), True)
expect("generated path fails", drafts("public/index.js"), False, "generated file")
expect("missing Changes line fails", drafts("app/a.php", changes=""), False, "missing the 'Changes:' line")
expect("Changes line that differs fails", drafts("app/a.php", changes="9 files: 9 source"), False, "does not match classes.json")
expect("no classes.json, no Changes line needed", drafts("app/a.php", changes=""), True, classes=None)
expect("no classes.json, hashed name fails", drafts("public/index-D1CdT9Mr.js"), False, "generated file", classes=None)
expect("no classes.json, gz fails", drafts("public/app.js.gz"), False, "generated file", classes=None)
expect("no classes.json, plain path passes", drafts("public/index.js"), True, classes=None)
expect("hashed name unlisted in classes.json fails", drafts("public/index-D1CdT9Mr.js"), False, "generated file")

_, path = run(drafts("app/a.php"))
if read(path)["prs"][0]["changes"] != CHANGES:
    FAILS.append(f"Changes not parsed: {read(path)['prs'][0]['changes']!r}")
if any("Changes" in c for f in read(path)["prs"][0]["findings"] for c in f["comment"]):
    FAILS.append("Changes line leaked into a comment")
page = render(path)
if f'<p class="changes">{html.escape(CHANGES)}</p>' not in page:
    FAILS.append("render did not show the Changes line")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from post_review import plan  # noqa: E402

review, _ = plan(read(path)["prs"][0])
if "Changes" in json.dumps(review):
    FAILS.append("post_review payload carries the Changes line")

pr_level = drafts("app/a.php").replace("### question | app/a.php:3 | " + URL + "3", "### question | PR | https://github.com/o/r/pull/1")
expect("PR-level finding passes", pr_level, True)
_, path = run(pr_level)
review, replies = plan(read(path)["prs"][0])
if review["comments"] or [c for c, _ in replies] != [None]:
    FAILS.append(f"post_review did not turn the PR-level finding into a PR comment: {review['comments']} {replies}")
if "Posted on the PR" not in render(path):
    FAILS.append("render did not say the PR-level finding is posted on the PR")

head, moved = "a" * 40, "b" * 40
for name, args, want in [
    ("open at read head", ("o/r#1", "approve", "OPEN", head, CLASSES), 0),
    ("merged with approve", ("o/r#1", "approve", "MERGED", head, CLASSES), 1),
    ("merged with scope", ("o/r#1", "scope: merged since", "MERGED", head, CLASSES), 0),
    ("closed with hold", ("o/r#1", "hold: x", "CLOSED", head, None), 1),
    ("head moved", ("o/r#1", "approve", "OPEN", moved, CLASSES), 1),
    ("head moved without classes", ("o/r#1", "approve", "OPEN", moved, None), 0),
]:
    got = len(problems(*args))
    if got != want:
        FAILS.append(f"live_state {name}: wanted {want} problems, got {got}")

if __name__ == "__main__":
    for line in FAILS:
        print(f"FAIL {line}")
    print("done" if not FAILS else f"{len(FAILS)} failed")
    sys.exit(1 if FAILS else 0)
