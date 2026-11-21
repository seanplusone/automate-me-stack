"""Run: python3 check/test_json_contract.py

The markdown holes that three review rounds found. The JSON contract
closes each one, and a raw markdown pass is an error.
"""
import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from check_attack import check_attack, norm_location, norm_span, parse_attack  # noqa: E402
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
    ("parent", "pkg/../cap.py:3", None),
    ("hash", "cap.py#L3", None),
    ("backticks", "`cap.py`", 3),
    ("diff a", "a/cap.py", 3),
    ("diff b", "b/cap.py", 3),
    ("range", "cap.py:3-4", None),
    ("hash range", "cap.py#L3-L4", None),
    ("parent only", "../cap.py", 3),
    ("case root", "/checkout/cases/item-cap/cap.py", 3),
    ("zero uses suffix", "cap.py#L3", 0),
):
    got = norm_location(file, line)
    expect(label + " names cap.py:3", got, ("cap.py", 3))
expect("absolute keeps its directories", norm_location("/srv/checkout/cap.py:3", None), ("srv/checkout/cap.py", 3))
expect("a drive letter is stripped", norm_location("C:\\work\\cap.py", 3), ("work/cap.py", 3))
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

# Without a judge, a located finding is weak. It is not a meaning pass.
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
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    code = score_planted(key, denied, environ={"PATH": "/nonexistent"})
expect("a denial is not a pass", (code, "PASS" not in buf.getvalue() and "WEAK" in buf.getvalue()), (2, True))

# A real catch still keyword-passes when no CLI exists.
caught = block({
    "verdict": "needs fixes",
    "tried": [{"input": "within_cap(5)", "broke": True, "observed": "False"}],
    "findings": [finding("cap.py", 3)],
})
expect("a catch with no CLI is weak", score_planted(key, caught, environ={"PATH": "/nonexistent"}), 2)
expect("a column location is scored", score_planted(key, block({
    "verdict": "needs fixes",
    "tried": [{"input": "within_cap(5)", "broke": True, "observed": "False"}],
    "findings": [finding("cap.py:3:12", None)],
}), environ={"PATH": "/nonexistent"}), 2)
expect("a null line on the key file is scored", score_planted(key, block({
    "verdict": "needs fixes",
    "tried": [{"input": "within_cap(5)", "broke": True, "observed": "False"}],
    "findings": [{"file": "cap.py", "line": None, "claim": "within_cap(5) returns False", "repro": "within_cap(5)"}],
}), environ={"PATH": "/nonexistent"}), 2)
expect("a null line on another file misses", score_planted(key, block({
    "verdict": "needs fixes",
    "tried": [{"input": "within_cap(5)", "broke": True, "observed": "False"}],
    "findings": [{"file": "other.py", "line": None, "claim": "within_cap(5) returns False", "repro": "within_cap(5)"}],
}), environ={"PATH": "/nonexistent"}), 1)
yes = lambda prompt: "ITEM 1: yes\n"
for label, file, line in (
    ("judge backticks", "`cap.py`", 3),
    ("judge diff a", "a/cap.py", 3),
    ("judge diff b", "b/cap.py", 3),
    ("judge range", "cap.py:3-4", None),
    ("judge hash range", "cap.py#L3-L4", None),
    ("judge drive", "C:\\work\\cap.py", 3),
    ("judge parent", "../cap.py", 3),
    ("judge case root", "/checkout/cases/item-cap/cap.py", 3),
    ("judge zero line", "cap.py#L3", 0),
    ("judge absolute", "/srv/checkout/cap.py", 3),
):
    expect(label + " reaches the judge", score_planted(key, block({
        "verdict": "needs fixes",
        "tried": [{"input": "within_cap(5)", "broke": True, "observed": "False"}],
        "findings": [finding(file, line)],
    }), environ={"PATH": "/nonexistent"}, runner=yes), 0)
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

