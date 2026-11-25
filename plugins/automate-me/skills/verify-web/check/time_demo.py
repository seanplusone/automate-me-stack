#!/usr/bin/env python3
"""Measure demo-app verification timing for before/after modes."""
import argparse
import json
import os
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["before", "after"], required=True)
    ap.add_argument("--passes", type=int, default=3)
    ap.add_argument("--json", dest="json_path")
    args = ap.parse_args()

    if args.mode == "after":
        print("after mode not built yet")
        return 2

    if not check_playwright():
        print("SKIP")
        return 0

    results = []
    for i in range(1, args.passes + 1):
        row, err = run_before_pass(i)
        if err is not None:
            print(f"{args.mode}  pass={i} FAIL {err}")
            return 1
        results.append(row)
        print(
            f"{args.mode}  pass={i} build={row['build']:.1f}s serve={row['serve']:.1f}s "
            f"unit={row['unit']:.1f}s journeys={row['journeys']:.1f}s total={row['total']:.1f}s"
        )

    means = {k: statistics.mean(r[k] for r in results) for k in PHASES}
    maxes = {k: max(r[k] for r in results) for k in PHASES}

    print(f"\n{'phase':<10} {'mean':>8} {'max':>8}")
    for k in PHASES:
        print(f"{k:<10} {means[k]:>7.1f}s {maxes[k]:>7.1f}s")
    print(f"\n{args.mode}  mean total={means['total']:.1f}s max total={maxes['total']:.1f}s")

    if args.json_path:
        parent = os.path.dirname(os.path.abspath(args.json_path))
        if parent:
            os.makedirs(parent, exist_ok=True)
        payload = {"mode": args.mode, "passes": results, "mean": means, "max": maxes}
        with open(args.json_path, "w") as f:
            json.dump(payload, f, indent=2)

    return 0


if __name__ == "__main__":
    sys.exit(main())
