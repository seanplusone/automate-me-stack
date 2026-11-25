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
                 ready_path="/", fingerprint="[src.txt]", ready_timeout=10, include_fast=True,
                 journey_timeout=None, journeys=None, evidence_dir=None, extra_lines=None):
    lines = ["apps:", "  - name: demo", "    base_url: http://127.0.0.1:8000", "    test_data: true"]
    if include_fast:
        lines += ["fast:", f"  serve_command: {serve_command}", f"  ready_path: {ready_path}",
                  f"  fingerprint: {fingerprint}", f"  state_dir: {state_dir}"]
        if build_command is not None:
            lines.append(f"  build_command: {build_command}")
        if ready_timeout is not None:
            lines.append(f"  ready_timeout: {ready_timeout}")
        if journey_timeout is not None:
            lines.append(f"  journey_timeout: {journey_timeout}")
    if evidence_dir is not None:
        lines.append(f"evidence_dir: {evidence_dir}")
    if extra_lines:
        lines.extend(extra_lines)
    if journeys is not None:
        if not journeys:
            lines.append("journeys: []")
        else:
            lines.append("journeys:")
            for name, cmd, paths in journeys:
                paths_str = ", ".join(paths)
                lines += [f"  - name: {name}", f"    command: {cmd}", f"    paths: [{paths_str}]"]
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


def write_journey(root, name, exit_code=0, images=(), sleep_s=0):
    script = os.path.join(root, f"journey_{name}.py")
    body = (
        "import json, os, sys, time\n"
        f"name = {name!r}\n"
        "seen = {k: os.environ.get(k) for k in ('BASE_URL', 'EVIDENCE_DIR', 'JOURNEY', 'HEADLESS')}\n"
        "with open(f'seen-{name}.json', 'w') as f:\n"
        "    json.dump(seen, f)\n"
        "ev = os.environ.get('EVIDENCE_DIR', '')\n"
        f"for rel in {list(images)!r}:\n"
        "    dest = os.path.join(ev, rel)\n"
        "    os.makedirs(os.path.dirname(dest), exist_ok=True)\n"
        "    with open(dest, 'wb') as f:\n"
        "        f.write(b'x')\n"
        "print(f'journey {name} ran', flush=True)\n"
        f"if {sleep_s!r}:\n"
        f"    time.sleep({sleep_s!r})\n"
        f"sys.exit({exit_code!r})\n"
    )
    write_file(script, body)
    return f"python3 journey_{name}.py"


def read_json(path):
    if not os.path.isfile(path):
        return None
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def find_result(data, name):
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict) and (item.get("journey") == name or item.get("name") == name):
                return item
    elif isinstance(data, dict):
        if name in data and isinstance(data[name], dict):
            return data[name]
        for key in ("results", "journeys"):
            if isinstance(data.get(key), list):
                return find_result(data[key], name)
    return None


def test_run_select_headed_and_all():
    tmp, root, state_dir, cfg = make_env("run-basic")
    ev1 = os.path.join(tmp, "ev")
    ev2 = os.path.join(tmp, "ev-headed")
    ev3 = os.path.join(tmp, "ev-all")
    try:
        write_file(os.path.join(root, "src.txt"), "v1\n")
        cmd_a = write_journey(root, "a", exit_code=0)
        cmd_b = write_journey(root, "b", exit_code=0)
        write_config(cfg, state_dir, journeys=[
            ("a", cmd_a, ["src/a/**"]),
            ("b", cmd_b, ["src/b/**"]),
        ])

        code, lines, out = run_fastpass("run", cfg, root, "--paths", "src/a/file.js", "--evidence-dir", ev1)
        seen_a = read_json(os.path.join(root, "seen-a.json")) or {}
        state = read_json(state_path(state_dir, root)) or {}
        served_url = state.get("url")
        results = read_json(os.path.join(ev1, "results.json"))
        res_a = find_result(results, "a") or {}
        log_ok = os.path.isfile(os.path.join(ev1, "a", "journey.log"))
        check("run: selected journey passes with expected env, results.json, and log",
              code == 0
              and any(l.startswith("a: PASS (") for l in lines)
              and bool(lines) and lines[-1].startswith("FASTPASS: OK 1 passed")
              and seen_a.get("HEADLESS") == "1"
              and bool(served_url) and seen_a.get("BASE_URL") == served_url
              and (seen_a.get("EVIDENCE_DIR") or "").endswith("/a")
              and seen_a.get("JOURNEY") == "a"
              and res_a.get("status") == "PASS"
              and log_ok,
              f"{out} | seen_a={seen_a} url={served_url} res_a={res_a} log={log_ok}")

        check("run: only selected journey runs",
              code == 0 and bool(seen_a) and not os.path.exists(os.path.join(root, "seen-b.json")),
              out)

        code2, _, out2 = run_fastpass("run", cfg, root, "--paths", "src/a/file.js", "--evidence-dir", ev2, "--headed")
        seen_a2 = read_json(os.path.join(root, "seen-a.json")) or {}
        check("run: --headed passes HEADLESS=0",
              code2 == 0 and seen_a2.get("HEADLESS") == "0",
              f"{out2} | seen_a={seen_a2}")

        if os.path.exists(os.path.join(root, "seen-a.json")):
            os.unlink(os.path.join(root, "seen-a.json"))
        code3, lines3, out3 = run_fastpass("run", cfg, root, "--paths", "src/a/file.js", "--all", "--evidence-dir", ev3)
        check("run: --all runs every journey despite narrow --paths",
              code3 == 0
              and os.path.isfile(os.path.join(root, "seen-a.json"))
              and os.path.isfile(os.path.join(root, "seen-b.json"))
              and any(l.startswith("a: PASS (") for l in lines3)
              and any(l.startswith("b: PASS (") for l in lines3)
              and bool(lines3) and lines3[-1].startswith("FASTPASS: OK 2 passed"),
              out3)
    finally:
        run_fastpass("stop", cfg, root)
        shutil.rmtree(tmp, ignore_errors=True)


