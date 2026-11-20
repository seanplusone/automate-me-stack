"""Find codex and claude on PATH and run one headless pass with each.

Usage: python3 attack_agents.py
       python3 attack_agents.py --run --brief <file> --out <dir> [--cwd <dir>] [--timeout <seconds>] [--sandbox auto|bwrap|docker|none]

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
SANDBOXES = ("auto", "bwrap", "docker", "none")
ENV_ALLOW = (
    "OPENAI_API_KEY", "CODEX_API_KEY", "ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN",
    "CLAUDE_API_KEY", "CLAUDE_CODE_OAUTH_TOKEN",
    "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN",
    "AWS_REGION", "AWS_DEFAULT_REGION",
    "HTTPS_PROXY", "HTTP_PROXY", "NO_PROXY", "https_proxy", "http_proxy", "no_proxy",
    "SSL_CERT_FILE", "SSL_CERT_DIR", "REQUESTS_CA_BUNDLE", "CURL_CA_BUNDLE",
    "NODE_EXTRA_CA_CERTS",
)
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


def _stop_signals():
    found = []
    for name in ("SIGTERM", "SIGINT", "SIGHUP", "SIGQUIT"):
        sig = getattr(signal, name, None)
        if sig is not None:
            found.append(sig)
    return found


def _preexec():
    """On Linux, die if the parent dies, including when the parent is SIGKILL'd."""
    if sys.platform != "linux":
        return
    try:
        import ctypes
        libc = ctypes.CDLL(None, use_errno=True)
        if libc.prctl(1, int(signal.SIGKILL)) != 0:
            return
        if os.getppid() == 1:
            os.kill(os.getpid(), signal.SIGKILL)
    except Exception:
        return


def _on_stop(signum, _frame):
    """Stop signals kill the agent group, then this process exits."""
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


def _inside(path, root):
    try:
        target = os.path.realpath(path)
        base = os.path.realpath(root)
    except OSError:
        return False
    return target == base or target.startswith(base + os.sep)


def _copy_tree(src, dst, root):
    """Copy a tree. A symlink that points outside the tree is skipped."""
    os.makedirs(dst, exist_ok=True)
    for name in os.listdir(src):
        if name == "key.md":
            continue
        source = os.path.join(src, name)
        target = os.path.join(dst, name)
        if os.path.islink(source):
            if not _inside(source, root):
                continue
            os.symlink(os.readlink(source), target)
            continue
        if os.path.isdir(source):
            _copy_tree(source, target, root)
            continue
        shutil.copy2(source, target, follow_symlinks=False)


def agent_cwd(cwd):
    """(directory, created). A planted case is copied so the key stays out."""
    root = _case_root(cwd)
    if not root:
        return cwd, False
    temp = tempfile.mkdtemp(prefix="attack-cwd-")
    for name in ("head", "base"):
        src = os.path.join(root, name)
        if os.path.isdir(src):
            _copy_tree(src, os.path.join(temp, name), src)
    return temp, True


def _exposes(path, forbidden):
    """True when binding this path would show a forbidden tree or sit inside one."""
    try:
        real = os.path.realpath(path)
    except OSError:
        return True
    for item in forbidden:
        if not item:
            continue
        try:
            bad = os.path.realpath(item)
        except OSError:
            continue
        if real == bad or real.startswith(bad + os.sep) or bad.startswith(real + os.sep):
            return True
    return False


def resolve_sandbox(choice):
    """auto, bwrap, docker, none, missing, or bad. Only bwrap is a real backend."""
    choice = (choice or "auto").strip().lower()
    if choice not in SANDBOXES:
        return "bad"
    if choice == "none":
        return "none"
    if choice == "docker":
        return "docker"
    if choice == "bwrap":
        return "bwrap" if shutil.which("bwrap") else "missing"
    if shutil.which("bwrap"):
        return "bwrap"
    return "missing"


