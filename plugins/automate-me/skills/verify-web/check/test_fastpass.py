"""Tests for fastpass.py select.

Run: python3 check/test_fastpass.py
"""
import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
FASTPASS = os.path.join(SKILL, "fastpass.py")

FAILS = []

BASE_CFG = """\
apps:
  - name: demo
    base_url: http://127.0.0.1:8000
    test_data: true
fast:
  serve_command: python3 app.py --port {port}
  ready_path: /health
  fingerprint: [app.py]
"""

JOURNEYS_CFG = BASE_CFG + """\
journeys:
  - name: refund
    command: node journeys/refund.js
    paths: [src/refund/**, src/orders/refund*]
  - name: login
    command: node journeys/login.js
    paths: [src/auth/**]
  - name: checkout
    command: node journeys/checkout.js
    paths: [src/cart/**]
journey_ignore: [README.md, docs/**]
"""

ALL_NAMES = ["refund", "login", "checkout"]


def check(name, ok, detail=""):
    print(f"{'PASS' if ok else 'FAIL'} {name}")
    if not ok:
        FAILS.append(name)
        if detail:
            print("    " + detail.replace("\n", "\n    "))


def write_file(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(text)


def run_select(cfg_path, root, *args):
    cmd = [sys.executable, FASTPASS, "select", "--config", cfg_path, "--root", root, *args]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    lines = p.stdout.splitlines()
    detail = (p.stdout + p.stderr).strip()
    return p.returncode, lines, detail


def test_select_paths():
    tmp = tempfile.mkdtemp(prefix="verify-web-fastpass-")
    try:
        cfg = os.path.join(tmp, "verify-web.yaml")
        write_file(cfg, JOURNEYS_CFG)

        code, lines, out = run_select(cfg, tmp, "--paths", "src/refund/page.js")
        check("select: one mapped path",
              code == 0 and lines == ["SELECT: mapped refund", "refund"], out)

        code, lines, out = run_select(cfg, tmp, "--paths", "src/cart/total.js", "src/refund/form.js")
        check("select: two mapped paths in config order",
              code == 0 and lines == ["SELECT: mapped refund, checkout", "refund", "checkout"], out)

        code, lines, out = run_select(cfg, tmp, "--paths", "src/unknown/file.js")
        check("select: unmapped path runs all",
              code == 0 and bool(lines)
              and lines[0].startswith("SELECT: all (unmapped: src/unknown/file.js")
              and lines[1:] == ALL_NAMES, out)

        code, lines, out = run_select(cfg, tmp, "--paths", "README.md", "docs/guide.md")
        check("select: ignored-only paths run all",
              code == 0 and bool(lines)
              and lines[0].startswith("SELECT: all (no changed path maps")
              and lines[1:] == ALL_NAMES, out)

        code, lines, out = run_select(cfg, tmp, "--paths", "src/refund/calc.js", "docs/x.md")
        check("select: mapped plus ignored path runs mapped only",
              code == 0 and lines == ["SELECT: mapped refund", "refund"], out)

        code, lines, out = run_select(cfg, tmp, "--paths", "src/refund/calc.js", "src/other/util.js")
        check("select: mapped plus unmapped path runs all",
              code == 0 and bool(lines)
              and lines[0].startswith("SELECT: all (unmapped: src/other/util.js")
              and lines[1:] == ALL_NAMES, out)

        code, lines, out = run_select(cfg, tmp, "--paths", "src/refund/a/b/c.js")
        check("select: ** crosses directories",
              code == 0 and lines == ["SELECT: mapped refund", "refund"], out)

        code, lines, out = run_select(cfg, tmp, "--paths", "src/orders/refund_x.js")
        check("select: * matches within one segment",
              code == 0 and lines == ["SELECT: mapped refund", "refund"], out)

        code, lines, out = run_select(cfg, tmp, "--paths", "src/orders/a/refund.js")
        check("select: * does not cross /",
              code == 0 and bool(lines)
              and lines[0].startswith("SELECT: all (unmapped: src/orders/a/refund.js")
              and lines[1:] == ALL_NAMES, out)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_select_git():
    tmp = tempfile.mkdtemp(prefix="verify-web-fastpass-git-")
    try:
        # Keep the config outside the git repo so it is not seen as an untracked file.
        cfg = os.path.join(tmp, "verify-web.yaml")
        repo = os.path.join(tmp, "repo")
        write_file(cfg, JOURNEYS_CFG)
        write_file(os.path.join(repo, "src", "refund", "base.js"), "v1\n")

        def git(*args):
            subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True)

        git("init")
        git("config", "user.email", "test@example.com")
        git("config", "user.name", "Test")
        git("add", ".")
        git("commit", "-m", "init")

        write_file(os.path.join(repo, "src", "refund", "base.js"), "v2\n")
        write_file(os.path.join(repo, "src", "auth", "new_login.js"), "new\n")

        code, lines, out = run_select(cfg, repo, "--base", "HEAD")
        check("select: git diff plus untracked file",
              code == 0 and lines == ["SELECT: mapped refund, login", "refund", "login"], out)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_select_no_journeys():
    tmp = tempfile.mkdtemp(prefix="verify-web-fastpass-empty-")
    try:
        empty_cfg = os.path.join(tmp, "empty.yaml")
        write_file(empty_cfg, BASE_CFG + "journeys: []\n")
        code, lines, out = run_select(empty_cfg, tmp, "--paths", "src/refund/page.js")
        check("select: empty journeys list exits 1",
              code == 1 and bool(lines) and lines[0] == "SELECT: none (no journeys configured)", out)

        missing_cfg = os.path.join(tmp, "missing.yaml")
        write_file(missing_cfg, BASE_CFG)
        code, lines, out = run_select(missing_cfg, tmp, "--paths", "src/refund/page.js")
        check("select: missing journeys key exits 1",
              code == 1 and bool(lines) and lines[0] == "SELECT: none (no journeys configured)", out)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


