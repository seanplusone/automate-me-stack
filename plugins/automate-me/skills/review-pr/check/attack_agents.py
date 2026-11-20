"""Find codex and claude on PATH and run one headless pass with each.

Usage: python3 attack_agents.py
       python3 attack_agents.py --run --brief <file> --out <dir>

Prints one name per line, codex then claude. Prints `none` when neither
binary is on PATH. --run writes <dir>/<name>.md with that CLI's stdout.
The brief file is the whole prompt. This script does not decide what to
attack, and it does not pick a fallback agent.
"""
import os
import shutil
import subprocess
import sys

NAMES = ("codex", "claude")


def command(binary, name, brief):
    """The headless argv for one CLI. The brief is the last argument."""
    if name == "codex":
        return [binary, "exec", "--skip-git-repo-check", brief]
    if name == "claude":
        return [binary, "-p", brief]
    raise SystemExit(f"unknown agent {name}")


def detect(search_path=None):
    """(name, binary) pairs that resolve, in a stable order. search_path replaces PATH."""
    found = []
    for name in NAMES:
        binary = shutil.which(name, path=search_path)
        if binary:
            found.append((name, binary))
    return found


def run_all(brief_path, out_dir, search_path=None, runner=None):
    """Run each detected CLI. Returns 0, or 1 when a CLI exits non-zero."""
    found = detect(search_path)
    if not found:
        print("none")
        return 0
    os.makedirs(out_dir, exist_ok=True)
    brief = open(brief_path).read()
    failed = 0
    for name, binary in found:
        cmd = command(binary, name, brief)
        if runner:
            result = runner(cmd)
        else:
            result = subprocess.run(cmd, capture_output=True, text=True)
        open(os.path.join(out_dir, name + ".md"), "w").write(result.stdout or "")
        if result.returncode != 0:
            failed = 1
            open(os.path.join(out_dir, name + ".err"), "w").write(result.stderr or "")
        print(name)
    return failed


def main(argv):
    if any(a in ("-h", "--help") for a in argv[1:]):
        print((__doc__ or "").strip())
        return 0
    if "--run" not in argv[1:]:
        names = [name for name, _binary in detect()]
        print("\n".join(names) if names else "none")
        return 0
    if "--brief" not in argv or "--out" not in argv:
        print((__doc__ or "").strip(), file=sys.stderr)
        return 2
    brief = argv[argv.index("--brief") + 1]
    out = argv[argv.index("--out") + 1]
    return run_all(brief, out)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
