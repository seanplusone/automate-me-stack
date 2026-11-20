"""Run: python3 check/test_break.py

Adversarial decisions.md files. 00_valid_control.md passes.
22_no_map_line.md passes: the control also has no map line, so a map is not required.
26_open_6_but_none_cap.md passes: it has five non-slot opens, not six, and stop is done
with every slot decided. Extra opens do not block done. The open cap is more than five
non-slot opens, and only for an open-cap stop.
14_open_and_turncap_ok_but_6_open_items.md fails: the name says six opens can be ok, but
this file stops open-cap on turn 1. That stop is never valid on turn 1, and it has five
non-slot opens, which is not more than five.
lenient.md and the other numbered files fail.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_decisions import check  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURES = os.path.join(HERE, "fixtures")

# Files that are valid under the current rules. See the module docstring.
PASS = {
    "00_valid_control.md",
    "22_no_map_line.md",
    "26_open_6_but_none_cap.md",
}

FAILS = []
RAN = []


def run(name):
    path = os.path.join(FIXTURES, name)
    try:
        bad = [label for label, items in check(open(path).read()) if items]
        crashed = None
    except Exception as exc:
        bad, crashed = [], exc
    return bad, crashed


for name in sorted(os.listdir(FIXTURES)):
    if not name.endswith(".md"):
        continue
    RAN.append(name)
    bad, crashed = run(name)
    want_pass = name in PASS
    if crashed is not None:
        FAILS.append(f"{name}: crashed: {crashed}")
        print(f"FAIL {name}: crashed: {crashed}")
        continue
    ok = (not bad) if want_pass else bool(bad)
    print(f"{'PASS' if ok else 'FAIL'} {name}: {'ok' if not bad else ', '.join(bad)}")
    if not ok:
        FAILS.append(f"{name}: wanted {'pass' if want_pass else 'fail'}, got {bad}")

if __name__ == "__main__":
    print(f"{len(RAN) - len(FAILS)}/{len(RAN)} fixtures matched")
    sys.exit(1 if FAILS else 0)