def test_run_failure_and_screenshots():
    tmp, root, state_dir, cfg = make_env("run-fail")
    ev = os.path.join(tmp, "ev")
    try:
        write_file(os.path.join(root, "src.txt"), "v1\n")
        cmd_a = write_journey(root, "a", exit_code=0, images=("ok.png",))
        cmd_b = write_journey(root, "b", exit_code=1, images=("shot.png", "sub/deep.png"))
        write_config(cfg, state_dir, journeys=[
            ("a", cmd_a, ["src/a/**"]),
            ("b", cmd_b, ["src/b/**"]),
        ])

        code, lines, out = run_fastpass("run", cfg, root, "--all", "--evidence-dir", ev)
        shot_lines = [l for l in lines if l.startswith("  screenshot:")]
        has_shot = any("shot.png" in l for l in shot_lines)
        has_deep = any("deep.png" in l for l in shot_lines)
        has_log = any(l.startswith("  log:") for l in lines)
        no_ok_listed = not any("ok.png" in l for l in lines)
        files_exist = (
            os.path.isfile(os.path.join(ev, "a", "ok.png"))
            and os.path.isfile(os.path.join(ev, "b", "shot.png"))
            and os.path.isfile(os.path.join(ev, "b", "sub", "deep.png"))
        )
        check("run: failing journey lists its screenshots and log, hides passing screenshots",
              code == 1
              and any(l.startswith("b: FAIL (exit 1") for l in lines)
              and len(shot_lines) == 2 and has_shot and has_deep
              and has_log and no_ok_listed and files_exist
              and bool(lines) and lines[-1].startswith("FASTPASS: FAIL 1 of 2"),
              f"{out} | shots={shot_lines} files_exist={files_exist}")
    finally:
        run_fastpass("stop", cfg, root)
        shutil.rmtree(tmp, ignore_errors=True)


def test_run_timeout():
    tmp, root, state_dir, cfg = make_env("run-timeout")
    ev = os.path.join(tmp, "ev")
    try:
        write_file(os.path.join(root, "src.txt"), "v1\n")
        cmd_slow = write_journey(root, "slow", exit_code=0, sleep_s=5)
        write_config(cfg, state_dir, journey_timeout=1, journeys=[
            ("slow", cmd_slow, ["src/slow/**"]),
        ])

        code, lines, out = run_fastpass("run", cfg, root, "--paths", "src/slow/x.js", "--evidence-dir", ev)
        check("run: journey exceeding journey_timeout fails with timeout",
              code == 1 and any(l.startswith("slow: FAIL") and "timeout" in l.lower() for l in lines),
              f"{out} (code={code})")
    finally:
        run_fastpass("stop", cfg, root)
        shutil.rmtree(tmp, ignore_errors=True)


