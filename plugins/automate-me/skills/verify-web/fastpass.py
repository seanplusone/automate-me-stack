#!/usr/bin/env python3
"""Fast local verification runner for verify-web. Python stdlib only.

Usage:
  python3 fastpass.py select [--config <file>] [--root <dir>] [--paths <p> ...] [--base <ref>]
  python3 fastpass.py serve  [--config <file>] [--root <dir>]
  python3 fastpass.py stop   [--config <file>] [--root <dir>]
  python3 fastpass.py run    [--config <file>] [--root <dir>] [--paths <p> ...] [--base <ref>] [--all] [--evidence-dir <dir>] [--headed]

The config is the first of .claude/verify-web.yaml, .claude/verify-web.yml or .claude/verify-web.json
found from the root or current directory upward, unless --config names one.
"""
import argparse
import hashlib
import json
import os
import re
import shlex
import signal
import socket
import subprocess
import sys
import time

SKILL_DIR = os.path.dirname(os.path.abspath(__file__))
if SKILL_DIR not in sys.path:
    sys.path.insert(0, SKILL_DIR)

import doctor

DEFAULT_STATE_DIR = "~/.cache/verify-web"
DEFAULT_READY_TIMEOUT = 60
DEFAULT_JOURNEY_TIMEOUT = 120
DEFAULT_EVIDENCE_DIR = "~/.claude/verify-evidence/web"
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}


def _norm_path(path: str) -> str:
    norm = path.replace("\\", "/")
    while norm.startswith("./"):
        norm = norm[2:]
    return norm


def _segment_to_regex(segment: str) -> str:
    parts = []
    for ch in segment:
        if ch == "*":
            parts.append("[^/]*")
        elif ch == "?":
            parts.append("[^/]")
        else:
            parts.append(re.escape(ch))
    return "".join(parts)


def glob_to_regex(pattern: str) -> re.Pattern[str]:
    norm = _norm_path(pattern)
    segs = []
    for seg in norm.split("/"):
        if seg == "**" and segs and segs[-1] == "**":
            continue
        segs.append(seg)

    if segs == ["**"]:
        return re.compile(r"^.*$")

    out = ["^"]
    for i, seg in enumerate(segs):
        if seg == "**":
            if i == len(segs) - 1:
                out.append("(?:/.*)?")
            else:
                if i > 0:
                    out.append("/")
                out.append("(?:.*/)?")
        else:
            if i > 0 and segs[i - 1] != "**":
                out.append("/")
            out.append(_segment_to_regex(seg))
    out.append("$")
    return re.compile("".join(out))


def select_journeys(
    journeys: list[dict],
    ignore: list[str],
    paths: list[str],
) -> tuple[str, list[str], str]:
    journeys = journeys or []
    ignore = ignore or []
    paths = paths or []

    if not journeys:
        return "none", [], "no journeys configured"

    all_names = [j["name"] for j in journeys]
    if not paths:
        return "all", all_names, "no changed paths"

    ignore_rxs = [glob_to_regex(pat) for pat in ignore]
    journey_rxs = [
        (j["name"], [glob_to_regex(pat) for pat in (j.get("paths") or [])])
        for j in journeys
    ]

    selected = set()
    for raw_path in paths:
        p = _norm_path(raw_path)
        if any(rx.match(p) for rx in ignore_rxs):
            continue
        matched = [name for name, rxs in journey_rxs if any(rx.match(p) for rx in rxs)]
        if not matched:
            return "all", all_names, f"unmapped: {raw_path}"
        selected.update(matched)

    if not selected:
        return "all", all_names, "no changed path maps"

    ordered = [name for name in all_names if name in selected]
    return "mapped", ordered, ""


def _git(root: str, *args: str) -> tuple[int, str]:
    try:
        p = subprocess.run(
            ["git", *args],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=20,
        )
        return p.returncode, p.stdout
    except (OSError, subprocess.TimeoutExpired):
        return 1, ""


def changed_paths_from_git(root: str, base_ref: str = "origin/main") -> list[str]:
    code, out = _git(root, "merge-base", base_ref, "HEAD")
    base = out.strip() if code == 0 and out.strip() else "HEAD"

    paths = []
    seen = set()
    for cmd in (("diff", "--name-only", base), ("ls-files", "--others", "--exclude-standard")):
        c, text = _git(root, *cmd)
        if c != 0:
            continue
        for line in text.splitlines():
            line = line.strip()
            if line and line not in seen:
                seen.add(line)
                paths.append(line)
    return paths


