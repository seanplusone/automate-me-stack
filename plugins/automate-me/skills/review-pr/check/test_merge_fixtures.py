"""Run: python3 check/test_merge_fixtures.py

Fixtures stand in for two agent passes on the planted cases. Paths differ
on purpose (head/cap.py vs cap.py). The merge must keep each planted bug.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_attack import norm_where  # noqa: E402
from merge_attacks import merge  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "fixtures", "passes")
FAILS = []
PLANTED = {
    "item-cap": ("cap.py", "3"),
    "trust-report": ("report.py", "4"),
    "word-score": ("score_review.py", "6"),
}


def expect(name, got, want):
    if got != want:
        FAILS.append(f"{name}: wanted {want!r}, got {got!r}")


def paths(case):
    folder = os.path.join(ROOT, case)
    return [os.path.join(folder, name) for name in ("codex.md", "claude.md")]


for case, where in PLANTED.items():
    doc = merge(paths(case))
    expect(case + " needs fixes", doc["verdict"], "needs fixes")
    kept = [norm_where(f["where"]) for f in doc["findings"]]
    expect(case + " keeps the planted line", where in kept, True)
    agents = []
    for finding in doc["findings"]:
        if norm_where(finding["where"]) == where:
            agents = finding["passes"]
    expect(case + " keeps both agents", agents, ["codex", "claude"])

raw_cap = open(os.path.join(ROOT, "item-cap", "codex.md")).read()
raw_other = open(os.path.join(ROOT, "item-cap", "claude.md")).read()
expect("fixture paths differ", "head/cap.py:3" in raw_cap and "cap.py:3" in raw_other, True)

clean = merge(paths("clean"))
expect("a clean pair approves", clean["verdict"], "approve")
expect("a clean pair has no finding", clean["findings"], [])

garbage = os.path.join(ROOT, "breaks", "garbage.md")
expect("unparseable output is not an approve", merge([garbage, paths("clean")[0]])["verdict"], "")
timeout = os.path.join(ROOT, "breaks", "timeout.md")
late = merge([timeout, paths("item-cap")[0]])
expect("a timeout keeps the other bug", late["verdict"], "needs fixes")
expect("a timeout keeps the planted line", norm_where(late["findings"][0]["where"]), ("cap.py", "3"))

if __name__ == "__main__":
    for item in FAILS:
        print(f"FAIL {item}")
    total = 15
    print(f"{total - len(FAILS)}/{total} passed")
    sys.exit(1 if FAILS else 0)
