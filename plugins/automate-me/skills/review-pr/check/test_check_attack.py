"""Run: python3 check/test_check_attack.py"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_attack import check_attack, parse_attack, planted_bug  # noqa: E402

FAILS = []
CHECKS = []


def expect(name, got, want):
    CHECKS.append(name)
    if got != want:
        FAILS.append(f"{name}: wanted {want!r}, got {got!r}")


def dump_raw(text):
    path = os.path.join(tempfile.mkdtemp(), "attack.md")
    open(path, "w").write(text)
    return path


def dump(data, prose=""):
    return dump_raw(prose + "\n```json\n" + json.dumps(data) + "\n```\n")


def approve():
    return {
        "verdict": "approve",
        "tried": [{"input": "empty", "broke": False, "observed": "ok"}],
        "findings": [],
    }


expect("a clean approve passes", check_attack(dump(approve())), [])
expect(
    "approve with a finding fails",
    "not a valid approve" in check_attack(dump({
        "verdict": "approve",
        "tried": [{"input": "within_cap(5)", "broke": True, "observed": "False"}],
        "findings": [{"file": "cap.py", "line": 3, "claim": "rejects 5", "repro": "within_cap(5)"}],
    })),
    True,
)
expect("markdown only does not parse", parse_attack(dump_raw("Verdict: approve | needs fixes\n"))["parsed"], False)
expect("broke true forces needs fixes", parse_attack(dump({
    "verdict": "approve",
    "tried": [
        {"input": "within_cap(5)", "broke": True, "observed": "False"},
        {"input": "within_cap(4)", "broke": False, "observed": "True"},
    ],
    "findings": [],
}))["verdict"], "needs fixes")
expect("missing observed is an error", parse_attack(dump_raw(
    '```json\n{"verdict": "approve", "tried": [{"input": "x", "broke": true}], "findings": []}\n```\n'
))["parsed"], False)
expect("prose with a path still approves", check_attack(dump(approve(), prose="See cap.py:3 in the diff.\nNone\n")), [])

key = os.path.join(tempfile.mkdtemp(), "key.md")
open(key, "w").write("Planted: yes.\n")
expect("planted yes with a period", planted_bug(key), True)

root = tempfile.mkdtemp()
case = os.path.join(root, "cases", "item-cap", "runs")
os.makedirs(case)
open(os.path.join(root, "cases", "item-cap", "key.md"), "w").write("Planted: yes\nCatch: x\n")
approved = os.path.join(case, "attack.md")
open(approved, "w").write(open(dump(approve())).read())
expect("a planted approve fails", check_attack(approved), ["approve on a case with a planted bug"])
expect("an empty key does not disable lookup", check_attack(approved, ""), ["approve on a case with a planted bug"])

raw = dump_raw("")
open(raw, "wb").write(b"\xff\xfe")
expect("non-utf8 is an error", parse_attack(raw)["errors"], ["file is not UTF-8"])

if __name__ == "__main__":
    for item in FAILS:
        print(f"FAIL {item}")
    print(f"{len(CHECKS) - len(FAILS)}/{len(CHECKS)} passed")
    sys.exit(1 if FAILS else 0)
