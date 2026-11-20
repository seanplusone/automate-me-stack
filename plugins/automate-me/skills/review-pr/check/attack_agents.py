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
import tempfile

NAMES = ("codex", "claude")
OWNED = ("codex.md", "claude.md", "codex.err", "claude.err")
DEFAULT_TIMEOUT = 600
LIVE = []


def contract_bytes():
    """The attack-file shape. It stops before any mention of the case key."""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "references", "attack.md")
    try:
        text = open(path, encoding="utf-8").read()
    except OSError:
        return b""
    marker = "## Attack file"
    if marker not in text:
        return b""
    body = text[text.index(marker):]
    for stop in ("## Check", "## Merge"):
        if stop in body:
            body = body[:body.index(stop)]
            break
    return ("\n\n" + body.rstrip() + "\n").encode("utf-8")


def clear_owned(out_dir):
    """Remove only the pass files this script writes. Leave briefs and keys alone."""
    os.makedirs(out_dir, exist_ok=True)
    for name in OWNED:
        path = os.path.join(out_dir, name)
        if os.path.isfile(path) or os.path.islink(path):
            os.remove(path)


def _kill_group(proc):
    """Kill the child and every process it started."""
    if proc is None:
        return
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


def _kill_live():
    for proc in list(LIVE):
        _kill_group(proc)


def _on_stop(signum, _frame):
    """SIGTERM and SIGINT kill the agent group, then this process exits."""
    _kill_live()
    raise SystemExit(128 + signum)


def _same(left, right):
    try:
        return os.path.realpath(left) == os.path.realpath(right)
    except OSError:
        return False


def _case_root(path):
    """The cases/<name> directory when path sits in a case that has key.md."""
    if not path:
        return None
    directory = os.path.realpath(path)
    if not os.path.isdir(directory):
        directory = os.path.dirname(directory)
    while True:
        parent = os.path.dirname(directory)
        if os.path.basename(parent) == "cases" and os.path.isfile(os.path.join(directory, "key.md")):
            return directory
        if parent == directory:
            return None
        directory = parent


def agent_cwd(cwd):
    """A copy of the checkout when cwd is a planted case. The key stays out."""
    root = _case_root(cwd)
    if not root:
        return cwd
    temp = tempfile.mkdtemp(prefix="attack-cwd-")
    real = os.path.realpath(cwd)
    if os.path.basename(real) in ("head", "base") and os.path.dirname(real) == root:
        source = real
        for name in os.listdir(source):
            if name == "key.md":
                continue
            src = os.path.join(source, name)
            dst = os.path.join(temp, name)
            if os.path.isdir(src):
                shutil.copytree(src, dst, symlinks=True)
            else:
                shutil.copy2(src, dst, follow_symlinks=True)
    else:
        for name in ("head", "base"):
            src = os.path.join(root, name)
            if os.path.isdir(src):
                shutil.copytree(src, os.path.join(temp, name), symlinks=True)
    print("warning: agents run outside the case so they cannot read key.md", file=sys.stderr)
    return temp
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
    """(returncode, stdout, stderr). The child is its own process group."""
    proc = subprocess.Popen(
        cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        cwd=work, start_new_session=True,
    )
    LIVE.append(proc)
    try:
        try:
            stdout, stderr = proc.communicate(brief, timeout=timeout)
        except BaseException:
            _kill_group(proc)
            raise
        return proc.returncode, stdout, stderr
    finally:
        if proc.poll() is None:
            _kill_group(proc)
        if proc in LIVE:
            LIVE.remove(proc)


def run_all(brief_path, out_dir, search_path=None, runner=None, timeout=DEFAULT_TIMEOUT, cwd=None):
    """Run each detected CLI. Returns 0, or 1 when a CLI exits non-zero or times out."""
    for name in OWNED:
        if _same(brief_path, os.path.join(out_dir, name)):
            print("refusing to delete the brief", file=sys.stderr)
            return 2
    brief_body = b""
    if os.path.isfile(brief_path):
        brief_body = open(brief_path, "rb").read()
    clear_owned(out_dir)
    found = detect(search_path)
    if not found:
        print("none")
        return 0
    if not os.path.isfile(brief_path) and not brief_body:
        print("brief: missing file", file=sys.stderr)
        return 2
    brief = contract_bytes() + b"\n" + brief_body
    work = agent_cwd(cwd if cwd is not None else os.getcwd())
    previous = {
        signal.SIGTERM: signal.signal(signal.SIGTERM, _on_stop),
        signal.SIGINT: signal.signal(signal.SIGINT, _on_stop),
    }
    try:
        return _run_found(found, brief, work, out_dir, runner, timeout)
    finally:
        _kill_live()
        for sig, old in previous.items():
            signal.signal(sig, old)


def _run_found(found, brief, work, out_dir, runner, timeout):
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
    known = {"--run", "--brief", "--out", "--cwd", "--timeout", "--help", "-h"}
    if any(arg.startswith("--") and arg not in known for arg in argv[1:]):
        print((__doc__ or "").strip(), file=sys.stderr)
        return 2
    if "--brief" not in argv or "--out" not in argv:
        print((__doc__ or "").strip(), file=sys.stderr)
        return 2
    if any(argv[1:].count(flag) > 1 for flag in ("--brief", "--out", "--cwd", "--timeout")):
        print("repeated option", file=sys.stderr)
        return 2

    def _value(flag):
        index = argv.index(flag)
        if index + 1 >= len(argv) or argv[index + 1].startswith("--"):
            print((__doc__ or "").strip(), file=sys.stderr)
            return None
        return argv[index + 1]

    brief = _value("--brief")
    out = _value("--out")
    if brief is None or out is None:
        return 2
    cwd = _value("--cwd") if "--cwd" in argv else None
    if "--cwd" in argv and cwd is None:
        return 2
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
