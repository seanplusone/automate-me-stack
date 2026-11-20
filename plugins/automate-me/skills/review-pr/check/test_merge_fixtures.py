"""Run: python3 check/test_merge_fixtures.py

Merges the JSON fixture passes and checks the verdict against each key.
"""
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from check_attack import norm_location, parse_attack  # noqa: E402

FAILS = []
CHECKS = []
CASES = ("item-cap", "trust-report", "word-score")
LINES = {"item-cap": ("cap.py", 3), "trust-report": ("report.py", 4), "word-score": ("score_review.py", 6)}


def expect(name, got, want):
    CHECKS.append(name)
    if got != want:
        FAILS.append(f"{name}: wanted {want!r}, got {got!r}")


def run(args):
    return subprocess.run(
        [sys.executable, os.path.join(HERE, "merge_attacks.py")] + args,
        capture_output=True, text=True,
    )


def merged(paths):
    out = os.path.join(tempfile.mkdtemp(), "attack.md")
    ran = run(["--out", out] + paths)
    expect("merge " + os.path.basename(os.path.dirname(paths[0])), ran.returncode, 0)
    return parse_attack(out)


for case in CASES:
    folder = os.path.join(HERE, "fixtures", "passes", case)
    doc = merged([os.path.join(folder, "codex.md"), os.path.join(folder, "claude.md")])
    expect(case + " needs fixes", doc["verdict"], "needs fixes")
    want = LINES[case]
    if case == "trust-report":
        lines = sorted(item["line"] for item in doc["findings"] if item["file"] == "report.py")
        expect("trust-report keeps both lines", lines, [3, 4])
    else:
        hits = [
            item for item in doc["findings"]
            if norm_location(item["file"], item["line"]) == want
        ]
        expect(case + " is one finding", len(hits), 1)
        expect(case + " keeps both claims", " | " in hits[0]["claim"], True)
    out = os.path.join(tempfile.mkdtemp(), "attack.md")
    run(["--out", out, os.path.join(folder, "codex.md"), os.path.join(folder, "claude.md")])
    checked = subprocess.run(
        [sys.executable, os.path.join(HERE, "check_attack.py"), out,
         "--key", os.path.join(SKILL, "cases", case, "key.md")],
        capture_output=True, text=True,
    )
    expect(case + " check passes a needs-fixes file", checked.returncode, 0)

clean = os.path.join(HERE, "fixtures", "passes", "clean")
doc = merged([os.path.join(clean, "codex.md"), os.path.join(clean, "claude.md")])
expect("two clean passes approve", doc["verdict"], "approve")
expect("prose about a path is ignored", doc["findings"], [])

ran = run([
    "--out", os.path.join(tempfile.mkdtemp(), "a.md"),
    os.path.join(HERE, "fixtures", "passes", "breaks", "garbage.md"),
    os.path.join(clean, "codex.md"),
])
expect("garbage plus clean is not an approve", ran.returncode, 1)

ran = run([
    "--out", os.path.join(tempfile.mkdtemp(), "a.md"),
    os.path.join(HERE, "fixtures", "passes", "breaks", "raw-markdown.md"),
    os.path.join(HERE, "fixtures", "passes", "item-cap", "codex.md"),
])
expect("raw markdown plus a bug still merges", ran.returncode, 0)

if __name__ == "__main__":
    for item in FAILS:
        print(f"FAIL {item}")
    print(f"{len(CHECKS) - len(FAILS)}/{len(CHECKS)} passed")
    sys.exit(1 if FAILS else 0)
