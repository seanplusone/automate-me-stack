"""Run: python3 check/test_map_decisions.py"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_brief import check  # noqa: E402
from map_decisions import map_text  # noqa: E402

FAILS = []
HERE = os.path.dirname(os.path.abspath(__file__))
CASES = os.path.join(HERE, "..", "cases", "from-decisions")
SHAPE = os.path.join(HERE, "..", "..", "shape-idea", "cases")


def failed(text):
    return [name for name, items in check(text) if items]


def check_honest(name, brief):
    low = brief.lower()
    for needle in ("which tool must the run use", "who does the work", "one case that should pass"):
        if needle not in low:
            FAILS.append(f"{name} invented or dropped {needle}")
    if "write first: none" in low:
        FAILS.append(f"{name} invented write first: none")


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
    check_honest(name, brief)
    if name == "capped" and brief.lower().count("unknown: what comes back, a list or a page?") < 2:
        FAILS.append("capped open output is not both a slot and an Unknown")
    if name == "done" and "out of scope:" not in brief:
        FAILS.append("done brief dropped the later parked item")

for src in sorted(__import__("pathlib").Path(SHAPE).glob("*/runs/run-1/decisions.md")):
    name = src.parents[2].name
    brief = map_text(src.read_text())
    bad = failed(brief)
    if bad:
        FAILS.append(f"case {name}: {bad}")
        print(f"FAIL case {name}")
        for item in bad:
            print(f"  {item}")
    else:
        print(f"PASS case {name}")
    check_honest(name, brief)

if __name__ == "__main__":
    print(f"{'PASS' if not FAILS else 'FAIL'} map briefs")
    for item in FAILS:
        print(item)
    sys.exit(1 if FAILS else 0)
