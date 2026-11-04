"""Run: python3 check/test_score_case.py"""
import contextlib
import io
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

if __name__ == "__main__":
    for f in FAILS:
        print(f"FAIL {f}")
    total = len(RAN)
    print(f"{total - len(FAILS)}/{total} passed")
    sys.exit(1 if FAILS else 0)
