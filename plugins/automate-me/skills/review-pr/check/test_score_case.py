"""Run: python3 check/test_score_case.py"""
import contextlib
import io
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from score_case import score  # noqa: E402

KEY = """| ID | PR | Path | Line | Finding | Min sites | Proof |
|----|----|------|------|---------|-----------|-------|
| K1 | o/r#1 | `scripts/stage.sh` | 17 | Guards run after the writes. | - | stub run |
| K2 | o/r#1 | `scripts/stage.sh` | 28 | Ambient profile. | - | policy |
| K3 | o/r#1 | `plugin/` | - | Paths rewritten. | 48 | grep |
| K4 | o/r#1 | PR | - | Stale body claim. | - | read |
"""

KEY_TERMS = KEY + "\nTerms: K1 | admin | owner\n"

FAILS = []
RAN = []


def drafts(*findings, text="Is this right?"):
    lines = ["# PR review: t", "", "Risk.", "", "## o/r#1 | approve", ""]
    for anchor, sites in findings:
        lines += [f"### question | {anchor} | https://github.com/o/r/pull/1/files#diff-aR1", text]
        if sites:
            lines.append(f"Sites: {sites} | grep -rn x")
        lines.append("")
    lines += ["## Totals", "Refuter: checked 1, reworded 0, dropped 0."]
    return "\n".join(lines) + "\n"


def found(text, key=KEY):
    d = tempfile.mkdtemp()
    k, p = os.path.join(d, "key.md"), os.path.join(d, "drafts.md")
    open(k, "w").write(key)
    open(p, "w").write(text)
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        score(k, p)
    return {line.split()[0] for line in out.getvalue().splitlines() if line.endswith(" found")}


def expect(name, text, want, key=KEY):
    RAN.append(name)
    got = found(text, key)
    if got != want:
        FAILS.append(f"{name}: wanted {sorted(want)}, got {sorted(got)}")


expect("exact lines", drafts(("scripts/stage.sh:17", None), ("scripts/stage.sh:28", None), ("plugin/a.md:3", 48)),
       {"K1", "K2", "K3"})
expect("PR-level comment earns only the PR row", drafts(("PR", None)), {"K4"})
expect("nearest changed line, 3 away", drafts(("scripts/stage.sh:20", None)), {"K1"})
expect("4 away is a different line", drafts(("scripts/stage.sh:21", None)), set())
expect("same file, far away", drafts(("scripts/stage.sh:132", None)), set())
expect("one comment does not earn two rows", drafts(("scripts/stage.sh:17", None)), {"K1"})
expect("dash means any line", drafts(("plugin/deep/b.md:900", 48)), {"K3"})
expect("sites minimum still applies", drafts(("plugin/a.md:3", 2)), set())
expect("terms all present", drafts(("scripts/stage.sh:17", None), text="Admin and owner are skipped."),
       {"K1"}, KEY_TERMS)
expect("terms one missing", drafts(("scripts/stage.sh:17", None), text="Only the admin is skipped."), set(), KEY_TERMS)
expect("terms case-insensitive", drafts(("scripts/stage.sh:17", None), text="ADMIN and OWNER."), {"K1"}, KEY_TERMS)
expect("a/b term matches the second word", drafts(("scripts/stage.sh:17", None), text="An admin, so only the assignee."), {"K1"}, KEY + "\nTerms: K1 | admin | owner/assignee\n")
expect("a/b term needs one of its words", drafts(("scripts/stage.sh:17", None), text="An admin only."), set(), KEY + "\nTerms: K1 | admin | owner/assignee\n")
expect("row without terms unaffected", drafts(("scripts/stage.sh:28", None)), {"K2"}, KEY_TERMS)


def planted_files(attack, catch="returns True | ok\": false"):
    d = tempfile.mkdtemp()
    k, p = os.path.join(d, "key.md"), os.path.join(d, "attack.md")
    open(k, "w").write(f"Planted: yes\nCatch: {catch}\n")
    open(p, "w").write(attack)
    return k, p


def planted_score(attack, catch="returns True | ok\": false", runner=None):
    k, p = planted_files(attack, catch)
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = score(k, p, environ={"PATH": "/nonexistent"}, runner=runner)
    return code, out.getvalue()


def attack_json(file, line, claim, repro):
    body = {
        "verdict": "needs fixes",
        "tried": [{"input": "{\"ok\": false}", "broke": True, "observed": "True"}],
        "findings": [{"file": file, "line": line, "claim": claim, "repro": repro}],
    }
    return "```json\n" + json.dumps(body) + "\n```\n"


CAUGHT = attack_json(
    "report.py", 4,
    "accept returns True when a case has ok: false.",
    "{\"passed\": true, \"ok\": false}",
)
MISSED = attack_json("report.py", 9, "The name field has no length cap.", "{\"name\": \"\"}")
def expect_planted(name, got, want):
    RAN.append(name)
    if got != want:
        FAILS.append(f"{name}: wanted {want!r}, got {got!r}")


