"""Run: python3 shared/test_pr_prose.py"""
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pr_prose import check, collect  # noqa: E402

FAILS = []


def run(*args, cwd):
    subprocess.run(args, cwd=cwd, check=True, capture_output=True)


def expect(name, ok, got):
    if not ok:
        FAILS.append(f"{name}: got {got}")


repo = tempfile.mkdtemp()
run("git", "init", "-q", "-b", "main", cwd=repo)
run("git", "config", "user.email", "t@example.test", cwd=repo)
run("git", "config", "user.name", "t", cwd=repo)
open(os.path.join(repo, "a.php"), "w").write("<?php\n$x = 1;\n")
run("git", "add", ".", cwd=repo)
run("git", "commit", "-q", "-m", "base", cwd=repo)
base = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True).stdout.strip()

open(os.path.join(repo, "a.php"), "w").write(
    "<?php\n$x = 1;\n// This serves as the guard for the save.\n$y = 'robust'; // trailing note\n"
    "/**\n * @param int $id\n * Loads the row.\n */\n")
open(os.path.join(repo, "notes.md"), "w").write("# Notes\n\nThe pull runs on a schedule — not instantly.\n")
run("git", "add", ".", cwd=repo)
run("git", "commit", "-q", "-m", "fix: ensure the photos load\n\nCo-Authored-By: Someone <x@example.test>", cwd=repo)

body = os.path.join(repo, "body.md")
open(body, "w").write("Adds the photos.\n\nIn order to match the regions version.\n")

cwd = os.getcwd()
os.chdir(repo)
items = collect(base, "HEAD", body=body)
hits = check(items)
os.chdir(cwd)

texts = [t for _, t in items]
expect("full-line comment collected without its marker", "This serves as the guard for the save." in texts, texts)
expect("code line skipped", not any("$y" in t for t in texts), texts)
expect("docblock tag skipped", not any(t.startswith("@param") for t in texts), texts)
expect("docblock prose collected", "Loads the row." in texts, texts)
expect("trailer skipped", not any("Co-Authored-By" in t for t in texts), texts)
expect("comment hit carries path:line", any(h.startswith("a.php:3 W20") for h in hits), hits)
expect("markdown hit carries path:line", any(h.startswith("notes.md:3 W1") for h in hits), hits)
expect("commit message hit", any(h.startswith("commit ") and "W5" in h for h in hits), hits)
expect("body hit", any(h.startswith(f"body {body}:3 W6") for h in hits), hits)

expect("clean text passes", check([("x:1", "The path is wrong at line 99.")]) == [], "hit on clean text")

if __name__ == "__main__":
    for f in FAILS:
        print(f"FAIL {f}")
    total = 10
    print(f"{total - len(FAILS)}/{total} passed")
    sys.exit(1 if FAILS else 0)