BUILD_CMD = """python3 -c "open('build-counter.txt','a').write('built\\n')" """.strip()
SERVE_CMD = "python3 -m http.server {port} --bind 127.0.0.1"
STARTED_RE = re.compile(r"^SERVE: started pid=(\d+) url=(\S+) build=(ran|reused)$")
REUSE_RE = re.compile(r"^SERVE: reuse pid=(\d+)(?:\s+url=(\S+))?$")


def make_env(name):
    tmp = tempfile.mkdtemp(prefix=f"verify-web-{name}-")
    return tmp, os.path.join(tmp, "root"), os.path.join(tmp, "state"), os.path.join(tmp, "verify-web.yaml")


def write_config(cfg_path, state_dir, build_command=BUILD_CMD, serve_command=SERVE_CMD,
                 ready_path="/", fingerprint="[src.txt]", ready_timeout=10, include_fast=True):
    lines = ["apps:", "  - name: demo", "    base_url: http://127.0.0.1:8000", "    test_data: true"]
    if include_fast:
        lines += ["fast:", f"  serve_command: {serve_command}", f"  ready_path: {ready_path}",
                  f"  fingerprint: {fingerprint}", f"  state_dir: {state_dir}"]
        if build_command is not None:
            lines.append(f"  build_command: {build_command}")
        if ready_timeout is not None:
            lines.append(f"  ready_timeout: {ready_timeout}")
    write_file(cfg_path, "\n".join(lines) + "\n")


def run_fastpass(subcmd, cfg_path, root, *args, timeout=30):
    p = subprocess.run([sys.executable, FASTPASS, subcmd, "--config", cfg_path, "--root", root, *args],
                       capture_output=True, text=True, timeout=timeout)
    return p.returncode, p.stdout.splitlines(), (p.stdout + p.stderr).strip()


def pid_alive(pid):
    if not pid or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def wait_gone(pid, timeout=5.0):
    end = time.monotonic() + timeout
    while time.monotonic() < end and pid_alive(pid):
        time.sleep(0.05)
    return not pid_alive(pid)


def state_path(state_dir, root):
    return os.path.join(state_dir, f"{hashlib.sha1(os.path.abspath(root).encode()).hexdigest()}.json")


def state_has_server(state_dir, root):
    sp = state_path(state_dir, root)
    if not os.path.exists(sp):
        return False
    try:
        return bool(json.loads(open(sp).read()).get("pid"))
    except (OSError, ValueError):
        return True


def counter_lines(root):
    p = os.path.join(root, "build-counter.txt")
    return len(open(p).read().splitlines()) if os.path.exists(p) else 0


def http_status(url):
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            return resp.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception:
        return None


def parse_started(lines):
    m = STARTED_RE.match(lines[0]) if lines else None
    return (int(m.group(1)), m.group(2), m.group(3)) if m else (None, None, None)


