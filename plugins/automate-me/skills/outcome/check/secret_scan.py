"""Scan staged changes or commits for secrets with gitleaks.

Usage:
  python3 check/secret_scan.py [--staged | --range <rev-range> | --install | --reset]

Exit 0 for a clean scan, hook install, or reset.
Exit 1 for a first hit or an existing hook we cannot replace.
Exit 2 for STOP. A human clears the stop with --reset.
"""
import argparse
from pathlib import Path
import subprocess
import sys

HOOK_MARKER = "# automate-me secret scan"


def git_path(*args):
    return Path(subprocess.check_output(["git", "rev-parse", *args], text=True).rstrip("\n"))


def install_hook():
    hook = git_path("--git-path", "hooks") / "pre-commit"
    if hook.is_symlink() or (
        hook.exists() and HOOK_MARKER.encode() not in hook.read_bytes().splitlines()
    ):
        print(f"Refusing to replace existing pre-commit hook at {hook}.")
        return 1

    script = str(Path(__file__).resolve())
    for char in '\\`"$':
        script = script.replace(char, "\\" + char)
    hook.parent.mkdir(parents=True, exist_ok=True)
    hook.write_text(f'#!/bin/sh\n{HOOK_MARKER}\nexec python3 "{script}" --staged\n')
    hook.chmod(0o755)
    return 0


def stop(reason):
    print(f"STOP: {reason} Report this to the human and do not retry. "
          "A human clears the stop with --reset.")
    return 2


def scan(state, rev_range):
    status = state.read_text().strip() if state.exists() else ""
    if status == "stop":
        return stop("A previous scan set a stop.")

    root = git_path("--show-toplevel")
    mode = ["--pre-commit", "--staged"] if rev_range is None else [f"--log-opts={rev_range}"]
    try:
        result = subprocess.run(
            ["gitleaks", "git", *mode, "--redact", "--no-banner", "--exit-code", "3",
             "--verbose", str(root)],
            cwd=root,
        )
    except FileNotFoundError:
        return stop("gitleaks is missing from PATH. Install it from "
                    "https://github.com/gitleaks/gitleaks/releases and add it to PATH.")
    except OSError as err:
        state.write_text("stop")
        return stop(f"Could not run gitleaks: {err}.")

    if result.returncode == 0:
        state.unlink(missing_ok=True)
        return 0
    if result.returncode != 3:
        state.write_text("stop")
        return stop(f"gitleaks exited with code {result.returncode}.")
    if status == "hits=1":
        state.write_text("stop")
        return stop("gitleaks found a secret after the one cleanup.")

    state.write_text("hits=1")
    print("You get one cleanup. Clean up by unstaging or editing the secret. "
          "Rotate it if it is real, then rerun the scan.")
    return 1


def main():
    parser = argparse.ArgumentParser(description="Scan git changes for secrets with gitleaks.")
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--staged", action="store_true")
    modes.add_argument("--range", metavar="REV-RANGE")
    modes.add_argument("--install", action="store_true")
    modes.add_argument("--reset", action="store_true")
    args = parser.parse_args()

    try:
        if args.install:
            return install_hook()
        state = git_path("--git-path", "automate-me-secret-scan")
        if args.reset:
            state.unlink(missing_ok=True)
            return 0
        return scan(state, args.range)
    except (OSError, subprocess.CalledProcessError) as err:
        return stop(f"Could not complete the secret scan command: {err}.")


if __name__ == "__main__":
    sys.exit(main())