def cmd_select(cfg: dict, root: str, args: argparse.Namespace) -> int:
    journeys = cfg.get("journeys") or []
    ignore = cfg.get("journey_ignore") or []
    if not journeys:
        paths = []
    elif args.paths is not None:
        paths = args.paths
    else:
        paths = changed_paths_from_git(root, args.base)

    mode, names, reason = select_journeys(journeys, ignore, paths)
    if mode == "none":
        print(f"SELECT: none ({reason})")
        return 1
    if mode == "mapped":
        print(f"SELECT: mapped {', '.join(names)}")
    else:
        print(f"SELECT: all ({reason})")
    for name in names:
        print(name)
    return 0


def fingerprint(root: str, globs: list[str]) -> str:
    rxs = [glob_to_regex(pat) for pat in (globs or [])]
    matches: list[tuple[str, str]] = []
    if rxs and os.path.isdir(root):
        for dirpath, subdirs, files in os.walk(root):
            subdirs[:] = sorted(d for d in subdirs if d not in doctor.SKIP_DIRS)
            for name in sorted(files):
                full = os.path.join(dirpath, name)
                rel = _norm_path(os.path.relpath(full, root))
                if any(rx.match(rel) for rx in rxs):
                    matches.append((rel, full))
    matches.sort(key=lambda item: item[0])
    h = hashlib.sha256()
    for rel, full in matches:
        h.update(rel.encode("utf-8"))
        h.update(b"\0")
        with open(full, "rb") as f:
            while True:
                chunk = f.read(65536)
                if not chunk:
                    break
                h.update(chunk)
        h.update(b"\0")
    return h.hexdigest()


def _state_key(root: str) -> str:
    return hashlib.sha1(os.path.abspath(root).encode("utf-8")).hexdigest()


def state_path(state_dir: str, root: str) -> str:
    base = os.path.expanduser(state_dir or DEFAULT_STATE_DIR)
    return os.path.join(base, f"{_state_key(root)}.json")


def _log_path(state_dir: str, root: str) -> str:
    base = os.path.expanduser(state_dir or DEFAULT_STATE_DIR)
    return os.path.join(base, f"{_state_key(root)}.log")


