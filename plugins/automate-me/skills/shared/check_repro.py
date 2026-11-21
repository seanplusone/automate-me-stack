"""Parent-vs-head repro check. Runs the test itself; it never trusts a log the agent wrote.

Usage: python3 check_repro.py --test <path-or-command> --parent <sha> --head <sha> [--repo DIR] [--timeout SECONDS]

Checks out the parent and the head into throwaway git worktrees under a temp folder, and removes them after.
The user's own worktree is never touched.

1. Parent side: the head version of the test file goes into the parent tree. Every other parent file stays as it was.
   The test must fail (exit not 0). If it passes, the test does not reproduce the bug: a tweaked old test that
   already passed, or a new test that misses it.
2. Head side: the same test at head must pass (exit 0).

--test is a path ending in .py, run as `python3 <path>`, or a command with a space, run with a shell in the worktree.
For a command, each word that names a file at head is copied into the parent tree; at least one must.
Prints PASS or FAIL, says which side failed, and exits 1 on FAIL.
"""
import argparse
import os
import shlex
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_writing import FAILED, report  # noqa: E402


def git(repo, *args):
    return subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True)


def commit(repo, sha):
    r = git(repo, "rev-parse", "--verify", "--quiet", f"{sha}^{{commit}}")
    return r.stdout.strip() if r.returncode == 0 else None


def at_head(repo, head, path):
    return git(repo, "cat-file", "-e", f"{head}:{path}").returncode == 0


def test_files(test, repo, head):
    """Returns (command, files at head the command names)."""
    if " " not in test.strip():
        files = [test] if at_head(repo, head, test) else []
        return ([sys.executable, test] if test.endswith(".py") else ["sh", "-c", test]), files
    words = [w for w in shlex.split(test) if not w.startswith("-")]
    return ["sh", "-c", test], [w for w in words if at_head(repo, head, os.path.normpath(w))]


def run(cmd, cwd, timeout):
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    try:
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout, env=env)
        return r.returncode, (r.stdout + r.stderr).strip()
    except subprocess.TimeoutExpired:
        return None, f"timed out after {timeout}s"


def tail(out, n=8):
    return "\n".join("    " + line for line in out.splitlines()[-n:])


def check_repro(test, parent, head, repo=".", timeout=600):
    fails, notes = [], []
    repo = os.path.abspath(repo)
    p_sha, h_sha = commit(repo, parent), commit(repo, head)
    if not p_sha:
        fails.append(f"parent commit not found: {parent}")
    if not h_sha:
        fails.append(f"head commit not found: {head}")
    if fails:
        report(f"repro: {test}", fails)
        return fails
    cmd, files = test_files(test, repo, h_sha)
    if not files:
        fails.append(f"test missing at head: {test} names no file in {h_sha[:12]}")
        report(f"repro: {test}", fails)
        return fails

    tmp = tempfile.mkdtemp(prefix="check-repro-")
    trees = {"parent": os.path.join(tmp, "parent"), "head": os.path.join(tmp, "head")}
    try:
        for side, sha in (("parent", p_sha), ("head", h_sha)):
            r = git(repo, "worktree", "add", "--detach", "--quiet", trees[side], sha)
            if r.returncode:
                fails.append(f"could not check out {side} {sha[:12]}: {r.stderr.strip()}")
        if not fails:
            r = git(trees["parent"], "checkout", h_sha, "--", *files)
            if r.returncode:
                fails.append(f"could not copy the head test into the parent tree: {r.stderr.strip()}")
        if not fails:
            code, out = run(cmd, trees["parent"], timeout)
            if code == 0:
                fails.append(f"parent passed: the head test exits 0 on the parent tree {p_sha[:12]}, so it reproduces no bug. "
                             "A tweaked old test, or a new test that misses the bug.\n" + tail(out))
            elif code is None:
                fails.append(f"parent timed out: {out}")
            else:
                notes.append(f"parent {p_sha[:12]} with the head test: exit {code} (fails, as a repro must)")
            code, out = run(cmd, trees["head"], timeout)
            if code != 0:
                fails.append(f"head failed: the test exits {code if code is not None else 'on timeout'} at head {h_sha[:12]}.\n" + tail(out))
            else:
                notes.append(f"head {h_sha[:12]}: exit 0 (passes)")
    finally:
        for path in trees.values():
            if os.path.isdir(path):
                git(repo, "worktree", "remove", "--force", path)
        shutil.rmtree(tmp, ignore_errors=True)
        git(repo, "worktree", "prune")
    for n in notes:
        print(f"  {n}")
    report(f"repro: {test}", fails)
    return fails


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Run a new test on the parent tree (must fail) and at head (must pass).")
    ap.add_argument("--test", required=True, help="test path ending in .py, or a command with a space")
    ap.add_argument("--parent", required=True, help="commit before the fix")
    ap.add_argument("--head", required=True, help="commit with the fix and the new test")
    ap.add_argument("--repo", default=".", help="the git repo (default: the current folder)")
    ap.add_argument("--timeout", type=int, default=600, help="seconds per test run")
    a = ap.parse_args()
    check_repro(a.test, a.parent, a.head, a.repo, a.timeout)
    sys.exit(1 if FAILED else 0)
