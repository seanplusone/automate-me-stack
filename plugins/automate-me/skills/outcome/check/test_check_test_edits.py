"""Run: python3 check/test_check_test_edits.py"""
from pathlib import Path
import subprocess
import sys
import tempfile

SCRIPT = Path(__file__).resolve().with_name("check_test_edits.py")
TEST = "tests/test_a.py"
ORIGINAL = "def test_add():\n    assert 1 + 2 == 3\n"
MORE = "\ndef test_more():\n    assert 2 + 2 == 4\n"
BASE_FILES = {TEST: ORIGINAL, "app.py": "value = 1\n"}
FAILS = []


def git(repo, *args):
    return subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True, check=True,
    ).stdout


def commit(repo, message):
    git(repo, "add", "-A")
    git(repo, "-c", "user.name=t", "-c", "user.email=t@t",
        "-c", "commit.gpgsign=false", "commit", "-qm", message)
    return git(repo, "rev-parse", "HEAD").strip()


def init(repo, files):
    git(repo, "init", "-q")
    for path, contents in files.items():
        file = repo / path
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(contents, encoding="utf-8")
    return commit(repo, "tests first")


def check(repo, name, arg, expected, path=None):
    if not SCRIPT.is_file():
        FAILS.append(f"{name}: missing {SCRIPT.name}")
        return
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), arg], cwd=repo, capture_output=True, text=True,
    )
    output = proc.stdout + proc.stderr
    if (proc.returncode != expected or "Traceback (most recent call last)" in output
            or (path is not None and ("STOP" not in output or path not in output))):
        wanted = f"exit {expected}"
        if path is not None:
            wanted += f" with STOP and {path}"
        FAILS.append(f"{name}: expected {wanted}, got exit {proc.returncode}: {output!r}")


def test_assertion_and_stop():
    for state in ("unstaged", "staged", "committed"):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            base = init(repo, BASE_FILES)
            (repo / TEST).write_text(ORIGINAL.replace("== 3", ">= 0"), encoding="utf-8")
            if state == "staged":
                git(repo, "add", TEST)
            elif state == "committed":
                commit(repo, "weaken assertion")
            check(repo, f"{state} assertion edit", base, 2, TEST)
            if state == "unstaged":
                status = git(repo, "status", "--porcelain")
                if status != f" M {TEST}\n":
                    FAILS.append(f"stop state: unexpected git status {status!r}")
                git(repo, "checkout", "--", TEST)
                check(repo, "stop holds after checkout", base, 2)
                check(repo, "reset after checkout", "--reset", 0)
                check(repo, "check after reset", base, 0)


def test_other_stops():
    js = "a.test.js"
    for change in ("delete", "rename", "skip", "xfail", "JS skip"):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            base = init(repo, {**BASE_FILES, js: "it('adds', () => {});\n"})
            path = TEST
            if change == "delete":
                (repo / TEST).unlink()
            elif change == "rename":
                git(repo, "mv", TEST, "tests/test_b.py")
            elif change == "JS skip":
                path = js
                with (repo / js).open("a", encoding="utf-8") as file:
                    file.write("it.skip('subtracts', () => {});\n")
            else:
                (repo / TEST).write_text(
                    ORIGINAL + f"\n@pytest.mark.{change}" + MORE, encoding="utf-8",
                )
            check(repo, change, base, 2, path)


def test_allowed_and_invalid_base():
    with tempfile.TemporaryDirectory() as directory:
        repo = Path(directory)
        base = init(repo, BASE_FILES)
        check(repo, "clean repo", base, 0)
        (repo / "tests/test_new.py").write_text(MORE, encoding="utf-8")
        check(repo, "untracked new test file", base, 0)
        commit(repo, "add test file")
        check(repo, "committed new test file", base, 0)
        (repo / TEST).write_text(ORIGINAL + MORE, encoding="utf-8")
        check(repo, "appended test case", base, 0)
    with tempfile.TemporaryDirectory() as directory:
        repo = Path(directory)
        init(repo, BASE_FILES)
        check(repo, "invalid base", "nope", 2)


def test_generic_paths():
    paths = (
        "src/foo_test.go", "web/a.test.ts", "web/b.spec.js",
        "pkg/__tests__/x.js", "tests/fixtures/data.json", "app.py",
    )
    with tempfile.TemporaryDirectory() as directory:
        repo = Path(directory)
        base = init(repo, dict.fromkeys(paths, "one\n"))
        for path in paths[:-1]:
            (repo / path).write_text("two\n", encoding="utf-8")
            check(repo, f"edit {path}", base, 2, path)
            git(repo, "checkout", "--", path)
            check(repo, f"reset after {path}", "--reset", 0)
        (repo / "app.py").write_text("two\n", encoding="utf-8")
        check(repo, "non-test edit only", base, 0)


def test_binary_and_type_change():
    blob = "tests/fixtures/blob.bin"
    with tempfile.TemporaryDirectory() as directory:
        repo = Path(directory)
        init(repo, BASE_FILES)
        file = repo / blob
        file.parent.mkdir(parents=True)
        file.write_bytes(b"\x00\x01FAKE\x00")
        base = commit(repo, "add binary fixture")
        file.write_bytes(b"\x00\x02FAKE\x00")
        check(repo, "binary fixture edit", base, 2, blob)

    with tempfile.TemporaryDirectory() as directory:
        repo = Path(directory)
        base = init(repo, {**BASE_FILES, "tests/helper.py": "x = 1\n"})
        file = repo / TEST
        file.unlink()
        file.symlink_to("helper.py")
        check(repo, "test file replaced by symlink", base, 2, TEST)


if __name__ == "__main__":
    test_assertion_and_stop()
    test_other_stops()
    test_allowed_and_invalid_base()
    test_generic_paths()
    test_binary_and_type_change()
    for failure in FAILS:
        print(f"FAIL {failure}")
    print(f"{len(FAILS)} failed" if FAILS else "done")
    sys.exit(1 if FAILS else 0)
