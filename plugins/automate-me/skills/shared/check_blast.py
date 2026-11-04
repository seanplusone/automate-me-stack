"""Shared blast-radius check for automate-me. Checks a blast-radius or current-state list against the code.

Usage: python3 check_blast.py <repo[,repo...]> <blast.txt or current.txt>

Every BR or CS line must name a file:line that exists in one of the repos, with its quoted code on that line.
Prints PASS or FAIL and each failure. Exits 1 on FAIL.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_writing import FAILED, norm, report  # noqa: E402


def resolve(roots, path):
    for r in roots.split(","):
        full = os.path.join(r, path)
        if os.path.isfile(full):
            return full
    return None


def check_blast(roots, blast_path):
    """roots is a comma-separated list of repo paths. A file must exist in one of them."""
    fails = []
    ids = []
    n = 0
    for raw in open(blast_path):
        s = raw.strip()
        m = re.match(r"^(HOOK|SCOPE|WRITER|READER|STEP)\s+((?:BR|CS)\d+):\s*(.*)$", s)
        if m:
            n += 1
            ids.append(m.group(2))
            parts = [p.strip() for p in m.group(3).split("|")]
            loc = next((p for p in parts if re.match(r"^[^\s]+:\d+$", p)), None)
            quote = next((p for p in parts if p.startswith('"')), None)
            if not loc or not quote:
                fails.append(f"{m.group(2)} needs file:line and a quoted line")
                continue
            path, line = loc.rsplit(":", 1)
            full = resolve(roots, path)
            if not full:
                fails.append(f"{m.group(2)} file not found in {roots}: {path}")
                continue
            lines = open(full, errors="replace").read().split("\n")
            i = int(line) - 1
            if i < 0 or i >= len(lines):
                fails.append(f"{m.group(2)} line {line} out of range in {path}")
                continue
            q = norm(quote.strip('"'))
            window = norm(" ".join(lines[max(0, i - 1):i + 2]))
            if q not in window:
                fails.append(f"{m.group(2)} quote not on {loc}")
        elif s.startswith("CHAIN:") or s.startswith("ENTITY:"):
            path = s.split("|")[-1].strip()
            if not resolve(roots, path):
                fails.append(f"chain file not found in {roots}: {path}")
    dupes = sorted({i for i in ids if ids.count(i) > 1})
    if dupes:
        fails.append(f"duplicate ids: {dupes}")
    report(f"{'current' if any(i.startswith('CS') for i in ids) else 'blast'}: {n} items checked", fails)


if __name__ == "__main__":
    check_blast(*sys.argv[1:])
    sys.exit(1 if FAILED else 0)
