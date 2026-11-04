"""Compares each PR in drafts.md with GitHub as it is now. Read-only.

Usage: python3 check/live_state.py <drafts.md>
Prints `<pr> <STATE> <head8> <verdict>` per PR. Exits 1 when a PR is closed or merged and its
verdict is not `scope:`, or, with a classes.json beside drafts.md, when the live head is not
the head the review read.
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_drafts import parse, read_classes  # noqa: E402


def live(pr):
    repo, _, num = pr.partition("#")
    out = subprocess.run(["gh", "pr", "view", num, "-R", repo, "--json", "state,headRefOid"],
                         capture_output=True, text=True, check=True).stdout
    view = json.loads(out)
    return view["state"], view["headRefOid"]


def problems(pr, verdict, state, head, classes):
    """What is wrong with one PR's review given its live state, as a list of messages."""
    found = []
    if state in ("CLOSED", "MERGED") and not verdict.startswith("scope:"):
        found.append(f"{pr} is {state}; change its verdict to 'scope: {state.lower()} since the review' and drop its comments")
    read_head = ((classes or {}).get(pr) or {}).get("head")
    if read_head and read_head != head:
        found.append(f"{pr} head moved from {read_head[:8]} to {head[:8]}; redo steps 6 to 9 for the changed files")
    return found


def main(argv):
    prs, _ = parse(argv[1])
    classes = read_classes(argv[1])
    bad = []
    for pr in prs:
        state, head = live(pr["pr"])
        print(pr["pr"], state, head[:8], pr["verdict"])
        bad += problems(pr["pr"], pr["verdict"], state, head, classes)
    for line in bad:
        print(f"FAIL {line}")
    return 1 if bad else 0


if __name__ == "__main__":
    from cli import usage_or_exit
    usage_or_exit(__doc__, sys.argv, 1)
    sys.exit(main(sys.argv))
