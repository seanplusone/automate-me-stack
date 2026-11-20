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
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time

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
CODEX_FILES = ("auth.json", "config.toml")
CLAUDE_FILES = (".credentials.json",)
CLAUDE_JSON_KEEP = (
    "hasCompletedOnboarding", "lastOnboardingVersion", "oauthAccount", "userID",
    "numStartups", "installMethod", "autoUpdates", "theme", "primaryApiKey",
)
STALE_SECONDS = 3600
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


def practice_roots(path):
    """Case directories whose key.md is this path, above it, or anywhere under it."""
    found, seen = [], set()

    def add(directory):
        if not directory:
            return
        real = os.path.realpath(directory)
        if real in seen or not os.path.isfile(os.path.join(real, "key.md")):
            return
        seen.add(real)
        found.append(real)

    add(_case_root(path))
    start = path if os.path.isdir(path) else os.path.dirname(path or "")
    if os.path.isdir(start):
        for dirpath, dirnames, filenames in os.walk(start, followlinks=False):
            dirnames[:] = [name for name in dirnames if name not in (".git", "node_modules") and not name.startswith(".")]
            if "key.md" in filenames:
                add(dirpath)
    return found


def agent_cwd(cwd):
    """(directory, created). Practice trees are copied without their key.md."""
    cases = practice_roots(cwd)
    if not cases:
        return cwd, False
    temp = tempfile.mkdtemp(prefix="attack-cwd-")
    single = len(cases) == 1
    for case in cases:
        label = "" if single else os.path.basename(case)
        for name in ("head", "base"):
            src = os.path.join(case, name)
            if not os.path.isdir(src):
                continue
            dest = os.path.join(temp, name) if not label else os.path.join(temp, label, name)
            _copy_tree(src, dest, src)
    return temp, True


def _host_codex_dir():
    return os.environ.get("CODEX_HOME") or os.path.join(os.path.expanduser("~"), ".codex")


def _host_claude_dir():
    return os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join(os.path.expanduser("~"), ".claude")


def _stripped_claude_json(src):
    try:
        data = json.loads(open(src, encoding="utf-8").read())
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    kept = {key: data[key] for key in CLAUDE_JSON_KEEP if key in data}
    return json.dumps(kept).encode("utf-8")


def _minimal_codex_config(text):
    """Keep model, provider, and auth tables. Drop project paths, hooks, and plugins."""
    keep_tables = ("model_providers", "profiles", "auth")
    keep_keys = ("model", "model_provider", "review_model", "profile")
    out, section = [], ""
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            section = stripped.strip("[]").split(".", 1)[0].strip().strip('"')
            if section in keep_tables:
                out.append(line)
            continue
        if section in keep_tables:
            out.append(line)
            continue
        key = stripped.split("=", 1)[0].strip()
        if key in keep_keys:
            out.append(line)
    return ("\n".join(out) + "\n").encode("utf-8") if out else b""


def _login_feeds():
    """(payload, sandbox dest). payload is a host path or bytes. Nothing is written to disk."""
    feeds = []
    codex = _host_codex_dir()
    auth = os.path.join(codex, CODEX_FILES[0])
    if os.path.isfile(auth) and not os.path.islink(auth):
        feeds.append((auth, "/home/agent/.codex/" + CODEX_FILES[0]))
    config = os.path.join(codex, CODEX_FILES[1])
    if os.path.isfile(config) and not os.path.islink(config):
        try:
            text = open(config, encoding="utf-8", errors="replace").read()
        except OSError:
            text = ""
        body = _minimal_codex_config(text)
        if body.strip():
            feeds.append((body, "/home/agent/.codex/" + CODEX_FILES[1]))
    claude = _host_claude_dir()
    creds = os.path.join(claude, CLAUDE_FILES[0])
    if os.path.isfile(creds) and not os.path.islink(creds):
        feeds.append((creds, "/home/agent/.claude/" + CLAUDE_FILES[0]))
    if os.environ.get("CLAUDE_CONFIG_DIR"):
        raw = os.path.join(os.environ["CLAUDE_CONFIG_DIR"], ".claude.json")
    else:
        raw = os.path.join(os.path.expanduser("~"), ".claude.json")
    if os.path.isfile(raw) and not os.path.islink(raw):
        body = _stripped_claude_json(raw)
        if body:
            feeds.append((body, "/home/agent/.claude/.claude.json"))
    return feeds


