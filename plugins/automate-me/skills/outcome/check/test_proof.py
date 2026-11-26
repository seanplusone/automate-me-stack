"""Run: python3 check/test_proof.py"""
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
OUTCOME = os.path.dirname(HERE)
PROOF = os.path.join(HERE, "proof.py")
BRIEFS = "check/fixtures/proof/briefs/demo"

FAILS = []
RAN = []


def run_proof(*args, timeout=None):
    if not os.path.isfile(PROOF):
        return None, f"missing {PROOF}"
    try:
        proc = subprocess.run(
            [sys.executable, "check/proof.py", *args],
            cwd=OUTCOME,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return None, f"timed out after {timeout}s"
    return proc, None


def read_lines(path):
    with open(path) as f:
        return f.read().splitlines()


def set_line(path, index, value):
    lines = read_lines(path)
    while len(lines) <= index:
        lines.append("")
    lines[index] = value
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")


def drop_first_line(path):
    lines = read_lines(path)
    with open(path, "w") as f:
        f.write("\n".join(lines[1:]) + "\n")


def test_run_pass():
    name = "run on pass.md writes verify files and exits 0"
    RAN.append(name)
    out = tempfile.mkdtemp()
    try:
        proc, err = run_proof("run", f"{BRIEFS}/pass.md", out)
        if err:
            FAILS.append(f"{name}: {err}")
            return
        reasons = []
        if proc.returncode != 0:
            reasons.append(f"wanted exit 0, got {proc.returncode}")
        for mid in ("m1", "m2", "m3"):
            path = os.path.join(out, f"verify-{mid}.txt")
            if not os.path.isfile(path):
                reasons.append(f"missing verify-{mid}.txt")
                continue
            lines = read_lines(path)
            if not lines or lines[0] != "exit=0":
                reasons.append(f"verify-{mid}.txt line 1 was {lines[0] if lines else None!r}, wanted 'exit=0'")
        m2_path = os.path.join(out, "verify-m2.txt")
        if os.path.isfile(m2_path):
            m2 = read_lines(m2_path)
            if len(m2) < 2 or m2[1] != "cmd: echo ok":
                reasons.append(f"verify-m2.txt line 2 was {m2[1] if len(m2) >= 2 else None!r}, wanted 'cmd: echo ok'")
            if len(m2) < 3 or m2[2] != "ok":
                reasons.append(f"verify-m2.txt line 3 was {m2[2] if len(m2) >= 3 else None!r}, wanted 'ok'")
        if reasons:
            FAILS.append(f"{name}: {'; '.join(reasons)}")
    finally:
        shutil.rmtree(out, ignore_errors=True)


def test_run_fail():
    name = "run on fail.md exits 1 and records exit=3"
    RAN.append(name)
    out = tempfile.mkdtemp()
    try:
        proc, err = run_proof("run", f"{BRIEFS}/fail.md", out)
        if err:
            FAILS.append(f"{name}: {err}")
            return
        reasons = []
        if proc.returncode != 1:
            reasons.append(f"wanted exit 1, got {proc.returncode}")
        path = os.path.join(out, "verify-m1.txt")
        if not os.path.isfile(path):
            reasons.append("missing verify-m1.txt")
        else:
            lines = read_lines(path)
            if not lines or lines[0] != "exit=3":
                reasons.append(f"verify-m1.txt line 1 was {lines[0] if lines else None!r}, wanted 'exit=3'")
        if reasons:
            FAILS.append(f"{name}: {'; '.join(reasons)}")
    finally:
        shutil.rmtree(out, ignore_errors=True)


def test_run_slow():
    name = "run --timeout 1 on slow.md exits 1 with exit=124"
    RAN.append(name)
    out = tempfile.mkdtemp()
    try:
        start = time.monotonic()
        proc, err = run_proof("run", "--timeout", "1", f"{BRIEFS}/slow.md", out, timeout=20)
        elapsed = time.monotonic() - start
        if err:
            FAILS.append(f"{name}: {err}")
            return
        reasons = []
        if proc.returncode != 1:
            reasons.append(f"wanted exit 1, got {proc.returncode}")
        if elapsed >= 20:
            reasons.append(f"took {elapsed:.1f}s, limit 20s")
        path = os.path.join(out, "verify-m1.txt")
        if not os.path.isfile(path):
            reasons.append("missing verify-m1.txt")
        else:
            lines = read_lines(path)
            if not lines or lines[0] != "exit=124":
                reasons.append(f"verify-m1.txt line 1 was {lines[0] if lines else None!r}, wanted 'exit=124'")
        if reasons:
            FAILS.append(f"{name}: {'; '.join(reasons)}")
    finally:
        shutil.rmtree(out, ignore_errors=True)


def test_run_broken():
    name = "run on broken.md exits 2 and writes nothing"
    RAN.append(name)
    out = tempfile.mkdtemp()
    try:
        proc, err = run_proof("run", f"{BRIEFS}/broken.md", out)
        if err:
            FAILS.append(f"{name}: {err}")
            return
        reasons = []
        if proc.returncode != 2:
            reasons.append(f"wanted exit 2, got {proc.returncode}")
        entries = os.listdir(out)
        if entries:
            reasons.append(f"wanted empty out dir, found {entries!r}")
        if reasons:
            FAILS.append(f"{name}: {'; '.join(reasons)}")
    finally:
        shutil.rmtree(out, ignore_errors=True)


def test_round_trip():
    name = "round trip run then check on pass.md exits 0"
    RAN.append(name)
    out = tempfile.mkdtemp()
    try:
        proc, err = run_proof("run", f"{BRIEFS}/pass.md", out)
        if err:
            FAILS.append(f"{name}: {err}")
            return
        if proc.returncode != 0:
            FAILS.append(f"{name}: setup run exited {proc.returncode}")
            return
        proc, err = run_proof("check", f"{BRIEFS}/pass.md", out)
        if err:
            FAILS.append(f"{name}: {err}")
            return
        if proc.returncode != 0:
            FAILS.append(f"{name}: wanted exit 0, got {proc.returncode}")
    finally:
        shutil.rmtree(out, ignore_errors=True)


def test_check_extra_file():
    name = "check passes with an extra verify file for an unknown id"
    RAN.append(name)
    out = tempfile.mkdtemp()
    try:
        proc, err = run_proof("run", f"{BRIEFS}/pass.md", out)
        if err:
            FAILS.append(f"{name}: {err}")
            return
        if proc.returncode != 0:
            FAILS.append(f"{name}: setup run exited {proc.returncode}")
            return
        with open(os.path.join(out, "verify-zz.txt"), "w") as f:
            f.write("exit=0\ncmd: true\n")
        proc, err = run_proof("check", f"{BRIEFS}/pass.md", out)
        if err:
            FAILS.append(f"{name}: {err}")
            return
        if proc.returncode != 0:
            FAILS.append(f"{name}: wanted exit 0, got {proc.returncode}")
    finally:
        shutil.rmtree(out, ignore_errors=True)


def test_check_none():
    name = "check on none.md with empty out dir exits 0"
    RAN.append(name)
    out = tempfile.mkdtemp()
    try:
        proc, err = run_proof("check", f"{BRIEFS}/none.md", out)
        if err:
            FAILS.append(f"{name}: {err}")
            return
        if proc.returncode != 0:
            FAILS.append(f"{name}: wanted exit 0, got {proc.returncode}")
    finally:
        shutil.rmtree(out, ignore_errors=True)


def test_check_tampered(name, mutate):
    RAN.append(name)
    out = tempfile.mkdtemp()
    try:
        proc, err = run_proof("run", f"{BRIEFS}/pass.md", out)
        if err:
            FAILS.append(f"{name}: {err}")
            return
        if proc.returncode != 0:
            FAILS.append(f"{name}: setup run exited {proc.returncode}")
            return
        target = os.path.join(out, "verify-m1.txt")
        if not os.path.isfile(target):
            FAILS.append(f"{name}: setup did not create verify-m1.txt")
            return
        mutate(target)
        proc, err = run_proof("check", f"{BRIEFS}/pass.md", out)
        if err:
            FAILS.append(f"{name}: {err}")
            return
        reasons = []
        if proc.returncode != 1:
            reasons.append(f"wanted exit 1, got {proc.returncode}")
        if not any(line.startswith("FAIL m1") for line in proc.stdout.splitlines()):
            reasons.append("wanted stdout line starting with 'FAIL m1'")
        if reasons:
            FAILS.append(f"{name}: {'; '.join(reasons)}")
    finally:
        shutil.rmtree(out, ignore_errors=True)


def test_check_empty_dir():
    name = "check on pass.md with empty out dir exits 1"
    RAN.append(name)
    out = tempfile.mkdtemp()
    try:
        proc, err = run_proof("check", f"{BRIEFS}/pass.md", out)
        if err:
            FAILS.append(f"{name}: {err}")
            return
        if proc.returncode != 1:
            FAILS.append(f"{name}: wanted exit 1, got {proc.returncode}")
    finally:
        shutil.rmtree(out, ignore_errors=True)


def test_proof_source():
    name = "proof.py imports check_brief and does not copy parse or regexes"
    RAN.append(name)
    if not os.path.isfile(PROOF):
        FAILS.append(f"{name}: missing {PROOF}")
        return
    with open(PROOF) as f:
        src = f.read()
    reasons = []
    if not re.search(r"^(from check_brief import|import check_brief)", src, re.M):
        reasons.append("missing check_brief import")
    if re.search(r"^def parse\(", src, re.M):
        reasons.append("defines def parse(")
    m = re.search(r"^(RULE_ID|VERIFY_ID|BACKTICK_CMD|SLOT) =", src, re.M)
    if m:
        reasons.append(f"defines {m.group(1)} =")
    if reasons:
        FAILS.append(f"{name}: {'; '.join(reasons)}")


test_run_pass()
test_run_fail()
test_run_slow()
test_run_broken()
test_round_trip()
test_check_extra_file()
test_check_none()
test_check_tampered("check fails when verify-m1.txt is deleted", os.remove)
test_check_tampered("check fails when line 1 is exit=1", lambda p: set_line(p, 0, "exit=1"))
test_check_tampered("check fails when line 1 is removed", drop_first_line)
test_check_tampered("check fails when line 2 is cmd: old", lambda p: set_line(p, 1, "cmd: old"))
test_check_empty_dir()
test_proof_source()

if __name__ == "__main__":
    for f in FAILS:
        print(f"FAIL {f}")
    print(f"{len(RAN) - len(FAILS)}/{len(RAN)} passed")
    sys.exit(1 if FAILS else 0)
