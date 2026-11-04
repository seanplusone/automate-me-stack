"""Run: python3 check/test_verdicts.py"""
import contextlib
import io
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_drafts import check_drafts, parse  # noqa: E402
from post_review import event  # noqa: E402
from render_page import render  # noqa: E402
from summary import groups, summary  # noqa: E402

FAILS = []
ASK = "should a read-only admin open events?"


def expect(name, got, want):
    if got != want:
        FAILS.append(f"{name}: wanted {want!r}, got {got!r}")


def drafts(verdict, *findings):
    lines = ["# PR review: t", "", "Risk.", "", f"## o/r#1 | {verdict}", "About: Adds events.", ""]
    for tag, line in findings:
        lines += [f"### {tag} | a.py:{line} | https://github.com/o/r/pull/1/files#diff-aR{line}",
                  "The guard is skipped here. Can it call the guard first?", ""]
    lines += ["Body: Waiting on the answer.", "", "## Totals", "Refuter: checked 1, reworded 0, dropped 0."]
    path = os.path.join(tempfile.mkdtemp(), "drafts.md")
    open(path, "w").write("\n".join(lines) + "\n")
    return path


def checked(path):
    with contextlib.redirect_stdout(io.StringIO()):
        return check_drafts(path)


path = drafts(f"needs answer: {ASK}")
expect("check accepts needs answer", checked(path), [])
expect("check rejects an empty question", bool(checked(drafts("needs answer: "))), True)
expect("blocking still needs hold", bool(checked(drafts(f"needs answer: {ASK}", ("blocking", 3)))), True)
expect("summary groups the question", groups(parse(path)[0]),
       [("Needs an answer", [("https://github.com/o/r/pull/1", "#1", ASK)])])
expect("markdown line", summary(path), f"**Needs an answer**\n- [#1](https://github.com/o/r/pull/1), needs an answer: {ASK}")
expect("slack line", summary(path, "slack"), f"*Needs an answer*\n• <https://github.com/o/r/pull/1|#1>, needs an answer: {ASK}")
page = render(path)
expect("slack escapes markup in the question", summary(drafts("needs answer: is a < b & c > d?"), "slack").splitlines()[-1].endswith("is a &lt; b &amp; c &gt; d?"), True)
expect("markdown escapes links in the question", summary(drafts("needs answer: is [x] a *list*?")).splitlines()[-1].endswith("is \\[x\\] a \\*list\\*?"), True)
expect("page has the summary box", "Summary message" in page, True)
expect("badge label", "Needs an answer" in page, True)
expect("badge sentence", f"Waits on an answer: {ASK}" in page, True)
expect("event", event(f"needs answer: {ASK}"), "COMMENT")

gone = drafts("blocked by o/r#2")
expect("check rejects blocked by", any("verdict must be" in f and "<repo>#<n>" not in f for f in checked(gone)), True)
expect("summary has no Blocked group", "Blocked" in [name for name, _ in groups(parse(drafts("approve"))[0])], False)
expect("summary drops a rejected verdict", groups(parse(gone)[0]), [])

for line in FAILS:
    print(f"FAIL {line}")
print("done" if not FAILS else f"{len(FAILS)} failed")
sys.exit(1 if FAILS else 0)
