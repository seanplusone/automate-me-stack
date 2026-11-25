"""Tests for fastpass.py select.

Run: python3 check/test_fastpass.py
"""
import os
import shutil
import subprocess
import sys
import tempfile

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


if __name__ == "__main__":
    test_select_paths()
    test_select_git()
    test_select_no_journeys()
    print(f"\n{'FAIL' if FAILS else 'PASS'} test_fastpass ({len(FAILS)} failing)")
    sys.exit(1 if FAILS else 0)