def test_run_no_unit_suite():
    tmp, root, state_dir, cfg = make_env("run-nounit")
    ev = os.path.join(tmp, "ev")
    try:
        write_file(os.path.join(root, "src.txt"), "v1\n")
        cmd_a = write_journey(root, "a", exit_code=0)
        write_config(cfg, state_dir,
                     extra_lines=['test_command: python3 -c "open(\'unit-ran\',\'w\')"'],
                     journeys=[("a", cmd_a, ["src/a/**"])])

        code, _, out = run_fastpass("run", cfg, root, "--paths", "src/a/x.js", "--evidence-dir", ev)
        hp = subprocess.run([sys.executable, FASTPASS, "run", "--help"],
                            capture_output=True, text=True, timeout=30)
        help_text = hp.stdout + hp.stderr
        check("run: never runs test_command and --help has no word unit",
              code == 0 and not os.path.exists(os.path.join(root, "unit-ran"))
              and hp.returncode == 0 and "unit" not in help_text.lower(),
              f"run={out} | help={help_text.strip()}")
    finally:
        run_fastpass("stop", cfg, root)
        shutil.rmtree(tmp, ignore_errors=True)


def test_run_reuses_server():
    tmp, root, state_dir, cfg = make_env("run-reuse")
    ev1 = os.path.join(tmp, "ev1")
    ev2 = os.path.join(tmp, "ev2")
    try:
        write_file(os.path.join(root, "src.txt"), "v1\n")
        cmd_a = write_journey(root, "a", exit_code=0)
        write_config(cfg, state_dir, journeys=[("a", cmd_a, ["src/a/**"])])

        code1, _, out1 = run_fastpass("run", cfg, root, "--paths", "src/a/x.js", "--evidence-dir", ev1)
        url1 = (read_json(os.path.join(root, "seen-a.json")) or {}).get("BASE_URL")
        if os.path.exists(os.path.join(root, "seen-a.json")):
            os.unlink(os.path.join(root, "seen-a.json"))
        code2, _, out2 = run_fastpass("run", cfg, root, "--paths", "src/a/x.js", "--evidence-dir", ev2)
        url2 = (read_json(os.path.join(root, "seen-a.json")) or {}).get("BASE_URL")
        check("run: two runs reuse server without rebuilding",
              code1 == 0 and code2 == 0 and counter_lines(root) == 1 and bool(url1) and url1 == url2,
              f"r1={out1} | r2={out2} | counter={counter_lines(root)} url1={url1} url2={url2}")
    finally:
        run_fastpass("stop", cfg, root)
        shutil.rmtree(tmp, ignore_errors=True)


def test_run_default_evidence_dir():
    tmp, root, state_dir, cfg = make_env("run-evdir")
    ev_base = os.path.join(tmp, "ev-base")
    try:
        write_file(os.path.join(root, "src.txt"), "v1\n")
        cmd_a = write_journey(root, "a", exit_code=0)
        write_config(cfg, state_dir, evidence_dir=ev_base, journeys=[("a", cmd_a, ["src/a/**"])])

        code, _, out = run_fastpass("run", cfg, root, "--paths", "src/a/x.js")
        dirs = (
            [d for d in os.listdir(ev_base) if d.endswith("-fastpass") and os.path.isdir(os.path.join(ev_base, d))]
            if os.path.isdir(ev_base) else []
        )
        ev_run = os.path.join(ev_base, dirs[0]) if len(dirs) == 1 else ""
        check("run: default evidence dir uses config evidence_dir with -fastpass suffix",
              code == 0 and len(dirs) == 1
              and os.path.isfile(os.path.join(ev_run, "results.json"))
              and os.path.isfile(os.path.join(ev_run, "a", "journey.log")),
              f"{out} | dirs={dirs}")
    finally:
        run_fastpass("stop", cfg, root)
        shutil.rmtree(tmp, ignore_errors=True)


def test_run_no_journeys():
    tmp, root, state_dir, cfg = make_env("run-empty")
    ev = os.path.join(tmp, "ev")
    try:
        write_file(os.path.join(root, "src.txt"), "v1\n")
        write_config(cfg, state_dir)

        code, lines, out = run_fastpass("run", cfg, root, "--paths", "src/a/x.js", "--evidence-dir", ev)
        check("run: no journeys configured exits 1 with SELECT: none",
              code == 1 and any(l == "SELECT: none (no journeys configured)" for l in lines),
              f"{out} (code={code})")
    finally:
        run_fastpass("stop", cfg, root)
        shutil.rmtree(tmp, ignore_errors=True)


