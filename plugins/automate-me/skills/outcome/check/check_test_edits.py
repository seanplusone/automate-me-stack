"""Check for edits to existing tests after the tests-first commit.

Usage:
  python3 check/check_test_edits.py <tests-first-commit>
  python3 check/check_test_edits.py --reset

Exit 0 for a clean check or reset.
Exit 2 for STOP. A human clears the saved stop with --reset.
"""
import argparse
from fnmatch import fnmatchcase
import os
import re
import subprocess
import sys

sys.dont_write_bytecode = True
from secret_scan import git_path, stop

TEST_PATTERNS = ("test_*.py", "*_test.*", "*.test.*", "*.spec.*")
SKIP_MARKER = re.compile(r"\bskip|\bxfail|\bx(it|describe|test)\(|\.only\(|@disabled|@ignore", re.I)
DIFF = ("diff", "--no-color", "--no-ext-diff")
STOP_REASON = "A fix edited an existing test."


def is_test(path):
    *folders, basename = path.split("/")
    return (any(folder in ("tests", "__tests__") for folder in folders)
            or any(fnmatchcase(basename, pattern) for pattern in TEST_PATTERNS))


def git(*args, cwd=None):
    return subprocess.check_output(["git", *args], cwd=cwd)


def edit_reason(patch):
    in_hunk = False
    for line in patch.decode("utf-8", errors="replace").split("\n"):
        if line.startswith("Binary files ") and line.endswith(" differ"):
            return "changed a binary file"
        if line.startswith("@@ "):
            in_hunk = True
        if not in_hunk:
            continue
        if line.startswith("-") and line[1:].strip():
            return "changed or removed a line"
        if line.startswith("+") and SKIP_MARKER.search(line[1:]):
            return "added a skip"
    return None


def test_edits(root, base):
    fields = git(*DIFF, "-M", "--name-status", "-z", base, "--", cwd=root)
    entries = iter(os.fsdecode(fields).split("\0")[:-1])
    for status in entries:
        path = next(entries)
        kind = status[0]
        if kind in ("R", "C"):
            next(entries)
        if not is_test(path):
            continue
        if kind == "D":
            yield f"{path}: deleted"
        elif kind == "R":
            yield f"{path}: renamed"
        elif kind == "T":
            yield f"{path}: changed type"
        elif kind == "M":
            patch = git("--literal-pathspecs", *DIFF, "-U0", base, "--", path, cwd=root)
            reason = edit_reason(patch)
            if reason:
                yield f"{path}: {reason}"


def report(reasons):
    for reason in reasons:
        print(reason)
    return stop(STOP_REASON)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("base", nargs="?", metavar="tests-first-commit")
    modes.add_argument("--reset", action="store_true")
    args = parser.parse_args()

    try:
        if args.base is not None:
            try:
                base = git("rev-parse", "--verify", "--end-of-options",
                           f"{args.base}^{{commit}}").decode("ascii").strip()
            except subprocess.CalledProcessError:
                return stop("Could not verify the tests-first commit.")

        state = git_path("--git-path", "automate-me-test-edits")
        if args.reset:
            state.unlink(missing_ok=True)
            return 0

        if state.exists():
            status, _, reasons = state.read_text(encoding="utf-8").partition("\n")
            if status == "stop":
                return report(reasons.split("\n") if reasons else [])

        reasons = list(test_edits(git_path("--show-toplevel"), base))
        if reasons:
            state.write_text("\n".join(["stop", *reasons]), encoding="utf-8")
            return report(reasons)
    except (OSError, subprocess.CalledProcessError) as err:
        return stop(f"Could not complete the test edit check: {err}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
