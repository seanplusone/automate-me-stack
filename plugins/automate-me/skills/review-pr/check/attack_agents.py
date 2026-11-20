"""Find codex and claude on PATH and run one headless pass with each.

Usage: python3 attack_agents.py
       python3 attack_agents.py --run --brief <file> --out <dir> [--cwd <dir>] [--timeout <seconds>]

Prints one name per line, codex then claude. Prints `none` when neither
binary is on PATH. --run writes <dir>/<name>.md and <dir>/<name>.err.
The brief file is the whole prompt, written to the CLI's stdin, not argv.
Codex runs sandboxed workspace-write. Claude may run Bash in the checkout
(acceptEdits), not a bypass of the whole machine. The default wait is 600
seconds. A timeout writes `Parse: timeout`. A non-zero exit, crash, or
undecodable output writes `Parse: error`. A merge does not treat either as
an approve.
This script does not decide what to attack, and it does not pick a fallback agent.
"""
import os
import shutil
import subprocess
import sys

NAMES = ("codex", "claude")
DEFAULT_TIMEOUT = 600
def command(binary, name):
    """Argv for one CLI. The brief is not included. It goes on stdin."""
    if name == "codex":
        return [binary, "exec", "--skip-git-repo-check", "--sandbox", "workspace-write"]
    if name == "claude":
        return [binary, "-p", "--permission-mode", "acceptEdits", "--allowedTools", "Bash"]
    raise SystemExit(f"unknown agent {name}")


def as_text(blob):
    """Decode CLI bytes. Invalid bytes become U+FFFD instead of raising."""
    if blob is None:
        return ""
    if isinstance(blob, bytes):
        return blob.decode("utf-8", "replace")
    return blob


def write_error(out_path, err_path, detail):
    open(err_path, "w").write(detail)
    open(out_path, "w").write("Parse: error\n")


def detect(search_path=None):
    """(name, binary) pairs that resolve, in a stable order. search_path replaces PATH."""
    found = []
    for name in NAMES:
        binary = shutil.which(name, path=search_path)
        if binary:
            found.append((name, binary))
    return found


def run_all(brief_path, out_dir, search_path=None, runner=None, timeout=DEFAULT_TIMEOUT, cwd=None):
    """Run each detected CLI. Returns 0, or 1 when a CLI exits non-zero or times out."""
    found = detect(search_path)
    if not found:
        print("none")
        return 0
    os.makedirs(out_dir, exist_ok=True)
    for name in os.listdir(out_dir):
        if name.endswith(".md") or name.endswith(".err"):
            os.remove(os.path.join(out_dir, name))
    brief = open(brief_path, "rb").read()
    work = cwd if cwd is not None else os.getcwd()
    failed = 0
    for name, binary in found:
        cmd = command(binary, name)
        out_path = os.path.join(out_dir, name + ".md")
        err_path = os.path.join(out_dir, name + ".err")
        try:
            if runner:
                result = runner(cmd, brief)
            else:
                result = subprocess.run(
                    cmd, input=brief, cwd=work, capture_output=True, timeout=timeout)
        except subprocess.TimeoutExpired as exc:
            failed = 1
            open(err_path, "w").write(as_text(exc.stderr) + f"\ntimed out after {timeout}s\n")
            open(out_path, "w").write("Parse: timeout\n")
            print(name)
            continue
        except Exception as exc:
            failed = 1
            write_error(out_path, err_path, f"{type(exc).__name__}: {exc}\n")
            print(name)
            continue
        stdout = as_text(getattr(result, "stdout", "") or "")
        stderr = as_text(getattr(result, "stderr", "") or "")
        if getattr(result, "returncode", 1) != 0:
            failed = 1
            write_error(out_path, err_path, stderr + ("\n" if stderr else "") + stdout)
            print(name)
            continue
        open(out_path, "w").write(stdout)
        open(err_path, "w").write(stderr)
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
    if any(argv[1:].count(flag) > 1 for flag in ("--brief", "--out", "--cwd", "--timeout")):
        print("repeated option", file=sys.stderr)
        return 2
    brief = argv[argv.index("--brief") + 1]
    out = argv[argv.index("--out") + 1]
    cwd = argv[argv.index("--cwd") + 1] if "--cwd" in argv else None
    timeout = DEFAULT_TIMEOUT
    if "--timeout" in argv:
        try:
            timeout = float(argv[argv.index("--timeout") + 1])
        except ValueError:
            print("timeout must be a positive number of seconds", file=sys.stderr)
            return 2
        if timeout <= 0:
            print("timeout must be a positive number of seconds", file=sys.stderr)
            return 2
    return run_all(brief, out, timeout=timeout, cwd=cwd)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
