"""Run: python3 check/test_check_attack.py"""
import os
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_attack import check_attack, parse_finding_heading, planted_bug  # noqa: E402

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
clean_approve = attack(verdict="approve", findings=[], tried=[("{}", "ok", "no")], held=[("{}", "ok")])
expect(
    "approve on a planted bug",
    check_attack(clean_approve, key(True)),
    ["approve on a case with a planted bug"],
)
expect(
    "needs fixes on a planted bug",
    check_attack(attack(verdict="needs fixes"), key(True)),
    [],
)
expect("approve with no planted key", check_attack(clean_approve), [])
expect(
    "approve with a located finding fails",
    "approve contradicts a break" in check_attack(attack(verdict="approve")),
    True,
)
expect(
    "approve with a break and no finding fails",
    "approve contradicts a break" in check_attack(attack(verdict="approve", findings=[])),
    True,
)
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
loose = os.path.join(tempfile.mkdtemp(), "attack.md")
open(loose, "w").write("\n".join([
    "# Attack review: loose", "", "Verdict: needs fixes", "", "## Tried",
    "- Input: within_cap(4)", "  Observed: True", "  Broke: No, 4 is allowed", "",
    "## Findings",
    "### F1 | head/cap.py:3",
    "The boundary is wrong.",
    "Repro: within_cap(5)",
    "Observed: False",
    "",
    "## Held",
    "4 stayed inside. Input within_cap(4) observed True.",
    "",
]))
expect("broke case and a prose held list", check_attack(loose), [])
planted_root = tempfile.mkdtemp()
case_dir = os.path.join(planted_root, "cases", "item-cap", "runs", "run-9")
os.makedirs(case_dir)
open(os.path.join(planted_root, "cases", "item-cap", "key.md"), "w").write("Planted: yes\nCatch: x\n")
approved = os.path.join(case_dir, "attack.md")
open(approved, "w").write(open(clean_approve).read())
expect("a case key is found without --key", check_attack(approved), ["approve on a case with a planted bug"])
expect("an empty --key does not disable the case", check_attack(approved, ""), ["approve on a case with a planted bug"])
dotted = os.path.join(tempfile.mkdtemp(), "key.md")
open(dotted, "w").write("Planted: yes.\n")
expect("planted yes with a period", planted_bug(dotted), True)
bare = os.path.join(tempfile.mkdtemp(), "attack.md")
open(bare, "w").write("Verdict: approve\n")
expect("approve with no inputs fails the check", "not a valid approve" in check_attack(bare), True)
started = time.perf_counter()
parse_finding_heading("### " + ("a" * 40000))
expect("a huge heading line stays fast", time.perf_counter() - started < 0.5, True)

if __name__ == "__main__":
    for item in FAILS:
        print(f"FAIL {item}")
    total = 18
    print(f"{total - len(FAILS)}/{total} passed")
    sys.exit(1 if FAILS else 0)