def parse_reuse(lines):
    m = REUSE_RE.match(lines[0]) if lines else None
    return int(m.group(1)) if m else None


def stop_proc(proc):
    if proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


def test_serve_lifecycle():
    tmp, root, state_dir, cfg = make_env("serve-life")
    try:
        write_file(os.path.join(root, "src.txt"), "v1\n")
        write_config(cfg, state_dir)

        code, lines, out = run_fastpass("serve", cfg, root)
        pid1, url1, build1 = parse_started(lines)
        st1 = http_status(url1) if url1 else None
        check("serve: first start runs build and answers HTTP",
              code == 0 and pid1 is not None and build1 == "ran"
              and counter_lines(root) == 1 and st1 is not None and st1 < 500,
              f"{out} (counter={counter_lines(root)}, status={st1})")

        code, lines, out = run_fastpass("serve", cfg, root)
        pid2 = parse_reuse(lines)
        check("serve: second call reuses server without rebuilding",
              code == 0 and pid1 is not None and pid2 == pid1 and counter_lines(root) == 1,
              f"{out} (pid1={pid1}, counter={counter_lines(root)})")

        write_file(os.path.join(root, "src.txt"), "v2\n")
        code, lines, out = run_fastpass("serve", cfg, root)
        pid3, _, build3 = parse_started(lines)
        old_gone = wait_gone(pid1) if pid1 else False
        check("serve: fingerprint change rebuilds and restarts",
              code == 0 and pid3 is not None and pid3 != pid1 and build3 == "ran"
              and counter_lines(root) == 2 and old_gone,
              f"{out} (pid1={pid1}, old_gone={old_gone}, counter={counter_lines(root)})")

        killed = False
        if pid3 and pid_alive(pid3):
            os.kill(pid3, signal.SIGTERM)
            killed = wait_gone(pid3)
        code, lines, out = run_fastpass("serve", cfg, root)
        pid4, _, build4 = parse_started(lines)
        check("serve: dead server with same fingerprint reuses build",
              killed and code == 0 and pid4 is not None and pid4 != pid3
              and build4 == "reused" and counter_lines(root) == 2,
              f"{out} (killed={killed}, counter={counter_lines(root)})")
    finally:
        run_fastpass("stop", cfg, root)
        shutil.rmtree(tmp, ignore_errors=True)


def test_stop_and_unrelated_process():
    tmp, root, state_dir, cfg = make_env("stop")
    sleeper = subprocess.Popen(["sleep", "60"])
    try:
        write_file(os.path.join(root, "src.txt"), "v1\n")
        write_config(cfg, state_dir)

        code, lines, out = run_fastpass("serve", cfg, root)
        pid, _, _ = parse_started(lines)
        scode, slines, sout = run_fastpass("stop", cfg, root)
        gone = wait_gone(pid) if pid else False
        deleted = not os.path.exists(state_path(state_dir, root))
        sleeper_ok = sleeper.poll() is None and pid_alive(sleeper.pid)
        check("stop: stops server, deletes state, spares unrelated sleep",
              code == 0 and pid is not None and scode == 0 and bool(slines)
              and slines[0] == f"STOP: stopped pid={pid}" and gone and deleted and sleeper_ok,
              f"serve={out} | stop={sout} (gone={gone}, deleted={deleted}, sleeper_ok={sleeper_ok})")

        scode2, slines2, sout2 = run_fastpass("stop", cfg, root)
        check("stop: second stop reports nothing running",
              scode2 == 0 and bool(slines2) and slines2[0] == "STOP: nothing running", sout2)
    finally:
        run_fastpass("stop", cfg, root)
        stop_proc(sleeper)
        shutil.rmtree(tmp, ignore_errors=True)


def test_serve_build_fail():
    tmp, root, state_dir, cfg = make_env("buildfail")
    try:
        write_file(os.path.join(root, "src.txt"), "v1\n")
        write_config(cfg, state_dir, build_command='python3 -c "import sys; sys.exit(3)"')
        code, lines, out = run_fastpass("serve", cfg, root)
        no_server = not state_has_server(state_dir, root)
        check("serve: failing build exits 1 with no server state",
              code == 1 and bool(lines) and lines[0] == "SERVE: FAIL build exit 3" and no_server,
              f"{out} (code={code}, no_server={no_server})")
    finally:
        run_fastpass("stop", cfg, root)
        shutil.rmtree(tmp, ignore_errors=True)


