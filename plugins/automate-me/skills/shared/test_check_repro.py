"""Run: python3 shared/test_check_repro.py"""
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
CHECK = os.path.join(HERE, "check_repro.py")
TRIM = os.path.join(HERE, "cases", "resume", "trim")
GIT = ["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false"]
FAILS = []


def expect(name, ok, got):
    if not ok:
        FAILS.append(f"{name}: {got}")


def run(*args, cwd=None):
    r = subprocess.run([sys.executable, CHECK, *args], capture_output=True, text=True, cwd=cwd)
    return r.returncode, r.stdout + r.stderr


def git(repo, *args):
    return subprocess.run(GIT + list(args), cwd=repo, capture_output=True, text=True, check=True).stdout.strip()


def put(repo, src):
    shutil.copy(os.path.join(TRIM, src), os.path.join(repo, os.path.basename(src)))


def commit(repo, msg):
    git(repo, "add", ".")
    git(repo, "commit", "-q", "-m", msg)
    return git(repo, "rev-parse", "HEAD")


def test_exit(repo, test):
    return subprocess.run([sys.executable, test], cwd=repo, capture_output=True, text=True,
                          env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1")).returncode


with tempfile.TemporaryDirectory() as tmp:
    repo = os.path.join(tmp, "repo")
    os.makedirs(repo)
    git(repo, "init", "-q", "-b", "main")

    # The parent: buggy trim() and an old test that passes on it.
    put(repo, "parent/trim.py")
    put(repo, "parent/trim_test.py")
    parent = commit(repo, "trim strips spaces")
    expect("old test passes on the parent", test_exit(repo, "trim_test.py") == 0, "old test failed")

    # The new test, written before the fix. Run it on the parent code and see it fail.
    put(repo, "head/trim_tabs_test.py")
    expect("new test fails on the parent code", test_exit(repo, "trim_tabs_test.py") == 1, "new test did not fail")
    test_only = commit(repo, "test: trim strips tabs")

    # Then the fix, and the same test passes.
    put(repo, "head/trim.py")
    expect("new test passes with the fix", test_exit(repo, "trim_tabs_test.py") == 0, "new test did not pass")
    head = commit(repo, "fix: trim strips all whitespace")

    # Case 5: a real new repro. check_repro reruns it and agrees.
    code, out = run("--test", "trim_tabs_test.py", "--parent", parent, "--head", head, "--repo", repo)
    expect("new failing-then-passing repro passes", code == 0 and "PASS" in out and "exit 1" in out, out)
    code, out = run("--test", "python3 trim_tabs_test.py", "--parent", parent, "--head", head, cwd=repo)
    expect("a command with a space runs in a shell, --repo defaults to the cwd", code == 0, out)

    # Case 6: a tweaked old test. Head changes the old test, and the head version still passes on the parent tree.
    git(repo, "checkout", "-q", "-b", "tweaked", parent)
    put(repo, "tweaked/trim_test.py")
    put(repo, "head/trim.py")
    tweaked = commit(repo, "fix: trim, and tweak the old test")
    code, out = run("--test", "trim_test.py", "--parent", parent, "--head", tweaked, "--repo", repo)
    expect("tweaked old test fails the check", code == 1 and "parent passed" in out, out)

    # Other sides that fail.
    code, out = run("--test", "trim_tabs_test.py", "--parent", parent, "--head", test_only, "--repo", repo)
    expect("a head without the fix fails", code == 1 and "head failed" in out and "parent passed" not in out, out)
    code, out = run("--test", "trim_tabs_test.py", "--parent", parent, "--head", parent, "--repo", repo)
    expect("a test missing at head fails", code == 1 and "test missing at head" in out, out)
    code, out = run("--test", "trim_tabs_test.py", "--parent", "0123456789abcdef", "--head", head, "--repo", repo)
    expect("an unknown commit fails", code == 1 and "parent commit not found" in out, out)

    # The user's worktree is left as it was.
    expect("no worktree is left behind", git(repo, "worktree", "list").count("\n") == 0, git(repo, "worktree", "list"))
    expect("the checkout is untouched", git(repo, "status", "--porcelain") == "" and git(repo, "rev-parse", "HEAD") == tweaked,
           git(repo, "status", "--porcelain"))

if FAILS:
    print("\n".join(FAILS))
    sys.exit(1)
print("PASS test_check_repro")