DOCTOR = os.path.join(SKILL, "doctor.py")
DEMO_DIR = os.path.join(SKILL, "cases", "demo-app")
DEMO_CFG = os.path.join(DEMO_DIR, "verify-web.fast.yaml")
TIME_DEMO = os.path.join(HERE, "time_demo.py")
REPO_ROOT = os.path.abspath(os.path.join(SKILL, "..", "..", "..", ".."))


def has_playwright():
    if not shutil.which("node"):
        return False
    p = subprocess.run(["node", "-e", "require('playwright')"], capture_output=True, text=True, timeout=30)
    return p.returncode == 0


def with_state_dir(cfg_text, state_dir):
    out = []
    in_fast = False
    inserted = False
    for line in cfg_text.splitlines():
        is_top = bool(line) and not line[0].isspace() and not line.lstrip().startswith("#")
        if is_top:
            in_fast = line.startswith("fast:")
            out.append(line)
            if in_fast:
                out.append(f"  state_dir: {state_dir}")
                inserted = True
            continue
        if in_fast and re.match(r"^\s+state_dir\s*:", line):
            continue
        out.append(line)
    if not inserted:
        out.append(f"  state_dir: {state_dir}")
    return "\n".join(out) + "\n"


def run_fastpass_env(subcmd, cfg_path, root, *args, env=None, timeout=120):
    p = subprocess.run(
        [sys.executable, FASTPASS, subcmd, "--config", cfg_path, "--root", root, *args],
        capture_output=True,
        text=True,
        env=env,
        timeout=timeout,
    )
    return p.returncode, p.stdout.splitlines(), (p.stdout + p.stderr).strip()


def test_demo_config():
    p = subprocess.run(
        [sys.executable, DOCTOR, "--check-config", "--config", DEMO_CFG],
        capture_output=True,
        text=True,
        timeout=30,
    )
    doc_lines = p.stdout.splitlines()
    doc_out = (p.stdout + p.stderr).strip()
    check("demo config: doctor --check-config reports CONFIG: OK",
          p.returncode == 0 and any(l.strip() == "CONFIG: OK" for l in doc_lines),
          f"{doc_out} (code={p.returncode})")

    code, lines, out = run_select(DEMO_CFG, DEMO_DIR, "--paths", "src/refund/button.js")
    check("demo config: src/refund/button.js selects refund",
          code == 0 and lines == ["SELECT: mapped refund", "refund"], out)

    code, lines, out = run_select(DEMO_CFG, DEMO_DIR, "--paths", "src/auth/login.js")
    check("demo config: src/auth/login.js selects login",
          code == 0 and lines == ["SELECT: mapped login", "login"], out)

    code, lines, out = run_select(DEMO_CFG, DEMO_DIR, "--paths", "src/orders/list.js")
    check("demo config: src/orders/list.js selects orders",
          code == 0 and lines == ["SELECT: mapped orders", "orders"], out)

    code, lines, out = run_select(DEMO_CFG, DEMO_DIR, "--paths", "src/other/x.js")
    check("demo config: unmapped path selects login, orders, refund",
          code == 0 and bool(lines)
          and lines[0].startswith("SELECT: all (unmapped: src/other/x.js")
          and set(lines[1:]) == {"login", "orders", "refund"} and len(lines[1:]) == 3,
          out)