def cleanup_stale():
    """Drop leftover homes immediately, and work copies older than an hour."""
    now = time.time()
    root = tempfile.gettempdir()
    try:
        names = os.listdir(root)
    except OSError:
        return
    for name in names:
        path = os.path.join(root, name)
        try:
            if name.startswith("attack-home-"):
                shutil.rmtree(path, ignore_errors=True)
            elif name.startswith("attack-cwd-") and now - os.path.getmtime(path) > STALE_SECONDS:
                shutil.rmtree(path, ignore_errors=True)
        except OSError:
            continue


def key_reachable(path):
    """True when key.md is under path, following links and dot dirs, or in a parent up to root."""
    path = os.path.abspath(path or ".")
    start = path if os.path.isdir(path) else os.path.dirname(path)
    seen = set()
    if os.path.isdir(start):
        for dirpath, dirnames, filenames in os.walk(start, followlinks=True):
            real = os.path.realpath(dirpath)
            if real in seen:
                dirnames[:] = []
                continue
            seen.add(real)
            if "key.md" in filenames:
                return True
    current = os.path.realpath(start)
    while True:
        if os.path.isfile(os.path.join(current, "key.md")):
            return True
        parent = os.path.dirname(current)
        if parent == current:
            return False
        current = parent


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
        return "bwrap" if _bwrap_bin() else "missing"
    if _bwrap_bin():
        return "bwrap"
    return "unavailable"


def _sandbox_env():
    """The only environment the agent gets. API keys are copied by name and never printed."""
    env = {
        "PATH": "/usr/local/bin:/usr/bin:/bin",
        "HOME": "/home/agent",
        "PWD": "/work",
        "LANG": os.environ.get("LANG") or "C.UTF-8",
        "TERM": os.environ.get("TERM") or "dumb",
        "CODEX_HOME": "/home/agent/.codex",
        "CLAUDE_CONFIG_DIR": "/home/agent/.claude",
    }
    for key in ENV_ALLOW:
        value = os.environ.get(key)
        if value:
            env[key] = value
    return env


def _package_dir(binary):
    """Directory of the resolved binary. Sibling helpers such as codex-code-mode-host live here."""
    real = os.path.realpath(binary)
    if not os.path.exists(real):
        return None
    parent = os.path.dirname(real)
    if parent in ("/", "/usr", "/bin", "/lib", "/lib64"):
        return None
    return parent


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


def _feed(fds, payload, dest, argv):
    if isinstance(payload, bytes):
        read_fd, write_fd = os.pipe()
        view = payload
        while view:
            wrote = os.write(write_fd, view)
            view = view[wrote:]
        os.close(write_fd)
        fd = read_fd
    else:
        fd = os.open(payload, os.O_RDONLY)
    fds.append(fd)
    argv += ["--file", str(fd), dest]


def bwrap_command(cmd, binary, work, forbidden, host_tmp=None):
    """(argv, fds). Login files are copied from fds and are not written to the host."""
    tool = _bwrap_bin() or "bwrap"
    work = os.path.abspath(work)
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
        "/etc/alternatives", "/etc/ssl", "/etc/ca-certificates", "/etc/pki",
    ):
        if os.path.exists(path) and not _exposes(path, forbidden):
            argv += ["--ro-bind", path, path]
    argv += ["--proc", "/proc", "--dev", "/dev"]
    if host_tmp:
        argv += ["--bind", os.path.abspath(host_tmp), "/tmp"]
    else:
        argv += ["--tmpfs", "/tmp"]
    argv += [
        "--bind", work, "/work", "--chdir", "/work",
        "--tmpfs", "/home", "--dir", "/home/agent",
        "--dir", "/home/agent/.codex", "--dir", "/home/agent/.claude",
    ]
    fds = []
    for payload, dest in _login_feeds():
        _feed(fds, payload, dest, argv)
    seen = {"/", "/etc", "/tmp", "/work", "/home", "/home/agent", "/home/agent/.codex", "/home/agent/.claude"}
    real_bin = os.path.realpath(binary)
    package = _package_dir(binary)
    launch = real_bin
    work_real = os.path.realpath(work)
    if package and (_inside(package, work_real) or package == work_real):
        rel = os.path.relpath(real_bin, work_real)
        launch = "/work" if rel == "." else "/work/" + rel
    elif package and not _exposes(package, forbidden):
        _ro_bind(argv, package, package, seen, forbidden)
    argv += ["--clearenv"]
    for key, value in _sandbox_env().items():
        argv += ["--setenv", key, value]
    argv += [launch if index == 0 else part for index, part in enumerate(cmd)]
    return argv, fds