def test_serve_not_ready():
    tmp, root, state_dir, cfg = make_env("notready")
    hung_pid = None
    try:
        write_file(os.path.join(root, "src.txt"), "v1\n")
        hung_cmd = 'python3 -c "import os,time; open(\'hung.pid\',\'w\').write(str(os.getpid())); time.sleep(60)" {port}'
        write_config(cfg, state_dir, build_command=None, serve_command=hung_cmd, ready_timeout=1)
        code, lines, out = run_fastpass("serve", cfg, root)
        pid_file = os.path.join(root, "hung.pid")
        hung_pid = int(open(pid_file).read().strip()) if os.path.exists(pid_file) else None
        gone = wait_gone(hung_pid) if hung_pid else False
        check("serve: timeout kills unready process and exits 1",
              code == 1 and bool(lines) and lines[0] == "SERVE: FAIL not ready"
              and hung_pid is not None and gone,
              f"{out} (code={code}, hung_pid={hung_pid}, gone={gone})")
    finally:
        run_fastpass("stop", cfg, root)
        if hung_pid and pid_alive(hung_pid):
            os.kill(hung_pid, signal.SIGKILL)
        shutil.rmtree(tmp, ignore_errors=True)


def test_serve_no_fast_block():
    tmp, root, state_dir, cfg = make_env("nofast")
    try:
        os.makedirs(root, exist_ok=True)
        write_config(cfg, state_dir, include_fast=False)
        code, lines, out = run_fastpass("serve", cfg, root)
        check("serve: missing fast block exits 1",
              code == 1 and bool(lines) and lines[0] == "SERVE: FAIL no fast block in config",
              f"{out} (code={code})")
    finally:
        run_fastpass("stop", cfg, root)
        shutil.rmtree(tmp, ignore_errors=True)


def test_serve_stale_lstart():
    tmp, root, state_dir, cfg = make_env("lstart")
    sleeper = subprocess.Popen(["sleep", "60"])
    try:
        write_file(os.path.join(root, "src.txt"), "v1\n")
        write_config(cfg, state_dir)
        write_file(state_path(state_dir, root), json.dumps({
            "pid": sleeper.pid, "lstart": "Mon Jan  1 00:00:00 1990",
            "port": 1, "url": "http://127.0.0.1:1",
            "fingerprint": "stale", "built_fingerprint": "stale",
        }))
        code, lines, out = run_fastpass("serve", cfg, root)
        pid, _, _ = parse_started(lines)
        sleeper_ok = sleeper.poll() is None and pid_alive(sleeper.pid)
        check("serve: wrong lstart spares unrelated sleep and starts new server",
              code == 0 and pid is not None and pid != sleeper.pid and sleeper_ok,
              f"{out} (sleeper={sleeper.pid}, sleeper_ok={sleeper_ok})")
    finally:
        run_fastpass("stop", cfg, root)
        stop_proc(sleeper)
        shutil.rmtree(tmp, ignore_errors=True)


def test_serve_two_roots():
    tmp, _, state_dir, cfg = make_env("tworoots")
    root_a, root_b = os.path.join(tmp, "root-a"), os.path.join(tmp, "root-b")
    try:
        write_file(os.path.join(root_a, "src.txt"), "a\n")
        write_file(os.path.join(root_b, "src.txt"), "b\n")
        write_config(cfg, state_dir)
        code_a, lines_a, out_a = run_fastpass("serve", cfg, root_a)
        pid_a, url_a, _ = parse_started(lines_a)
        code_b, lines_b, out_b = run_fastpass("serve", cfg, root_b)
        pid_b, url_b, _ = parse_started(lines_b)
        check("serve: two roots get distinct servers",
              code_a == 0 and code_b == 0 and pid_a is not None and pid_b is not None
              and pid_a != pid_b and url_a != url_b and pid_alive(pid_a) and pid_alive(pid_b),
              f"a={out_a} | b={out_b}")
    finally:
        run_fastpass("stop", cfg, root_a)
        run_fastpass("stop", cfg, root_b)
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    test_select_paths()
    test_select_git()
    test_select_no_journeys()
    test_serve_lifecycle()
    test_stop_and_unrelated_process()
    test_serve_build_fail()
    test_serve_not_ready()
    test_serve_no_fast_block()
    test_serve_stale_lstart()
    test_serve_two_roots()
    print(f"\n{'FAIL' if FAILS else 'PASS'} test_fastpass ({len(FAILS)} failing)")
    sys.exit(1 if FAILS else 0)