bug = {
    "verdict": "needs fixes",
    "tried": [{"input": "within_cap(5)", "broke": True, "observed": "False"}],
    "findings": [finding("cap.py", 3)],
}
second = write(
    "```json\n" + json.dumps(bug) + "\n```\n"
    "````\n```json\n" + json.dumps(clean()) + "\n```\n````\n"
)
expect("a second json fence is an error", parse_attack(second)["parsed"], False)
stale = os.path.join(tempfile.mkdtemp(), "attack.md")
open(stale, "w").write(open(block(clean())).read())
from merge_attacks import main as merge_main
expect("a failed merge removes the old approve", merge_main(["merge", "--out", stale, second]), 1)
expect("the old approve is gone", os.path.exists(stale), False)

dup = write(
    '```json\n{"verdict":"approve","tried":[{"input":"x","broke":true,"observed":"n","broke":false}],"findings":[]}\n```\n'
)
expect("a repeated broke key is an error", parse_attack(dup)["parsed"], False)
dup_findings = write(
    '```json\n{"verdict":"approve","tried":[],"findings":[{"file":"cap.py","line":3,"claim":"x","repro":"y"}],"findings":[]}\n```\n'
)
expect("a repeated findings key is an error", parse_attack(dup_findings)["parsed"], False)

extra = clean()
extra["severity"] = "low"
expect("an extra key is ignored", parse_attack(block(extra))["verdict"], "approve")
spaced = write("``` json\n" + json.dumps(clean()) + "\n```\n")
expect("a spaced json fence is read", parse_attack(spaced)["verdict"], "approve")
tilde = write("~~~json\n" + json.dumps(clean()) + "\n~~~\n")
expect("a tilde json fence is read", parse_attack(tilde)["verdict"], "approve")
bare = write(json.dumps(clean()) + "\n")
expect("bare json is the whole output", parse_attack(bare)["verdict"], "approve")
prose_parse = write("Parse: I looked at the diff.\n```json\n" + json.dumps(clean()) + "\n```\n")
expect("a prose Parse line is kept", parse_attack(prose_parse)["verdict"], "approve")
wide = "```json\n" + json.dumps(clean()).replace('"ok"', '"ok\u2028still"') + "\n```\n"
expect("a line separator inside a string parses", parse_attack(write(wide))["parsed"], True)

huge = os.path.join(tempfile.mkdtemp(), "attack.md")
open(huge, "w").write(
    '```json\n{"verdict":"needs fixes","tried":[],"findings":[{"file":"cap.py","line":'
    + ("1" * 5000) + ',"claim":"x","repro":"y"}]}\n```\n'
)
ran = subprocess.run([sys.executable, os.path.join(HERE, "check_attack.py"), huge], capture_output=True, text=True)
expect("a huge line exits", ran.returncode, 1)
expect("a huge line has no traceback", "Traceback" not in ran.stderr and "Traceback" not in ran.stdout, True)

quoted_src = open(os.path.join(HERE, "fixtures", "passes", "item-cap", "codex.md")).read()
quoted = "\n".join("> " + line for line in quoted_src.splitlines())
clean_src = open(os.path.join(HERE, "fixtures", "passes", "clean", "claude.md")).read()
hidden = write(quoted + "\n" + clean_src + "\n")
expect("a quoted fence still counts", parse_attack(hidden)["parsed"], False)
expect("a quoted fence does not approve", merge_main(["merge", "--out", os.path.join(tempfile.mkdtemp(), "a.md"), hidden]), 1)
only_quoted = write(quoted + "\n")
expect("one quoted fence still parses", parse_attack(only_quoted)["verdict"], "needs fixes")

ranged = block({
    "verdict": "needs fixes",
    "tried": [{"input": "bug line bug line", "broke": True, "observed": "True"}],
    "findings": [{"file": "score_review.py:3-6", "line": None, "claim": "returns True", "repro": "bug line bug line"}],
})
span = merge([ranged])["findings"][0]
expect("a range keeps its start", span["line_start"], 3)
expect("a range keeps its end", span["line_end"], 6)
range_key = os.path.join(tempfile.mkdtemp(), "key.md")
open(range_key, "w").write("Planted: yes\nWhere: score_review.py:6\nCatch: bug line bug line | returns True\n")
range_out = os.path.join(tempfile.mkdtemp(), "attack.md")
expect("the range merge writes", merge_main(["merge", "--out", range_out, ranged]), 0)
expect("a merged range still reaches line 6", score_planted(
    range_key, range_out, environ={"PATH": "/nonexistent"}, runner=yes,
), 0)

