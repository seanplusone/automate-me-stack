"""Scores one JUDGE-mode output against a case key.

Usage: python3 score_judge.py <key.md> <scenario> <output.txt> <case dir>

A key row is `| <id> | <scenario> | HOLDS or FAILS | <step or -> | <path prefixes or -> | <why> |`.
HOLDS needs at least one SHAPE line and no FAILS. FAILS needs a SHAPE FAILS that names the step
and cites a file:line under one of the prefixes. Every file:line in a SHAPE's last field, its citation,
must exist in <case dir>/repo or be added by <case dir>/inputs/<scenario>.diff. Whether the picked shape is right is still scored
by a person. Prints PASS or FAIL and exits 1 on FAIL.
"""
import os
import re
import sys

ROW = re.compile(r"^\| (K\d+) \| ([\w-]+) \| (HOLDS|FAILS) \| (\d+|-) \| ([^|]+) \| [^|]* \|$")
SHAPE = re.compile(r"^SHAPE (A\d+):\s*(HOLDS|FAILS)\b(.*)$")
CITE = re.compile(r"(?:repo/)?([\w./-]+\.\w+):(\d+)")


def lines_after_diff(diff_path):
    """Line counts of every file as the diff leaves it, for files the diff adds or changes."""
    sizes, path = {}, None
    for line in open(diff_path):
        if line.startswith("+++ b/"):
            path = line[6:].strip()
        elif line.startswith("@@") and path:
            start, _, count = re.search(r"\+(\d+)(,(\d+))?", line).groups()
            sizes[path] = max(sizes.get(path, 0), int(start) + int(count or 1) - 1)
    return sizes


def cite_exists(case_dir, after, path, line):
    full = os.path.join(case_dir, "repo", path)
    n = len(open(full).read().split("\n")) if os.path.isfile(full) else 0
    return 1 <= line <= max(n, after.get(path, 0))


def score(key_path, scenario, output_path, case_dir):
    rows = [ROW.match(l.strip()).groups() for l in open(key_path) if ROW.match(l.strip())]
    rows = [r for r in rows if r[1] == scenario]
    shapes = [SHAPE.match(l.strip()).groups() for l in open(output_path) if SHAPE.match(l.strip())]
    after = lines_after_diff(os.path.join(case_dir, "inputs", f"{scenario}.diff"))
    fails = []
    if not rows:
        fails.append(f"no key row for {scenario}")
    if not shapes:
        fails.append("no SHAPE lines")
    for aid, _, rest in shapes:
        for path, line in CITE.findall(rest.rsplit("|", 1)[-1]):
            if not cite_exists(case_dir, after, path, int(line)):
                fails.append(f"{aid} cites {path}:{line}, which is not in the repo or the diff")
    for kid, _, verdict, step, prefixes in rows:
        if verdict == "HOLDS":
            failed = [aid for aid, v, _ in shapes if v == "FAILS"]
            if failed:
                fails.append(f"{kid} wants HOLDS, got FAILS on {', '.join(failed)}")
            continue
        wanted = [p.strip(" `") for p in prefixes.split(",")]
        hit = [aid for aid, v, rest in shapes if v == "FAILS"
               and re.search(rf"\bstep\s*{step}\b", rest, re.I)
               and any(path.startswith(w) for path, _ in CITE.findall(rest) for w in wanted)]
        if not hit:
            fails.append(f"{kid} wants FAILS at step {step} citing one of {', '.join(wanted)}")
    print(f"{'FAIL' if fails else 'PASS'} judge {scenario}: {len(shapes)} shapes")
    for f in fails:
        print(f"  {f}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(score(*sys.argv[1:]))