def _sandbox_env(name):
    """The only environment the agent gets inside the sandbox."""
    env = {
        "PATH": "/usr/local/bin:/usr/bin:/bin",
        "HOME": "/home/agent",
        "PWD": "/work",
        "LANG": os.environ.get("LANG") or "C.UTF-8",
        "TERM": os.environ.get("TERM") or "dumb",
    }
    for key in ENV_ALLOW:
        if os.environ.get(key):
            env[key] = os.environ[key]
    return env


def _auth_paths(name, binary):
    """The CLI file and its auth dir. A path that would reveal the case is left out."""
    home = os.path.expanduser("~")
    paths = [os.path.realpath(binary)]
    if os.path.abspath(binary) != os.path.realpath(binary):
        paths.append(os.path.abspath(binary))
    if name == "codex":
        paths.append(os.path.join(home, ".codex"))
    if name == "claude":
        paths.append(os.path.join(home, ".claude"))
        paths.append(os.path.join(home, ".local", "share", "claude"))
        real = os.path.realpath(binary)
        parts = real.split(os.sep)
        if "claude" in parts:
            index = len(parts) - 1 - parts[::-1].index("claude")
            paths.append(os.sep.join(parts[:index + 1]))
    return [path for path in paths if path and os.path.exists(path)]


def _ro_bind(argv, src, dest, seen_dirs, forbidden):
    if not os.path.exists(src) or _exposes(src, forbidden):
        return
    parent = os.path.dirname(dest)
    chain = []
    while parent and parent != "/":
        chain.append(parent)
        parent = os.path.dirname(parent)
    for directory in reversed(chain):
        if directory not in seen_dirs:
            argv += ["--dir", directory]
            seen_dirs.add(directory)
    argv += ["--ro-bind", src, dest]


def bwrap_command(cmd, binary, name, work, forbidden):
    """Argv that runs cmd with only system dirs and /work visible."""
    tool = shutil.which("bwrap") or "bwrap"
    argv = [
        tool,
        "--unshare-all", "--share-net", "--die-with-parent", "--new-session",
        "--tmpfs", "/",
    ]
    for path in ("/usr", "/lib", "/lib64", "/bin"):
        if os.path.exists(path) and not _exposes(path, forbidden):
            argv += ["--ro-bind", path, path]
    argv += ["--dir", "/etc"]
    for path in (
        "/etc/resolv.conf", "/etc/hosts", "/etc/passwd", "/etc/group", "/etc/nsswitch.conf",
        "/etc/ssl", "/etc/ssl/certs", "/etc/ca-certificates", "/etc/pki",
    ):
        if os.path.exists(path) and not _exposes(path, forbidden):
            argv += ["--ro-bind", path, path]
    argv += ["--proc", "/proc", "--dev", "/dev"]
    argv += ["--bind", work, "/work", "--chdir", "/work"]
    argv += ["--tmpfs", "/home", "--dir", "/home/agent"]
    seen = {"/", "/etc", "/home", "/home/agent", "/work"}
    for path in _auth_paths(name, binary):
        if path == os.path.realpath(work) or _inside(path, work):
            continue
        _ro_bind(argv, path, path, seen, forbidden)
    argv += ["--clearenv"]
    for key, value in _sandbox_env(name).items():
        argv += ["--setenv", key, value]
    argv += cmd
    return argv


def _agent_env(work, hide):
    """PWD is the agent directory. Drop OLDPWD and any value that names a hidden path."""
    hidden = []
    for path in hide:
        if not path:
            continue
        hidden.append(os.path.abspath(path))
        try:
            hidden.append(os.path.realpath(path))
        except OSError:
            pass
    env = {}
    for key, value in os.environ.items():
        if key in ("OLDPWD", "PWD"):
            continue
        if any(item and item in str(value) for item in hidden):
            continue
        env[key] = value
    env["PWD"] = os.path.abspath(work)
    return env
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