code, text = planted_score(CAUGHT)
expect_planted("planted bug caught", (code, "caught" in text and text.strip().endswith("PASS caught planted bug")), (0, True))
code, text = planted_score(MISSED)
expect_planted("planted bug missed", (code, "FAIL missed planted bug" in text and "SKIP" in text), (1, True))
code, _text = planted_score(CAUGHT, "returns true/returns True")
expect_planted("a/b catch term", code, 0)
QUOTED = attack_json("report.py", 4, "accept returns True", "`ok`: False")
code, _text = planted_score(QUOTED, "'ok': False | returns True")
expect_planted("quotes and case are ignored", code, 0)
PARAPHRASE = attack_json(
    "report.py", 4,
    "The early return treats the summary as proof.",
    "a failed case with a true summary",
)
seen = []
code, text = planted_score(
    PARAPHRASE, "returns True | 'ok': False",
    runner=lambda prompt: seen.append(prompt) or "ITEM 1: yes\n",
)
expect_planted("meaning judge can catch a paraphrase", (code, "PASS judge caught planted bug" in text), (0, True))
expect_planted("the judge sees the matching claim", "summary as proof" in seen[0], True)
mixed = attack_json("unrelated.py", 900, "MARKER other bug", "other")
# A second finding on the key line is the only one the judge should see.
parsed = json.loads(mixed.split("```json\n", 1)[1].split("\n```", 1)[0])
parsed["findings"].append({
    "file": "report.py", "line": 4,
    "claim": "The early return treats the summary as proof.",
    "repro": "a failed case",
})
mixed_path_key, mixed_path = planted_files("```json\n" + json.dumps(parsed) + "\n```\n", "returns True | 'ok': False")
open(mixed_path_key, "a").write("Where: report.py:4\n")
prompts = []
out = io.StringIO()
with contextlib.redirect_stdout(out):
    code = score(mixed_path_key, mixed_path, environ={"PATH": "/nonexistent"}, runner=lambda prompt: prompts.append(prompt) or "ITEM 1: yes\n")
expect_planted("only the matching finding is judged", (code, "MARKER" not in prompts[0] and "summary as proof" in prompts[0]), (0, True))
DENIED = attack_json("unrelated.py", 900, "accept returns True when a case has ok false.", "ok false")
k, p = planted_files(DENIED, "returns True | ok false")
open(k, "a").write("Where: report.py:4\n")
out = io.StringIO()
with contextlib.redirect_stdout(out):
    code = score(k, p, environ={"PATH": "/nonexistent"}, runner=lambda prompt: (7, "ITEM 1: no\nITEM 1: yes\n"))
text = out.getvalue()
expect_planted("a denial on another file is not a catch", (code, "PASS" not in text), (1, True))
code, text = planted_score(PARAPHRASE, "returns True | 'ok': False", runner=lambda prompt: (7, "ITEM 1: no\nITEM 1: yes\n"))
expect_planted("a non-zero judge does not pass", (code, "SKIP judge exited non-zero" in text and "PASS judge" not in text), (1, True))
code, text = planted_score(PARAPHRASE, "returns True | 'ok': False", runner=lambda prompt: "ITEM 1: no\nITEM 1: yes\n")
expect_planted("conflicting judge answers fail", (code, "FAIL judge missed planted bug" in text), (1, True))
SPAN = attack_json("report.py", 3, "accept returns True when a case has ok false.", "ok false")
k, p = planted_files(SPAN, "returns True | ok false")
open(k, "a").write("Where: report.py:3-4\n")
out = io.StringIO()
with contextlib.redirect_stdout(out):
    code = score(k, p, environ={"PATH": "/nonexistent"})
expect_planted("a line in the key span counts", code, 0)
FAR = attack_json("report.py", 9, "accept returns True when a case has ok false.", "ok false")
k, p = planted_files(FAR, "returns True | ok false")
open(k, "a").write("Where: report.py:4\n")
out = io.StringIO()
with contextlib.redirect_stdout(out):
    code = score(k, p, environ={"PATH": "/nonexistent"})
expect_planted("a line outside the window misses", code, 1)
DENY = attack_json(
    "report.py", 4,
    "This does not show a bug. returns True and ok false are only words.",
    "ok false",
)
k, p = planted_files(DENY, "returns True | ok false")
open(k, "a").write("Where: report.py:4\n")
out = io.StringIO()
with contextlib.redirect_stdout(out):
    code = score(k, p, environ={"PATH": "/nonexistent"})
text = out.getvalue()
expect_planted("a denial on the key line is not a keyword pass", (code, "PASS" not in text), (1, True))
from judge_case import parse_verdict
expect_planted("a sentence is not a judge answer", parse_verdict("The answer is not ITEM 1: yes."), None)

if __name__ == "__main__":
    for f in FAILS:
        print(f"FAIL {f}")
    total = len(RAN)
    print(f"{total - len(FAILS)}/{total} passed")
    sys.exit(1 if FAILS else 0)