def _bwrap_bin():
    found = shutil.which("bwrap")
    if found:
        return found
    if os.path.isfile("/usr/bin/bwrap") and os.access("/usr/bin/bwrap", os.X_OK):
        return "/usr/bin/bwrap"
    return None


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
def command(binary, name, outer_sandbox=False):
    """Argv for one CLI. The brief is not included. It goes on stdin."""
    binary = os.path.realpath(binary)
    if name == "codex":
        mode = "danger-full-access" if outer_sandbox else "workspace-write"
        return [binary, "exec", "--skip-git-repo-check", "--sandbox", mode]
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


def _run_one(cmd, brief, work, timeout, env, pass_fds=()):
    """(returncode, stdout, stderr). The child dies with this process, and its group is killable."""
    proc = subprocess.Popen(
        cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        cwd=os.path.abspath(work), env=env, start_new_session=True, preexec_fn=_preexec,
        pass_fds=tuple(pass_fds),
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


def run_all(brief_path, out_dir, search_path=None, runner=None, timeout=DEFAULT_TIMEOUT, cwd=None, sandbox="auto", host_tmp=None):
    """Run each detected CLI. Returns 0, or 1 when a CLI exits non-zero or times out."""
    cleanup_stale()
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
    origin = os.path.abspath(cwd if cwd is not None else os.getcwd())
    chosen = resolve_sandbox(sandbox)
    if chosen == "bad":
        print((__doc__ or "").strip(), file=sys.stderr)
        return 2
    if chosen == "docker":
        print("error: the docker sandbox is not implemented. bwrap is the reference.", file=sys.stderr)
        return 2
    if chosen == "missing":
        print("error: bwrap was requested but it is not installed.", file=sys.stderr)
        return 2
    if chosen == "unavailable":
        if key_reachable(origin):
            print("error: no sandbox is available and a key.md is reachable. Refusing to run.", file=sys.stderr)
            return 2
        print("warning: no sandbox is available. Running unsandboxed.", file=sys.stderr)
        chosen = "none"
    elif chosen == "none":
        print("warning: --sandbox none leaves the whole filesystem visible.", file=sys.stderr)
    work, made = agent_cwd(origin)
    env = _agent_env(work, [origin] + practice_roots(origin))
    previous = {sig: signal.signal(sig, _on_stop) for sig in _stop_signals()}
    try:
        return _run_found(found, brief, work, out_dir, runner, timeout, env, chosen, origin, host_tmp)
    finally:
        _kill_live()
        for sig, old in previous.items():
            signal.signal(sig, old)
        if made:
            shutil.rmtree(work, ignore_errors=True)


def _run_found(found, brief, work, out_dir, runner, timeout, env, sandbox_name, origin, host_tmp):
    failed = 0
    forbidden = [origin] + practice_roots(origin)
    outer = sandbox_name == "bwrap"
    for name, binary in found:
        cmd = command(binary, name, outer)
        launch_env = env
        fds = ()
        if outer:
            cmd, fds = bwrap_command(cmd, binary, work, forbidden, host_tmp)
            launch_env = _sandbox_env()
        out_path = os.path.join(out_dir, name + ".md")
        err_path = os.path.join(out_dir, name + ".err")
        try:
            try:
                if runner:
                    result = runner(cmd, brief)
                    code = getattr(result, "returncode", 1)
                    stdout, stderr = getattr(result, "stdout", "") or "", getattr(result, "stderr", "") or ""
                else:
                    code, stdout, stderr = _run_one(cmd, brief, work, timeout, launch_env, fds)
            finally:
                for fd in fds:
                    os.close(fd)
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
