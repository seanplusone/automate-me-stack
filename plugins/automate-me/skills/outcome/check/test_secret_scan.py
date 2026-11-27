"""Run: python3 check/test_secret_scan.py"""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

SCRIPT = Path(__file__).resolve().with_name("secret_scan.py")
FAILS = []

# Synthetic key assembled at runtime.
FAKE_KEY = "\n".join(("-----BEGIN " + "PRIVATE KEY-----", "FAKE" * 16,
                      "-----END " + "PRIVATE KEY-----", ""))


def git(repo, *args, check=True):
    return subprocess.run(["git", *args], cwd=repo, capture_output=True,
                          text=True, check=check)


def commit(repo, *args, check=True):
    return git(repo, "-c", "user.name=t", "-c", "user.email=t@t",
               "-c", "commit.gpgsign=false", "commit", "-qm", "test", *args,
               check=check)


def stage(repo, name="clean.txt", content="ok\n"):
    (repo / name).write_text(content)
    git(repo, "add", "--", name)


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def scan(repo, expected, *args, env=None):
    proc = subprocess.run(
        [sys.executable, SCRIPT, *args], cwd=repo, env=env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=30,
    )
    require("FAKE" * 3 not in proc.stdout, "scanner exposed the fake key body")
    require(proc.returncode == expected,
            f"{' '.join(args)} wanted exit {expected}, got {proc.returncode}")
    return proc.stdout


def test_clean_stage(repo):
    stage(repo)
    scan(repo, 0, "--staged")


def test_first_hit(repo):
    stage(repo, "key.txt", FAKE_KEY)
    output = scan(repo, 1, "--staged")
    require("clean up" in output.lower(), "first hit must say to clean up")


def test_stop_and_reset(repo):
    test_first_hit(repo)
    output = scan(repo, 2, "--staged")
    require("STOP" in output, "second hit must say STOP")
    git(repo, "rm", "--cached", "--", "key.txt")
    stage(repo)
    scan(repo, 2, "--staged")
    scan(repo, 0, "--reset")
    scan(repo, 0, "--staged")


def test_cleanup_clears_count(repo):
    test_first_hit(repo)
    git(repo, "rm", "--cached", "--", "key.txt")
    stage(repo)
    scan(repo, 0, "--staged")
    test_first_hit(repo)


def hook_path(repo):
    return repo / git(repo, "rev-parse", "--git-path", "hooks").stdout.strip() / "pre-commit"


def test_installed_hook(repo):
    scan(repo, 0, "--install")
    require(hook_path(repo).is_file(), "install did not write pre-commit")
    stage(repo, "key.txt", FAKE_KEY)
    require(commit(repo, check=False).returncode != 0, "hook allowed the fake key")
    git(repo, "rm", "--cached", "--", "key.txt")
    scan(repo, 0, "--reset")
    stage(repo)
    commit(repo)


def test_existing_hook(repo):
    hook = hook_path(repo)
    hook.parent.mkdir(parents=True, exist_ok=True)
    original = b"#!/bin/sh\nexit 0\n"
    hook.write_bytes(original)
    proc = subprocess.run([sys.executable, SCRIPT, "--install"], cwd=repo,
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=30)
    require(proc.returncode != 0, "install accepted an existing hook")
    require(hook.is_file() and hook.read_bytes() == original, "existing hook changed")


def test_range(repo):
    stage(repo)
    commit(repo)
    stage(repo, "key.txt", FAKE_KEY)
    commit(repo, "--no-verify")
    scan(repo, 1, "--range", "HEAD~1..HEAD")


def test_missing_gitleaks(repo):
    stage(repo)
    with tempfile.TemporaryDirectory() as bin_dir:
        Path(bin_dir, "git").symlink_to(shutil.which("git"))
        Path(bin_dir, "python3").symlink_to(sys.executable)
        output = scan(repo, 2, "--staged", env=dict(os.environ, PATH=bin_dir))
    require("gitleaks" in output.lower(), "missing dependency must name gitleaks")


def test_state_stays_out_of_worktree(repo):
    stage(repo, "key.txt", FAKE_KEY)
    before = git(repo, "status", "--porcelain").stdout
    scan(repo, 1, "--staged")
    require(git(repo, "status", "--porcelain").stdout == before,
            "scan changed git status")


if __name__ == "__main__":
    cases = (test_clean_stage, test_first_hit, test_stop_and_reset,
             test_cleanup_clears_count, test_installed_hook, test_existing_hook,
             test_range, test_missing_gitleaks, test_state_stays_out_of_worktree)
    if SCRIPT.is_file() and not shutil.which("gitleaks"):
        print("SKIP: gitleaks not installed")
        cases = (test_missing_gitleaks,)
    for case in cases:
        try:
            require(SCRIPT.is_file(), f"missing {SCRIPT}")
            with tempfile.TemporaryDirectory() as tmp:
                repo = Path(tmp)
                git(repo, "init", "-q")
                case(repo)
        except (AssertionError, OSError, subprocess.SubprocessError) as err:
            FAILS.append(f"{case.__name__}: {err}")
    for failure in FAILS:
        print(f"FAIL {failure}")
    print(f"{len(FAILS)} failed" if FAILS else "done")
    sys.exit(1 if FAILS else 0)