def load_state(path: str) -> dict | None:
    if not os.path.isfile(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def save_state(path: str, state: dict) -> None:
    parent = os.path.dirname(os.path.abspath(path))
    os.makedirs(parent, exist_ok=True)
    tmp = f"{path}.{os.getpid()}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, sort_keys=True)
        f.write("\n")
    os.replace(tmp, path)


def _remove_file(path: str) -> None:
    try:
        os.unlink(path)
    except FileNotFoundError:
        pass


def pid_lstart(pid: int) -> str | None:
    if not isinstance(pid, int) or isinstance(pid, bool) or pid <= 0:
        return None
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return None
    except PermissionError:
        pass
    try:
        p = subprocess.run(
            ["ps", "-o", "lstart=", "-p", str(pid)],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if p.returncode != 0:
        return None
    out = p.stdout.strip()
    return out or None


def is_ours(state: dict | None) -> bool:
    if not isinstance(state, dict):
        return False
    pid = state.get("pid")
    recorded = state.get("lstart")
    if not isinstance(pid, int) or isinstance(pid, bool) or pid <= 0:
        return False
    if not isinstance(recorded, str) or not recorded.strip():
        return False
    actual = pid_lstart(pid)
    return actual is not None and actual == recorded.strip()


def _signal_pid(pid: int, sig: int) -> bool:
    try:
        pgid = os.getpgid(pid)
        if pgid == os.getpgrp():
            os.kill(pid, sig)
        else:
            os.killpg(pgid, sig)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        try:
            os.kill(pid, sig)
            return True
        except (ProcessLookupError, PermissionError):
            return False


def stop_pid(pid: int, lstart: str, timeout: float = 5.0) -> bool:
    if not isinstance(lstart, str) or not lstart.strip():
        return False
    want = lstart.strip()
    if pid_lstart(pid) != want:
        return False
    if not _signal_pid(pid, signal.SIGTERM):
        return True
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if pid_lstart(pid) != want:
            return True
        time.sleep(0.05)
    if pid_lstart(pid) == want:
        _signal_pid(pid, signal.SIGKILL)
        kill_deadline = time.monotonic() + 2.0
        while time.monotonic() < kill_deadline and pid_lstart(pid) == want:
            time.sleep(0.05)
    return True


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _ready(url: str, timeout: float = 2.0) -> bool:
    try:
        code, _ = doctor.http_status(url, timeout=timeout)
    except Exception:
        return False
    return 0 < code < 500


def _terminate_child(proc: subprocess.Popen) -> None:
    if proc.poll() is not None:
        return
    _signal_pid(proc.pid, signal.SIGTERM)
    try:
        proc.wait(timeout=2.0)
        return
    except subprocess.TimeoutExpired:
        pass
    _signal_pid(proc.pid, signal.SIGKILL)
    try:
        proc.wait(timeout=2.0)
    except subprocess.TimeoutExpired:
        pass


def start_server(
    serve_command: str,
    ready_path: str,
    root: str,
    log_file: str,
    ready_timeout: float = DEFAULT_READY_TIMEOUT,
) -> tuple[int | None, str | None, int | None, str | None]:
    port = free_port()
    url = f"http://127.0.0.1:{port}"
    path = ready_path or "/"
    if not path.startswith("/"):
        path = "/" + path
    ready_url = url + path

    argv = shlex.split(serve_command.replace("{port}", str(port)))
    os.makedirs(os.path.dirname(os.path.abspath(log_file)), exist_ok=True)
    log_fh = open(log_file, "wb")
    try:
        proc = subprocess.Popen(
            argv,
            cwd=root,
            stdin=subprocess.DEVNULL,
            stdout=log_fh,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    except OSError:
        log_fh.close()
        return None, None, None, None
    log_fh.close()

    deadline = time.monotonic() + max(0.1, float(ready_timeout))
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            return None, None, None, None
        remaining = deadline - time.monotonic()
        if _ready(ready_url, timeout=min(2.0, max(0.2, remaining))):
            lstart = pid_lstart(proc.pid)
            if lstart:
                return proc.pid, lstart, port, url
            break
        time.sleep(0.1)

    _terminate_child(proc)
    return None, None, None, None


def _run_build(build_command: str, root: str) -> int:
    argv = shlex.split(build_command)
    try:
        p = subprocess.run(argv, cwd=root, capture_output=True, text=True)
        return p.returncode
    except FileNotFoundError:
        return 127


def ensure_server(cfg: dict, root: str) -> tuple[int, str | None]:
    fast = cfg.get("fast")
    if not isinstance(fast, dict) or not fast:
        print("SERVE: FAIL no fast block in config")
        return 1, None
    serve_cmd = fast.get("serve_command")
    if not serve_cmd:
        print("SERVE: FAIL missing serve_command in config")
        return 1, None

    state_dir = fast.get("state_dir") or DEFAULT_STATE_DIR
    ready_path = fast.get("ready_path") or "/"
    if not ready_path.startswith("/"):
        ready_path = "/" + ready_path
    ready_timeout = fast.get("ready_timeout")
    if ready_timeout is None:
        ready_timeout = DEFAULT_READY_TIMEOUT
    build_cmd = fast.get("build_command") or ""
    fp = fingerprint(root, fast.get("fingerprint") or [])

    sp = state_path(state_dir, root)
    state = load_state(sp)
    alive = is_ours(state)

    if alive and state.get("fingerprint") == fp:
        url = state.get("url") or ""
        if url and _ready(url + ready_path):
            print(f"SERVE: reuse pid={state['pid']} url={url}")
            return 0, url
        stop_pid(state["pid"], state["lstart"])
        _remove_file(sp)
    elif alive:
        stop_pid(state["pid"], state["lstart"])
        _remove_file(sp)

    built_fp = state.get("built_fingerprint") if isinstance(state, dict) else None
    if build_cmd and built_fp != fp:
        code = _run_build(build_cmd, root)
        if code != 0:
            print(f"SERVE: FAIL build exit {code}")
            return 1, None
        build_status = "ran"
    else:
        build_status = "reused"

    pid, lstart, port, url = start_server(
        serve_cmd,
        ready_path,
        root,
        _log_path(state_dir, root),
        ready_timeout=ready_timeout,
    )
    if pid is None:
        print("SERVE: FAIL not ready")
        return 1, None

    save_state(sp, {
        "pid": pid,
        "lstart": lstart,
        "port": port,
        "url": url,
        "fingerprint": fp,
        "built_fingerprint": fp,
    })
    print(f"SERVE: started pid={pid} url={url} build={build_status}")
    return 0, url


def cmd_serve(cfg: dict, root: str) -> int:
    code, _ = ensure_server(cfg, root)
    return code


def cmd_stop(cfg: dict, root: str) -> int:
    fast = cfg.get("fast") if isinstance(cfg.get("fast"), dict) else {}
    state_dir = fast.get("state_dir") or DEFAULT_STATE_DIR
    sp = state_path(state_dir, root)
    state = load_state(sp)
    if state is not None and is_ours(state):
        pid = state["pid"]
        stop_pid(pid, state["lstart"])
        _remove_file(sp)
        print(f"STOP: stopped pid={pid}")
        return 0
    _remove_file(sp)
    print("STOP: nothing running")
    return 0


def _find_screenshots(directory: str) -> list[str]:
    found: list[str] = []
    if not os.path.isdir(directory):
        return found
    for dirpath, subdirs, files in os.walk(directory):
        subdirs.sort()
        for fname in sorted(files):
            if os.path.splitext(fname)[1].lower() in IMAGE_EXTS:
                found.append(os.path.join(dirpath, fname))
    found.sort()
    return found


def _tail_lines(path: str, limit: int = 15) -> list[str]:
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            lines = f.read().splitlines()
    except OSError:
        return []
    return lines[-limit:] if limit > 0 else []


def _resolve_evidence_dir(cfg: dict, override: str | None) -> str:
    if override:
        return os.path.abspath(os.path.expanduser(override))
    base = os.path.expanduser(cfg.get("evidence_dir") or DEFAULT_EVIDENCE_DIR)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    return os.path.abspath(os.path.join(base, f"{stamp}-fastpass"))


def _run_journey(
    journey: dict,
    root: str,
    url: str,
    evidence_dir: str,
    headed: bool,
    timeout: float,
) -> tuple[bool, bool, int | None, float, str, str]:
    name = journey["name"]
    cmd = journey.get("command") or ""
    argv = shlex.split(cmd)
    j_ev_dir = os.path.join(evidence_dir, name)
    os.makedirs(j_ev_dir, exist_ok=True)
    log_file = os.path.join(j_ev_dir, "journey.log")

    env = os.environ.copy()
    env["BASE_URL"] = url
    env["EVIDENCE_DIR"] = j_ev_dir
    env["JOURNEY"] = name
    env["HEADLESS"] = "0" if headed else "1"

    t0 = time.monotonic()
    timed_out = False
    exit_code: int | None = None

    with open(log_file, "wb") as log_fh:
        if not argv:
            log_fh.write(b"Empty journey command\n")
            exit_code = 127
        else:
            try:
                proc = subprocess.Popen(
                    argv,
                    cwd=root,
                    env=env,
                    stdin=subprocess.DEVNULL,
                    stdout=log_fh,
                    stderr=subprocess.STDOUT,
                    start_new_session=True,
                )
            except OSError as e:
                log_fh.write(f"Failed to start command: {e}\n".encode("utf-8"))
                exit_code = 127
            else:
                try:
                    exit_code = proc.wait(timeout=timeout)
                except subprocess.TimeoutExpired:
                    timed_out = True
                    _terminate_child(proc)
                    exit_code = None

    elapsed = time.monotonic() - t0
    passed = (not timed_out) and exit_code == 0
    return passed, timed_out, exit_code, elapsed, j_ev_dir, log_file


def cmd_run(cfg: dict, root: str, args: argparse.Namespace) -> int:
    run_start = time.monotonic()
    journeys = cfg.get("journeys") or []
    ignore = cfg.get("journey_ignore") or []

    if not journeys:
        print("SELECT: none (no journeys configured)")
        return 1

    if args.run_all:
        chosen = [j["name"] for j in journeys]
        print("SELECT: all (--all)")
    else:
        paths = args.paths if args.paths is not None else changed_paths_from_git(root, args.base)
        mode, chosen, reason = select_journeys(journeys, ignore, paths)
        if mode == "none":
            print(f"SELECT: none ({reason})")
            return 1
        if mode == "mapped":
            print(f"SELECT: mapped {', '.join(chosen)}")
        else:
            print(f"SELECT: all ({reason})")

    serve_code, url = ensure_server(cfg, root)
    if serve_code != 0 or not url:
        return 1

    fast = cfg.get("fast") if isinstance(cfg.get("fast"), dict) else {}
    journey_timeout = fast.get("journey_timeout")
    if journey_timeout is None:
        journey_timeout = DEFAULT_JOURNEY_TIMEOUT
    timeout = max(0.1, float(journey_timeout))

    evidence_dir = _resolve_evidence_dir(cfg, args.evidence_dir)
    os.makedirs(evidence_dir, exist_ok=True)

    by_name = {j["name"]: j for j in journeys}
    results = []
    failed = 0

    for name in chosen:
        passed, timed_out, exit_code, elapsed, j_ev_dir, log_file = _run_journey(
            by_name[name],
            root,
            url,
            evidence_dir,
            args.headed,
            timeout,
        )
        results.append({
            "journey": name,
            "status": "PASS" if passed else "FAIL",
            "seconds": round(elapsed, 3),
            "exit": "timeout" if timed_out else exit_code,
        })
        if passed:
            print(f"{name}: PASS ({elapsed:.1f}s)")
        else:
            failed += 1
            if timed_out:
                print(f"{name}: FAIL (timeout, {elapsed:.1f}s)")
            else:
                print(f"{name}: FAIL (exit {exit_code}, {elapsed:.1f}s)")
            for shot in _find_screenshots(j_ev_dir):
                print(f"  screenshot: {shot}")
            print(f"  log: {log_file}")
            for line in _tail_lines(log_file, 15):
                print(f"    {line}")

    results_path = os.path.join(evidence_dir, "results.json")
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
        f.write("\n")

    total = len(chosen)
    total_elapsed = time.monotonic() - run_start
    if failed == 0:
        print(f"FASTPASS: OK {total} passed in {total_elapsed:.1f}s")
        return 0
    print(f"FASTPASS: FAIL {failed} of {total} failed in {total_elapsed:.1f}s")
    return 1


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--config", default=None, help="path to verify-web config")
    ap.add_argument("--root", default=None, help="worktree root directory")

    # SUPPRESS lets subcommand flags override top-level defaults without clobbering them.
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--config", default=argparse.SUPPRESS, help="path to verify-web config")
    common.add_argument("--root", default=argparse.SUPPRESS, help="worktree root directory")

    sub = ap.add_subparsers(dest="command", required=True)

    p_select = sub.add_parser("select", parents=[common], help="choose journeys for changed paths")
    p_select.add_argument("--paths", nargs="*", default=None, help="changed paths relative to root")
    p_select.add_argument("--base", default="origin/main", help="git base ref (default: origin/main)")

    sub.add_parser("serve", parents=[common], help="start or reuse the test server")
    sub.add_parser("stop", parents=[common], help="stop the test server")

    p_run = sub.add_parser("run", parents=[common], help="select, serve, and run journeys")
    p_run.add_argument("--paths", nargs="*", default=None, help="changed paths relative to root")
    p_run.add_argument("--base", default="origin/main", help="git base ref (default: origin/main)")
    p_run.add_argument("--all", action="store_true", dest="run_all", help="run all configured journeys")
    p_run.add_argument("--evidence-dir", default=None, help="directory for logs, screenshots, and results")
    p_run.add_argument("--headed", action="store_true", help="run journeys with HEADLESS=0")
    return ap


def main(argv=None) -> int:
    ap = build_parser()
    args = ap.parse_args(argv)

    label = args.command.upper()
    cfg_path = args.config or doctor.find_config(args.root or os.getcwd())
    if not cfg_path or not os.path.isfile(cfg_path):
        print(f"{label}: FAIL no config found")
        return 1
    try:
        cfg = doctor.load_config(cfg_path)
    except (OSError, ValueError) as e:
        print(f"{label}: FAIL {cfg_path}: {e}")
        return 1

    root = os.path.abspath(args.root) if args.root else doctor.project_root(cfg_path)
    if args.command == "select":
        return cmd_select(cfg or {}, root, args)
    if args.command == "serve":
        return cmd_serve(cfg or {}, root)
    if args.command == "stop":
        return cmd_stop(cfg or {}, root)
    if args.command == "run":
        return cmd_run(cfg or {}, root, args)
    return 2


if __name__ == "__main__":
    sys.exit(main())
