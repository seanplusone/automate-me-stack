"""Fail if a skill's cases directory holds a test_*.py file.

Run: python3 shared/test_case_files.py

The suite runs every test_*.py it finds. A planted program with that name
would pass while the bug is still there. list_tests.sh also skips head and
base under cases, and this file checks that skip.
"""
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SKILLS = os.path.dirname(HERE)
LIST = os.path.join(HERE, "list_tests.sh")
FAILS = []


def case_tests(root):
    """Paths of test_*.py files under any directory named cases."""
    found = []
    for dirpath, _, filenames in os.walk(root):
        parts = os.path.relpath(dirpath, root).split(os.sep)
        if "cases" not in parts:
            continue
        for name in filenames:
            if name.startswith("test_") and name.endswith(".py"):
                found.append(os.path.join(dirpath, name))
    return sorted(found)


def listed(root):
    out = subprocess.run(["sh", LIST, root], capture_output=True, text=True)
    if out.returncode != 0:
        return None, out.stderr
    return [line for line in out.stdout.splitlines() if line], ""


def expect(name, got, want):
    if got != want:
        FAILS.append(f"{name}: wanted {want!r}, got {got!r}")


fixture = tempfile.mkdtemp()
for rel in (
    "check/test_real.py",
    "cases/demo/head/test_planted.py",
    "cases/demo/base/test_old.py",
    "cases/demo/case_test_ok.py",
    "nested/cases/deep/head/test_nested.py",
    "nested/cases/deep/notes.md",
):
    path = os.path.join(fixture, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "w").write("print('x')\n")

expect(
    "scanner finds every test_*.py under cases",
    case_tests(fixture),
    [
        os.path.join(fixture, "cases/demo/base/test_old.py"),
        os.path.join(fixture, "cases/demo/head/test_planted.py"),
        os.path.join(fixture, "nested/cases/deep/head/test_nested.py"),
    ],
)
lines, err = listed(fixture)
expect("list script runs", err, "")
expect("list script keeps a real test", "./check/test_real.py" in lines, True)
expect("list script skips head and base under cases",
       [p for p in lines if "/cases/" in p and ("/head/" in p or "/base/" in p)], [])
expect("list script does not print a planted name",
       [p for p in lines if p.endswith("test_planted.py") or p.endswith("test_old.py") or p.endswith("test_nested.py")],
       [])

live = case_tests(SKILLS)
expect("this repo has no test_*.py under cases", live, [])
suite, err = listed(SKILLS)
expect("suite list runs", err, "")
expect("suite list skips case head and base",
       [p for p in suite if "/cases/" in p and ("/head/" in p or "/base/" in p)], [])

if __name__ == "__main__":
    for item in FAILS:
        print(f"FAIL {item}")
    total = 8
    print(f"{total - len(FAILS)}/{total} passed")
    sys.exit(1 if FAILS else 0)
