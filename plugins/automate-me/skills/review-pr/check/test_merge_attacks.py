"""Run: python3 check/test_merge_attacks.py"""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from check_attack import check_attack, parse_attack  # noqa: E402
from merge_attacks import main as merge_main, merge  # noqa: E402

FAILS = []
CHECKS = []


def expect(name, got, want):
    CHECKS.append(name)
    if got != want:
        FAILS.append(f"{name}: wanted {want!r}, got {got!r}")


def write(text, name="pass.md"):
    path = os.path.join(tempfile.mkdtemp(), name)
    open(path, "w").write(text)
    return path


def block(data, name="pass.md"):
    return write("\n```json\n" + json.dumps(data) + "\n```\n", name)


def finding(file, line, claim, repro):
    return {"file": file, "line": line, "claim": claim, "repro": repro}


def bug(file="cap.py", line=3, claim="rejects 5", repro="within_cap(5)"):
    return {
        "verdict": "needs fixes",
        "tried": [
            {"input": "within_cap(5)", "broke": True, "observed": "False"},
            {"input": "within_cap(4)", "broke": False, "observed": "True"},
        ],
        "findings": [finding(file, line, claim, repro)],
    }


def clean():
    return {
        "verdict": "approve",
        "tried": [{"input": "empty", "broke": False, "observed": "ok"}],
        "findings": [],
    }


doc = merge([
    block(bug("head/cap.py", 3, "the comparison rejects 5", "within_cap(5)"), "codex.md"),
    block(bug("cap.py", 3, "five is outside the cap", "call within_cap on 5"), "claude.md"),
])
expect("two paths are one finding", len(doc["findings"]), 1)
expect("both claims are kept", "the comparison rejects 5" in doc["findings"][0]["claim"] and "five is outside the cap" in doc["findings"][0]["claim"], True)
expect("both agents are kept", doc["findings"][0]["passes"], ["codex", "claude"])
expect("a bug is needs fixes", doc["verdict"], "needs fixes")

nulled = merge([
    block(bug("cap.py", 3, "rejects 5", "within_cap(5)")),
    block({
        "verdict": "needs fixes",
        "tried": [],
        "findings": [finding("none", None, "the cap is wrong", "within_cap(5)")],
    }),
])
expect("a null line is not dropped", any(item["line"] is None for item in nulled["findings"]), True)

out = os.path.join(tempfile.mkdtemp(), "attack.md")
expect("the merge writes", merge_main(["merge", "--out", out, block(bug()), block(clean())]), 0)
expect("the merged file checks", check_attack(out), [])
expect("one bug and one approve is needs fixes", parse_attack(out)["verdict"], "needs fixes")

expect("garbage plus a clean pass is not an approve", merge_main([
    "merge", "--out", os.path.join(tempfile.mkdtemp(), "a.md"),
    write("Ship it. The tests pass.\n"), block(clean()),
]), 1)
expect("a timeout plus a bug stays needs fixes", merge_main([
    "merge", "--out", os.path.join(tempfile.mkdtemp(), "a.md"),
    write("Parse: timeout\n"), block(bug()),
]), 0)
expect("a missing pass is not an approve", merge_main([
    "merge", "--out", os.path.join(tempfile.mkdtemp(), "a.md"),
    os.path.join(tempfile.mkdtemp(), "missing.md"), block(clean()),
]), 1)

bad = os.path.join(tempfile.mkdtemp(), "bad.md")
open(bad, "wb").write(b"\xff\xfe")
expect("non-utf8 is not an approve", merge_main([
    "merge", "--out", os.path.join(tempfile.mkdtemp(), "a.md"), bad, block(clean()),
]), 1)
expect("an option-like name is an error", merge_main(["merge", "--out", out, "--x.md"]), 2)
expect("a name after -- is a pass", merge_main([
    "merge", "--out", os.path.join(tempfile.mkdtemp(), "a.md"), "--", block(clean(), "--x.md"),
]), 0)
expect("a repeated out is an error", merge_main(["merge", "--out", out, "--out", out, block(clean())]), 2)

ran = subprocess.run(
    [sys.executable, os.path.join(HERE, "merge_attacks.py"), "--help"],
    capture_output=True, text=True,
)
expect("help exits 0", ran.returncode, 0)

if __name__ == "__main__":
    for item in FAILS:
        print(f"FAIL {item}")
    print(f"{len(CHECKS) - len(FAILS)}/{len(CHECKS)} passed")
    sys.exit(1 if FAILS else 0)
