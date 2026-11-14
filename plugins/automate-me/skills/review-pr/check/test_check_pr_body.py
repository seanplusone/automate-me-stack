"""Run: python3 check/test_check_pr_body.py"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_pr_body import check_pr_body  # noqa: E402

FAILS = []


def write(text):
    path = os.path.join(tempfile.mkdtemp(), "body.md")
    open(path, "w").write(text)
    return path


def expect(name, text, ok, needle=""):
    got = check_pr_body(write(text))
    if ok and got:
        FAILS.append(f"{name}: wanted pass, got {got}")
    if not ok and not any(needle in f for f in got):
        FAILS.append(f"{name}: wanted a failure naming '{needle}', got {got}")


expect("short what-why-bullets passes",
       "Adds a timeout to the checkout request.\n\n"
       "Without it, a hung provider leaves the tab spinning.\n\n"
       "- Return a 504 after 8 seconds.\n"
       "- Show the same error the retry path already uses.\n",
       True)

expect("empty body fails", "\n", False, "empty")

expect("one sentence and no list passes",
       "Fixes the typo in the logout label.\n",
       True)

expect("too many opening sentences fails",
       "Adds a timeout. It covers checkout. It also covers cart. It also covers search. It also covers help.\n\n- Add the timeout.\n",
       False, "opening has")

expect("word cap fails", "Adds a fix.\n\n" + " ".join(["word"] * 200) + "\n", False, "words, max")

expect("too many bullets fails",
       "Adds a timeout to the request.\n\n" + "\n".join(f"- Change item {i}." for i in range(7)) + "\n",
       False, "bullets, max")

expect("table fails",
       "Adds a timeout.\n\n| path | score |\n| --- | --- |\n| a | 1 |\n",
       False, "table")

expect("glossary heading fails",
       "Adds a timeout.\n\n## Glossary\n\nGate means a check.\n",
       False, "glossary")

expect("long fence fails",
       "Adds a timeout.\n\n```\n" + "\n".join(f"log line {i}" for i in range(9)) + "\n```\n",
       False, "fenced block")

expect("review-process phrase fails",
       "Adds a timeout.\n\nThis PR was reviewed by a staff engineer and a security staff member.\n",
       False, "review process")

expect("naming a review panel feature passes",
       "Adds an optional review panel for linked PRs.\n",
       True)

expect("the review panel as process notes fails",
       "Adds a timeout.\n\nThe review panel agreed this is fine.\n",
       False, "review process")

expect("e.g. is not a second sentence",
       "Adds a timeout for hung calls, e.g. a provider that never replies.\n\nThe tab stayed spinning.\n",
       True)

if __name__ == "__main__":
    for line in FAILS:
        print(f"FAIL {line}")
    print("done" if not FAILS else f"{len(FAILS)} failed")
    sys.exit(1 if FAILS else 0)
