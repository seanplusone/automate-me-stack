"""Run: python3 check/test_size.py"""
import os
import subprocess
import sys
import tempfile

SIZE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "size.py")
FAILS = []


def sh(repo, *args):
    subprocess.run(args, cwd=repo, check=True, capture_output=True)


def write(repo, path, lines):
    full = os.path.join(repo, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w") as f:
        f.write("".join(f"line {i}\n" for i in range(lines)))


def commit(repo, msg):
    sh(repo, "git", "add", "-A")
    sh(repo, "git", "commit", "-q", "-m", msg)


def run(repo, *args):
    r = subprocess.run([sys.executable, SIZE, *args], cwd=repo, capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


def expect(name, cond, out):
    if not cond:
        FAILS.append(f"{name}\n{out}")


def new_repo():
    repo = tempfile.mkdtemp()
    sh(repo, "git", "init", "-q", "-b", "main")
    sh(repo, "git", "config", "user.email", "t@example.com")
    sh(repo, "git", "config", "user.name", "t")
    write(repo, "app/Base.php", 10)
    write(repo, "config/app.php", 10)
    for i in range(31):
        write(repo, f"app/F{i}.php", 1)
    commit(repo, "base")
    sh(repo, "git", "checkout", "-q", "-b", "feature")
    return repo


def test_small_change_reviews_as_one():
    repo = new_repo()
    write(repo, "app/Thing.php", 50)
    commit(repo, "small")
    code, out = run(repo, "main", "feature")
    expect("small change", code == 0 and "verdict: review as one" in out and "new files 1" in out, out)


def test_each_threshold_trips_on_its_own():
    repo = new_repo()
    for i in range(21):
        write(repo, f"app/F{i}.php", 2)
    commit(repo, "many files")
    _, out = run(repo, "main", "feature")
    expect("21 files", "verdict: consider splitting (files 21 >= 20)" in out, out)
    write(repo, "app/Big.php", 1300)
    for i in range(21, 31):
        write(repo, f"app/F{i}.php", 2)
    commit(repo, "big")
    _, out = run(repo, "main", "feature")
    expect("1300 lines and 32 files", "verdict: split" in out and "lines added" in out and "files 32 > 30" in out, out)
    for i in range(11):
        write(repo, f"app/New{i}.php", 1)
    commit(repo, "new files")
    _, out = run(repo, "main", "feature")
    expect("12 new files", "new files 12 >= 10" in out, out)


def test_exclude_drops_files_from_the_count():
    repo = new_repo()
    write(repo, "composer.lock", 5000)
    write(repo, "app/Thing.php", 10)
    commit(repo, "lock")
    _, out = run(repo, "main", "feature", "--exclude", "*.lock")
    expect("excluded lock", "verdict: review as one" in out and "lines added 10" in out, out)


def test_rename_counts_as_one_changed_file():
    repo = new_repo()
    sh(repo, "git", "mv", "app/Base.php", "app/Renamed.php")
    commit(repo, "rename")
    _, out = run(repo, "main", "feature")
    expect("rename", "files 1" in out and "new files 0" in out, out)


def plan(repo, text):
    path = os.path.join(repo, "..", os.path.basename(repo) + "-plan.tsv")
    with open(path, "w") as f:
        f.write(text)
    return path


def test_plan_must_cover_the_diff_exactly_once():
    repo = new_repo()
    write(repo, "app/A.php", 5)
    write(repo, "app/B.php", 5)
    commit(repo, "two")
    code, out = run(repo, "main", "feature", "--plan", plan(repo, "1\tapp/A.php\n1\tapp/B.php\n"))
    expect("good plan", code == 0 and "PASS plan" in out, out)
    code, out = run(repo, "main", "feature", "--plan", plan(repo, "1\tapp/A.php\n"))
    expect("missing file", code == 1 and "app/B.php is in the diff but in no slice" in out, out)
    code, out = run(repo, "main", "feature", "--plan", plan(repo, "1\tapp/A.php\n2\tapp/A.php\n2\tapp/B.php\n"))
    expect("file in two slices", code == 1 and "app/A.php is in slice 1 and slice 2" in out, out)
    code, out = run(repo, "main", "feature", "--plan", plan(repo, "1\tapp/A.php\n1\tapp/B.php\n1\tapp/C.php\n"))
    expect("unknown file", code == 1 and "app/C.php is in a slice but not in the diff" in out, out)


def test_empty_plan_or_empty_diff_never_passes():
    repo = new_repo()
    code, out = run(repo, "main", "feature", "--plan", plan(repo, "# nothing\n"))
    expect("empty plan and diff", code == 1 and "the plan is empty" in out and "the diff is empty" in out, out)


def test_plan_fails_when_base_moved_under_a_sliced_file():
    repo = new_repo()
    write(repo, "config/app.php", 12)
    commit(repo, "feature edits config")
    sh(repo, "git", "checkout", "-q", "main")
    write(repo, "config/app.php", 15)
    write(repo, "app/Other.php", 3)
    commit(repo, "main adds a block to config")
    sh(repo, "git", "checkout", "-q", "feature")
    code, out = run(repo, "main", "feature", "--plan", plan(repo, "1\tconfig/app.php\n"))
    expect("base drift", code == 1 and "config/app.php changed on main" in out, out)


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
    for f in FAILS:
        print(f"FAIL {f}")
    print(f"{len(tests) - len(FAILS)}/{len(tests)} passed")
    sys.exit(1 if FAILS else 0)
