"""Run: python3 shared/test_check_resume.py"""
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
CHECK = os.path.join(HERE, "check_resume.py")
CASES = os.path.join(HERE, "cases", "resume")
GIT = ["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false"]
FAILS = []


def expect(name, ok, got):
    if not ok:
        FAILS.append(f"{name}: {got}")


def run(path, *args):
    r = subprocess.run([sys.executable, CHECK, path, *args], capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


def case(name, code, *needles, args=()):
    got, out = run(os.path.join(CASES, name), *args)
    expect(f"{name} exits {code}", got == code, out)
    for n in needles:
        expect(f"{name} says {n!r}", n in out, out)


def variant(root, base, edits, name="RESUME.md"):
    """Writes a copy of a fixture resume into root, with each (old, new) edit applied."""
    text = open(os.path.join(CASES, base)).read()
    for old, new in edits:
        expect(f"{name}: edit applies", old in text, old)
        text = text.replace(old, new)
    path = os.path.join(root, name)
    with open(path, "w") as f:
        f.write(text)
    return path


# The six fixture cases.
case("good.md", 0, "PASS")
case("self-report.md", 1, "self-report only", "step 3 done", "tests passed")
case("dangling.md", 1, "path does not exist: logs/lint-missing.txt")
case("no-next-step.md", 1, "empty slot: Next step")
case("bugfix.md", 0, "PASS")
case("status-typo.md", 1, "Status must be one of")
case("nothing-done.md", 0, "PASS")

with tempfile.TemporaryDirectory() as tmp:
    root = os.path.join(tmp, "work")
    shutil.copytree(CASES, root)
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "add", "."], cwd=root, check=True)
    subprocess.run(GIT + ["commit", "-q", "-m", "base"], cwd=root, check=True)
    sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, check=True).stdout.strip()
    git_dir = ["--git-dir", root]

    def check(edits, base="good.md"):
        return run(variant(root, base, edits), *git_dir)

    lint = "script: checks/lint.sh exit 0 log: logs/lint.txt"
    code, out = check([(lint, sha[:10])])
    expect("a short SHA in the repo resolves", code == 0, out)
    code, out = check([(lint, sha)])
    expect("a full SHA in the repo resolves", code == 0, out)
    code, out = check([(lint, "0123456789abcdef0123")])
    expect("an unknown SHA fails", code == 1 and "unknown commit: 0123456789abcdef0123" in out, out)
    code, out = check([(lint, "logs/lint.txt and 0123456789abcdef0123")])
    expect("an unknown SHA fails next to a log that resolves", code == 1 and "unknown commit" in out, out)
    code, out = check([(lint, "log: logs/lint.txt")])
    expect("a log path alone resolves", code == 0, out)
    code, out = check([(lint, "script: checks/lint.sh log: logs/lint.txt")])
    expect("a script needs its exit code", code == 1 and "no recorded exit code" in out, out)
    code, out = check([(lint, "script: checks/lint.sh exit 0")])
    expect("a script needs its log", code == 1 and "script has no log" in out, out)
    code, out = check([(lint, "script: checks/missing.sh exit 0 log: logs/lint.txt")])
    expect("a dangling script fails", code == 1 and "script does not exist: checks/missing.sh" in out, out)
    code, out = check([(lint, "I checked, ok")])
    expect("words alone fail as self-report", code == 1 and "self-report only" in out, out)
    code, out = check([("  - Lint runs", "- Lint runs")])
    expect("an unindented done item is still checked", code == 0, out)
    code, out = check([(f"| evidence: {lint}\n", f"| evidence: {lint}\n- tests passed\n")])
    expect("an unindented self-report item fails", code == 1 and "tests passed" in out, out)

    code, out = check([("- Goal: the counter module passes lint with no warnings\n", "")])
    expect("a missing Goal fails", code == 1 and "missing slot: Goal" in out, out)
    code, out = check([("- Key files: checks/lint.sh, src/counter.py", "- Key files: none")])
    expect("Key files cannot be none", code == 1 and "Key files cannot be none" in out, out)
    code, out = check([("- Gotchas: none\n", "- Gotchas: none\n- Gotchas: none\n")])
    expect("a slot twice fails", code == 1 and "appears 2 times: Gotchas" in out, out)
    code, out = check([("# Resume: lint the counter module", "# Notes")])
    expect("a missing title fails", code == 1 and "# Resume:" in out, out)

    code, out = check([("- Status: waiting on user", "- Status: done")], base="nothing-done.md")
    expect("none Done with Status done fails", code == 1 and "Status is done" in out, out)
    code, out = check([("- Waiting on: should an empty title count as 0 words or raise?", "- Waiting on: none")], base="nothing-done.md")
    expect("waiting on user names the question", code == 1 and "names the question" in out, out)

    code, out = check([("- Repro at parent: none", "- Repro at parent: exit 1 log: logs/trim-parent.txt")])
    expect("a Repro mix fails", code == 1 and "Repro at parent must be none" in out, out)
    code, out = check([("- Repro test: trim/head/trim_tabs_test.py", "- Repro test: trim/head/missing_test.py")], base="bugfix.md")
    expect("a missing Repro test fails", code == 1 and "path does not exist: trim/head/missing_test.py" in out, out)
    code, out = check([("- Repro at parent: exit 1 log", "- Repro at parent: exit 0 log")], base="bugfix.md")
    expect("Repro at parent with exit 0 fails", code == 1 and "must fail at the parent" in out, out)
    code, out = check([("- Repro at parent: exit 1 log: logs/trim-parent.txt", "- Repro at parent: it failed")], base="bugfix.md")
    expect("Repro at parent in words fails", code == 1 and "Repro at parent: needs a log" in out, out)
    code, out = check([("- Repro at head: exit 0 log: logs/trim-head.txt", "- Repro at head: log: logs/trim-head.txt")], base="bugfix.md")
    expect("Repro at head needs exit 0", code == 1 and "needs `exit 0`" in out, out)
    code, out = check([("- Repro at head: exit 0 log: logs/trim-head.txt", "- Repro at head: exit 0 log: logs/gone.txt")], base="bugfix.md")
    expect("Repro at head with a dangling log fails", code == 1 and "path does not exist: logs/gone.txt" in out, out)
    code, out = check([("- Repro at parent: exit 1 log: logs/trim-parent.txt", f"- Repro at parent: exit 1 log: logs/trim-parent.txt at {sha[:8]}")], base="bugfix.md")
    expect("a SHA on a Repro line may sit beside the log", code == 0, out)

    # --root: the same resume checked from another folder resolves against the root it is given.
    elsewhere = variant(tmp, "good.md", [])
    code, out = run(elsewhere)
    expect("paths resolve from the resume's folder by default", code == 1 and "does not exist" in out, out)
    code, out = run(elsewhere, "--root", root)
    expect("--root moves where paths resolve", code == 0, out)

if FAILS:
    print("\n".join(FAILS))
    sys.exit(1)
print("PASS test_check_resume")
