"""Tests for doctor.py: its YAML subset parser, and a live run against the demo app.

Run: cd check && python3 test_doctor.py
Starts the demo app on a free port from a temp copy, then checks that the doctor says OK, catches a
STALE worker, catches a wrong serving tree, warns when page and job trees differ, and fails once
the app stops. Needs curl (the demo config's serving_tree command).
"""
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
DEMO = os.path.join(SKILL, "cases", "demo-app")
DOCTOR = os.path.join(SKILL, "doctor.py")
sys.path.insert(0, SKILL)
import doctor  # noqa: E402

SHA = "abc1234def5678abc1234def5678abc1234def56"
FAILS = []


def check(name, ok, detail=""):
    print(f"{'PASS' if ok else 'FAIL'} {name}")
    if not ok:
        FAILS.append(name)
        if detail:
            print("    " + detail.replace("\n", "\n    "))


def test_yaml():
    cfg = doctor.load_config(os.path.join(SKILL, "verify-web.example.yaml"))
    check("yaml: example parses with apps, personas, workers", len(cfg["apps"]) == 2
          and cfg["apps"][0]["test_data"] is True and cfg["personas"]["readonly"]["password_env"] == "READONLY_PASSWORD"
          and cfg["workers"][0]["source_dirs"] == ["app", "lib", "config"])
    check("yaml: health expect_status is an int", cfg["health"][0]["expect_status"] == 200)
    check("yaml: a quoted '#' is not a comment, a spaced one is",
          doctor.parse_yaml("a: 'x # y'  # real comment\nb: c#d\n") == {"a": "x # y", "b": "c#d"})
    check("yaml: list items at the key's indent", doctor.parse_yaml("k:\n- 1\n- two\nz: [a, 'b, c']\n")
          == {"k": [1, "two"], "z": ["a", "b, c"]})
    check("yaml: nested list of maps", doctor.parse_yaml("w:\n  - name: a\n    dirs: [x]\n  - name: b\n")
          == {"w": [{"name": "a", "dirs": ["x"]}, {"name": "b"}]})
    for bad in ("a: {x: 1}\n", "a:\n\tb: 1\n", "a: 1\na: 2\n", "a: 'open\n"):
        try:
            doctor.parse_yaml(bad)
            check(f"yaml: rejects {bad!r}", False)
        except doctor.YamlError:
            check(f"yaml: rejects {bad!r}", True)


def test_check_config():
    ex = os.path.join(SKILL, "verify-web.example.yaml")
    r = subprocess.run([sys.executable, DOCTOR, "--check-config", "--config", ex], capture_output=True, text=True)
    check("check-config: example is OK", r.returncode == 0 and "CONFIG: OK" in r.stdout, r.stdout)
    cases = {
        "no apps": ("login_path: /login\n", "apps: list at least one app"),
        "app without base_url": ("apps:\n  - name: local\n", "apps[0]: needs name and base_url"),
        "base_url not http": ("apps:\n  - name: l\n    base_url: localhost:3000\n", "is not an http(s) URL"),
        "persona without password_env": ("apps:\n  - name: l\n    base_url: http://x\npersonas:\n  admin:\n"
                                         "    username_env: A\n", "personas.admin: needs"),
        "bad expect_status": ("apps:\n  - name: l\n    base_url: http://x\nhealth:\n  - url: /\n"
                              "    expect_status: ok\n", "expect_status: must be"),
        "worker without source_dirs": ("apps:\n  - name: l\n    base_url: http://x\nworkers:\n  - name: w\n"
                                       "    container: c\n", "source_dirs"),
        "not yaml": ("apps: 'open\n", "unclosed quote"),
    }
    tmp = tempfile.mkdtemp(prefix="verify-web-cfg-")
    for name, (text, needle) in cases.items():
        path = os.path.join(tmp, "verify-web.yaml")
        with open(path, "w") as f:
            f.write(text)
        r = subprocess.run([sys.executable, DOCTOR, "--check-config", "--config", path], capture_output=True, text=True)
        check(f"check-config: fails on {name}", r.returncode == 1 and needle in r.stdout and "CONFIG: FAIL" in r.stdout,
              r.stdout)
    shutil.rmtree(tmp, ignore_errors=True)


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def run_doctor(cwd, env, *args):
    p = subprocess.run([sys.executable, DOCTOR, *args], cwd=cwd, env=env, capture_output=True, text=True, timeout=60)
    return p.returncode, p.stdout


