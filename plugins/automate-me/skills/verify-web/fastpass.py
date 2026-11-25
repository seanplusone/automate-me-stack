#!/usr/bin/env python3
"""Fast local verification runner for verify-web. Python stdlib only.

Usage:
  python3 fastpass.py select [--config <file>] [--root <dir>] [--paths <p> ...] [--base <ref>]
  python3 fastpass.py serve  [--config <file>] [--root <dir>]
  python3 fastpass.py stop   [--config <file>] [--root <dir>]
  python3 fastpass.py run    [--config <file>] [--root <dir>]

The config is the first of .claude/verify-web.yaml, .claude/verify-web.yml or .claude/verify-web.json
found from the root or current directory upward, unless --config names one.
"""
import argparse
import os
import re
import subprocess
import sys

SKILL_DIR = os.path.dirname(os.path.abspath(__file__))
if SKILL_DIR not in sys.path:
    sys.path.insert(0, SKILL_DIR)

import doctor


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
    sub.add_parser("run", parents=[common], help="select, serve, and run journeys")
    return ap


def main(argv=None) -> int:
    ap = build_parser()
    args = ap.parse_args(argv)
    if args.command in ("serve", "stop", "run"):
        print(f"{args.command}: not built yet")
        return 2

    cfg_path = args.config or doctor.find_config(args.root or os.getcwd())
    if not cfg_path or not os.path.isfile(cfg_path):
        print("SELECT: FAIL no config found")
        return 1
    try:
        cfg = doctor.load_config(cfg_path)
    except (OSError, ValueError) as e:
        print(f"SELECT: FAIL {cfg_path}: {e}")
        return 1

    root = os.path.abspath(args.root) if args.root else doctor.project_root(cfg_path)
    return cmd_select(cfg or {}, root, args)


if __name__ == "__main__":
    sys.exit(main())
