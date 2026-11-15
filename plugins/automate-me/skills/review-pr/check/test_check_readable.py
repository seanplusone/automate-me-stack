import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_readable import MAX_FN_LINES, check_readable  # noqa: E402

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
open(os.path.join(repo, "app.py"), "w").write("def small():\n    return 1\n")
run("git", "add", ".", cwd=repo)
run("git", "commit", "-q", "-m", "base", cwd=repo)
base = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True).stdout.strip()

long_fn = "def process():\n" + "    x = 1\n" * (MAX_FN_LINES) + "    return x\n"
short_fn = "def tiny():\n    return 2\n"
open(os.path.join(repo, "app.py"), "w").write(long_fn + "\n" + short_fn)
open(os.path.join(repo, "ok.py"), "w").write("def fine():\n    return 3\n")
run("git", "add", ".", cwd=repo)
run("git", "commit", "-q", "-m", "head", cwd=repo)
head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True).stdout.strip()

cwd = os.getcwd()
os.chdir(repo)
hits = check_readable(base, head)
os.chdir(cwd)

expect("long touched function is listed", any("app.py:1 process" in h and "lines, max" in h for h in hits), hits)
expect("short function is not listed", not any("tiny" in h for h in hits), hits)
expect("untouched short new file under cap is not listed", not any("ok.py" in h for h in hits), hits)
expect("only the long one fails", len(hits) == 1, hits)

if __name__ == "__main__":
    for line in FAILS:
        print(f"FAIL {line}")
    print("done" if not FAILS else f"{len(FAILS)} failed")
    sys.exit(1 if FAILS else 0)