blank = block({
    "verdict": "needs fixes",
    "tried": [{"input": "within_cap(5)", "broke": True, "observed": "False"}],
    "findings": [{"file": "", "line": None, "claim": "the cap is wrong", "repro": "within_cap(5) in cap.py"}],
})
kept = merge([blank])["findings"]
expect("an empty file with a repro is kept", kept[0]["repro"], "within_cap(5) in cap.py")
expect("an empty file with no judge is not weak", score_planted(key, blank, environ={"PATH": "/nonexistent"}), 1)
expect("an empty file can reach the judge", score_planted(key, blank, environ={"PATH": "/nonexistent"}, runner=yes), 0)

same = os.path.join(tempfile.mkdtemp(), "attack.md")
open(same, "w").write(open(block(clean())).read())
garbage = write("not json\n")
expect("out cannot be an input", merge_main(["merge", "--out", same, same, garbage]), 2)
expect("the input approve is still there", parse_attack(same)["verdict"], "approve")

crlf_bug = ("```json\n" + json.dumps(bug) + "\n```\n").replace("\n", "\r\n")
crlf = write(crlf_bug + "```json\n" + json.dumps(clean()) + "\n```\n")
expect("a crlf fence still counts", parse_attack(crlf)["parsed"], False)
bom = write("\ufeff```json\n" + json.dumps(clean()) + "\n```\n")
expect("a bom does not hide the block", parse_attack(bom)["verdict"], "approve")
folded = dict(clean())
folded["verdict"] = "Needs fixes"
expect("verdict case is folded", parse_attack(block(folded))["verdict"], "needs fixes")
numbered = block({
    "verdict": "needs fixes",
    "tried": [{"input": "within_cap(5)", "broke": True, "observed": "False"}],
    "findings": [{"file": "cap.py", "line": "3", "claim": "returns False", "repro": "within_cap(5)"}],
})
expect("a string line is a number", parse_attack(numbered)["findings"][0]["line"], 3)
expect("backticks around the path", norm_location("`head/cap.py`:3", None), ("cap.py", 3))
expect("a symbol suffix keeps the file", norm_location("cap.py::within_cap", None)[0], "cap.py")
expect("a range beats a point line", norm_span("score_review.py:3-6", 4)[1:], (3, 6))

symbol = block({
    "verdict": "needs fixes",
    "tried": [{"input": "within_cap(5)", "broke": True, "observed": "False"}],
    "findings": [{"file": "cap.py::within_cap", "line": None, "claim": "returns False", "repro": "within_cap(5)"}],
})
expect("a symbol with no judge is not weak", score_planted(key, symbol, environ={"PATH": "/nonexistent"}), 1)
expect("a symbol reaches the judge", score_planted(key, symbol, environ={"PATH": "/nonexistent"}, runner=yes), 0)
broke_only = block({
    "verdict": "needs fixes",
    "tried": [{"input": "within_cap(5)", "broke": True, "observed": "within_cap(5) returns False"}],
    "findings": [],
})
expect("a break with no finding is not weak", score_planted(key, broke_only, environ={"PATH": "/nonexistent"}), 1)
expect("a break with no finding reaches the judge", score_planted(
    key, broke_only, environ={"PATH": "/nonexistent"}, runner=yes,
), 0)
expect("an unparsed judge reply is a skip", score_planted(
    key, caught, environ={"PATH": "/nonexistent"}, runner=lambda prompt: "no idea\n",
), 2)

if __name__ == "__main__":
    for item in FAILS:
        print(f"FAIL {item}")
    print(f"{len(CHECKS) - len(FAILS)}/{len(CHECKS)} passed")
    sys.exit(1 if FAILS else 0)
