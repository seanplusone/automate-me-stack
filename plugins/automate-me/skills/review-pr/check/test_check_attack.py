"""Run: python3 check/test_check_attack.py"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_attack import check_attack  # noqa: E402

FAILS = []


def attack(verdict="needs fixes", tried=None, findings=None, held=None):
    tried = tried if tried is not None else [
        ("{\"passed\": true}", "True", "yes"),
    ]
    findings = findings if findings is not None else [
        ("F1", "report.py:4", "current", "accept returns True.", "{\"passed\": true}", "True"),
    ]
    held = [] if held is None else held
    lines = ["# Attack review: sample", "", f"Verdict: {verdict}", "", "## Tried"]
    for item, observed, broke in tried:
        lines += [f"- Input: {item}", f"  Observed: {observed}", f"  Broke: {broke}", ""]
    lines.append("## Findings")
    for fid, where, passes, claim, repro, observed in findings:
        lines += [
            f"### {fid} | {where} | passes: {passes}",
            claim,
            f"Repro: {repro}",
            f"Observed: {observed}",
            "",
        ]
    lines.append("## Held")
    if not held:
        lines.append("None")
    for item, observed in held:
        lines += [f"- Input: {item}", f"  Observed: {observed}", ""]
    path = os.path.join(tempfile.mkdtemp(), "attack.md")
    open(path, "w").write("\n".join(lines) + "\n")
    return path


def key(planted=True):
    path = os.path.join(tempfile.mkdtemp(), "key.md")
    body = "Planted: yes\nCatch: returns True\n" if planted else "Planted: no\n"
    open(path, "w").write(body)
    return path


def expect(name, fails, want):
    if fails != want:
        FAILS.append(f"{name}: wanted {want!r}, got {fails!r}")


expect("location is enough", check_attack(attack()), [])
expect(
    "repro is enough",
    check_attack(attack(findings=[("F1", "none", "current", "accept returns True.", "{\"ok\": false}", "True")])),
    [],
)
expect("zero breaking inputs", check_attack(attack(tried=[])), ["zero breaking inputs tried"])
expect(
    "input with no observed does not count",
    check_attack(attack(tried=[("{}", "", "yes")])),
    ["zero breaking inputs tried"],
)
expect(
    "finding with neither location nor repro",
    check_attack(attack(findings=[("F1", "none", "current", "something feels off.", "none", "none")])),
    ["F1 has no location and no repro"],
)
expect(
    "approve on a planted bug",
    check_attack(attack(verdict="approve", findings=[]), key(True)),
    ["approve on a case with a planted bug"],
)
expect(
    "needs fixes on a planted bug",
    check_attack(attack(verdict="needs fixes"), key(True)),
    [],
)
expect("approve with no planted key", check_attack(attack(verdict="approve", findings=[])), [])
held_try = [("{\"passed\": false}", "False", "no")]
expect(
    "held input omitted",
    check_attack(attack(tried=held_try, findings=[])),
    ["held list omits an input that did not break: {\"passed\": false}"],
)
expect(
    "held input listed",
    check_attack(attack(tried=held_try, findings=[], held=[("{\"passed\": false}", "False")], verdict="approve")),
    [],
)

if __name__ == "__main__":
    for item in FAILS:
        print(f"FAIL {item}")
    total = 10
    print(f"{total - len(FAILS)}/{total} passed")
    sys.exit(1 if FAILS else 0)
