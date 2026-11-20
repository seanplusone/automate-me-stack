"""Run: python3 check/test_map_decisions.py"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_brief import check  # noqa: E402
from map_decisions import map_text  # noqa: E402

FAILS = []
HERE = os.path.dirname(os.path.abspath(__file__))
CASES = os.path.join(HERE, "..", "cases", "from-decisions")


def failed(text):
    return [name for name, items in check(text) if items]


for name in ("done", "capped"):
    src = os.path.join(CASES, name, "decisions.md")
    brief = map_text(open(src).read())
    bad = failed(brief)
    open(os.path.join(CASES, name, "brief.md"), "w").write(brief)
    if bad:
        FAILS.append(f"{name}: {bad}")
        print(f"FAIL {name}")
        for item in bad:
            print(f"  {item}")
    else:
        print(f"PASS {name}")
    if name == "capped" and "unknown: what comes back, a list or a page?" not in brief.lower():
        FAILS.append("capped brief does not put the open output question in the brief")
    if name == "capped" and brief.lower().count("unknown: what comes back, a list or a page?") < 2:
        FAILS.append("capped open output is not both a slot and an Unknown")
    if name == "done" and "out of scope:" not in brief:
        FAILS.append("done brief dropped the later parked item")

if __name__ == "__main__":
    print(f"{2 - len([f for f in FAILS if f.startswith('done') or f.startswith('capped')])}/2 briefs passed the shape check")
    sys.exit(1 if FAILS else 0)
