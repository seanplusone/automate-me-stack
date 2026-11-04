"""Measures a change against the review-size thresholds, and checks a split plan against it.

Usage, run inside the repo:
  python3 size.py <base> <head> [--exclude GLOB ...]
  python3 size.py <base> <head> --plan plan.tsv [--exclude GLOB ...]

A plan is one `<slice>\t<path>` line per file, slices in merge order.
Plan mode exits 1 if any check fails.
"""
import argparse
import fnmatch
import subprocess
import sys
from collections import OrderedDict

# metric: (consider splitting at, split at)
THRESHOLDS = OrderedDict([
    ("lines added", (800, 1200)),
    ("files", (20, 30)),
    ("new files", (10, 15)),
])
VERDICTS = ["review as one", "consider splitting", "split"]


def git(*args):
    return subprocess.run(["git", *args], check=True, capture_output=True, text=True).stdout


def changes(base, head, excludes):
    """Return {path: [status, adds, dels]} for base...head, renames keyed by the new path."""
    out = {}
    tokens = git("diff", "-z", "-M", "--name-status", f"{base}...{head}").split("\0")
    i = 0
    while i < len(tokens) - 1:
        status = tokens[i][0]
        if status in "RC":
            path, i = tokens[i + 2], i + 3
        else:
            path, i = tokens[i + 1], i + 2
        out[path] = [status, 0, 0]
    tokens = git("diff", "-z", "-M", "--numstat", f"{base}...{head}").split("\0")
    i = 0
    while i < len(tokens) - 1:
        adds, dels, path = tokens[i].split("\t")
        if path == "":
            path, i = tokens[i + 2], i + 3
        else:
            i += 1
        if path in out and adds != "-":
            out[path][1:] = [int(adds), int(dels)]
    return {p: c for p, c in out.items() if not any(fnmatch.fnmatch(p, g) for g in excludes)}


def measure(chg):
    return OrderedDict([
        ("lines added", sum(c[1] for c in chg.values())),
        ("files", len(chg)),
        ("new files", sum(1 for c in chg.values() if c[0] == "A")),
    ])


def verdict(metrics):
    level, why = 0, []
    for name, (consider, split) in THRESHOLDS.items():
        v = metrics[name]
        hit = 2 if v > split else 1 if v >= consider else 0
        if hit:
            why.append(f"{name} {v} > {split}" if hit == 2 else f"{name} {v} >= {consider}")
        level = max(level, hit)
    return VERDICTS[level], why


def size_line(metrics):
    return ", ".join(f"{k} {v}" for k, v in metrics.items())


def report(base, head, chg):
    m = measure(chg)
    v, why = verdict(m)
    print(f"range: {base}...{head}")
    print(f"size: {size_line(m)}, lines removed {sum(c[2] for c in chg.values())}")
    groups = OrderedDict()
    for p in sorted(chg):
        key = "/".join(p.split("/")[:-1][:2]) or "."
        g = groups.setdefault(key, [0, 0])
        g[0] += 1
        g[1] += chg[p][1]
    for key, (n, adds) in sorted(groups.items(), key=lambda kv: -kv[1][1]):
        print(f"  {key}: {n} files, +{adds}")
    print(f"verdict: {v}" + (f" ({'; '.join(why)})" if why else ""))


def base_drift(base, head, paths):
    """Files the slices carry that base changed after head branched. Slicing would revert them."""
    if subprocess.run(["git", "merge-base", "--is-ancestor", base, head]).returncode == 0:
        return []
    newer = set(git("diff", "--name-only", f"{head}...{base}").split())
    return sorted(newer & set(paths))


def check_plan(base, head, chg, plan_path):
    fails = []
    slices = OrderedDict()
    seen = {}
    with open(plan_path) as f:
        for n, line in enumerate(f, 1):
            line = line.rstrip("\n")
            if not line.strip() or line.startswith("#"):
                continue
            if "\t" not in line:
                fails.append(f"line {n} is not <slice>\\t<path>")
                continue
            name, path = line.split("\t", 1)
            if path in seen:
                fails.append(f"{path} is in slice {seen[path]} and slice {name}")
            seen[path] = name
            slices.setdefault(name, []).append(path)
    if not chg:
        fails.append("the diff is empty, so there is nothing to check the plan against")
    if not slices:
        fails.append("the plan is empty")
    for p in sorted(set(chg) - set(seen)):
        fails.append(f"{p} is in the diff but in no slice")
    for p in sorted(set(seen) - set(chg)):
        fails.append(f"{p} is in a slice but not in the diff")
    for p in base_drift(base, head, seen):
        fails.append(f"{p} changed on {base} after {head} branched; merge {base} in before slicing")
    for name, paths in slices.items():
        m = measure({p: chg[p] for p in paths if p in chg})
        v, why = verdict(m)
        print(f"slice {name}: {size_line(m)}, {v}" + (f" ({'; '.join(why)})" if why else ""))
    for f in fails:
        print(f"FAIL {f}")
    print("PASS plan" if not fails else f"{len(fails)} failed")
    return not fails


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("base")
    ap.add_argument("head")
    ap.add_argument("--exclude", action="append", default=[])
    ap.add_argument("--plan")
    a = ap.parse_args()
    chg = changes(a.base, a.head, a.exclude)
    report(a.base, a.head, chg)
    drift = base_drift(a.base, a.head, chg)
    if drift and not a.plan:
        print(f"note: {len(drift)} changed files also changed on {a.base} since {a.head} branched")
    if a.plan:
        sys.exit(0 if check_plan(a.base, a.head, chg, a.plan) else 1)


if __name__ == "__main__":
    main()
