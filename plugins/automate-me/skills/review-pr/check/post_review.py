"""Posts a checked drafts.md to GitHub, one review per PR, so posting is the same every time.

Usage: python3 check/post_review.py <drafts.md> [--submit] [--reviewer <login>]
Without --submit it only prints each payload. With --submit it adds the reviewer to each PR that
does not already have them, posts the review at the PR's current head, and checks that every
inline comment landed. Run it only when the user has said to post.

The event follows the verdict: `approve` posts APPROVE, `hold:` posts REQUEST_CHANGES, and
`approve after`, `needs answer:` or `scope:` post COMMENT. A `reply <id>` finding cannot go in a review, so it is
posted into that thread after the review. A `PR` finding has no line, so it is posted as a PR
comment after the review.
"""
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_drafts import parse  # noqa: E402

REPLY = re.compile(r"\| reply (\d+)$")


def gh(*args, payload=None):
    out = subprocess.run(["gh", "api", *args] + (["--input", "-"] if payload is not None else []),
                         input=json.dumps(payload) if payload is not None else None,
                         capture_output=True, text=True, check=True)
    return json.loads(out.stdout) if out.stdout.strip() else None


def event(verdict):
    if verdict == "approve":
        return "APPROVE"
    if verdict.startswith("hold:"):
        return "REQUEST_CHANGES"
    return "COMMENT"


def plan(pr):
    comments, replies = [], []
    for f in pr["findings"]:
        m = f["match"]
        if not m:
            continue
        body = " ".join(f["comment"])
        reply = REPLY.search(f["head"])
        if reply:
            replies.append((reply.group(1), body))
        elif m.group(2) == "PR":
            replies.append((None, body))
        else:
            path, line = m.group(2).rsplit(":", 1)
            comments.append({"path": path, "line": int(line), "side": "RIGHT", "body": body})
    review = {"event": event(pr["verdict"]), "comments": comments}
    if pr["body"]:
        review["body"] = pr["body"]
    return review, replies


def submit(pr, review, replies, reviewer):
    repo, _, num = pr["pr"].partition("#")
    head = gh(f"repos/{repo}/pulls/{num}")
    if reviewer and reviewer != head["user"]["login"] and reviewer not in [r["login"] for r in head["requested_reviewers"]]:
        gh("-X", "POST", f"repos/{repo}/pulls/{num}/requested_reviewers", "-f", f"reviewers[]={reviewer}")
    posted = gh("-X", "POST", f"repos/{repo}/pulls/{num}/reviews", payload=dict(review, commit_id=head["head"]["sha"]))
    landed = [c for c in gh("--paginate", f"repos/{repo}/pulls/{num}/comments?per_page=100")
              if c["pull_request_review_id"] == posted["id"]]
    for comment_id, body in replies:
        if comment_id is None:
            gh("-X", "POST", f"repos/{repo}/issues/{num}/comments", "-f", f"body={body}")
        else:
            gh("-X", "POST", f"repos/{repo}/pulls/{num}/comments/{comment_id}/replies", "-f", f"body={body}")
    ok = len(landed) == len(review["comments"])
    print(f"{'OK  ' if ok else 'FAIL'} {pr['pr']} {posted['state']} {posted['html_url']} "
          f"({len(landed)}/{len(review['comments'])} inline, {len(replies)} replies or PR comments)")
    return ok


def main(argv):
    path = argv[1]
    reviewer = argv[argv.index("--reviewer") + 1] if "--reviewer" in argv else None
    prs, _ = parse(path)
    ok = True
    for pr in prs:
        review, replies = plan(pr)
        if "--submit" in argv:
            ok = submit(pr, review, replies, reviewer) and ok
        else:
            print(pr["pr"], json.dumps(review, indent=1), "replies:", replies)
    return 0 if ok else 1


if __name__ == "__main__":
    from cli import usage_or_exit
    usage_or_exit(__doc__, sys.argv, 1)
    sys.exit(main(sys.argv))
