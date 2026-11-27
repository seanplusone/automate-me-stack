"""Run: python3 check/test_proof_seal.py"""
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROOF = HERE / "proof.py"
FIXTURE = HERE / "fixtures/proof/briefs/demo/pass.md"
BRIEF = "briefs/demo/b.md"
SUMMARY = "proof-summary.txt"

FAILS = []


def git(repo, *args):
    return subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True, check=True, timeout=20,
    ).stdout.strip("\n")


def commit(repo, *args):
    git(repo, "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false",
        "commit", "-q", *args)


def make_repo(repo):
    git(repo, "init", "-q")
    brief = repo / BRIEF
    brief.parent.mkdir(parents=True)
    (repo / "briefs/WORKSTREAMS").write_text("demo\n")
    brief.write_text(re.sub(r"test -f [^ `]*md", "true", FIXTURE.read_text()))
    (repo / ".gitignore").write_text("out/\nother/\n")
    git(repo, "add", "-A")
    commit(repo, "-m", "init")


def expect_proof(repo, *args, code=0, stop=False):
    proc = subprocess.run(
        [sys.executable, str(PROOF), *args],
        cwd=repo, capture_output=True, text=True, timeout=20,
    )
    output = proc.stdout + proc.stderr
    if proc.returncode != code or (stop and "STOP" not in output):
        expected = f"exit {code}" + (" with STOP" if stop else "")
        raise AssertionError(
            f"{' '.join(args)} wanted {expected}, got exit {proc.returncode}: {output.strip()!r}"
        )


def replace(path, old, new):
    content = path.read_text()
    if old not in content:
        raise AssertionError(f"{path.name} missing {old!r} before edit")
    path.write_text(content.replace(old, new))


def test_honest(repo):
    expect_proof(repo, "run", BRIEF, "out")
    expect_proof(repo, "check", BRIEF, "out")


def test_fail_to_pass(repo):
    brief = repo / BRIEF
    brief.write_text(re.sub(r"^(  - m1: )`true`", r"\1`false`", brief.read_text(), flags=re.M))
    commit(repo, "-am", "fail")
    expect_proof(repo, "run", BRIEF, "out", code=1)
    verify = repo / "out/verify-m1.txt"
    first, _, rest = verify.read_text().partition("\n")
    if first != "exit=1":
        raise AssertionError(f"verify-m1.txt wanted exit=1 before edit, got {first!r}")
    verify.write_text("exit=0\n" + rest)
    replace(repo / "out" / SUMMARY, "VERIFY: FAIL", "VERIFY: PASS")
    expect_proof(repo, "check", BRIEF, "out", code=2, stop=True)


def test_edited_stale_sha(repo):
    expect_proof(repo, "run", BRIEF, "out")
    old_head = git(repo, "rev-parse", "HEAD")
    commit(repo, "--allow-empty", "-m", "next")
    expect_proof(repo, "check", BRIEF, "out", code=1)
    replace(repo / "out" / SUMMARY, old_head, git(repo, "rev-parse", "HEAD"))
    expect_proof(repo, "check", BRIEF, "out", code=2)


def test_copied_proof(repo):
    expect_proof(repo, "run", BRIEF, "out")
    old_head = git(repo, "rev-parse", "HEAD")
    commit(repo, "--allow-empty", "-m", "next")
    shutil.copytree(repo / "out", repo / "other")
    replace(repo / "other" / SUMMARY, old_head, git(repo, "rev-parse", "HEAD"))
    expect_proof(repo, "check", BRIEF, "other", code=2)


def append_junk(repo):
    with (repo / "out/verify-m2.txt").open("r+") as verify:
        verify.read()
        verify.write("junk\n")


def test_edited_verify_output(repo):
    expect_proof(repo, "run", BRIEF, "out")
    append_junk(repo)
    expect_proof(repo, "check", BRIEF, "out", code=2)


def test_stop_holds(repo):
    expect_proof(repo, "run", BRIEF, "out")
    append_junk(repo)
    expect_proof(repo, "check", BRIEF, "out", code=2, stop=True)
    expect_proof(repo, "run", BRIEF, "out")
    expect_proof(repo, "check", BRIEF, "out", code=2)
    expect_proof(repo, "--reset")
    expect_proof(repo, "check", BRIEF, "out")


def test_extra_unknown_id(repo):
    expect_proof(repo, "run", BRIEF, "out")
    (repo / "out/verify-zz.txt").write_text("exit=0\ncmd: true\n")
    expect_proof(repo, "check", BRIEF, "out")


def test_state_in_git_dir(repo):
    expect_proof(repo, "run", BRIEF, "out")
    append_junk(repo)
    expect_proof(repo, "check", BRIEF, "out", code=2, stop=True)
    status = git(repo, "status", "--porcelain", "--ignored")
    outside_out = [line for line in status.splitlines() if not line[3:].startswith("out/")]
    if outside_out:
        raise AssertionError(f"git status listed paths outside out/: {outside_out!r}")


if __name__ == "__main__":
    cases = (
        test_honest,
        test_fail_to_pass,
        test_edited_stale_sha,
        test_copied_proof,
        test_edited_verify_output,
        test_stop_holds,
        test_extra_unknown_id,
        test_state_in_git_dir,
    )
    for case in cases:
        try:
            with tempfile.TemporaryDirectory() as tmp:
                repo = Path(tmp)
                make_repo(repo)
                case(repo)
        except (AssertionError, OSError, subprocess.SubprocessError) as err:
            reason = getattr(err, "stderr", None) or str(err)
            FAILS.append(f"{case.__name__}: {reason.strip()}")
    for failure in FAILS:
        print(f"FAIL {failure}")
    print(f"{len(cases) - len(FAILS)}/{len(cases)} passed")
    sys.exit(1 if FAILS else 0)