def start_app(work, env):
    proc = subprocess.Popen([sys.executable, "app.py", "--port", env["DEMO_PORT"], "--pid-file", "run/app.pid",
                             "--data-dir", "run/data"], cwd=work, env=env,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(50):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{env['DEMO_PORT']}/health", timeout=1)
            return proc
        except OSError:
            time.sleep(0.1)
    proc.kill()
    raise RuntimeError("demo app did not start")


def start_app_copy(work, env):
    """A second copy (PR mode), with its own data dir and no pid file."""
    proc = subprocess.Popen([sys.executable, "app.py", "--port", env["DEMO_PORT"], "--data-dir", "run/data2"],
                            cwd=work, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(50):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{env['DEMO_PORT']}/health", timeout=1)
            return proc
        except OSError:
            time.sleep(0.1)
    proc.kill()
    raise RuntimeError("second demo app did not start")


def test_live():
    tmp = tempfile.mkdtemp(prefix="verify-web-doctor-")
    work = os.path.join(tmp, "demo-app")
    shutil.copytree(DEMO, work, ignore=shutil.ignore_patterns("run", "__pycache__"))
    users = os.path.join(tmp, "users.env")
    with open(users, "w") as f:
        f.write("ADMIN_USERNAME=admin\nADMIN_PASSWORD=demo-admin-pass\nREADONLY_USERNAME=viewer\nREADONLY_PASSWORD=x\n")
    os.chmod(users, 0o600)
    env = dict(os.environ, DEMO_PORT=str(free_port()), DEMO_USERS_ENV=users, DEMO_TREE=f"main {SHA}")
    proc = start_app(work, env)
    try:
        code, out = run_doctor(work, env)
        check("live: doctor OK while the app runs", code == 0 and "DOCTOR: OK" in out, out)
        check("live: doctor reports the served tree", f"page runs main {SHA[:12]}" in out, out)

        other = dict(env, DEMO_TREE=f"fix/x {SHA[::-1]}", DEMO_PORT=str(free_port()))
        proc2 = start_app_copy(work, other)
        try:
            code, out = run_doctor(work, env, "--base-url", f"http://127.0.0.1:{other['DEMO_PORT']}",
                                   "--expect-sha", SHA[::-1])
            check("live: --base-url checks a second copy on its own port", code == 0
                  and f"page runs fix/x {SHA[::-1][:12]}" in out and other["DEMO_PORT"] in out, out)
        finally:
            proc2.kill()
            proc2.wait()

        code, out = run_doctor(work, env, "--expect-sha", SHA)
        check("live: --expect-sha with the served sha is OK", code == 0, out)
        code, out = run_doctor(work, env, "--expect-sha", "9999999")
        check("live: --expect-sha with another sha FAILs the tree", code == 1 and "FAIL  tree page" in out, out)

        cfg = doctor.load_config(os.path.join(work, ".claude", "verify-web.yaml"))
        jpath = os.path.join(tmp, "verify-web.json")
        cfg["serving_tree"]["job_command"] = "echo main 7777777aaaa"
        cfg["workers"][0]["pid_file"] = os.path.join(work, "run", "app.pid")
        cfg["workers"][0]["source_dirs"] = [work]
        json.dump(cfg, open(jpath, "w"))
        code, out = run_doctor(work, env, "--config", jpath)
        check("live: JSON config works, and different page/job trees WARN",
              code == 0 and "WARN  tree match" in out and "DIFFERENT trees" in out, out)

        os.chmod(users, 0o644)
        code, out = run_doctor(work, env)
        check("live: a users.env readable by others WARNs", code == 0 and "chmod 600" in out, out)
        os.chmod(users, 0o600)

        time.sleep(doctor.CLOCK_SLACK + 1.5)
        src = os.path.join(work, "app.py")
        os.utime(src, None)  # a source edit after the app started: it is running the old code
        code, out = run_doctor(work, env)
        check("live: a source file newer than the worker start FAILs STALE",
              code == 1 and "FAIL  worker app" in out and "STALE" in out and "app.py changed after" in out, out)
        check("live: the STALE line prints its pre-authorized restart", "pre-authorized fix: kill" in out, out)
    finally:
        proc.kill()
        proc.wait()

    code, out = run_doctor(work, env)
    check("live: app stopped FAILs the health check", code == 1 and "FAIL  http login page" in out
          and "no answer" in out and "DOCTOR: FAIL" in out, out)
    check("live: app stopped FAILs the worker", "is not running" in out, out)

    empty = os.path.join(tmp, "empty")
    os.makedirs(empty)
    code, out = run_doctor(empty, dict(os.environ, HOME=empty))
    check("live: no config FAILs and says where to put one", code == 1 and "verify-web.example.yaml" in out, out)
    shutil.rmtree(tmp)


if __name__ == "__main__":
    test_yaml()
    test_check_config()
    test_live()
    shutil.rmtree(os.path.join(SKILL, "__pycache__"), ignore_errors=True)
    print(f"\n{'FAIL' if FAILS else 'PASS'} test_doctor ({len(FAILS)} failing)")
    sys.exit(1 if FAILS else 0)
