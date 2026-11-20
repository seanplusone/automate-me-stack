"""Find codex and claude on PATH and run one headless pass with each.

Usage: python3 attack_agents.py
       python3 attack_agents.py --run --brief <file> --out <dir> [--cwd <dir>] [--timeout <seconds>]

Prints one name per line, codex then claude. Prints `none` when neither
binary is on PATH. --run writes <dir>/<name>.md and <dir>/<name>.err.
The brief file is written to the CLI's stdin, not argv, after the attack-file contract.
Codex runs sandboxed workspace-write. Claude may run Bash in the checkout
(acceptEdits), not a bypass of the whole machine. The default wait is 600
seconds. A timeout writes `Parse: timeout`. A non-zero exit, crash, or
undecodable output writes `Parse: error`. A merge does not treat either as
an approve.
This script does not decide what to attack, and it does not pick a fallback agent.
"""
import os
import shutil
import signal
import subprocess
import sys

NAMES = ("codex", "claude")
OWNED = ("codex.md", "claude.md", "codex.err", "claude.err")
DEFAULT_TIMEOUT = 600


def contract_bytes():
    """The attack-file rules, appended so a short brief still states the JSON shape."""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "references", "attack.md")
    try:
        text = open(path, encoding="utf-8").read()
    except OSError:
        return b""
    marker = "## Attack file"
    if marker not in text:
        return b""
    return ("\n\n" + text[text.index(marker):]).encode("utf-8")


def clear_owned(out_dir):
    """Remove only the pass files this script writes. Leave briefs and keys alone."""
    os.makedirs(out_dir, exist_ok=True)
    for name in OWNED:
        path = os.path.join(out_dir, name)
        if os.path.isfile(path) or os.path.islink(path):
            os.remove(path)


def _kill_group(proc):
    """Kill the child and every process it started."""
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError, OSError):
        try:
            proc.kill()
        except OSError:
            pass
    try:
        proc.wait(timeout=2)
    except subprocess.TimeoutExpired:
        pass
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


def _run_one(cmd, brief, work, timeout):
    """(returncode, stdout, stderr). Timeout kills the process group and raises TimeoutExpired."""
    proc = subprocess.Popen(
        cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        cwd=work, start_new_session=True,
    )
    try:
        stdout, stderr = proc.communicate(brief, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        _kill_group(proc)
        raise exc
    return proc.returncode, stdout, stderr


def run_all(brief_path, out_dir, search_path=None, runner=None, timeout=DEFAULT_TIMEOUT, cwd=None):
    """Run each detected CLI. Returns 0, or 1 when a CLI exits non-zero or times out."""
    clear_owned(out_dir)
    found = detect(search_path)
    if not found:
        print("none")
        return 0
    brief = contract_bytes() + b"\n" + open(brief_path, "rb").read()
    work = cwd if cwd is not None else os.getcwd()
    failed = 0
    for name, binary in found:
        cmd = command(binary, name)
        out_path = os.path.join(out_dir, name + ".md")
        err_path = os.path.join(out_dir, name + ".err")
        try:
            if runner:
                result = runner(cmd, brief)
                code = getattr(result, "returncode", 1)
                stdout, stderr = getattr(result, "stdout", "") or "", getattr(result, "stderr", "") or ""
            else:
                code, stdout, stderr = _run_one(cmd, brief, work, timeout)
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
        stdout, stderr = as_text(stdout), as_text(stderr)
        if code != 0:
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