def _run_one(cmd, brief, work, timeout, env):
    """(returncode, stdout, stderr). The child dies with this process, and its group is killable."""
    proc = subprocess.Popen(
        cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        cwd=work, env=env, start_new_session=True, preexec_fn=_preexec,
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


def run_all(brief_path, out_dir, search_path=None, runner=None, timeout=DEFAULT_TIMEOUT, cwd=None, sandbox="auto"):
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
    origin = cwd if cwd is not None else os.getcwd()
    chosen = resolve_sandbox(sandbox)
    if chosen == "bad":
        print((__doc__ or "").strip(), file=sys.stderr)
        return 2
    planted = _case_root(origin) is not None
    if (sandbox or "auto") == "auto" and not planted:
        chosen = "none"
    if chosen == "docker":
        print("error: the docker sandbox is not implemented. bwrap is the reference.", file=sys.stderr)
        chosen = "missing" if planted else "none"
    if planted and chosen != "bwrap":
        print("error: a practice case needs bwrap. Refusing to run without a sandbox.", file=sys.stderr)
        return 2
    if chosen != "bwrap":
        print("warning: running unsandboxed. There is no practice key to hide.", file=sys.stderr)
        chosen = "none"
    work, made = agent_cwd(origin)
    env = _agent_env(work, [origin, _case_root(origin)])
    previous = {sig: signal.signal(sig, _on_stop) for sig in _stop_signals()}
    try:
        return _run_found(found, brief, work, out_dir, runner, timeout, env, chosen, origin)
    finally:
        _kill_live()
        for sig, old in previous.items():
            signal.signal(sig, old)
        if made:
            shutil.rmtree(work, ignore_errors=True)


def _run_found(found, brief, work, out_dir, runner, timeout, env, sandbox_name, origin):
    failed = 0
    forbidden = [origin, _case_root(origin)]
    for name, binary in found:
        cmd = command(binary, name)
        launch_env = env
        if sandbox_name == "bwrap":
            cmd = bwrap_command(cmd, binary, name, work, forbidden)
            launch_env = _sandbox_env(name)
        out_path = os.path.join(out_dir, name + ".md")
        err_path = os.path.join(out_dir, name + ".err")
        try:
            if runner:
                result = runner(cmd, brief)
                code = getattr(result, "returncode", 1)
                stdout, stderr = getattr(result, "stdout", "") or "", getattr(result, "stderr", "") or ""
            else:
                code, stdout, stderr = _run_one(cmd, brief, work, timeout, launch_env)
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


def _main(argv):
    if any(a in ("-h", "--help") for a in argv[1:]):
        print((__doc__ or "").strip())
        return 0
    if "--run" not in argv[1:]:
        names = [name for name, _binary in detect()]
        print("\n".join(names) if names else "none")
        return 0
    known = {"--run", "--brief", "--out", "--cwd", "--timeout", "--sandbox", "--help", "-h"}
    if any(arg.startswith("--") and arg not in known for arg in argv[1:]):
        print((__doc__ or "").strip(), file=sys.stderr)
        return 2
    if "--brief" not in argv or "--out" not in argv:
        print((__doc__ or "").strip(), file=sys.stderr)
        return 2
    if any(argv[1:].count(flag) > 1 for flag in ("--brief", "--out", "--cwd", "--timeout", "--sandbox")):
        print((__doc__ or "").strip(), file=sys.stderr)
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
    sandbox = _value("--sandbox") if "--sandbox" in argv else "auto"
    if "--sandbox" in argv and sandbox is None:
        return 2
    if "--timeout" in argv:
        try:
            timeout = float(argv[argv.index("--timeout") + 1])
        except ValueError:
            print("timeout must be a positive number of seconds", file=sys.stderr)
            return 2
        if timeout <= 0:
            print("timeout must be a positive number of seconds", file=sys.stderr)
            return 2
    return run_all(brief, out, timeout=timeout, cwd=cwd, sandbox=sandbox)


def main(argv):
    try:
        return _main(argv)
    except SystemExit:
        raise
    except Exception:
        print((__doc__ or "").strip(), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
