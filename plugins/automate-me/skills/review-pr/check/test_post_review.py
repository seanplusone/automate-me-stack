import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_drafts import parse  # noqa: E402
from post_review import comments_only_body, plan  # noqa: E402

FAILS = []
URL = "https://github.com/o/r/pull/1/files#diff-aR3"


def write():
    text = "\n".join([
        "# PR review: t", "", "Risk.", "",
        "## o/r#1 | approve after the guard", "About: Adds uploads.",
        "Changes: 2 files: 2 source", "",
        f"### should fix | a.py:3 | {URL}",
        "The upload skips the size guard. Can it call the guard first?",
        "Step: measured | Post a 90 MB file",
        "Step: inferred | The guard never runs", "",
        "### question | PR | https://github.com/o/r/pull/1",
        "The body says retries are unchanged. The retry helper still uses the old timeout.", "",
        "Body: Approving; the comments are inline.",
        "", "## Totals", "Refuter: checked 2, reworded 0, dropped 0.",
    ]) + "\n"
    path = os.path.join(tempfile.mkdtemp(), "drafts.md")
    open(path, "w").write(text)
    return path


def expect(name, ok, got=""):
    if not ok:
        FAILS.append(f"{name}: {got}")


path = write()
pr = parse(path)[0][0]
review, replies = plan(pr)
expect("default plan still returns a review event", review is not None and review["event"] == "COMMENT", review)
expect("default plan keeps inline comments", len(review["comments"]) == 1, review)
expect("Changes line stays out of the review", "Changes" not in json.dumps(review), review)

review_only, replies_only = plan(pr, comments_only=True)
expect("comments-only has no review event", review_only is None, review_only)
expect("comments-only is one PR comment", replies_only == [(None, comments_only_body(pr))], replies_only)
body = replies_only[0][1]
expect("comments-only names the inline site", "a.py:3:" in body, body)
expect("comments-only names the PR finding", "PR:" in body, body)
expect("comments-only includes the comment text", "size guard" in body, body)
expect("comments-only leaves out Changes", "Changes:" not in body, body)
expect("comments-only leaves out Step lines", "Step:" not in body, body)

if __name__ == "__main__":
    for line in FAILS:
        print(f"FAIL {line}")
    print("done" if not FAILS else f"{len(FAILS)} failed")
    sys.exit(1 if FAILS else 0)
