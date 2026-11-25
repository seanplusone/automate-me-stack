#!/usr/bin/env python3
"""Measure demo-app verification timing for before/after modes."""
import argparse
import json
import os
import re
import shutil
import socket
import statistics
import subprocess
import sys
import tempfile
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
DEMO = os.path.join(SKILL, "cases", "demo-app")
DEMO_CFG = os.path.join(DEMO, "verify-web.fast.yaml")
FASTPASS = os.path.join(SKILL, "fastpass.py")
JOURNEYS = ("login", "orders", "refund")
PHASES = ("build", "serve", "unit", "journeys", "total")


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def check_playwright():
    if not shutil.which("node"):
        return False
    res = subprocess.run(["node", "-e", "require('playwright')"], capture_output=True, text=True)
    return res.returncode == 0


def wait_ready(url, proc, timeout=15.0):
    deadline = time.perf_counter() + timeout
    while time.perf_counter() < deadline:
        if proc.poll() is not None:
            return False
        try:
            with urllib.request.urlopen(url, timeout=1) as resp:
                if resp.status < 500:
                    return True
        except OSError:
            time.sleep(0.05)
    return False


def stop_proc(proc):
    if proc is None or proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()


def run_before_pass(pass_num):
    tmp = tempfile.mkdtemp(prefix="verify-web-time-")
    work = os.path.join(tmp, "demo-app")
    proc = None
    try:
        shutil.copytree(DEMO, work, ignore=shutil.ignore_patterns("build", "run", "__pycache__"))

        t0 = time.perf_counter()
        res = subprocess.run([sys.executable, "build.py"], cwd=work, capture_output=True, text=True)
        build_s = time.perf_counter() - t0
        if res.returncode != 0:
            return None, f"build failed (exit {res.returncode}): {res.stderr.strip() or res.stdout.strip()}"

        port = free_port()
        data_dir = os.path.join(tmp, "data")
        url = f"http://127.0.0.1:{port}"
        t0 = time.perf_counter()
        proc = subprocess.Popen(
            [sys.executable, "build/app.py", "--port", str(port), "--data-dir", data_dir],
            cwd=work,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if not wait_ready(f"{url}/health", proc):
            return None, "serve failed: /health did not answer in time"
        serve_s = time.perf_counter() - t0

        t0 = time.perf_counter()
        res = subprocess.run(
            [sys.executable, "-m", "unittest", "discover", "-s", "tests"],
            cwd=work,
            capture_output=True,
            text=True,
        )
        unit_s = time.perf_counter() - t0
        if res.returncode != 0:
            return None, f"unit failed (exit {res.returncode}): {res.stderr.strip() or res.stdout.strip()}"

        t0 = time.perf_counter()
        for name in JOURNEYS:
            ev_dir = os.path.join(tmp, "evidence", name)
            env = dict(os.environ, BASE_URL=url, EVIDENCE_DIR=ev_dir, HEADLESS="1")
            res = subprocess.run(
                ["node", os.path.join("journeys", f"{name}.js")],
                cwd=work,
                env=env,
                capture_output=True,
                text=True,
            )
            if res.returncode != 0:
                detail = res.stderr.strip() or res.stdout.strip()
                return None, f"journeys/{name}.js failed (exit {res.returncode}): {detail}"
        journeys_s = time.perf_counter() - t0

        total_s = build_s + serve_s + unit_s + journeys_s
        return {
            "pass": pass_num,
            "build": build_s,
            "serve": serve_s,
            "unit": unit_s,
            "journeys": journeys_s,
            "total": total_s,
        }, None
    finally:
        stop_proc(proc)
        shutil.rmtree(tmp, ignore_errors=True)


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


def run_before_mode(passes):
    results = []
    for i in range(1, passes + 1):
        row, err = run_before_pass(i)
        if err is not None:
            print(f"before  pass={i} FAIL {err}")
            return None, 1
        results.append(row)
        print(
            f"before  pass={i} build={row['build']:.1f}s serve={row['serve']:.1f}s "
            f"unit={row['unit']:.1f}s journeys={row['journeys']:.1f}s total={row['total']:.1f}s"
        )

    means = {k: statistics.mean(r[k] for r in results) for k in PHASES}
    maxes = {k: max(r[k] for r in results) for k in PHASES}

    print(f"\n{'phase':<10} {'mean':>8} {'max':>8}")
    for k in PHASES:
        print(f"{k:<10} {means[k]:>7.1f}s {maxes[k]:>7.1f}s")
    print(f"\nbefore  mean total={means['total']:.1f}s max total={maxes['total']:.1f}s")
    return {"mode": "before", "passes": results, "mean": means, "max": maxes}, 0


def run_after_mode(passes):
    if not os.path.isfile(DEMO_CFG):
        print(f"after  FAIL missing {DEMO_CFG}")
        return None, 1

    with open(DEMO_CFG) as f:
        cfg_text = f.read()

    tmp = tempfile.mkdtemp(prefix="verify-web-time-after-")
    work = os.path.join(tmp, "demo-app")
    state_dir = os.path.join(tmp, "state")
    cfg = os.path.join(work, "verify-web.fast.yaml")
    try:
        shutil.copytree(DEMO, work, ignore=shutil.ignore_patterns("build", "run", "__pycache__"))
        with open(cfg, "w") as f:
            f.write(with_state_dir(cfg_text, state_dir))

        results = []
        for i in range(1, passes + 1):
            ev_dir = os.path.join(tmp, f"ev{i}")
            cmd = [
                sys.executable,
                FASTPASS,
                "run",
                "--config",
                cfg,
                "--root",
                work,
                "--paths",
                "src/refund/button.js",
                "--evidence-dir",
                ev_dir,
            ]
            t0 = time.perf_counter()
            res = subprocess.run(cmd, capture_output=True, text=True)
            total_s = time.perf_counter() - t0
            if res.returncode != 0:
                detail = res.stderr.strip() or res.stdout.strip()
                print(f"after  pass={i} FAIL exit {res.returncode}: {detail}")
                return None, 1
            kind = "cold" if i == 1 else "warm"
            results.append({"pass": i, "kind": kind, "total": total_s})
            print(f"after  pass={i} total={total_s:.1f}s ({kind})")

        warm_totals = [r["total"] for r in results if r["kind"] == "warm"]
        warm_mean = statistics.mean(warm_totals) if warm_totals else results[0]["total"]
        print(f"after  mean warm total={warm_mean:.1f}s")
        return {
            "mode": "after",
            "passes": results,
            "cold_total": results[0]["total"],
            "mean_warm_total": warm_mean,
        }, 0
    finally:
        if os.path.isfile(cfg) and os.path.isdir(work):
            subprocess.run(
                [sys.executable, FASTPASS, "stop", "--config", cfg, "--root", work],
                capture_output=True,
                text=True,
            )
        shutil.rmtree(tmp, ignore_errors=True)


def write_json(path, payload):
    parent = os.path.dirname(os.path.abspath(path))
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w") as f:
        json.dump(payload, f, indent=2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["before", "after", "both"], required=True)
    ap.add_argument("--passes", type=int, default=3)
    ap.add_argument("--json", dest="json_path")
    args = ap.parse_args()

    if args.passes < 1:
        print("--passes must be at least 1")
        return 1

    if not check_playwright():
        print("SKIP")
        return 0

    if args.mode == "before":
        payload, code = run_before_mode(args.passes)
        if code != 0:
            return code
    elif args.mode == "after":
        payload, code = run_after_mode(args.passes)
        if code != 0:
            return code
    else:
        before_data, code = run_before_mode(args.passes)
        if code != 0:
            return code
        print()
        after_data, code = run_after_mode(args.passes)
        if code != 0:
            return code
        before_mean = before_data["mean"]["total"]
        after_warm_mean = after_data["mean_warm_total"]
        ratio = before_mean / after_warm_mean if after_warm_mean > 0 else 0.0
        print(
            f"\nspeedup  before mean total={before_mean:.1f}s, "
            f"after warm mean total={after_warm_mean:.1f}s, {ratio:.1f}x"
        )
        payload = {
            "mode": "both",
            "before": before_data,
            "after": after_data,
            "speedup": {
                "before_mean_total": before_mean,
                "after_warm_mean_total": after_warm_mean,
                "factor": ratio,
            },
        }

    if args.json_path:
        write_json(args.json_path, payload)

    return 0


if __name__ == "__main__":
    sys.exit(main())