def test_demo_e2e():
    if not has_playwright():
        print("SKIP demo e2e: playwright not available")
        return

    if not os.path.isfile(DEMO_CFG):
        check("demo e2e: demo config exists", False, f"missing {DEMO_CFG}")
        return

    with open(DEMO_CFG) as f:
        demo_cfg_text = f.read()

    tmp_ok = tempfile.mkdtemp(prefix="verify-web-demo-ok-")
    root_ok = os.path.join(tmp_ok, "demo-app")
    state_ok = os.path.join(tmp_ok, "state")
    cfg_ok = os.path.join(root_ok, "verify-web.fast.yaml")
    ev_ok = os.path.join(tmp_ok, "ev")
    try:
        shutil.copytree(DEMO_DIR, root_ok, ignore=shutil.ignore_patterns("build", "run", "__pycache__"))
        write_file(cfg_ok, with_state_dir(demo_cfg_text, state_ok))

        code, lines, out = run_fastpass_env(
            "run", cfg_ok, root_ok, "--paths", "src/refund/button.js", "--evidence-dir", ev_ok
        )
        shot_lines = [l for l in lines if "screenshot:" in l]
        after_png = os.path.join(ev_ok, "refund", "refund-after.png")
        check("demo e2e: refund passes with no screenshot line and writes refund-after.png",
              code == 0
              and any(l.startswith("refund: PASS") for l in lines)
              and not shot_lines
              and os.path.isfile(after_png),
              f"{out} (code={code}, after_png={os.path.isfile(after_png)})")
    finally:
        run_fastpass_env("stop", cfg_ok, root_ok, timeout=30)
        shutil.rmtree(tmp_ok, ignore_errors=True)

    tmp_fail = tempfile.mkdtemp(prefix="verify-web-demo-fail-")
    root_fail = os.path.join(tmp_fail, "demo-app")
    state_fail = os.path.join(tmp_fail, "state")
    cfg_fail = os.path.join(root_fail, "verify-web.fast.yaml")
    ev_fail = os.path.join(tmp_fail, "ev")
    try:
        shutil.copytree(DEMO_DIR, root_fail, ignore=shutil.ignore_patterns("build", "run", "__pycache__"))
        write_file(cfg_fail, with_state_dir(demo_cfg_text, state_fail))

        env = dict(os.environ, REFUND_DELAY="6")
        code, lines, out = run_fastpass_env(
            "run", cfg_fail, root_fail, "--paths", "src/refund/button.js", "--evidence-dir", ev_fail, env=env
        )
        fail_shots = [l for l in lines if l.startswith("  screenshot:") and "refund-failed.png" in l]
        check("demo e2e: REFUND_DELAY=6 fails with refund-failed.png screenshot line",
              code == 1
              and any(l.startswith("refund: FAIL") for l in lines)
              and bool(fail_shots),
              f"{out} (code={code}, fail_shots={fail_shots})")
    finally:
        run_fastpass_env("stop", cfg_fail, root_fail, timeout=30)
        shutil.rmtree(tmp_fail, ignore_errors=True)


def test_docs_mention_fastpass():
    guide_path = os.path.join(REPO_ROOT, "GUIDE.md")
    check("docs: repo root contains GUIDE.md",
          os.path.isfile(guide_path),
          f"missing {guide_path}")

    doc_files = [
        ("SKILL.md", os.path.join(SKILL, "SKILL.md")),
        ("GUIDE.md", guide_path),
        ("README.md", os.path.join(REPO_ROOT, "README.md")),
    ]
    for label, path in doc_files:
        if not os.path.isfile(path):
            check(f"docs: {label} mentions fastpass.py and journeys", False, f"missing file: {path}")
            continue
        with open(path) as f:
            text = f.read()
        missing = [tok for tok in ("fastpass.py", "journeys") if tok not in text]
        check(f"docs: {label} mentions fastpass.py and journeys",
              not missing,
              f"{path} missing: {', '.join(missing)}")


def test_time_demo():
    if not has_playwright():
        print("SKIP time_demo: playwright not available")
        return

    p1 = subprocess.run(
        [sys.executable, TIME_DEMO, "--mode", "after", "--passes", "2"],
        cwd=SKILL,
        capture_output=True,
        text=True,
        timeout=180,
    )
    lines1 = p1.stdout.splitlines()
    out1 = (p1.stdout + p1.stderr).strip()
    check("time_demo: --mode after --passes 2 prints pass=1 and pass=2",
          p1.returncode == 0
          and any(l.startswith("after  pass=1") for l in lines1)
          and any(l.startswith("after  pass=2") for l in lines1),
          f"{out1} (code={p1.returncode})")

    p2 = subprocess.run(
        [sys.executable, TIME_DEMO, "--mode", "both", "--passes", "2"],
        cwd=SKILL,
        capture_output=True,
        text=True,
        timeout=300,
    )
    lines2 = p2.stdout.splitlines()
    out2 = (p2.stdout + p2.stderr).strip()
    check("time_demo: --mode both --passes 2 prints speedup",
          p2.returncode == 0
          and any(l.startswith("speedup") for l in lines2),
          f"{out2} (code={p2.returncode})")


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
    test_run_select_headed_and_all()
    test_run_failure_and_screenshots()
    test_run_timeout()
    test_run_no_unit_suite()
    test_run_reuses_server()
    test_run_default_evidence_dir()
    test_run_no_journeys()
    test_demo_config()
    test_demo_e2e()
    test_docs_mention_fastpass()
    test_time_demo()
    print(f"\n{'FAIL' if FAILS else 'PASS'} test_fastpass ({len(FAILS)} failing)")
    sys.exit(1 if FAILS else 0)
