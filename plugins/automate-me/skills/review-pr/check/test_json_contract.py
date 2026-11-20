"""Run: python3 check/test_json_contract.py

The markdown holes that three review rounds found. The JSON contract
closes each one, and a raw markdown pass is an error.
"""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from check_attack import check_attack, norm_location, parse_attack  # noqa: E402
from merge_attacks import merge  # noqa: E402
from score_case import score_planted  # noqa: E402

FAILS = []
CHECKS = []


def expect(name, got, want):
    CHECKS.append(name)
    if got != want:
        FAILS.append(f"{name}: wanted {want!r}, got {got!r}")


def write(text):
    path = os.path.join(tempfile.mkdtemp(), "pass.md")
    open(path, "w").write(text)
    return path


def block(data, prose=""):
    return write(prose + "\n```json\n" + json.dumps(data) + "\n```\n")


def clean():
    return {
        "verdict": "approve",
        "tried": [{"input": "empty", "broke": False, "observed": "ok"}],
        "findings": [],
    }


def finding(file, line, repro="within_cap(5)"):
    return {"file": file, "line": line, "claim": "within_cap(5) returns False", "repro": repro}


# A later false row does not erase an earlier true row.
expect("a later false row keeps the break", parse_attack(block({
    "verdict": "approve",
    "tried": [
        {"input": "within_cap(5)", "broke": True, "observed": "False"},
        {"input": "within_cap(4)", "broke": False, "observed": "True"},
    ],
    "findings": [],
}))["verdict"], "needs fixes")

# A 4-backtick wrapper must not hide the json block.
wrapped = write(
    "````markdown\n```json\n" + json.dumps({
        "verdict": "approve",
        "tried": [{"input": "within_cap(5)", "broke": True, "observed": "False"}],
        "findings": [finding("cap.py", 3)],
    }) + "\n```\n````\n"
)
expect("a 4-backtick wrapper still needs fixes", parse_attack(wrapped)["verdict"], "needs fixes")

# An outer markdown fence with the json inside is still readable.
outer = write(
    "```markdown\nnotes\n```json\n" + json.dumps(clean()) + "\n```\n```\n"
)
expect("an outer markdown fence is readable", parse_attack(outer)["verdict"], "approve")

# Raw markdown, including a template verdict line, does not parse and is not an approve.
raw = write(
    "Verdict: approve | needs fixes\n\n## Tried\n- Input: within_cap(5)\n  Broke: yes\n"
)
expect("raw markdown does not parse", parse_attack(raw)["parsed"], False)
expect("raw markdown is not an approve", check_attack(raw) != [], True)

# These spellings all name cap.py line 3. A null line with a repro is kept.
for label, file, line in (
    ("column", "cap.py:3:12", None),
    ("absolute", "/srv/checkout/cap.py:3", None),
    ("parent", "pkg/../cap.py:3", None),
    ("hash", "cap.py#L3", None),
):
    got = norm_location(file, line)
    expect(label + " names cap.py:3", got, ("cap.py", 3))
expect("none stays a null line", norm_location("none", None), ("", None))

merged = merge([
    block({"verdict": "needs fixes", "tried": [], "findings": [finding("cap.py:3:12", None)]}),
    block({"verdict": "needs fixes", "tried": [], "findings": [finding("/srv/checkout/cap.py", 3)]}),
    block({"verdict": "needs fixes", "tried": [], "findings": [finding("pkg/../cap.py#L3", None)]}),
    block({"verdict": "needs fixes", "tried": [], "findings": [
        {"file": "none", "line": None, "claim": "the cap is wrong", "repro": "within_cap(5)"},
    ]}),
])
located = [(item["file"], item["line"]) for item in merged["findings"]]
expect("spellings collapse to one line", located.count(("cap.py", 3)), 1)
expect("a null line is kept", ("", None) in located, True)

# A heading in prose is not rewritten and does not become a finding.
heading = write(
    "## Findings (all in cap.py:3)\nNone\n```json\n" + json.dumps(clean()) + "\n```\n"
)
expect("a heading in prose stays an approve", parse_attack(heading)["verdict"], "approve")
expect("the heading text is left alone", "Findings (all in cap.py:3)" in open(heading).read(), True)

# A denial on the key line does not keyword-pass.
key = os.path.join(tempfile.mkdtemp(), "key.md")
open(key, "w").write("Planted: yes\nWhere: cap.py:3\nCatch: within_cap(5) | returns False\n")
denied = block({
    "verdict": "needs fixes",
    "tried": [{"input": "within_cap(5)", "broke": False, "observed": "True"}],
    "findings": [{
        "file": "cap.py", "line": 3,
        "claim": "within_cap(5) returns False is not a bug and does not matter",
        "repro": "within_cap(5)",
    }],
})
expect(
    "a denial does not keyword-pass",
    score_planted(key, denied, environ={"PATH": "/nonexistent"}),
    1,
)

# A real catch still keyword-passes when no CLI exists.
caught = block({
    "verdict": "needs fixes",
    "tried": [{"input": "within_cap(5)", "broke": True, "observed": "False"}],
    "findings": [finding("cap.py", 3)],
})
expect("a catch keyword-passes with no CLI", score_planted(key, caught, environ={"PATH": "/nonexistent"}), 0)
expect("a column location is scored", score_planted(key, block({
    "verdict": "needs fixes",
    "tried": [{"input": "within_cap(5)", "broke": True, "observed": "False"}],
    "findings": [finding("cap.py:3:12", None)],
}), environ={"PATH": "/nonexistent"}), 0)
expect("a null line with a repro is scored", score_planted(key, block({
    "verdict": "needs fixes",
    "tried": [{"input": "within_cap(5)", "broke": True, "observed": "False"}],
    "findings": [{"file": "none", "line": None, "claim": "within_cap(5) returns False", "repro": "within_cap(5)"}],
}), environ={"PATH": "/nonexistent"}), 0)
expect("a missing observed line is an error", parse_attack(write(
    '```json\n{"verdict": "approve", "tried": [{"input": "within_cap(5)", "broke": true}], "findings": []}\n```\n'
))["parsed"], False)

# The merged JSON still satisfies the checker.
out = os.path.join(tempfile.mkdtemp(), "attack.md")
subprocess.run(
    [sys.executable, os.path.join(HERE, "merge_attacks.py"), "--out", out, caught],
    check=True, capture_output=True, text=True,
)
expect("the merged file passes its own check", check_attack(out), [])

if __name__ == "__main__":
    for item in FAILS:
        print(f"FAIL {item}")
    print(f"{len(CHECKS) - len(FAILS)}/{len(CHECKS)} passed")
    sys.exit(1 if FAILS else 0)
